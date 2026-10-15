# Amazon Managed Grafana (AMG) Dashboards Guide

This directory contains pre-configured, production-grade JSON dashboard templates for **Amazon Managed Grafana (AMG)** or self-hosted Grafana.

---

## 1. Dashboards Overview

| Dashboard File | Title | Primary Data Source | Telemetry Source |
| :--- | :--- | :--- | :--- |
| [`dashboards/ai-service-dashboard.json`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/grafana/dashboards/ai-service-dashboard.json) | **AI Service & LLM Performance Dashboard** | CloudWatch Metrics / EMF | FastAPI Inbound Traffic, Latency P50/P90/P99, Groq Tokens & Cost |
| [`dashboards/cluster-dashboard.json`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/grafana/dashboards/cluster-dashboard.json) | **EKS Cluster & OpenTelemetry Collector Operations** | CloudWatch ContainerInsights | Kubernetes Pod CPU/Memory, Restarts, Collector OTLP Spans & Drop Rates |

---

## 2. ⚠️ Platform Telemetry vs Application-Level Metrics

To maintain full transparency and clean-room separation:

### Available Out-of-the-Box (Platform Telemetry):
* **HTTP Inbound Requests & Error Rates:** Captured by ALB Ingress and ContainerInsights.
* **Latency Percentiles (p50 / p90 / p99):** Ingress and ASGI request timing.
* **CPU and Memory Utilization:** Kubelet / ContainerInsights cgroup metrics.
* **Pod Restarts and CrashLoops:** Kubernetes kube-state-metrics.
* **OpenTelemetry Collector Telemetry:** OTLP receiver ingestion rates and exporter queue lengths.

### Application-Level Instrumentation & Observability:
* **Groq LLM Token Consumption (`llm.tokens.prompt`, `llm.tokens.completion`):** Extracted from model response metadata.
* **Estimated LLM Cost (`llm.cost.estimated`):** Calculated from token multiplication at runtime.
* **Model-Level Error Taxonomy (`llm.errors`):** Classifies Groq rate limits (HTTP 429) vs upstream timeouts (HTTP 504) vs invalid auth (HTTP 502).
* **LangSmith Integration:** Complete prompt, execution span, and evaluation tracing via `LANGSMITH_TRACING=true` in `qa-chatbot`.

---

## 3. Configuring Data Sources in Amazon Managed Grafana

### Step 1: Access Grafana Workspace
1. Retrieve the Grafana URL from Terraform outputs:
   ```bash
   terraform output grafana_endpoint
   ```
2. Sign in using AWS IAM Identity Center (AWS SSO).

### Step 2: Add CloudWatch Data Source
1. Navigate to **Administration -> Data Sources -> Add data source**.
2. Select **CloudWatch**.
3. Configure settings:
   * **Authentication Provider:** AWS SDK Default (AMG IAM execution role provisioned by Terraform).
   * **Default Region:** Set to your deployment region (e.g., `us-east-1`).
   * **Custom Metric Namespaces:** Enter `QAChatbot/AIPlatform` and `ContainerInsights`.
4. Click **Save & test**. Note the assigned Data Source UID (e.g. `cloudwatch-default`).

### Step 3: Add Amazon Managed Prometheus (Optional)
1. Add data source **Prometheus**.
2. Set **URL** to the AMP workspace endpoint:
   ```bash
   terraform output amp_remote_write_endpoint
   ```
3. Enable **SigV4 auth** and set **Default Region** to your AWS region.
4. Click **Save & test**.

---

## 4. Importing the Dashboards

1. In the Grafana side navigation, go to **Dashboards -> New -> Import**.
2. Click **Upload dashboard JSON file** and select `observability/grafana/dashboards/ai-service-dashboard.json`.
3. Select your configured CloudWatch data source when prompted.
4. Click **Import**.
5. Repeat the process for `observability/grafana/dashboards/cluster-dashboard.json`.
