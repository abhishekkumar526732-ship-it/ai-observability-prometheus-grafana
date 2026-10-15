# CloudWatch Alarms & Cost Monitoring Architecture

## 1. Cost Taxonomy: AWS Infrastructure vs LLM Provider

When running an AI service on AWS, costs fall into **three distinct categories**. Conflating these leads to financial blind spots and inaccurate reporting:

```
+----------------------------------------------------------------------------------------------------+
|                                    TOTAL COST OF OWNERSHIP (TCO)                                   |
+--------------------------------------------------+-------------------------------------------------+
|               1. AWS INFRASTRUCTURE              |               2. AI PROVIDER BILLING            |
|                (Billed by Amazon)                |              (Billed directly by Groq)          |
+--------------------------------------------------+-------------------------------------------------+
| - Amazon EKS Control Plane ($73/mo)              | - Incurred at Groq Cloud (console.groq.com)     |
| - EC2 Worker Nodes (m5.large compute & memory)   | - Billed per million tokens (input & output)    |
| - AWS NAT Gateway ($32.40/mo + Data Processing)  | - Charged to your credit card or invoice        |
| - CloudWatch Logs Ingestion & Metrics Storage    | - NEVER appears on your AWS billing statement   |
| - Amazon Managed Prometheus (AMP) & Grafana (AMG)|                                                 |
+--------------------------------------------------+-------------------------------------------------+
|                                3. ESTIMATED IN-FLIGHT LLM COST                                     |
|                       (Derived from Token Telemetry in CloudWatch/Grafana)                         |
|  * Calculated in real-time: (Prompt_Tokens * Rate) + (Completion_Tokens * Rate)                    |
|  * Gives instantaneous visibility into per-request and per-user cost before monthly billing       |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. AWS Budget Setup (Infrastructure Spend)

To prevent AWS infrastructure bill shock, configure an AWS Budget using the AWS CLI or AWS Billing Console:

```bash
# Example AWS CLI command to create a $250.00 monthly infrastructure budget
# (Replace <AWS_ACCOUNT_ID> and <ALERT_EMAIL> with real values)
cat <<EOF > /tmp/budget.json
{
  "BudgetLimit": {
    "Amount": "250",
    "Unit": "USD"
  },
  "BudgetName": "QAChatbot-Monthly-Infrastructure-Budget",
  "BudgetType": "COST",
  "CostFilters": {},
  "CostTypes": {
    "IncludeCredit": false,
    "IncludeDiscount": true,
    "IncludeOtherSubscription": true,
    "IncludeRecurring": true,
    "IncludeRefund": false,
    "IncludeSubscription": true,
    "IncludeSupport": true,
    "IncludeTax": true,
    "IncludeUpfront": true,
    "UseBlended": false
  },
  "TimeUnit": "MONTHLY"
}
EOF

# Create budget (manual execution)
# aws budgets create-budget --account-id <AWS_ACCOUNT_ID> --budget file:///tmp/budget.json
```

---

## 3. CloudWatch Metric Alarms

The template file [`cloudwatch-alarms.json`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/alerts/cloudwatch-alarms.json) defines 5 mission-critical alerts:

| Alarm Name | Trigger Condition | Evaluation Window | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **`qa-chatbot-high-5xx-error-rate`** | HTTP 5xx errors >= 10 | 5 minutes | Backend crash, unhandled exceptions, or upstream Groq downtime. |
| **`qa-chatbot-high-p95-latency`** | p95 latency > 5000ms | 10 minutes | Extreme inference degradation, network congestion, or pod CPU throttling. |
| **`qa-chatbot-pod-crash-loop`** | Container restarts >= 3 | 15 minutes | OOMKills, failing liveness probes, or container configuration errors. |
| **`qa-chatbot-otel-collector-export-failure`** | Export failures >= 1 | 5 minutes | Collector cannot push metrics/logs to CloudWatch or X-Ray (check IRSA permissions). |
| **`qa-chatbot-estimated-daily-llm-spend-exceeded`** | Groq token cost > $25.00 | 24 hours | **[Requires Application Instrumentation]** Spikes in user traffic or prompt looping. |

### Applying Alarms via AWS CLI:
```bash
# Iterate through the alarm definitions and provision them in CloudWatch
aws cloudwatch put-metric-alarm \
  --alarm-name "qa-chatbot-high-5xx-error-rate" \
  --alarm-description "Triggers when HTTP 5xx error rate from the FastAPI backend exceeds threshold." \
  --namespace "QAChatbot/AIPlatform" \
  --metric-name "http.server.requests" \
  --dimensions Name=service.name,Value=qa-chatbot Name=http.status_code,Value=500 \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --treat-missing-data "notBreaching"
```

---

## 4. Optional SNS Alert Notification Channel

To route alarm triggers to an on-call email distribution list, Slack channel, or PagerDuty:

```bash
# 1. Create an SNS Topic
aws sns create-topic --name qa-chatbot-sre-alerts

# 2. Subscribe an operational email address
aws sns subscribe \
  --topic-arn arn:aws:sns:<AWS_REGION>:<AWS_ACCOUNT_ID>:qa-chatbot-sre-alerts \
  --protocol email \
  --notification-endpoint sre-alerts@example.com

# 3. Associate the SNS Topic ARN with the CloudWatch Alarms
# Pass --alarm-actions arn:aws:sns:<AWS_REGION>:<AWS_ACCOUNT_ID>:qa-chatbot-sre-alerts
```
