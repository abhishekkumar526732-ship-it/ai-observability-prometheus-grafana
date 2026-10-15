"""Chat and Health API Endpoints.

Provides:
- POST /api/chat: Multi-turn Q&A chat endpoint orchestrated with Groq via LangChain.
- GET /api/health: Basic service liveness health check.
- GET /api/ready: Configuration readiness check without external API calls.
- DELETE /api/chat/session/{session_id}: Reset conversation history for a given session.
"""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status

from app.config import Settings, get_settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ReadyResponse,
)
from app.services.conversation_service import (
    ConversationService,
    get_conversation_service,
)
from app.services.llm_service import (
    LLMAuthError,
    LLMProviderError,
    LLMRateLimitError,
    LLMService,
    LLMTimeoutError,
    get_llm_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat & Health"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process user query and generate AI response",
    responses={
        400: {"description": "Bad Request"},
        422: {"description": "Validation Error (e.g., empty message, invalid UUID)"},
        429: {"description": "AI Provider Rate Limit Exceeded"},
        502: {"description": "AI Provider Error or Misconfiguration"},
        504: {"description": "AI Provider Request Timeout"},
    },
)
async def chat_endpoint(
    payload: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ChatResponse:
    """Submit a question to the AI assistant.

    Orchestrates conversation history retrieval, LangChain prompt execution via Groq,
    and server-side conversation state persistence.
    """
    # Guardrail: Enforce configurable maximum message length
    if len(payload.message) > settings.MAX_MESSAGE_LENGTH:
        logger.warning(
            "Rejected message from session %s: length %d exceeds max %d",
            payload.session_id,
            len(payload.message),
            settings.MAX_MESSAGE_LENGTH,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Message length ({len(payload.message)} characters) exceeds "
                f"the maximum permitted length of {settings.MAX_MESSAGE_LENGTH} characters."
            ),
        )

    # Retrieve authoritative server-side conversation history for this session
    session_history = await conversation_service.get_history(payload.session_id)

    try:
        # Invoke LLM through isolated service
        result = await llm_service.generate_response(
            session_id=payload.session_id,
            user_message=payload.message,
            history=session_history,
        )

        # Atomically record dialogue turn in server-side history
        await conversation_service.add_turn(
            session_id=payload.session_id,
            user_message=payload.message,
            assistant_message=result.answer,
        )

        return ChatResponse(
            session_id=payload.session_id,
            answer=result.answer,
            model=result.model,
        )

    except LLMRateLimitError as exc:
        logger.warning("Rate limit hit during chat for session %s: %s", payload.session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI service rate limit has been reached. Please wait a moment before retrying.",
        ) from exc

    except LLMTimeoutError as exc:
        logger.warning("Timeout during chat for session %s: %s", payload.session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The request to the AI service timed out. Please try again.",
        ) from exc

    except LLMAuthError as exc:
        logger.error("Authentication error during chat for session %s: %s", payload.session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service authentication failure. Please check server configuration.",
        ) from exc

    except LLMProviderError as exc:
        logger.error("Provider error during chat for session %s: %s", payload.session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the AI service provider.",
        ) from exc

    except Exception as exc:
        # Catch-all: log detailed exception internally, but never expose stack trace to user
        logger.exception("Unexpected error in chat_endpoint for session %s", payload.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred.",
        ) from exc


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application liveness health check",
)
async def health_check(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Basic health check verifying the application is running.

    Does not call external APIs and does not expose secrets or sensitive configuration.
    """
    return HealthResponse(
        status="ok",
        app="qa-chatbot",
        environment=settings.APP_ENV,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Application readiness check",
)
async def ready_check(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadyResponse:
    """Readiness probe checking application configuration.

    Verifies model configuration and API key presence without executing external API calls.
    """
    is_ready = settings.is_api_key_configured and bool(settings.GROQ_MODEL)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="not_ready",
            model=settings.GROQ_MODEL,
            api_key_configured=settings.is_api_key_configured,
            langsmith_configured=settings.is_langsmith_configured,
        )

    return ReadyResponse(
        status="ready",
        model=settings.GROQ_MODEL,
        api_key_configured=True,
        langsmith_configured=settings.is_langsmith_configured,
    )


@router.delete(
    "/chat/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Clear conversation history for a session",
)
async def clear_session_endpoint(
    session_id: str,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict[str, str]:
    """Reset and clear conversation history for a specific session ID."""
    try:
        uuid.UUID(session_id.strip())
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid session_id format: '{session_id}'",
        )

    existed = await conversation_service.clear_session(session_id.strip())
    return {
        "session_id": session_id.strip(),
        "status": "cleared" if existed else "not_found",
    }
