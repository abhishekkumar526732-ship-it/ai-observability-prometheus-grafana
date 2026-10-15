# 🌐 Observability & Cost Dashboard for an AI Service

An end-to-end, enterprise-ready platform integrating a high-performance **Q&A Chatbot** (FastAPI + LangChain + Groq LPUs) with full-stack **Kubernetes deployment**, **Terraform Infrastructure as Code (AWS EKS)**, and comprehensive **Observability & Cost Management** (OpenTelemetry, Prometheus, Grafana, CloudWatch, and LangSmith).

---

## 📁 Repository Directory Structure

```
.
├── .gitignore                      # Master git ignore rules (caches, secrets, TF state)
├── README.md                       # Master project overview & architectural index
│
├── docs/                           # Comprehensive Project Documentation
│   ├── README.md                   # Documentation index & architecture summary
│   ├── architecture.md             # System design, data flow & security boundaries
│   ├── api-reference.md            # Complete REST API specification & schemas
│   ├── observability-and-tracing.md# LangSmith, OpenTelemetry, Grafana & CloudWatch
│   ├── setup-and-deployment.md     # Local development & Kubernetes EKS runbook
│   └── testing-guide.md            # Automated testing & mocking guide
│
├── FDE-docs/                       # Forward Deployed Engineering (FDE) Suite
│   ├── README.md                   # Suite overview & stakeholder sign-off matrix
│   ├── BRD.md                      # Business Requirements Document (ROI, FinOps, SLAs)
│   ├── TRD.md                      # Technical Requirements Document (AWS EKS, Sizing, VPC)
│   └── SRD.md                      # Software Requirements Document (API Contracts, BDD)
│
├── infrastructure/                 # Infrastructure as Code (IaC)
│   └── terraform/                  # Terraform configurations for AWS EKS & services
│       ├── main.tf                 # Root Terraform provider & resource definitions
│       ├── eks.tf                  # Managed AWS EKS cluster & worker node groups
│       ├── networking.tf           # VPC, private/public subnets, NAT gateways
│       ├── prometheus.tf           # Managed Prometheus server deployment
│       ├── grafana.tf              # Managed Grafana instance configuration
│       ├── cloudwatch.tf           # CloudWatch log groups & metric alarms
│       ├── iam.tf                  # IRSA & least-privilege IAM roles
│       └── README.md               # Infrastructure deployment documentation
│
├── k8s/                            # Production Kubernetes Manifests
│   ├── namespace.yaml              # Dedicated 'qa-chatbot' namespace
│   ├── chatbot-deployment.yaml     # Application deployment with readiness/liveness probes
│   ├── chatbot-service.yaml        # ClusterIP service definition
│   ├── chatbot-ingress.yaml        # AWS ALB Ingress controller routing
│   ├── hpa.yaml                    # Horizontal Pod Autoscaler (CPU/Memory targets)
│   ├── network-policy.yaml         # Egress/Ingress zero-trust isolation
│   ├── pod-disruption-budget.yaml  # High availability guarantees during cluster upgrades
│   ├── otel-collector-*.yaml       # OpenTelemetry Collector Deployment & RBAC
│   └── README.md                   # Kubernetes deployment runbook
│
├── observability/                  # Monitoring, Alerting & Tracing Plane
│   ├── alerts/                     # CloudWatch alarms & alert specifications
│   │   ├── cloudwatch-alarms.json  # Pre-configured alarm definitions (P99, 5xx, CPU)
│   │   └── README.md               # Alarm thresholds and runbooks
│   ├── grafana/                    # Grafana dashboards & visualizations
│   │   ├── dashboards/             # Importable JSON dashboards (AI service & cluster)
│   │   └── README.md               # Grafana setup and query guide
│   ├── langsmith/                  # Application-layer LLM diagnostic plane
│   │   ├── env.example             # LangSmith environment variables guide
│   │   └── README.md               # Tracing, evaluation, and data privacy guide
│   └── otel-collector/             # OpenTelemetry telemetry ingestion pipeline
│       ├── otel-collector-config.yaml # Pipelines for traces, metrics, and logs
│       └── README.md               # Collector architecture and pipeline guide
│
└── qa-chatbot/                     # Conversational AI Application
    ├── .env                        # Active local environment configuration (git-ignored)
    ├── .env.example                # Template for environment variables
    ├── .gitignore                  # Application-specific git ignore
    ├── docker-compose.yml          # Local multi-container stack (Nginx + FastAPI)
    ├── README.md                   # Application guide, API reference, & quick start
    │
    ├── backend/                    # FastAPI + LangChain Backend Service
    │   ├── Dockerfile              # Hardened non-root Python 3.12 container image
    │   ├── pyproject.toml          # Test & linter configuration
    │   ├── requirements.txt        # Pinned Python dependencies (including LangSmith)
    │   ├── app/                    # Application source code
    │   │   ├── main.py             # FastAPI entrypoint, CORS, & error handlers
    │   │   ├── config.py           # Pydantic Settings with LangSmith auto-sync
    │   │   ├── api/                # API routers (/api/chat, /api/health, /api/ready)
    │   │   ├── schemas/            # Request/Response Pydantic validation models
    │   │   └── services/           # LLM orchestration & in-memory session management
    │   └── tests/                  # Automated pytest suite (100% mocked, 21 tests)
    │       ├── test_chat.py        # Chat completion & error translation tests
    │       ├── test_conversation.py# Context persistence & isolation tests
    │       ├── test_health.py      # Health & readiness probe tests
    │       └── test_langsmith.py   # LangSmith configuration & tracing tests
    │
    ├── frontend/                   # Responsive ChatGPT-Style Web UI
    │   ├── index.html              # Semantic HTML5 layout
    │   ├── nginx.conf              # Nginx reverse proxy configuration
    │   ├── css/style.css           # Glassmorphism dark/light design system
    │   └── js/                     # Vanilla JavaScript controllers & API client
    │
    └── scripts/                    # Diagnostic & Management Scripts
        └── test_langsmith.py       # Interactive LangSmith local testing CLI tool
```

---

## 🚀 Quick Navigation

| Layer | Path | Key Technologies | Documentation |
| :--- | :--- | :--- | :--- |
| **Documentation** | [`docs/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/) | Architecture, API, Observability, Deployment | [Docs Index](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/docs/README.md) |
| **FDE Suite** | [`FDE-docs/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/) | BRD, TRD, SRD, Stakeholder Matrix | [FDE Index](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/FDE-docs/README.md) |
| **Application** | [`qa-chatbot/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/) | FastAPI, LangChain, Groq LPUs, Vanilla JS | [App Readme](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/qa-chatbot/README.md) |
| **Observability** | [`observability/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/) | OpenTelemetry, Prometheus, Grafana, LangSmith | [Observability Guides](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/observability/) |
| **Kubernetes** | [`k8s/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/k8s/) | EKS Manifests, HPA, NetworkPolicy, PDB | [K8s Readme](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/k8s/README.md) |
| **Infrastructure**| [`infrastructure/`](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/infrastructure/) | Terraform, AWS VPC, EKS, CloudWatch | [Terraform Readme](file:///d:/Observability%20and%20cost%20dashboard%20for%20an%20AI%20service/infrastructure/terraform/README.md) |

---

## ⚡ Running the Chatbot Locally

```bash
# 1. Navigate to the application directory
cd qa-chatbot

# 2. Configure environment (Groq API Key + optional LangSmith Tracing)
cp .env.example .env
# Edit .env with your GROQ_API_KEY and LANGSMITH_API_KEY

# 3. Test LangSmith tracing & pipeline connectivity
python scripts/test_langsmith.py

# 4. Run automated test suite
python -m pytest backend/tests -v

# 5. Start development server
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the conversational UI!
