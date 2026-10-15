"""Automated unit and integration tests for LangSmith tracing and configuration.

Validates:
- LangSmith configuration defaults and validation.
- Masking of sensitive LangSmith credentials in logs.
- Environment variable synchronization for LangChain tracer.
- /api/ready status reporting for LangSmith.
- LLMService passing telemetry tags and metadata into LangChain invocations.
"""

import os
from unittest.mock import AsyncMock, patch
import uuid

from httpx import ASGITransport, AsyncClient
import pytest
from langchain_core.messages import AIMessage

from app.config import Settings, get_settings, setup_langsmith_tracing
from app.main import create_app
from app.services.llm_service import LLMResult, LLMService


def test_langsmith_settings_defaults() -> None:
    """Test default values for LangSmith configuration."""
    settings = Settings(GROQ_API_KEY="gsk_dummy")
    assert settings.LANGSMITH_TRACING is False
    assert settings.LANGSMITH_API_KEY == ""
    assert settings.LANGSMITH_PROJECT == "qa-chatbot-local"
    assert settings.LANGSMITH_ENDPOINT == "https://api.smith.langchain.com"
    assert settings.is_langsmith_configured is False
    assert settings.masked_langsmith_api_key == "<UNSET>"


def test_langsmith_configuration_validation() -> None:
    """Test is_langsmith_configured detection logic."""
    # Tracing false, key provided -> False
    s1 = Settings(GROQ_API_KEY="gsk_dummy", LANGSMITH_TRACING=False, LANGSMITH_API_KEY="lsv2_pt_test123")
    assert s1.is_langsmith_configured is False

    # Tracing true, key placeholder -> False
    s2 = Settings(GROQ_API_KEY="gsk_dummy", LANGSMITH_TRACING=True, LANGSMITH_API_KEY="lsv2_pt_your_langsmith_api_key_here")
    assert s2.is_langsmith_configured is False

    # Tracing true, empty key -> False
    s3 = Settings(GROQ_API_KEY="gsk_dummy", LANGSMITH_TRACING=True, LANGSMITH_API_KEY="   ")
    assert s3.is_langsmith_configured is False

    # Tracing true, valid key -> True
    s4 = Settings(GROQ_API_KEY="gsk_dummy", LANGSMITH_TRACING=True, LANGSMITH_API_KEY="lsv2_pt_abc123456789_valid")
    assert s4.is_langsmith_configured is True
    assert s4.masked_langsmith_api_key.startswith("lsv2_pt")
    assert s4.masked_langsmith_api_key.endswith("alid")


def test_setup_langsmith_tracing_sync() -> None:
    """Test environment variable synchronization for LangChain tracer."""
    # When enabled with valid key
    settings = Settings(
        GROQ_API_KEY="gsk_dummy",
        LANGSMITH_TRACING=True,
        LANGSMITH_API_KEY="lsv2_pt_sync_test_key_12345",
        LANGSMITH_PROJECT="test-project",
        LANGSMITH_ENDPOINT="https://custom.smith.langchain.com",
    )
    is_active = setup_langsmith_tracing(settings)
    assert is_active is True
    assert os.environ.get("LANGSMITH_TRACING") == "true"
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGSMITH_API_KEY") == "lsv2_pt_sync_test_key_12345"
    assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_pt_sync_test_key_12345"
    assert os.environ.get("LANGSMITH_PROJECT") == "test-project"
    assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
    assert os.environ.get("LANGSMITH_ENDPOINT") == "https://custom.smith.langchain.com"

    # When disabled
    disabled_settings = Settings(
        GROQ_API_KEY="gsk_dummy",
        LANGSMITH_TRACING=False,
    )
    is_active_disabled = setup_langsmith_tracing(disabled_settings)
    assert is_active_disabled is False
    assert os.environ.get("LANGSMITH_TRACING") == "false"
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"


@pytest.mark.asyncio
async def test_ready_endpoint_langsmith_status() -> None:
    """Test /api/ready endpoint reflects langsmith_configured state."""
    # Case 1: LangSmith configured
    configured_settings = Settings(
        GROQ_API_KEY="gsk_test_mock_12345678",
        GROQ_MODEL="openai/gpt-oss-120b",
        APP_ENV="test",
        LANGSMITH_TRACING=True,
        LANGSMITH_API_KEY="lsv2_pt_mock_key_987654321",
    )
    app1 = create_app()
    app1.dependency_overrides[get_settings] = lambda: configured_settings

    transport1 = ASGITransport(app=app1)
    async with AsyncClient(transport=transport1, base_url="http://testserver") as client:
        res1 = await client.get("/api/ready")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "ready"
        assert data1["api_key_configured"] is True
        assert data1["langsmith_configured"] is True

    # Case 2: LangSmith not configured
    unconfigured_settings = Settings(
        GROQ_API_KEY="gsk_test_mock_12345678",
        GROQ_MODEL="openai/gpt-oss-120b",
        APP_ENV="test",
        LANGSMITH_TRACING=False,
        LANGSMITH_API_KEY="",
    )
    app2 = create_app()
    app2.dependency_overrides[get_settings] = lambda: unconfigured_settings

    transport2 = ASGITransport(app=app2)
    async with AsyncClient(transport=transport2, base_url="http://testserver") as client:
        res2 = await client.get("/api/ready")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["langsmith_configured"] is False


@pytest.mark.asyncio
async def test_llm_service_invokes_with_telemetry_config() -> None:
    """Test that LLMService passes session metadata and tags to client.ainvoke."""
    settings = Settings(
        GROQ_API_KEY="gsk_test_mock_12345678",
        GROQ_MODEL="openai/gpt-oss-120b",
        APP_ENV="test",
        LANGSMITH_TRACING=True,
        LANGSMITH_API_KEY="lsv2_pt_mock_1234567890",
    )
    service = LLMService(settings=settings)

    mock_client = AsyncMock()
    mock_client.ainvoke.return_value = AIMessage(
        content="Test response from mocked LLM",
        response_metadata={"token_usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}},
    )
    service._client = mock_client

    session_id = str(uuid.uuid4())
    result = await service.generate_response(
        session_id=session_id,
        user_message="Hello, test LangSmith metadata!",
    )

    assert result.answer == "Test response from mocked LLM"
    assert result.token_usage == {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}

    # Verify client.ainvoke was called with config containing run_name, tags, and metadata
    mock_client.ainvoke.assert_awaited_once()
    _, kwargs = mock_client.ainvoke.call_args
    assert "config" in kwargs
    run_config = kwargs["config"]
    assert "tags" in run_config
    assert "groq" in run_config["tags"]
    assert "metadata" in run_config
    assert run_config["metadata"]["session_id"] == session_id
    assert run_config["metadata"]["model"] == "openai/gpt-oss-120b"
