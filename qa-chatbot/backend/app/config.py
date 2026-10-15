"""Application Configuration Module.

Loads and validates environment variables using Pydantic Settings.
Centralizes all runtime parameters for the backend, Groq AI provider,
and conversation guardrails.
"""

from functools import lru_cache
import logging
import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Central configuration class backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Groq AI Provider Configuration
    # --------------------------------------------------------------------------
    GROQ_API_KEY: str = Field(
        default="",
        description="Groq API key for authenticating with Groq Cloud.",
    )
    GROQ_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="Model ID configured for Groq inference (e.g. openai/gpt-oss-120b, llama-3.3-70b-versatile).",
    )
    REASONING_EFFORT: Literal["none", "low", "medium", "high"] | None = Field(
        default=None,
        description="Optional reasoning effort for OpenAI reasoning models like openai/gpt-oss-120b.",
    )

    # --------------------------------------------------------------------------
    # Application & Server Configuration
    # --------------------------------------------------------------------------
    APP_ENV: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        description="Runtime environment.",
    )
    APP_HOST: str = Field(
        default="0.0.0.0",
        description="Host interface for the ASGI server.",
    )
    APP_PORT: int = Field(
        default=8000,
        description="Listening port for the ASGI server.",
    )
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins. Configured for same-origin or reverse-proxy by default.",
    )

    # --------------------------------------------------------------------------
    # LLM Inference Parameters
    # --------------------------------------------------------------------------
    LLM_TEMPERATURE: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="LLM generation temperature (0.0=deterministic, 2.0=creative).",
    )
    LLM_MAX_TOKENS: int = Field(
        default=1024,
        gt=0,
        le=8192,
        description="Maximum generation output token limit.",
    )
    LLM_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        gt=0.0,
        le=300.0,
        description="Request timeout in seconds for Groq API calls.",
    )

    # --------------------------------------------------------------------------
    # Conversation and Input Guardrails
    # --------------------------------------------------------------------------
    MAX_MESSAGE_LENGTH: int = Field(
        default=4000,
        gt=0,
        le=32000,
        description="Maximum allowed character length for a single user message.",
    )
    MAX_HISTORY_TURNS: int = Field(
        default=10,
        gt=0,
        le=100,
        description="Maximum conversation turns (user+assistant pairs) to preserve in context.",
    )

    # --------------------------------------------------------------------------
    # LangSmith Observability & Tracing Configuration
    # --------------------------------------------------------------------------
    LANGSMITH_TRACING: bool = Field(
        default=False,
        description="Enable LangSmith tracing for LangChain pipeline.",
    )
    LANGSMITH_API_KEY: str = Field(
        default="",
        description="LangSmith API key for authenticating with LangSmith Cloud.",
    )
    LANGSMITH_PROJECT: str = Field(
        default="qa-chatbot-local",
        description="LangSmith project name for organizing trace sessions.",
    )
    LANGSMITH_ENDPOINT: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith API endpoint.",
    )

    @field_validator("GROQ_MODEL", mode="before")
    @classmethod
    def validate_groq_model(cls, v: str) -> str:
        """Ensure model identifier is non-empty string."""
        if not v or not v.strip():
            raise ValueError("GROQ_MODEL must be a non-empty string")
        return v.strip()

    @property
    def is_api_key_configured(self) -> bool:
        """Check whether a non-dummy Groq API key is present."""
        if not self.GROQ_API_KEY:
            return False
        clean = self.GROQ_API_KEY.strip()
        if clean in ("", "gsk_your_groq_api_key_here"):
            return False
        return True

    @property
    def is_langsmith_configured(self) -> bool:
        """Check whether LangSmith tracing is enabled with a valid API key."""
        if not self.LANGSMITH_TRACING:
            return False
        clean = self.LANGSMITH_API_KEY.strip()
        if not clean or clean in ("", "lsv2_pt_your_langsmith_api_key_here"):
            return False
        return True

    @property
    def masked_groq_api_key(self) -> str:
        """Return masked version of the API key for safe logging."""
        if not self.GROQ_API_KEY:
            return "<UNSET>"
        key = self.GROQ_API_KEY.strip()
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    @property
    def masked_langsmith_api_key(self) -> str:
        """Return masked version of the LangSmith API key for safe logging."""
        if not self.LANGSMITH_API_KEY:
            return "<UNSET>"
        key = self.LANGSMITH_API_KEY.strip()
        if len(key) <= 8:
            return "***"
        return f"{key[:7]}...{key[-4:]}"


def setup_langsmith_tracing(settings: Settings) -> bool:
    """Configure environment variables for LangSmith and LangChain tracing.

    Synchronizes Pydantic settings with process environment variables so that
    LangChain's automatic tracer and the LangSmith SDK can seamlessly capture runs.

    Returns:
        bool: True if LangSmith tracing is enabled and configured with an API key, False otherwise.
    """
    if not settings.LANGSMITH_TRACING:
        # Explicitly turn off tracing flags in the environment
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("LangSmith tracing is disabled (LANGSMITH_TRACING=false).")
        return False

    if not settings.is_langsmith_configured:
        # Tracing requested but key is missing or dummy placeholder
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.warning(
            "LangSmith tracing was requested (LANGSMITH_TRACING=true), but LANGSMITH_API_KEY "
            "is not set or has the placeholder value. Tracing has been disabled to prevent "
            "authentication errors. Add a valid API key from https://smith.langchain.com to enable."
        )
        return False

    # Sync to standard environment variables for LangSmith / LangChain SDK
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY.strip()
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY.strip()
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT.strip()
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT.strip()
    if settings.LANGSMITH_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT.strip()
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT.strip()

    logger.info(
        "LangSmith tracing ACTIVE: Project='%s', Endpoint='%s', Key='%s'",
        settings.LANGSMITH_PROJECT,
        settings.LANGSMITH_ENDPOINT,
        settings.masked_langsmith_api_key,
    )
    return True


def validate_startup_config(settings: Settings) -> None:
    """Validate critical configuration settings at application startup.

    Raises:
        RuntimeError: If critical configuration is invalid or missing in production.
    """
    logger.info("Initializing configuration check for environment: %s", settings.APP_ENV)
    logger.info("Configured Groq model: %s", settings.GROQ_MODEL)
    logger.info("Groq API key status: %s", settings.masked_groq_api_key)

    # Initialize LangSmith tracing environment variables
    setup_langsmith_tracing(settings)

    # In test mode, we permit unconfigured keys if mocked
    if settings.APP_ENV == "test":
        logger.info("Running in test mode. API key presence check relaxed.")
        return

    if not settings.is_api_key_configured:
        msg = (
            "Configuration Error: GROQ_API_KEY is not set or contains the default placeholder. "
            "Please obtain an API key from https://console.groq.com/keys and set GROQ_API_KEY "
            "in your .env file or environment variables."
        )
        logger.error(msg)
        if settings.APP_ENV in ("production", "staging"):
            raise RuntimeError(msg)
        else:
            logger.warning(
                "Backend started with missing or placeholder GROQ_API_KEY. "
                "Chat endpoint will reject requests until a valid key is provided."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    settings = Settings()
    setup_langsmith_tracing(settings)
    return settings
