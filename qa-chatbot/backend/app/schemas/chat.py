"""Chat Request and Response Schemas.

Defines Pydantic models with rigorous input validation for chat interactions,
session identification, and system health status.
"""

from typing import Literal
import uuid

from pydantic import BaseModel, Field, field_validator


class ChatMessageItem(BaseModel):
    """Represents a single message in conversation history."""

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Role of the message sender.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Text content of the message.",
    )

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, v: str) -> str:
        """Strip whitespace from message content."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Message content cannot be empty or whitespace only.")
            return v_stripped
        return v


class ChatRequest(BaseModel):
    """Request payload for POST /api/chat."""

    session_id: str = Field(
        ...,
        description="Unique UUID v4 session identifier for conversation continuity.",
        examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User question to be answered by the assistant.",
        examples=["Explain Python decorators with a simple example."],
    )
    history: list[ChatMessageItem] = Field(
        default_factory=list,
        description="Client-supplied conversation history (validated, but server state is authoritative).",
    )

    @field_validator("session_id")
    @classmethod
    def validate_uuid_session_id(cls, v: str) -> str:
        """Ensure session_id conforms to a valid UUID string format."""
        try:
            val = uuid.UUID(str(v).strip())
            return str(val)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(
                f"session_id must be a valid UUID string. Received: '{v}'"
            ) from exc

    @field_validator("message", mode="before")
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        """Ensure message is non-empty and stripped of surrounding whitespace."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("message must be a non-empty string.")
        return v.strip()


class ChatResponse(BaseModel):
    """Response payload for POST /api/chat."""

    session_id: str = Field(
        ...,
        description="Session identifier matching the conversation.",
    )
    answer: str = Field(
        ...,
        description="AI-generated response from the configured Groq LLM.",
    )
    model: str = Field(
        ...,
        description="Model identifier that produced the answer.",
    )


class HealthResponse(BaseModel):
    """Response payload for GET /api/health."""

    status: Literal["ok"] = "ok"
    app: str = "qa-chatbot"
    environment: str = "development"


class ReadyResponse(BaseModel):
    """Response payload for GET /api/ready."""

    status: Literal["ready", "not_ready"]
    model: str
    api_key_configured: bool
    langsmith_configured: bool = False


class ErrorResponse(BaseModel):
    """Standardized API error response format."""

    error: str = Field(..., description="High-level error classification.")
    detail: str = Field(..., description="User-friendly explanation of the issue.")
    code: str = Field(..., description="Machine-readable error code.")
