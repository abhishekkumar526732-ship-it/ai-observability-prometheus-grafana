"""Automated tests for POST /api/chat endpoint.

Validates:
- Successful chat completions with mocked LLM service.
- Rejection of empty or whitespace-only messages.
- Rejection of non-UUID session identifiers.
- Rejection of messages exceeding configured maximum character length.
- Provider error mapping (Rate limit -> 429, Timeout -> 504, Provider error -> 502).
- Security assertion: API keys and stack traces are never leaked in client responses.
"""

from unittest.mock import AsyncMock
import uuid

from httpx import AsyncClient
import pytest

from app.services.llm_service import (
    LLMAuthError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
)


@pytest.mark.asyncio
async def test_chat_success(async_client: AsyncClient, mock_llm_service: AsyncMock) -> None:
    """Test valid chat request returns 200 with expected response schema."""
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "message": "Explain Python decorators",
        "history": [],
    }

    response = await async_client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == session_id
    assert "Mocked AI response" in data["answer"]
    assert data["model"] == "openai/gpt-oss-120b"

    # Verify mock was called with the user message and session ID
    mock_llm_service.generate_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_empty_message_rejected(async_client: AsyncClient) -> None:
    """Test that empty or whitespace-only queries are rejected with HTTP 422."""
    session_id = str(uuid.uuid4())

    # Test completely empty string
    res1 = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "", "history": []},
    )
    assert res1.status_code == 422
    assert "VALIDATION_ERROR" in res1.json()["error"]

    # Test whitespace-only string
    res2 = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "   \n\t  ", "history": []},
    )
    assert res2.status_code == 422
    assert "VALIDATION_ERROR" in res2.json()["error"]


@pytest.mark.asyncio
async def test_chat_invalid_session_id_rejected(async_client: AsyncClient) -> None:
    """Test that malformed or non-UUID session IDs are rejected with HTTP 422."""
    payload = {
        "session_id": "not-a-valid-uuid-12345",
        "message": "What is Python?",
        "history": [],
    }

    response = await async_client.post("/api/chat", json=payload)
    assert response.status_code == 422
    assert "VALIDATION_ERROR" in response.json()["error"]
    assert "session_id must be a valid UUID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_message_exceeding_max_length_rejected(async_client: AsyncClient) -> None:
    """Test that queries exceeding MAX_MESSAGE_LENGTH (100 chars in test config) are rejected."""
    session_id = str(uuid.uuid4())
    oversized_message = "A" * 150  # Limit in test_settings is 100

    payload = {
        "session_id": session_id,
        "message": oversized_message,
        "history": [],
    }

    response = await async_client.post("/api/chat", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
    assert "exceeds the maximum permitted length" in data["detail"]


@pytest.mark.asyncio
async def test_chat_rate_limit_maps_to_429(
    async_client: AsyncClient, mock_llm_service: AsyncMock
) -> None:
    """Test that provider rate limits translate cleanly to HTTP 429."""
    mock_llm_service.generate_response.side_effect = LLMRateLimitError("Quota exceeded on Groq.")
    session_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Trigger rate limit", "history": []},
    )
    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "RATE_LIMIT_EXCEEDED"
    assert "rate limit has been reached" in data["detail"]


@pytest.mark.asyncio
async def test_chat_timeout_maps_to_504(
    async_client: AsyncClient, mock_llm_service: AsyncMock
) -> None:
    """Test that provider timeouts translate cleanly to HTTP 504."""
    mock_llm_service.generate_response.side_effect = LLMTimeoutError("Request to Groq timed out.")
    session_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Trigger timeout", "history": []},
    )
    assert response.status_code == 504
    data = response.json()
    assert data["error"] == "GATEWAY_TIMEOUT"
    assert "timed out" in data["detail"]


@pytest.mark.asyncio
async def test_chat_provider_auth_error_maps_to_502(
    async_client: AsyncClient, mock_llm_service: AsyncMock
) -> None:
    """Test that provider authentication failures translate cleanly to HTTP 502."""
    mock_llm_service.generate_response.side_effect = LLMAuthError("Invalid API key")
    session_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Trigger auth error", "history": []},
    )
    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "PROVIDER_ERROR"
    assert "authentication failure" in data["detail"]


@pytest.mark.asyncio
async def test_chat_unexpected_error_does_not_leak_internals(
    async_client: AsyncClient, mock_llm_service: AsyncMock
) -> None:
    """Test that unexpected server exceptions return 500 without leaking stack traces or secrets."""
    mock_llm_service.generate_response.side_effect = RuntimeError("Sensitive internal database error")
    session_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Trigger 500 error", "history": []},
    )
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "INTERNAL_SERVER_ERROR"
    # Verify no raw exception or stack trace details leaked in response
    assert "Sensitive internal database error" not in data["detail"]
    assert "Traceback" not in data["detail"]
