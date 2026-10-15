# Kubernetes (EKS) Workload & Observability Deployment Guide

This directory contains the production-grade Kubernetes manifests for deploying the Q&A Chatbot and its dedicated OpenTelemetry Collector sidecar infrastructure to **Amazon EKS**.

---

## 1. Directory Structure

```
k8s/
├── namespace.yaml                     # Isolated 'qa-chatbot' namespace definition
├── service-account.yaml               # Workload ServiceAccounts with IRSA annotations
├── configmap.example.yaml             # Non-sensitive runtime parameters template
├── chatbot-deployment.yaml            # Backend (FastAPI) and Frontend (Nginx) Deployments
├── chatbot-service.yaml               # Internal ClusterIP services (backend & frontend)
├── chatbot-ingress.yaml               # AWS ALB Controller Ingress (private VPC scheme)
├── resource-quota.yaml                # Namespace CPU, Memory, and Pod saturation limits
├── network-policy.yaml                # Zero-trust microsegmentation rules
├── hpa.yaml                           # Horizontal Pod Autoscaler for FastAPI backend
├── pod-disruption-budget.yaml         # PDB ensuring minimum replica availability
├── otel-collector-serviceaccount.yaml # IRSA ServiceAccount for OpenTelemetry Collector
├── otel-collector-configmap.yaml      # ADOT Collector YAML configuration mount
├── otel-collector-deployment.yaml     # Pinned ADOT Collector Deployment (v0.40.0)
├── otel-collector-service.yaml        # Private ClusterIP service for OTLP gRPC/HTTP
└── README.md                          # This deployment documentation
```

---

## 2. Prerequisites

Before applying these manifests:
1. **Amazon EKS Cluster (v1.28+)** must be operational (see `infrastructure/terraform/`).
2. **Kubeconfig** must be configured for the target cluster:
   ```bash
   aws eks update-kubeconfig --region <AWS_REGION> --name <CLUSTER_NAME>
   ```
3. **AWS Load Balancer Controller** must be installed in the cluster if ingress is used.
4. **Kubernetes Metrics Server** must be installed if Horizontal Pod Autoscaling (`hpa.yaml`) is enabled:
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   ```
5. **IAM Roles for Service Accounts (IRSA)** must be provisioned in AWS IAM and ARNs updated in `service-account.yaml` and `otel-collector-serviceaccount.yaml`.

---

## 3. Placeholders Requiring Substitution

Search and replace the following placeholder tokens across all YAML files before applying:

| Placeholder | Example Value | Affected Files |
| :--- | :--- | :--- |
| `<AWS_ACCOUNT_ID>` | `123456789012` | `service-account.yaml`, `otel-collector-serviceaccount.yaml`, `chatbot-deployment.yaml` |
| `<AWS_REGION>` | `us-east-1` | `service-account.yaml`, `otel-collector-serviceaccount.yaml`, `chatbot-deployment.yaml`, `otel-collector-deployment.yaml` |

---

## 4. Step-by-Step Deployment Order

### Step 1: Create Namespace and Core Governance
```bash
# Apply namespace
kubectl apply -f k8s/namespace.yaml

# Apply resource quotas and pod disruption budgets
kubectl apply -f k8s/resource-quota.yaml
kubectl apply -f k8s/pod-disruption-budget.yaml
```

### Step 2: Create Secrets (Never Commit Real Keys to Git!)
```bash
# Create application secrets containing your real Groq API key
kubectl create secret generic chatbot-secrets \
  --namespace=qa-chatbot \
  --from-literal=GROQ_API_KEY='gsk_your_real_groq_key_here'

# Optional: Add LangSmith credentials if enabling hosted LangChain tracing
# kubectl create secret generic langsmith-secrets \
#   --namespace=qa-chatbot \
#   --from-literal=LANGSMITH_API_KEY='lsv2_pt_your_real_key_here'
```

### Step 3: Apply ConfigMap and Service Accounts
```bash
# Copy and customize non-sensitive configuration
kubectl apply -f k8s/configmap.example.yaml

# Apply workload ServiceAccounts with IRSA bindings
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/otel-collector-serviceaccount.yaml
```

### Step 4: Deploy OpenTelemetry Collector
```bash
# Apply Collector configuration and deployment
kubectl apply -f k8s/otel-collector-configmap.yaml
kubectl apply -f k8s/otel-collector-deployment.yaml
kubectl apply -f k8s/otel-collector-service.yaml

# Wait for collector readiness
kubectl rollout status deployment/otel-collector -n qa-chatbot --timeout=90s
```

### Step 5: Deploy Chatbot Application Workloads
```bash
# Deploy Backend API and Frontend Static Web servers
kubectl apply -f k8s/chatbot-deployment.yaml
kubectl apply -f k8s/chatbot-service.yaml

# Wait for backend and frontend rollout
kubectl rollout status deployment/chatbot-backend -n qa-chatbot --timeout=120s
kubectl rollout status deployment/chatbot-frontend -n qa-chatbot --timeout=60s
```

### Step 6: Apply Autoscaling, Microsegmentation, and Ingress
```bash
# Apply Horizontal Pod Autoscaler
kubectl apply -f k8s/hpa.yaml

# Apply Zero-Trust Network Policies
kubectl apply -f k8s/network-policy.yaml

# Apply AWS Application Load Balancer Ingress (Private VPC)
kubectl apply -f k8s/chatbot-ingress.yaml
```

---

## 5. Verification Commands (Manual Execution)

```bash
# Inspect all running pods, services, and endpoints in namespace
kubectl get pods,svc,ingress,hpa -n qa-chatbot -o wide

# Check OpenTelemetry Collector logs for exporter health
kubectl logs -l app.kubernetes.io/name=otel-collector -n qa-chatbot --tail=50 -f

# Check Backend API container logs
kubectl logs -l app.kubernetes.io/name=chatbot-backend -n qa-chatbot -c backend --tail=50 -f

# Verify that backend health checks return HTTP 200
kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl --namespace=qa-chatbot \
  -- curl -v http://backend:8000/api/health
```

---

## 6. Teardown / Cleanup Commands

```bash
# Delete all resources within the qa-chatbot namespace
kubectl delete -f k8s/chatbot-ingress.yaml
kubectl delete -f k8s/hpa.yaml
kubectl delete -f k8s/network-policy.yaml
kubectl delete -f k8s/chatbot-deployment.yaml
kubectl delete -f k8s/chatbot-service.yaml
kubectl delete -f k8s/otel-collector-deployment.yaml
kubectl delete -f k8s/otel-collector-service.yaml
kubectl delete -f k8s/otel-collector-configmap.yaml
kubectl delete -f k8s/service-account.yaml
kubectl delete -f k8s/otel-collector-serviceaccount.yaml
kubectl delete -f k8s/configmap.example.yaml
kubectl delete secret chatbot-secrets -n qa-chatbot
kubectl delete -f k8s/pod-disruption-budget.yaml
kubectl delete -f k8s/resource-quota.yaml
kubectl delete -f k8s/namespace.yaml
```
