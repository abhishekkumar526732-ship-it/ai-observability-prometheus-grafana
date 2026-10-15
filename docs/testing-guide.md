# 🧪 Testing & Quality Assurance Guide

This guide details the automated test suite, mocking strategies, and local diagnostic tools for the Q&A Chatbot.

---

## 1. Testing Philosophy: Zero-Cost Mocking

Automated tests must be **fast**, **reliable**, **hermetic**, and **zero-cost**:

* **Air-Gapped Test Execution:** Real Groq API and LangSmith endpoints are never called during automated test runs.
* **Deterministic Fixtures:** FastAPI's `dependency_overrides` mechanism injects mock services (`mock_llm_service`) with predefined `LLMResult` payloads.
* **Instant Feedback:** All 21 unit and integration tests execute in **under 0.5 seconds**.
* **Security Validation:** Tests explicitly verify that API keys, passwords, and server tracebacks never leak in API response payloads or logs.

---

## 2. Test Suite Breakdown (21 Automated Tests)

The test suite is located in [`qa-chatbot/backend/tests/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/backend/tests/):

### 2.1 Chat Endpoint Tests (`tests/test_chat.py` - 8 Tests)
* `test_chat_success`: Validates successful 200 OK completions and response schemas.
* `test_chat_empty_message_rejected`: Rejects empty and whitespace-only queries with HTTP 422.
* `test_chat_invalid_session_id_rejected`: Enforces strict UUID v4 formatting on `session_id`.
* `test_chat_message_exceeding_max_length_rejected`: Ensures messages exceeding `MAX_MESSAGE_LENGTH` are rejected.
* `test_chat_rate_limit_maps_to_429`: Verifies upstream Groq rate limits cleanly translate to HTTP 429.
* `test_chat_timeout_maps_to_504`: Verifies provider timeouts translate to HTTP 504.
* `test_chat_provider_auth_error_maps_to_502`: Verifies auth failures translate to HTTP 502 without exposing keys.
* `test_chat_unexpected_error_does_not_leak_internals`: Asserts that internal exceptions return HTTP 500 without stack trace leaks.

### 2.2 Conversation State Tests (`tests/test_conversation.py` - 5 Tests)
* `test_session_history_persistence`: Verifies dialogue turns persist sequentially within the same session.
* `test_session_isolation`: Confirms that queries in Session A never leak into Session B.
* `test_history_truncation_at_limit`: Validates sliding-window eviction when dialogue exceeds `MAX_HISTORY_TURNS`.
* `test_clear_session`: Verifies `DELETE /api/chat/session/{id}` resets session memory.
* `test_concurrent_turns_safe_execution`: Launches 10 concurrent async worker tasks to prove thread safety under load.

### 2.3 Health & Readiness Probe Tests (`tests/test_health.py` - 3 Tests)
* `test_health_check_returns_ok`: Verifies `GET /api/health` returns 200 OK without leaking credentials.
* `test_ready_check_when_configured`: Confirms `GET /api/ready` returns 200 OK when model and keys are set.
* `test_ready_check_when_not_configured`: Asserts `GET /api/ready` returns 503 Service Unavailable when keys are missing.

### 2.4 LangSmith Tracing Tests (`tests/test_langsmith.py` - 5 Tests)
* `test_langsmith_settings_defaults`: Checks default values for `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, etc.
* `test_langsmith_configuration_validation`: Verifies `is_langsmith_configured` correctly identifies valid vs placeholder keys.
* `test_setup_langsmith_tracing_sync`: Confirms environment variables are properly exported to `os.environ` for the LangChain tracer.
* `test_ready_endpoint_langsmith_status`: Verifies `/api/ready` reflects `langsmith_configured: true/false`.
* `test_llm_service_invokes_with_telemetry_config`: Verifies that `LLMService` passes telemetry tags and metadata to `client.ainvoke()`.

---

## 3. Running Automated Tests

Run all tests from the `qa-chatbot/` directory:

```bash
cd qa-chatbot

# Run all tests
python -m pytest backend/tests

# Run tests with verbose output and short traceback
python -m pytest backend/tests -v --tb=short

# Run a specific test module
python -m pytest backend/tests/test_langsmith.py -v
```

---

## 4. Local Interactive Diagnostics (`scripts/test_langsmith.py`)

In addition to automated unit tests, a developer CLI diagnostic tool is provided in [`qa-chatbot/scripts/test_langsmith.py`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/scripts/test_langsmith.py):

```bash
cd qa-chatbot

# 1. Full diagnostic check (reads .env, tests LangSmith API, tests Groq LPU)
python scripts/test_langsmith.py

# 2. Offline simulation (tests traceable execution chain without burning tokens)
python scripts/test_langsmith.py --mock

# 3. Custom test prompt
python scripts/test_langsmith.py --query "Explain Python decorators in 1 sentence"
```

---

## 5. Code Style & Static Analysis (Ruff)

The project uses Ruff for high-speed Python linting and formatting (configured in [`backend/pyproject.toml`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/backend/pyproject.toml)):

```bash
# Check code style and rules
ruff check backend/ scripts/

# Format codebase
ruff format backend/ scripts/
```
