# 📡 REST API Reference

The Q&A Chatbot exposes a clean, standardized RESTful API powered by FastAPI.

---

## 1. Base URLs & Interactive Documentation

| Environment | Base URL | Swagger UI | ReDoc |
| :--- | :--- | :--- | :--- |
| **Local Native** | `http://localhost:8000` | [`/docs`](http://localhost:8000/docs) | [`/redoc`](http://localhost:8000/redoc) |
| **Docker Compose** | `http://localhost:3000` (Proxy) <br/> `http://localhost:8000` (Direct) | [`/docs`](http://localhost:8000/docs) | [`/redoc`](http://localhost:8000/redoc) |
| **Kubernetes** | `https://chatbot.yourdomain.com` | `/docs` *(Dev/Staging)* | `/redoc` *(Dev/Staging)* |

> **Note:** In `production` environment (`APP_ENV=production`), interactive Swagger (`/docs`) and ReDoc (`/redoc`) are automatically disabled for security.

---

## 2. Global Error Response Schema

All errors follow a unified, predictable JSON structure:

```json
{
  "error": "STRING",
  "detail": "STRING",
  "code": "STRING"
}
```

### Standard Error Codes

| Status Code | Error Key (`error`) | Machine Code (`code`) | Meaning |
| :--- | :--- | :--- | :--- |
| **400** | `BAD_REQUEST` | `HTTP_400` | Malformed JSON or invalid syntax. |
| **422** | `VALIDATION_ERROR` | `HTTP_422` | Request body failed Pydantic validation (e.g. invalid UUID, empty message, or exceeds 4000 characters). |
| **429** | `RATE_LIMIT_EXCEEDED` | `HTTP_429` | Groq AI provider rate limit reached. |
| **502** | `PROVIDER_ERROR` | `HTTP_502` | Upstream AI provider failure or authentication issue. |
| **503** | `SERVICE_UNAVAILABLE`| `HTTP_503` | Service readiness check failed (e.g., API key unconfigured). |
| **504** | `GATEWAY_TIMEOUT` | `HTTP_504` | Groq AI provider took longer than `LLM_TIMEOUT_SECONDS` (default: 60s). |
| **500** | `INTERNAL_SERVER_ERROR`| `HTTP_500` | Unhandled server exception. Stack traces are suppressed from client responses. |

---

## 3. Endpoints

### 3.1 Send Chat Query

* **Route:** `POST /api/chat`
* **Content-Type:** `application/json`
* **Summary:** Submits a user prompt, retrieves conversation context, invokes the Groq LLM, traces the execution via LangSmith, and persists the dialogue turn.

#### Request Headers
| Header | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `Content-Type` | String | Yes | Must be `application/json` |

#### Request Body Schema
```json
{
  "session_id": "string (UUID v4, required)",
  "message": "string (1-4000 chars, required)",
  "history": [
    {
      "role": "string (user | assistant | system)",
      "content": "string (1-32000 chars)"
    }
  ]
}
```

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "message": "Explain Kubernetes pods in two sentences.",
    "history": []
  }'
```

#### Successful Response (`200 OK`)
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "answer": "A Kubernetes pod is the smallest deployable unit in Kubernetes, representing a single instance of a running process in your cluster. It encapsulates one or more closely coupled containers that share networking, storage, and specifications on how to run.",
  "model": "openai/gpt-oss-120b"
}
```

#### Error Example (`422 Unprocessable Entity`)
```json
{
  "error": "VALIDATION_ERROR",
  "detail": "session_id must be a valid UUID string. Received: 'not-a-valid-uuid'",
  "code": "HTTP_422"
}
```

---

### 3.2 Service Liveness Probe

* **Route:** `GET /api/health`
* **Summary:** Lightweight health probe used by Kubernetes liveness checks. Does not perform external network calls.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/health"
```

#### Response (`200 OK`)
```json
{
  "status": "ok",
  "app": "qa-chatbot",
  "environment": "development"
}
```

---

### 3.3 Service Readiness Probe

* **Route:** `GET /api/ready`
* **Summary:** Validates that model configuration and API keys are initialized. Used by Kubernetes readiness probes before routing traffic.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/ready"
```

#### Response (`200 OK` - Ready)
```json
{
  "status": "ready",
  "model": "openai/gpt-oss-120b",
  "api_key_configured": true,
  "langsmith_configured": true
}
```

#### Response (`503 Service Unavailable` - Not Ready)
```json
{
  "status": "not_ready",
  "model": "openai/gpt-oss-120b",
  "api_key_configured": false,
  "langsmith_configured": false
}
```

---

### 3.4 Clear Conversation Session

* **Route:** `DELETE /api/chat/session/{session_id}`
* **Summary:** Clears all stored in-memory conversation history associated with the given session ID.

#### Parameters
| Parameter | In | Type | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `session_id` | Path | String (UUID) | Yes | Target session identifier to reset. |

#### Example Request
```bash
curl -X DELETE "http://localhost:8000/api/chat/session/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
```

#### Response (`200 OK`)
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "cleared"
}
```

---

## 4. Python SDK Usage Example

```python
import httpx
import uuid

BASE_URL = "http://localhost:8000"
session_id = str(uuid.uuid4())

def ask_question(prompt: str) -> str:
    payload = {
        "session_id": session_id,
        "message": prompt,
        "history": []
    }
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        response = client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["answer"]

# Turn 1
print("AI:", ask_question("Hello! My name is Alice."))
# Turn 2 (Session continuity preserved automatically)
print("AI:", ask_question("What is my name?"))
```
