"""Groq LLM Service using LangChain.

Handles interaction with the Groq API via langchain-groq, prompt orchestration,
multi-turn message construction, token usage extraction, and error translation.
Designed with clean abstraction seams for seamless future integration with
OpenTelemetry, Prometheus, and LangSmith.
"""

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Annotated, Sequence

from fastapi import Depends
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langsmith import traceable

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# System prompt defining the persona, accuracy, and tone of the assistant
SYSTEM_PROMPT = (
    "You are a helpful, professional, and knowledgeable AI assistant. "
    "Provide accurate, clear, and concise answers to the user's questions. "
    "If you do not know the answer, acknowledge it honestly. "
    "Format code snippets using standard markdown code blocks with language identifiers."
)


# ------------------------------------------------------------------------------
# Domain-Specific LLM Exceptions
# ------------------------------------------------------------------------------
class LLMServiceError(Exception):
    """Base exception for all LLM service failures."""


class LLMAuthError(LLMServiceError):
    """Raised when authentication with the AI provider fails."""


class LLMRateLimitError(LLMServiceError):
    """Raised when the AI provider returns a rate limit or quota exceeded status."""


class LLMTimeoutError(LLMServiceError):
    """Raised when the request to the AI provider exceeds the configured timeout."""


class LLMProviderError(LLMServiceError):
    """Raised when the AI provider returns an unexpected server or communication error."""


# ------------------------------------------------------------------------------
# LLM Result Container (Prepared for Future Observability/Cost Tracking)
# ------------------------------------------------------------------------------
@dataclass
class LLMResult:
    """Internal result payload containing generated response and telemetry metadata."""

    answer: str
    model: str
    token_usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0


class LLMService:
    """Encapsulates LangChain orchestration with ChatGroq."""

    def __init__(self, settings: Settings) -> None:
        """Initialize LLM service with application settings.

        Args:
            settings: Validated application configuration.
        """
        self.settings = settings
        self.model_name = settings.GROQ_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout_seconds = settings.LLM_TIMEOUT_SECONDS

        self._client: ChatGroq | None = None
        logger.info(
            "LLMService configured for model: %s (temp=%.2f, max_tokens=%d, timeout=%.1fs)",
            self.model_name,
            self.temperature,
            self.max_tokens,
            self.timeout_seconds,
        )

    def _get_client(self) -> ChatGroq:
        """Lazily initialize and return the ChatGroq client.

        Raises:
            LLMAuthError: If GROQ_API_KEY is missing or invalid.
        """
        if self._client is not None:
            return self._client

        if not self.settings.is_api_key_configured:
            logger.error("Attempted to initialize ChatGroq without a valid GROQ_API_KEY.")
            raise LLMAuthError(
                "Groq API key is not configured. Please set GROQ_API_KEY in the environment."
            )

        try:
            client_kwargs = {
                "groq_api_key": self.settings.GROQ_API_KEY,
                "model_name": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout": self.timeout_seconds,
                "max_retries": 1,
            }
            # Pass reasoning_effort for OpenAI reasoning models like openai/gpt-oss-120b
            if self.settings.REASONING_EFFORT:
                if hasattr(ChatGroq, "model_fields") and "reasoning_effort" in ChatGroq.model_fields:
                    client_kwargs["reasoning_effort"] = self.settings.REASONING_EFFORT
                else:
                    client_kwargs["model_kwargs"] = {"reasoning_effort": self.settings.REASONING_EFFORT}
                logger.info(
                    "Configured reasoning_effort='%s' for model %s",
                    self.settings.REASONING_EFFORT,
                    self.model_name,
                )

            self._client = ChatGroq(**client_kwargs)
            return self._client
        except Exception as exc:
            logger.error("Failed to instantiate ChatGroq client: %s", str(exc))
            raise LLMProviderError("Failed to initialize AI provider client.") from exc

    def build_prompt_messages(
        self,
        user_message: str,
        history: Sequence[BaseMessage] | None = None,
    ) -> list[BaseMessage]:
        """Construct the complete message sequence for model invocation.

        Order:
        1. SystemMessage (core instruction)
        2. Prior conversation history (HumanMessage and AIMessage turns)
        3. Current HumanMessage

        Args:
            user_message: The active user query.
            history: Optional sequence of prior dialogue messages.

        Returns:
            List of BaseMessage objects ready for the chat model.
        """
        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

        if history:
            messages.extend(history)

        messages.append(HumanMessage(content=user_message))
        return messages

    @traceable(
        name="qa_chatbot_generate_response",
        run_type="chain",
        tags=["qa-chatbot", "llm-turn"],
    )
    async def generate_response(
        self,
        session_id: str,
        user_message: str,
        history: Sequence[BaseMessage] | None = None,
    ) -> LLMResult:
        """Asynchronously invoke Groq through LangChain with error handling and timing.

        Args:
            session_id: Session identifier (used for logging and telemetry context).
            user_message: Validated user query.
            history: Prior turns from conversation history.

        Returns:
            LLMResult containing the answer, model ID, token usage, and latency.

        Raises:
            LLMAuthError: Authentication or credentials failure.
            LLMRateLimitError: Rate limit exceeded.
            LLMTimeoutError: Request exceeded configured timeout.
            LLMProviderError: General provider failure.
        """
        client = self._get_client()
        messages = self.build_prompt_messages(user_message, history)

        start_time = time.perf_counter()
        logger.info(
            "Invoking model %s for session %s with %d total messages",
            self.model_name,
            session_id,
            len(messages),
        )

        try:
            # LangChain async invocation with telemetry metadata and tags
            run_config = {
                "run_name": f"ChatGroq-{self.model_name}",
                "tags": ["qa-chatbot", self.settings.APP_ENV, "groq"],
                "metadata": {
                    "session_id": session_id,
                    "model": self.model_name,
                    "temperature": self.temperature,
                },
            }
            response: AIMessage = await client.ainvoke(messages, config=run_config)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Extract generated content safely
            if isinstance(response.content, str):
                answer_text = response.content
            elif isinstance(response.content, list):
                # In multimodal or complex outputs, concatenate text chunks
                answer_text = "".join(
                    str(chunk.get("text", chunk) if isinstance(chunk, dict) else chunk)
                    for chunk in response.content
                )
            else:
                answer_text = str(response.content)

            # Extract token usage metadata if available (future cost telemetry seam)
            token_usage: dict[str, int] = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                token_usage = {
                    k: int(v) for k, v in response.usage_metadata.items() if isinstance(v, (int, float))
                }
            elif hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
                raw_usage = response.response_metadata.get("token_usage", {})
                if isinstance(raw_usage, dict):
                    token_usage = {
                        k: int(v) for k, v in raw_usage.items() if isinstance(v, (int, float))
                    }

            logger.info(
                "Model response generated for session %s in %.2f ms. Tokens: %s",
                session_id,
                elapsed_ms,
                token_usage or "N/A",
            )

            return LLMResult(
                answer=answer_text,
                model=self.model_name,
                token_usage=token_usage,
                latency_ms=elapsed_ms,
            )

        except asyncio.TimeoutError as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("LLM timeout after %.2f ms for session %s: %s", elapsed_ms, session_id, exc)
            raise LLMTimeoutError(
                f"The AI provider request timed out after {self.timeout_seconds} seconds."
            ) from exc

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_str = str(exc).lower()

            logger.error(
                "Error during model invocation for session %s after %.2f ms: %s",
                session_id,
                elapsed_ms,
                exc.__class__.__name__,
            )

            # Classify known provider errors without exposing raw internal details
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                raise LLMRateLimitError(
                    "AI provider rate limit reached. Please wait a moment and try again."
                ) from exc

            if "auth" in error_str or "unauthorized" in error_str or "401" in error_str or "api_key" in error_str:
                raise LLMAuthError(
                    "AI provider authentication failed. Verify GROQ_API_KEY."
                ) from exc

            if "timeout" in error_str or "timed out" in error_str or "504" in error_str:
                raise LLMTimeoutError(
                    "AI provider communication timed out."
                ) from exc

            # Generic provider failure
            raise LLMProviderError(
                "An unexpected error occurred while communicating with the AI service."
            ) from exc


# Global singleton instance for the service lifecycle within the process
_llm_service_instance: LLMService | None = None


def get_llm_service() -> LLMService:
    """Dependency provider for LLMService."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService(settings=get_settings())
    return _llm_service_instance
