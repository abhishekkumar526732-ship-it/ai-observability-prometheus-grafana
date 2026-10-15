# ==============================================================================
# Main Orchestration File for AWS AI Observability Infrastructure
# ==============================================================================
# This module provisions the complete AWS infrastructure for the Q&A Chatbot:
# - Dedicated VPC with Public/Private subnets across 2 AZs (networking.tf)
# - EKS Control Plane v1.29 with Managed Node Group (eks.tf)
# - IAM Roles for EKS, Worker Nodes, and OpenTelemetry Collector IRSA (iam.tf)
# - CloudWatch Log Groups for Audit, Application, and EMF metrics (cloudwatch.tf)
# - Amazon Managed Service for Prometheus (AMP) workspace (prometheus.tf)
# - Amazon Managed Grafana (AMG) workspace with IAM data source bindings (grafana.tf)
# ==============================================================================
