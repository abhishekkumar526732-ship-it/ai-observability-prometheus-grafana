# 📊 Observability, Tracing & Cost Management

This guide details how telemetry, distributed tracing, metrics, and LLM diagnostic data are collected and visualized across the Q&A Chatbot platform.

---

## 1. Dual-Plane Observability Strategy

The architecture separates telemetry into two distinct planes to prevent overhead while maintaining complete transparency:

```
+-----------------------------------------------------------------------------------+
|                               Observability Planes                                |
+-----------------------------------------+-----------------------------------------+
|      Application / LLM Plane            |         Infrastructure Plane            |
|            (LangSmith)                  |  (OpenTelemetry + Prometheus + Grafana) |
+-----------------------------------------+-----------------------------------------+
| * Prompts & System Instructions         | * Pod CPU & Memory Utilization          |
| * Reasoning Steps & Tool Usage          | * Ingress Request Rate & 5xx Error Rate |
| * Prompt / Completion Token Counts      | * p50, p90, and p99 Latency Percentiles |
| * Execution Latency & Time-to-First-Tok | * Node Saturation & Pod CrashLoops      |
| * Output Evaluation & Datasets          | * Otel Collector Queue Saturation       |
+-----------------------------------------+-----------------------------------------+
```

---

## 2. Application Diagnostic Plane: LangSmith

### 2.1 How LangSmith Tracing Works

LangSmith is integrated into the application at two levels:

1. **Automatic SDK Synchronization (`app.config:setup_langsmith_tracing`):**
   When `LANGSMITH_TRACING=true` is present in `.env`, the startup process synchronizes Pydantic settings into process-level environment variables (`LANGCHAIN_TRACING_V2=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`).
   LangChain's internal callback manager automatically captures all invocations.
2. **Explicit Span Decoration (`app.services.llm_service`):**
   - The top-level method `generate_response()` is decorated with `@traceable(name="qa_chatbot_generate_response", run_type="chain")`.
   - The model invocation `client.ainvoke()` receives a dedicated `run_config` containing metadata (`session_id`, `model`, `temperature`) and tags (`["qa-chatbot", "groq", APP_ENV]`).

### 2.2 Trace Hierarchy

When a user submits a question, LangSmith renders a structured trace tree:

```
qa_chatbot_generate_response (Chain)
│  ├── Metadata: {session_id: "...", model: "openai/gpt-oss-120b"}
│  ├── Tags: ["qa-chatbot", "development"]
│  └── Duration: 245 ms
│
└── ChatGroq-openai/gpt-oss-120b (ChatModel)
   ├── System Prompt: "You are a helpful, professional..."
   ├── Human Message: "Explain Kubernetes pods"
   ├── Output Tokens: 82 | Prompt Tokens: 38 | Total: 120
   └── Latency: 232 ms
```

### 2.3 Local Diagnostic CLI (`scripts/test_langsmith.py`)

A built-in diagnostic tool allows testing your LangSmith integration before deploying:

```bash
# Test with live Groq query and push trace to LangSmith
python scripts/test_langsmith.py

# Test offline with mock trace (zero API keys/tokens required)
python scripts/test_langsmith.py --mock

# Test with a specific query
python scripts/test_langsmith.py --query "What is an API?"
```

---

## 3. Infrastructure Telemetry Plane: OpenTelemetry Collector

The OpenTelemetry Collector is deployed to the Kubernetes cluster as a DaemonSet/Deployment:

* **Config File:** [`observability/otel-collector/otel-collector-config.yaml`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/otel-collector/otel-collector-config.yaml)
* **Receivers:**
  - `otlp`: Receives gRPC (port 4317) and HTTP (port 4318) spans and metrics from container workloads.
  - `prometheus`: Scrapes internal endpoints and service monitors.
* **Processors:**
  - `batch`: Buffers telemetry in memory and flushes in batches (up to 1000 items or every 5 seconds) to minimize network I/O.
  - `memory_limiter`: Hard limit to prevent Collector pods from consuming excessive cluster RAM.
* **Exporters:**
  - `prometheus`: Exposes a Prometheus scrape target on port `8889`.
  - `awscloudwatchmetrics` / `awscloudwatchlogs`: Direct forwarder to CloudWatch in AWS deployments.

---

## 4. Visualizations: Grafana Dashboards

Pre-built dashboards are stored in JSON format ready for import into any Grafana instance:

### 4.1 AI Service Dashboard (`observability/grafana/dashboards/ai-service-dashboard.json`)
* **HTTP Requests & Ingress Rate:** Real-time request volume categorized by HTTP status code (`200 OK`, `422 Validation Error`, `429 Rate Limit`, `502 Provider Error`).
* **Latency Percentiles:** Live p50, p90, and p99 duration trends.
* **Token Usage Metrics:** Cumulative prompt tokens vs completion tokens.
* **Estimated LLM Spend:** Estimated cost based on Groq pricing metrics.

### 4.2 Cluster Infrastructure Dashboard (`observability/grafana/dashboards/cluster-dashboard.json`)
* **Pod CPU & Memory Utilization:** Identifies hot containers and assists in tuning HPA scaling thresholds.
* **Pod Restarts:** Visualizes crash loops and OOMKilled events.
* **Node Capacity:** Worker node CPU/Memory allocations against cluster limits.

---

## 5. Automated Alerting: CloudWatch Alarms

Pre-configured CloudWatch metric alarms are defined in [`observability/alerts/cloudwatch-alarms.json`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/alerts/cloudwatch-alarms.json):

| Alarm Name | Metric | Threshold | Action |
| :--- | :--- | :--- | :--- |
| **HighLatencyP99** | Ingress Latency (p99) | `> 3.0 seconds` for 2 consecutive periods (5 min) | SNS Alert -> On-call Pager |
| **HighHTTP5xxErrors** | Ingress 5xx Rate | `> 1%` of total requests for 3 consecutive minutes | SNS Alert -> High Severity |
| **PodCrashLooping** | Pod Restarts | `> 3 restarts` in 10 minutes | SNS Alert -> DevOps Warning |
| **ContainerCPUSaturation**| Pod CPU Utilization | `> 85%` for 5 minutes | SNS Alert -> Autoscaling Check |

---

## 6. LLM Cost Tracking Methodology

Groq LPU token-based costs are calculated per completion using token metrics extracted by `LLMService`:

$$\text{Request Cost} = \left(\frac{\text{Prompt Tokens}}{1{,}000{,}000} \times \text{Input Rate}\right) + \left(\frac{\text{Completion Tokens}}{1{,}000{,}000} \times \text{Output Rate}\right)$$

* **Token Extraction:** Every completion captures `prompt_tokens` and `completion_tokens` via `response.usage_metadata`.
* **LangSmith Cost Dashboard:** When `LANGSMITH_TRACING=true` is enabled, LangSmith automatically computes and visualizes cumulative dollar spend broken down by session, project, and model.
