# Terraform AWS EKS & AI Observability Infrastructure

This directory contains modular, production-ready **Terraform** configuration for provisioning the complete AWS cloud platform required by the Q&A Chatbot, including VPC networking, Amazon EKS, IAM Roles for Service Accounts (IRSA), CloudWatch log groups, Amazon Managed Service for Prometheus (AMP), and Amazon Managed Grafana (AMG).

---

## 1. Provisioned Architecture Components

```
+--------------------------------------------------------------------------------------------------+
|                                        AWS Cloud Region                                          |
|                                                                                                  |
|  +--------------------------------------------------------------------------------------------+  |
|  |                                  Dedicated VPC (10.0.0.0/16)                               |  |
|  |                                                                                            |  |
|  |   +--------------------------+                     +---------------------------+           |  |
|  |   | Public Subnet (AZ A)     |                     | Public Subnet (AZ B)      |           |  |
|  |   | [Internet Gateway, NAT]  |                     | [ALB Ingress Placement]   |           |  |
|  |   +-------------+------------+                     +-------------+-------------+           |  |
|  |                 | (NAT Gateway Outbound Route)                   |                         |  |
|  |   +-------------v------------+                     +-------------v-------------+           |  |
|  |   | Private Subnet (AZ A)    |                     | Private Subnet (AZ B)     |           |  |
|  |   | [EKS Worker Node A]      |                     | [EKS Worker Node B]       |           |  |
|  |   +--------------------------+                     +---------------------------+           |  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                                                                  |
|   +-------------------------+    +--------------------------+    +----------------------------+  |
|   |   Amazon EKS Cluster    |    | Amazon CloudWatch Groups |    | Amazon Managed Prometheus  |  |
|   | (v1.29 / KMS Encrypted) |    |  (Audit, App, EMF Logs)  |    |      (AMP Workspace)       |  |
|   +-------------------------+    +--------------------------+    +----------------------------+  |
|                                                                                                  |
|   +---------------------------------------------------------+    +----------------------------+  |
|   |         IAM Roles for Service Accounts (IRSA)           |    |   Amazon Managed Grafana   |  |
|   |       (OIDC Federation for OpenTelemetry Pods)          |    |      (AMG Workspace)       |  |
|   +---------------------------------------------------------+    +----------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. ⚠️ Important Cost & Billing Warnings

Provisioning these resources will incur recurring charges on your AWS bill. Estimated baseline cost:

| Component | Minimum Hourly / Monthly Rate | Billing Model | Cost Reduction Strategy |
| :--- | :--- | :--- | :--- |
| **Amazon EKS Control Plane** | $0.10 / hr (~$73.00 / month) | Fixed per active cluster | Destroy when not in use (`terraform destroy`). |
| **AWS NAT Gateway** | $0.045 / hr (~$32.40 / month) + Data | Hourly + $0.045 / GB processed | Configured as single NAT Gateway across AZs. |
| **EC2 Worker Nodes (2x m5.large)** | ~$0.096 / hr each (~$140 / month) | Per instance hour | Use Spot instances or scale node group to 1 node for testing. |
| **Amazon CloudWatch Logs** | $0.50 / GB ingested | Pay per GB data ingested | Log retention configured to 30 days. |
| **Amazon Managed Prometheus** | $0.90 per 10M samples ingested | Pay per metric sample | Can be toggled off (`enable_managed_prometheus = false`). |
| **Amazon Managed Grafana** | $9.00 / active editor user / month | Per licensed user / month | Can be toggled off (`enable_managed_grafana = false`). |

---

## 3. Remote State Management Recommendation

For production team environments, store Terraform state in a remote encrypted S3 bucket with DynamoDB state locking to prevent concurrent state corruption.

Uncomment the `backend "s3"` block in `versions.tf` after creating the prerequisites:
```bash
# 1. Create dedicated S3 bucket
aws s3api create-bucket \
  --bucket my-company-tf-state-ai-platform \
  --region us-east-1

# 2. Enable bucket versioning and server-side encryption
aws s3api put-bucket-versioning \
  --bucket my-company-tf-state-ai-platform \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket my-company-tf-state-ai-platform \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

# 3. Create DynamoDB locking table
aws dynamodb create-table \
  --table-name my-company-tf-locks-ai-platform \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## 4. Execution Workflow (Manual Step-by-Step)

> **Notice:** Terraform files are generated for manual execution. **No infrastructure has been provisioned automatically.**

### Step 1: Initialize Working Directory
```bash
cd infrastructure/terraform
terraform init
```

### Step 2: Validate Syntax and Configuration
```bash
terraform validate
```

### Step 3: Create Variable File & Review Plan
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your chosen region and cluster parameters

# Generate an execution plan
terraform plan -out=tfplan
```

### Step 4: Apply (Requires Human Confirmation)
```bash
# Apply only after careful review of all resources and cost implications
terraform apply tfplan
```

### Step 5: Export Outputs to Kubeconfig
```bash
# Configure local kubectl access using the Terraform output values
aws eks update-kubeconfig \
  --region $(terraform output -raw aws_region) \
  --name $(terraform output -raw cluster_name)

# Verify cluster nodes
kubectl get nodes
```

---

## 5. Teardown / Destruction Workflow

To decommission all cloud resources and stop recurring AWS charges:

```bash
# 1. First delete all Kubernetes applications, ALBs, and namespaces
kubectl delete -f ../../k8s/chatbot-ingress.yaml
kubectl delete -f ../../k8s/namespace.yaml

# 2. Destroy all Terraform infrastructure
cd infrastructure/terraform
terraform destroy
```
