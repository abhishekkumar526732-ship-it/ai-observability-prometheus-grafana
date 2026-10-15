# LangSmith Integration Guide for Q&A Chatbot

## 1. Overview

**LangSmith** is an observability and LLM evaluation platform developed by LangChain. In this architecture, LangSmith serves as the **application-layer LLM diagnostic plane**, while **AWS CloudWatch** and **OpenTelemetry** handle infrastructure, container performance, and platform-level availability.

```
+---------------------------------------------------------------------------------+
|                                    Workload                                     |
|                                                                                 |
|   +------------------------------------+   +--------------------------------+   |
|   |         Infrastructure Layer       |   |       Application / LLM Layer  |   |
|   | (CPU, Memory, Pod Restarts, HTTP)  |   | (Prompts, Token Counts, LLM)   |   |
|   +-----------------+------------------+   +---------------+----------------+   |
+---------------------|--------------------------------------|--------------------+
                      |                                      |
                      v                                      v
       +------------------------------+       +------------------------------+
       |   OpenTelemetry Collector    |       |       Hosted LangSmith       |
       |  (Internal Cluster Service)  |       |     (api.smith.langchain.com)|
       +--------------+---------------+       +------------------------------+
                      |
                      v
       +------------------------------+
       |   AWS CloudWatch & Grafana   |
       +------------------------------+
```

---

## 2. Configuration Variables

When enabled via Kubernetes Secrets or container environment variables, LangSmith requires:

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `LANGSMITH_TRACING` | Yes | `false` | Global feature flag (`true` or `false`). |
| `LANGSMITH_API_KEY` | Yes | *None* | Personal or service account API key (`lsv2_pt_...`). |
| `LANGSMITH_PROJECT` | No | `default` | Logical workspace grouping for runs (e.g. `qa-chatbot-prod`). |
| `LANGSMITH_ENDPOINT` | No | `https://api.smith.langchain.com` | Host API URL for SaaS or private enterprise instances. |

> **Note on Compatibility:** LangChain SDK versions historically checked `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`. The modern LangSmith SDK accepts either `LANGSMITH_*` or `LANGCHAIN_*` prefixes. It is recommended to supply both or alias them to ensure compatibility across LangChain versions.

---

## 3. Application Integration & Local Diagnostics

**LangSmith tracing is natively integrated into the Q&A Chatbot service (`qa-chatbot`):**
- LangSmith tracing is controlled purely via configuration flags (`LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`).
- When disabled (the default), the service runs with zero overhead and does not emit traces to external endpoints.
- When enabled with a valid API key, the LangChain pipeline automatically records request latency, model tokens, session metadata, and system prompts to the configured project.
- To test tracing locally or run an offline diagnostic, execute:
  ```bash
  cd qa-chatbot
  python scripts/test_langsmith.py
  ```

---

## 4. Security & Secret Management

### Strict Security Rules:
1. **Never commit API keys** to Git repositories or push them in `.env` files.
2. **Never expose keys in client-side code** or the Nginx frontend static files.
3. **Use Kubernetes Secrets** in production:
   ```bash
   kubectl create secret generic langsmith-secrets \
     --namespace=qa-chatbot \
     --from-literal=LANGSMITH_API_KEY='lsv2_pt_your_real_key_here' \
     --from-literal=LANGSMITH_PROJECT='qa-chatbot-prod' \
     --from-literal=LANGSMITH_TRACING='true'
   ```
4. For AWS-native enterprise management, leverage **AWS Secrets Manager** synchronized via the **Kubernetes External Secrets Operator** or the **AWS Secrets Store CSI Driver**.

---

## 5. Data Privacy & Compliance Considerations

Because LangSmith is a hosted third-party SaaS platform (unless deploying LangSmith Enterprise on a private VPC), operators must consider the following compliance factors:

1. **Payload Ingestion:** By default, LangSmith captures complete human input queries, system prompts, and AI model outputs.
2. **Personally Identifiable Information (PII):** If end-users submit sensitive data, phone numbers, or credentials, this data is transmitted to LangSmith servers.
3. **Data Masking:** In enterprise deployments, an input-hiding callback or pre-submission scrubbing filter should be configured before sending traces to external endpoints.
4. **Data Retention:** Configure workspace retention limits (e.g., 14 days, 30 days, or 90 days) in the LangSmith console at `Settings -> Data Retention` to comply with internal privacy standards.
