# OpenTelemetry Collector Deployment & Architecture Guide

## 1. Overview

This directory contains the production-ready OpenTelemetry Collector configuration for the Q&A Chatbot service running on AWS EKS. The OpenTelemetry Collector functions as a vendor-agnostic telemetry proxy, aggregator, and exporter, receiving metrics, traces, and logs from workloads and forwarding them to AWS native observability backends:
- **Amazon CloudWatch Metrics & Logs** (via Embedded Metric Format - EMF and CloudWatch Logs)
- **AWS X-Ray** (for distributed tracing)
- **Amazon Managed Service for Prometheus (AMP)** (for Prometheus-compatible metric storage)

```
+-------------------------------------------------------------+
|                        AWS EKS Cluster                      |
|                                                             |
|  +--------------------+         +------------------------+  |
|  |  Chatbot Backend   |         |    Chatbot Frontend    |  |
|  |  (FastAPI / 8000)  |         |     (Nginx / 80)       |  |
|  +---------+----------+         +-----------+------------+  |
|            | OTLP (gRPC:4317 / HTTP:4318)   | Logs       |  |
|            +-----------------------+        |            |  |
|                                    v        v            |  |
|                 +--------------------------------+       |  |
|                 |    OpenTelemetry Collector     |       |  |
|                 |    (ADOT / Contrib v0.40.0)    |       |  |
|                 +---------------+----------------+       |  |
+---------------------------------|---------------------------+
                                  |
         +------------------------+-----------------------+
         |                        |                       |
         v                        v                       v
+------------------+    +------------------+    +--------------------+
| Amazon CloudWatch|    |    AWS X-Ray     |    |   Amazon Managed   |
| (Metrics & Logs) |    | (Traces Backend) |    |  Prometheus (AMP)  |
+------------------+    +------------------+    +--------------------+
```

---

## 2. Collector Image Selection & Compatibility

### Recommended Image: AWS Distro for OpenTelemetry (ADOT)
- **Image Repository:** `public.ecr.aws/aws-observability/aws-otel-collector`
- **Pinned Version:** `v0.40.0`
- **Rationale:** The standard upstream OpenTelemetry Collector binary does **not** bundle proprietary AWS exporters (`awsemf`, `awsxray`). The ADOT Collector is hardened by AWS and includes native support for IAM Roles for Service Accounts (IRSA), SigV4 authentication for Amazon Managed Prometheus, and optimized CloudWatch EMF serialization.

### Upstream Alternative (Contrib):
- **Image:** `otel/opentelemetry-collector-contrib:0.100.0`
- *Note:* If using upstream Contrib, verify that `awsprometheusremotewrite` and `awsemf` extensions are enabled for the target architecture.

---

## 3. Network Architecture & Exposed Ports

The OpenTelemetry Collector runs as a dedicated Kubernetes Deployment exposed exclusively via a private `ClusterIP` Service within the cluster. **No collector ports are exposed through an external LoadBalancer or Ingress.**

| Port | Protocol | Purpose | Access Scope |
| :--- | :--- | :--- | :--- |
| `4317` | TCP / gRPC | OTLP gRPC telemetry receiver | Internal ClusterIP (`otel-collector.qa-chatbot.svc.cluster.local`) |
| `4318` | TCP / HTTP | OTLP HTTP telemetry receiver | Internal ClusterIP (`otel-collector.qa-chatbot.svc.cluster.local`) |
| `8888` | TCP / HTTP | Collector internal Prometheus metrics | Prometheus scrape only (Cluster internal) |
| `13133` | TCP / HTTP | Health check probe endpoint (`/`) | Kubelet liveness & readiness probes |
| `55679` | TCP / HTTP | zPages diagnostic endpoint | Development debugging only |

---

## 4. Pipeline Configuration Summary

The collector configuration in [otel-collector-config.yaml](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/otel-collector/otel-collector-config.yaml) sets up three isolated telemetry pipelines:

### 1. Traces Pipeline
* **Receivers:** `otlp` (gRPC: 4317, HTTP: 4318)
* **Processors:**
  * `memory_limiter`: Drops or backs off ingestion if RAM usage exceeds 80% (hard limit: 400 MiB).
  * `resource`: Enforces `service.name=qa-chatbot`, `service.namespace=qa-chatbot`, and appends cluster metadata.
  * `batch`: Batches spans (up to 8192 spans or 5 seconds) to minimize AWS API call overhead.
* **Exporters:** `awsxray` (forwards X-Ray segments using AWS SDK credentials provided by IRSA).

### 2. Metrics Pipeline
* **Receivers:** `otlp`, `prometheus` (self-monitoring on port 8888)
* **Processors:** `memory_limiter`, `resource`, `batch`
* **Exporters:**
  * `awsemf`: Translates standard OTLP metrics into Amazon CloudWatch Embedded Metric Format logs under the namespace `QAChatbot/AIPlatform`.
  * `prometheusremotewrite` (Optional): Forwards metrics to Amazon Managed Service for Prometheus using SigV4 authentication.

### 3. Logs Pipeline
* **Receivers:** `otlp`
* **Processors:** `memory_limiter`, `resource`, `batch`
* **Exporters:** `awscloudwatchlogs` (Pushes structured JSON log records to CloudWatch Log Group `/aws/eks/qa-chatbot/application`).

---

## 5. Security & IAM Requirements (IRSA)

The OpenTelemetry Collector pod authenticates against AWS APIs via **IAM Roles for Service Accounts (IRSA)** or **EKS Pod Identity**.

### Required IAM Policy: `QAChatbotOtelCollectorPolicy`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchMetricsAndEMF",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "QAChatbot/AIPlatform"
        }
      }
    },
    {
      "Sid": "CloudWatchLogsDelivery",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/eks/qa-chatbot/*"
    },
    {
      "Sid": "AWSXRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
        "xray:GetSamplingStatisticSummaries"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AmazonPrometheusRemoteWrite",
      "Effect": "Allow",
      "Action": [
        "aps:RemoteWrite",
        "aps:GetSeries",
        "aps:GetLabels",
        "aps:GetMetricMetadata"
      ],
      "Resource": "arn:aws:aps:*:*:workspace/*"
    }
  ]
}
```

---

## 6. Telemetry Separation of Concerns

* **Infrastructure & Platform Telemetry (Available Immediately):**
  * Container CPU, Memory, Network I/O, Pod restarts, and Kubelet container states.
  * Ingress HTTP status codes, request counts, and load balancer latency (via AWS Load Balancer Controller).
  * Collector internal health, memory saturation, and export drop counts.
* **Application & LLM Telemetry (Requires Application Instrumentation):**
  * Prompt tokens, completion tokens, and model latency per request.
  * Model error categories (Rate Limit 429 vs Provider 502 vs Timeout 504).
  * Cost tracking calculated from Groq token rates.
  * Detailed internal LangChain pipeline spans.
  *(Supported via application telemetry and LangSmith integration in `qa-chatbot`).*
