"""Pytest Fixtures and Mock Configurations.

Isolates all backend automated tests from external networks and real Groq API calls.
Provides dependency injection overrides for Settings, ConversationService, and LLMService.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock
import uuid

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.config import Settings, get_settings
from app.main import create_app
from app.services.conversation_service import (
    ConversationService,
    get_conversation_service,
)
from app.services.llm_service import (
    LLMResult,
    LLMService,
    get_llm_service,
)


@pytest.fixture
def test_settings() -> Settings:
    """Provide deterministic test settings."""
    return Settings(
        GROQ_API_KEY="gsk_test_valid_mock_key_abc123456789",
        GROQ_MODEL="openai/gpt-oss-120b",
        APP_ENV="test",
        APP_HOST="127.0.0.1",
        APP_PORT=8000,
        LLM_TEMPERATURE=0.0,
        LLM_MAX_TOKENS=512,
        LLM_TIMEOUT_SECONDS=10.0,
        MAX_MESSAGE_LENGTH=100,  # Small limit for easy validation testing
        MAX_HISTORY_TURNS=3,     # Small limit for easy sliding window testing
    )


@pytest.fixture
def conversation_service(test_settings: Settings) -> ConversationService:
    """Provide an isolated, fresh in-memory ConversationService for each test."""
    return ConversationService(max_history_turns=test_settings.MAX_HISTORY_TURNS)


@pytest.fixture
def mock_llm_service(test_settings: Settings) -> LLMService:
    """Provide a mock LLM service that returns canned responses without external network calls."""
    mock = AsyncMock(spec=LLMService)
    mock.settings = test_settings
    mock.model_name = test_settings.GROQ_MODEL

    # Default canned successful response
    mock.generate_response.return_value = LLMResult(
        answer="Mocked AI response: Python decorators wrap a function to extend its behavior.",
        model=test_settings.GROQ_MODEL,
        token_usage={"prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35},
        latency_ms=45.2,
    )
    return mock


@pytest.fixture
def app(
    test_settings: Settings,
    mock_llm_service: LLMService,
    conversation_service: ConversationService,
) -> FastAPI:
    """Create FastAPI application with injected mock dependencies."""
    application = create_app()

    # Override service dependencies
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_llm_service] = lambda: mock_llm_service
    application.dependency_overrides[get_conversation_service] = lambda: conversation_service

    return application


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client for calling the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
