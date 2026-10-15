# ⚡ Q&A Chatbot (Groq + LangChain + FastAPI)

A modular, production-grade conversational AI assistant featuring OpenAI's flagship open-weights reasoning model (**`openai/gpt-oss-120b`**) running on **Groq LPUs** with **LangChain**, backed by a high-performance **FastAPI** service and a responsive **ChatGPT-style Vanilla JS/CSS** interface.

> 📖 **Comprehensive Documentation:**
> * [System Architecture](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/architecture.md) &bull; [REST API Reference](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/api-reference.md) &bull; [Observability & Tracing](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/observability-and-tracing.md)
> * [Setup & Deployment](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/setup-and-deployment.md) &bull; [Testing Guide](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/testing-guide.md)
> * **FDE Engineering Suite:** [FDE Index](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/README.md) &bull; [BRD](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/BRD.md) &bull; [TRD](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/TRD.md) &bull; [SRD](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/SRD.md)

---

## 🚀 Quick Start

### 1. Configure API Key
Create a `.env` file in the `qa-chatbot/` directory (or edit the existing one):
```bash
cp .env.example .env
```
Add your Groq API key (get one free at [console.groq.com/keys](https://console.groq.com/keys)):
```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
REASONING_EFFORT=medium
```

---

### Option A: Run Locally (Without Docker)

The FastAPI backend automatically detects and serves the frontend static UI directly!

```bash
# 1. Install dependencies (from qa-chatbot/)
pip install -r backend/requirements.txt

# 2. Start the Uvicorn server
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open in your browser:
* **Web Chat UI:** [http://localhost:8000](http://localhost:8000)
* **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Run with Docker Compose

Runs the multi-container stack with Nginx as a reverse proxy on port 3000 and FastAPI on port 8000:

```bash
# Build and start services in the background
docker compose up --build -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

Open in your browser:
* **Web Chat UI:** [http://localhost:3000](http://localhost:3000)
* **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the containers:
```bash
docker compose down
```

---

## 🌐 Application URLs

| Service | Local (No Docker) | Docker Compose | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Chat UI** | `http://localhost:8000` | `http://localhost:3000` | Clean ChatGPT-style conversational interface |
| **Swagger UI** | `http://localhost:8000/docs` | `http://localhost:8000/docs` | Interactive OpenAPI playground |
| **ReDoc** | `http://localhost:8000/redoc` | `http://localhost:8000/redoc` | Clean API documentation reference |
| **Health Check** | `http://localhost:8000/api/health` | `http://localhost:8000/api/health` | Service liveness probe |
| **Readiness Check** | `http://localhost:8000/api/ready` | `http://localhost:8000/api/ready` | Model & API key readiness probe |

---

## ✨ Key Features

* **Groq LPU Inference:** Ultra-low latency responses (~500 tokens/sec) using open-weights models (`openai/gpt-oss-120b`).
* **Multi-Turn Session Continuity:** In-memory, thread-safe dialogue tracking keyed by UUID v4 with automatic sliding-window context management (`MAX_HISTORY_TURNS`).
* **Zero-Vulnerability Frontend:** Pure Vanilla JS (no node_modules build step required). Renders responses using safe DOM methods (`document.createElement`, `textContent`) — completely immune to XSS.
* **Code Blocks & Copy:** Automatic Markdown code block formatting with language tags and one-click copy buttons.
* **Robust Error Mapping:** Graceful handling and user-facing notifications for rate limits (HTTP 429), timeouts (HTTP 504), and provider issues (HTTP 502).
* **Comprehensive Test Suite:** 16 automated unit & integration tests with zero external API calls (fully mocked).

---

## 📂 Project Architecture

```
qa-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app factory, CORS, static routes & global error handlers
│   │   ├── config.py              # Pydantic Settings with env parsing & key validation
│   │   ├── api/
│   │   │   └── chat.py            # Endpoints: /api/chat, /api/health, /api/ready, session clear
│   │   ├── schemas/
│   │   │   └── chat.py            # Request/Response Pydantic models with input sanitization
│   │   └── services/
│   │       ├── llm_service.py     # LangChain ChatGroq client, prompt builder & token telemetry
│   │       └── conversation_service.py # Thread-safe in-memory session history manager
│   ├── tests/
│   │   ├── conftest.py            # Pytest fixtures & mock LLM providers
│   │   ├── test_chat.py           # Endpoint integration & error mapping tests
│   │   ├── test_conversation.py   # Multi-turn context & isolation tests
│   │   ├── test_health.py         # Liveness and readiness probe tests
│   │   └── test_langsmith.py      # LangSmith tracing & config tests
│   ├── requirements.txt           # Pinned Python dependencies
│   ├── pyproject.toml             # Pytest & Ruff configurations
│   └── Dockerfile                 # Hardened, non-root Python 3.12-slim image
├── frontend/
│   ├── index.html                 # Semantic HTML5 layout with sidebar, hero, & input capsule
│   ├── css/style.css              # Custom responsive stylesheet (dark/light themes)
│   ├── js/
│   │   ├── app.js                 # UI controller, message rendering, auto-expanding textarea
│   │   └── api.js                 # Fetch client, UUID generator, network timeout handling
│   ├── nginx.conf                 # Nginx static server and reverse proxy config
│   └── Dockerfile                 # Lightweight Alpine Nginx image
├── scripts/
│   └── test_langsmith.py          # Diagnostic & LangSmith CLI testing tool
├── .env.example                   # Environment configuration template
├── docker-compose.yml             # Orchestration with healthchecks & isolated network
└── README.md                      # Developer-friendly project documentation
```

---

## ⚙️ Environment Configuration

All settings are configured via environment variables or a `.env` file in the project root:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | String | *(Required)* | Groq API Key (`gsk_...`). |
| `GROQ_MODEL` | String | `openai/gpt-oss-120b` | Target Groq model identifier. |
| `REASONING_EFFORT` | String | `medium` | Optional reasoning depth (`none`, `low`, `medium`, `high`). |
| `APP_ENV` | String | `development` | Environment mode (`development`, `staging`, `production`, `test`). |
| `APP_HOST` | String | `0.0.0.0` | Host binding interface for FastAPI. |
| `APP_PORT` | Integer| `8000` | Port for the FastAPI ASGI application. |
| `LLM_TEMPERATURE` | Float | `0.2` | Sampling temperature (`0.0` = deterministic, `2.0` = creative). |
| `LLM_MAX_TOKENS` | Integer| `1024` | Maximum tokens per response completion. |
| `LLM_TIMEOUT_SECONDS`| Float | `60.0` | Maximum wait time for LLM API generation. |
| `MAX_MESSAGE_LENGTH` | Integer| `4000` | Max character length allowed for user input. |
| `MAX_HISTORY_TURNS` | Integer| `10` | Max previous conversation turns retained in memory. |
| `LANGSMITH_TRACING` | Boolean| `true` | Enable/disable LangSmith observability tracing. |
| `LANGSMITH_API_KEY` | String | *(Optional)* | LangSmith API key (`lsv2_pt_...`). |
| `LANGSMITH_PROJECT` | String | `qa-chatbot-local` | Logical project name in LangSmith console. |
| `LANGSMITH_ENDPOINT` | String | `https://api.smith.langchain.com` | LangSmith API Endpoint. |

---

## 📡 API Reference

### 1. Send Chat Message
* **Endpoint:** `POST /api/chat`
* **Content-Type:** `application/json`

**Request:**
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message": "Explain Python generators in two sentences.",
  "history": []
}
```

**Response (`200 OK`):**
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "answer": "A Python generator is a function that produces a sequence of values on the fly using the 'yield' keyword instead of returning them all at once. This enables lazy evaluation, saving memory by computing items only as they are requested.",
  "model": "openai/gpt-oss-120b"
}
```

### 2. Service Liveness Check
* **Endpoint:** `GET /api/health`

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "app": "qa-chatbot",
  "environment": "development"
}
```

### 3. Service Readiness Check
* **Endpoint:** `GET /api/ready`

**Response (`200 OK`):**
```json
{
  "status": "ready",
  "model": "openai/gpt-oss-120b",
  "api_key_configured": true
}
```

### 4. Clear Session History
* **Endpoint:** `DELETE /api/chat/session/{session_id}`

**Response (`200 OK`):**
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "cleared"
}
```

---

## 🧪 Testing & Code Quality

### Run Automated Tests
All external LLM requests are mocked for instant, zero-cost, air-gapped test execution:

```bash
# Run all unit and integration tests (from qa-chatbot/)
python -m pytest backend/tests

# Run tests with detailed test coverage and verbose output
python -m pytest backend/tests -v --tb=short
```

### Run Linter & Formatter (Ruff)
```bash
# Check code style and common errors
ruff check backend/

# Format code
ruff format backend/
```

### Test LangSmith Tracing Locally
To test LangSmith tracing and evaluate queries locally:
```bash
# 1. Run diagnostic and interactive test script (from qa-chatbot/)
python scripts/test_langsmith.py

# 2. Or test in offline mock mode (zero external tokens required)
python scripts/test_langsmith.py --mock

# 3. Test with a custom query
python scripts/test_langsmith.py --query "Explain Kubernetes pods in simple words"
```
When configured with your `LANGSMITH_API_KEY`, all traces, latencies, and token usages are automatically logged to the [LangSmith Console](https://smith.langchain.com/).

---

## 🔒 Security & Best Practices

1. **XSS Immunity:** Raw AI output is never passed through `innerHTML`. The UI parser converts plain text and markdown code blocks directly into DOM text nodes via `document.createTextNode()`.
2. **Key Protection:** `GROQ_API_KEY` is kept strictly within backend server memory; it is never forwarded to the client or returned in error payloads.
3. **Safe Error Responses:** Internal stack traces and uncaught server errors are intercepted by global FastAPI exception handlers and mapped to sanitized JSON responses.
4. **Least-Privilege Container:** The backend Docker image operates under a restricted non-root user (`appuser`, UID 1000).

---

## 💡 Troubleshooting

| Problem | Probable Cause | Quick Fix |
| :--- | :--- | :--- |
| **`Setup Needed` / `AI service authentication failure`** | `GROQ_API_KEY` missing or invalid in `.env`. | Add valid key from [Groq Console](https://console.groq.com/keys) to `.env` and restart. |
| **`Port already in use: 8000` or `3000`** | Another local process occupies the port. | Change `APP_PORT` in `.env` or port mapping in `docker-compose.yml`. |
| **`Rate limit reached (429)`** | Groq free-tier minute limit hit. | Wait a few seconds and retry; rate limits refresh every minute. |
| **Model Deprecation Error** | Groq updated or retired a model ID. | Update `GROQ_MODEL` in `.env` to any active model listed on [Groq Models](https://console.groq.com/docs/models). |

---

## 📄 License
This project is open-source and free to use under the [MIT License](LICENSE).
