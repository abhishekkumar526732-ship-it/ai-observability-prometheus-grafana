# 📜 Software Requirements Document (SRD)

**Project Name:** Observability & Cost Dashboard for an AI Service  
**Document Reference:** FDE-SRD-2026-v1.0  
**Status:** Approved  
**Author:** Forward Deployed Engineering (FDE) Team  

---

## 1. Software Architecture & Module Decomposition

The software runtime is organized into decoupled layers inside [`qa-chatbot/backend/app/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/backend/app/):

```
backend/app/
├── main.py              # Application factory, CORS, exception handlers, static routes
├── config.py            # Pydantic Settings, environment auto-sync, key masking
├── api/
│   └── chat.py          # REST endpoints: /api/chat, /api/health, /api/ready, /session
├── schemas/
│   └── chat.py          # Pydantic v2 validation models and custom field sanitizers
└── services/
    ├── conversation_service.py # In-memory session manager, sliding-window truncation
    └── llm_service.py   # LangChain ChatGroq orchestration, token telemetry, error translation
```

---

## 2. Functional Requirements (FR)

### 2.1 Chat & Inference Orchestration
* **FR-01: Query Ingestion:** The system shall accept user queries via `POST /api/chat` with JSON payload `{session_id, message, history}`.
* **FR-02: Input Validation & Sanitization:**
  - Queries exceeding `MAX_MESSAGE_LENGTH` (default: 4000 characters) must be rejected with HTTP 422.
  - Queries consisting of empty strings or whitespace only must be rejected with HTTP 422.
* **FR-03: Session UUID Format:** The `session_id` must conform to RFC 4122 UUID v4 formatting. Malformed UUIDs must be rejected with HTTP 422.
* **FR-04: Groq Model Inference:** The system shall invoke `openai/gpt-oss-120b` (or configured `GROQ_MODEL`) via LangChain's `ChatGroq` asynchronous client (`ainvoke`).
* **FR-05: Reasoning Effort Control:** For OpenAI reasoning models, the system shall pass `REASONING_EFFORT` (`none`, `low`, `medium`, `high`) into the model parameters.
* **FR-06: Telemetry & Token Extraction:** For every completion, the system shall extract `prompt_tokens`, `completion_tokens`, and `total_tokens` from model metadata and record execution latency in milliseconds.

### 2.2 Conversation State & Context Management
* **FR-07: Multi-Turn Persistence:** The system shall maintain dialogue continuity across sequential queries sharing the same `session_id`.
* **FR-08: Session Isolation:** Histories between distinct `session_id`s must be completely isolated with zero data leakage.
* **FR-09: Sliding-Window Truncation:** When conversation turns exceed `MAX_HISTORY_TURNS` (default: 10 turns = 20 messages), the system shall automatically discard oldest turns while preserving recent context and system instructions.
* **FR-10: Session Clearance:** The system shall provide `DELETE /api/chat/session/{session_id}` to reset and wipe memory for that session.

### 2.3 Observability & LangSmith Tracing
* **FR-11: Environment Auto-Sync:** When `LANGSMITH_TRACING=true` and a valid `LANGSMITH_API_KEY` are provided, the configuration engine must synchronize process environment variables (`LANGCHAIN_TRACING_V2`, `LANGSMITH_PROJECT`, etc.).
* **FR-12: Trace Span Hierarchy:** Top-level requests must be decorated with `@traceable` chains, and child model runs must include metadata tags (`session_id`, `model`, `temperature`, `env`).
* **FR-13: Graceful Observability Degradation:** If `LANGSMITH_TRACING=true` but `LANGSMITH_API_KEY` is empty or placeholder, the system must disable tracing flags, log a warning, and continue serving chat queries without failure.

### 2.4 Health & Diagnostic Probes
* **FR-14: Liveness Probe (`GET /api/health`):** Returns HTTP 200 with `{status: "ok", app: "qa-chatbot", environment: "..."}` without triggering external API calls.
* **FR-15: Readiness Probe (`GET /api/ready`):** Returns HTTP 200 with `{status: "ready", model: "...", api_key_configured: true, langsmith_configured: bool}` if keys are configured; returns HTTP 503 if unconfigured.

---

## 3. Non-Functional Requirements (NFR)

| ID | Category | Requirement Specification | Verification Method |
| :--- | :--- | :--- | :--- |
| **NFR-01** | **Performance** | p50 latency < 400ms; p95 latency < 1500ms for typical 100-token responses. | Load testing & Otel metrics. |
| **NFR-02** | **Concurrency** | The backend must support concurrent requests per session without memory corruption using per-session `asyncio.Lock`s. | Automated async concurrency tests (`test_concurrent_turns_safe_execution`). |
| **NFR-03** | **Security** | API keys must never appear in response bodies, error messages, client logs, or repository files. | Automated test assertion (`test_health_check_returns_ok`, `test_chat_provider_auth_error_maps_to_502`). |
| **NFR-04** | **XSS Immunity** | Frontend must render AI responses into DOM text nodes via `document.createTextNode` and `textContent`, prohibiting `innerHTML` on unparsed strings. | Code audit & browser security review. |
| **NFR-05** | **Zero-Cost Testability**| Automated tests must run 100% offline using mocked dependencies without consuming Groq or LangSmith tokens. | Pytest suite running in < 0.5s without network access. |
| **NFR-06** | **Footprint** | Idle backend container memory must remain below 128 MiB; active under-load memory < 512 MiB. | Container resource profiling. |
| **NFR-07** | **Zero Frontend Build**| Frontend must operate on pure Vanilla JS and CSS3 without requiring Node.js, `npm install`, or bundlers. | Directly served via Nginx and FastAPI static mounts. |
| **NFR-08** | **Code Quality** | 100% compliance with Ruff linter rules and PEP 8 formatting standards. | `ruff check backend/ scripts/` |

---

## 4. API Data Contracts & Pydantic Schemas

### 4.1 ChatRequest Schema
```python
class ChatMessageItem(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=32000)

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID v4 session identifier")
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessageItem] = Field(default_factory=list)
```

### 4.2 ChatResponse Schema
```python
class ChatResponse(BaseModel):
    session_id: str
    answer: str
    model: str
```

### 4.3 ReadyResponse Schema
```python
class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model: str
    api_key_configured: bool
    langsmith_configured: bool = False
```

### 4.4 Standard Error Response Schema
```python
class ErrorResponse(BaseModel):
    error: str   # e.g., "RATE_LIMIT_EXCEEDED"
    detail: str  # e.g., "AI provider rate limit reached. Please wait a moment."
    code: str    # e.g., "HTTP_429"
```

---

## 5. Behavior-Driven Development (BDD) Acceptance Criteria

### Scenario 1: Successful Chat Turn
```gherkin
Given a running Q&A Chatbot service with a valid GROQ_API_KEY
When a user sends a POST request to "/api/chat" with:
  | session_id | "a8098c1a-f86e-11da-bd1a-00112444be1e" |
  | message    | "What is Docker?"                       |
Then the response status code should be 200
And the response JSON should contain:
  | session_id | "a8098c1a-f86e-11da-bd1a-00112444be1e" |
  | model      | "openai/gpt-oss-120b"                   |
And "answer" should be a non-empty string explaining Docker
```

### Scenario 2: Context Retention Across Turns
```gherkin
Given a session with ID "b9198c1a-f86e-11da-bd1a-00112444be1f"
When the user asks "My favorite programming language is Python"
And the assistant responds successfully
When the user subsequently asks "What is my favorite programming language?"
Then the assistant answer must state "Python"
```

### Scenario 3: Sliding-Window Context Eviction
```gherkin
Given MAX_HISTORY_TURNS is set to 3 (6 messages)
When the user performs 5 consecutive query-response dialogue turns
Then only the 3 most recent turns (turns 3, 4, 5) must be present in conversation history
And turns 1 and 2 must be evicted from the active context
```

### Scenario 4: Upstream Rate Limit Handling
```gherkin
Given the Groq API returns HTTP 429 Rate Limit Exceeded
When a user submits a query to "/api/chat"
Then the backend must return HTTP 429 with error "RATE_LIMIT_EXCEEDED"
And the detail must provide clear retry instructions without exposing upstream raw stack traces
```

---

## 6. Verification & Test Traceability Matrix

Every requirement is mapped to automated test cases in [`qa-chatbot/backend/tests/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/backend/tests/):

| Requirement | Description | Validating Test Case | Result |
| :--- | :--- | :--- | :--- |
| **FR-01, FR-04** | Chat Completion & Schema | `test_chat.py::test_chat_success` | Passed |
| **FR-02** | Empty Message Sanitization | `test_chat.py::test_chat_empty_message_rejected` | Passed |
| **FR-03** | UUID Validation | `test_chat.py::test_chat_invalid_session_id_rejected` | Passed |
| **FR-02** | Max Length Boundary | `test_chat.py::test_chat_message_exceeding_max_length_rejected` | Passed |
| **FR-07** | Rate Limit Translation | `test_chat.py::test_chat_rate_limit_maps_to_429` | Passed |
| **FR-07** | Timeout Translation | `test_chat.py::test_chat_timeout_maps_to_504` | Passed |
| **FR-07, NFR-03**| Auth Error Translation | `test_chat.py::test_chat_provider_auth_error_maps_to_502` | Passed |
| **NFR-03** | No Internal Leakage | `test_chat.py::test_chat_unexpected_error_does_not_leak_internals` | Passed |
| **FR-07** | Multi-Turn Persistence | `test_conversation.py::test_session_history_persistence` | Passed |
| **FR-08** | Session Isolation | `test_conversation.py::test_session_isolation` | Passed |
| **FR-09** | Sliding-Window Truncation| `test_conversation.py::test_history_truncation_at_limit` | Passed |
| **FR-10** | Clear Session History | `test_conversation.py::test_clear_session` | Passed |
| **NFR-02** | Concurrency Safety | `test_conversation.py::test_concurrent_turns_safe_execution` | Passed |
| **FR-14** | Liveness Probe | `test_health.py::test_health_check_returns_ok` | Passed |
| **FR-15** | Readiness Probe | `test_health.py::test_ready_check_when_configured` | Passed |
| **FR-11** | LangSmith Defaults | `test_langsmith.py::test_langsmith_settings_defaults` | Passed |
| **FR-11, FR-13**| LangSmith Config Check | `test_langsmith.py::test_langsmith_configuration_validation` | Passed |
| **FR-11** | Environment Variable Sync| `test_langsmith.py::test_setup_langsmith_tracing_sync` | Passed |
| **FR-15** | Ready Check LangSmith | `test_langsmith.py::test_ready_endpoint_langsmith_status` | Passed |
| **FR-06, FR-12**| Telemetry Config Injection| `test_langsmith.py::test_llm_service_invokes_with_telemetry_config`| Passed |
