# 🚀 Setup & Deployment Guide

This guide covers running the Q&A Chatbot across different environments: locally without Docker, with multi-container Docker Compose, and on production Kubernetes (AWS EKS).

---

## 1. Prerequisites

* **Python:** 3.12 or higher.
* **Package Manager:** `pip` (or `uv` / `poetry`).
* **Container Runtime:** Docker 24+ and Docker Compose v2 (optional for containerized run).
* **Cloud CLI:** `kubectl` and `aws-cli` (optional for Kubernetes deployment).
* **Groq API Key:** Obtain free from [console.groq.com/keys](https://console.groq.com/keys).
* **LangSmith API Key:** *(Optional)* Obtain from [smith.langchain.com/settings](https://smith.langchain.com/settings).

---

## 2. Option A: Run Locally (Native Python)

The FastAPI backend automatically detects and serves the frontend static web UI directly on port `8000`.

### Step 1: Clone and Configure Environment
```bash
cd qa-chatbot
cp .env.example .env
```
Edit `.env` and fill in your keys:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_langsmith_key_here
```

### Step 2: Install Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

### Step 3: Start Development Server
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

* **Web Chat UI:** [http://localhost:8000](http://localhost:8000)
* **Swagger API Playground:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Readiness Check:** [http://localhost:8000/api/ready](http://localhost:8000/api/ready)

---

## 3. Option B: Run with Docker Compose

Runs an isolated multi-container stack with Nginx as a reverse proxy on port 3000 and FastAPI on port 8000:

```bash
cd qa-chatbot

# Build and start services in the background
docker compose up --build -d

# Check running container health status
docker compose ps

# View live application logs
docker compose logs -f

# Shut down the stack
docker compose down
```

* **Web Chat UI (via Nginx):** [http://localhost:3000](http://localhost:3000)
* **Backend API (Direct):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Option C: Production Kubernetes Deployment (AWS EKS)

The [`k8s/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/k8s/) directory contains hardened manifests for production deployments.

### Step 1: Create Namespace & Secrets
```bash
# Create dedicated namespace
kubectl apply -f k8s/namespace.yaml

# Create Groq credentials secret
kubectl create secret generic groq-secrets \
  --namespace=qa-chatbot \
  --from-literal=GROQ_API_KEY='gsk_your_actual_groq_api_key'

# Create optional LangSmith secret
kubectl create secret generic langsmith-secrets \
  --namespace=qa-chatbot \
  --from-literal=LANGSMITH_API_KEY='lsv2_pt_your_actual_key' \
  --from-literal=LANGSMITH_PROJECT='qa-chatbot-prod' \
  --from-literal=LANGSMITH_TRACING='true'
```

### Step 2: Apply Kubernetes Manifests
```bash
# Apply ConfigMap, ServiceAccount, and ResourceQuota
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/resource-quota.yaml

# Apply Deployment & ClusterIP Service
kubectl apply -f k8s/chatbot-deployment.yaml
kubectl apply -f k8s/chatbot-service.yaml

# Apply Horizontal Pod Autoscaler (HPA) & Zero-Trust NetworkPolicy
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/pod-disruption-budget.yaml

# Apply AWS ALB Ingress
kubectl apply -f k8s/chatbot-ingress.yaml
```

### Step 3: Monitor Rollout & Health
```bash
# Check rollout status
kubectl rollout status deployment/qa-chatbot-backend -n qa-chatbot

# Verify pods are healthy and running
kubectl get pods -n qa-chatbot -l app=qa-chatbot

# Inspect logs
kubectl logs -n qa-chatbot -l app=qa-chatbot -c backend -f
```

---

## 5. Complete Environment Variables Reference

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | String | *(Required)* | Groq API Key for model inference (`gsk_...`). |
| `GROQ_MODEL` | String | `openai/gpt-oss-120b` | Model identifier configured on Groq LPUs. |
| `REASONING_EFFORT` | String | `medium` | Optional reasoning effort (`none`, `low`, `medium`, `high`). |
| `APP_ENV` | String | `development` | Runtime mode: `development`, `staging`, `production`, `test`. |
| `APP_HOST` | String | `0.0.0.0` | Binding interface for ASGI server. |
| `APP_PORT` | Integer| `8000` | Port for ASGI server. |
| `LLM_TEMPERATURE` | Float | `0.2` | Sampling temperature (`0.0` to `2.0`). |
| `LLM_MAX_TOKENS` | Integer| `1024` | Maximum tokens per completion response. |
| `LLM_TIMEOUT_SECONDS`| Float | `60.0` | Maximum wait time for LLM API response. |
| `MAX_MESSAGE_LENGTH` | Integer| `4000` | Maximum characters permitted per query. |
| `MAX_HISTORY_TURNS` | Integer| `10` | Maximum conversation turns stored in memory. |
| `LANGSMITH_TRACING` | Boolean| `true` | Enables/disables LangSmith trace recording. |
| `LANGSMITH_API_KEY` | String | *(Optional)* | LangSmith personal/service account API key (`lsv2_pt_...`). |
| `LANGSMITH_PROJECT` | String | `qa-chatbot-local`| Workspace project grouping in LangSmith. |
| `LANGSMITH_ENDPOINT`| String | `https://api.smith.langchain.com` | LangSmith cloud or private enterprise endpoint. |
