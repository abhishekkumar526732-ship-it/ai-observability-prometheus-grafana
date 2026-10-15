"""Automated tests for health and readiness endpoints.

Validates:
- GET /api/health returns HTTP 200 and safe status metadata without credentials.
- GET /api/ready returns HTTP 200 when properly configured.
- GET /api/ready returns HTTP 503 when Groq API key is unconfigured.
- Verification that health/ready checks never trigger external model calls.
"""

from httpx import ASGITransport, AsyncClient
import pytest

from app.config import Settings, get_settings
from app.main import create_app
from app.services.llm_service import LLMService, get_llm_service


@pytest.mark.asyncio
async def test_health_check_returns_ok(async_client: AsyncClient) -> None:
    """Test that /api/health returns 200 OK and expected structure."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "qa-chatbot"
    assert "environment" in data
    # Ensure no sensitive credentials leaked
    assert "GROQ_API_KEY" not in data
    assert "key" not in str(data).lower()


@pytest.mark.asyncio
async def test_ready_check_when_configured(async_client: AsyncClient) -> None:
    """Test that /api/ready returns 200 when environment configuration is valid."""
    response = await async_client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["model"] == "openai/gpt-oss-120b"
    assert data["api_key_configured"] is True


@pytest.mark.asyncio
async def test_ready_check_when_not_configured(mock_llm_service: LLMService) -> None:
    """Test that /api/ready returns 503 Service Unavailable when API key is missing."""
    unconfigured_settings = Settings(
        GROQ_API_KEY="",  # Missing key
        GROQ_MODEL="openai/gpt-oss-120b",
        APP_ENV="test",
    )

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: unconfigured_settings
    app.dependency_overrides[get_llm_service] = lambda: mock_llm_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["api_key_configured"] is False
