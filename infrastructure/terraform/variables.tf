# ==============================================================================
# Terraform Input Variables Definition
# ==============================================================================

variable "aws_region" {
  description = "AWS deployment region."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment lifecycle stage (e.g. development, staging, production, poc)."
  type        = string
  default     = "poc"
}

variable "cluster_name" {
  description = "Identifier for the Amazon EKS cluster."
  type        = string
  default     = "qa-chatbot-eks"
}

variable "kubernetes_version" {
  description = "Desired Kubernetes control plane version for EKS."
  type        = string
  default     = "1.29"
}

# ------------------------------------------------------------------------------
# Networking Variables
# ------------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "Base IPv4 CIDR block for the dedicated VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of public subnet CIDRs for ALBs and NAT Gateways (minimum 2 AZs)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of private subnet CIDRs for EKS worker nodes (minimum 2 AZs)."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

# ------------------------------------------------------------------------------
# EKS Managed Node Group Variables (POC Sizing)
# ------------------------------------------------------------------------------
variable "node_instance_types" {
  description = "EC2 instance types for the EKS managed node group (t3.medium is optimal for POCs)."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "Minimum count of worker nodes in the auto-scaling group."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum count of worker nodes in the auto-scaling group."
  type        = number
  default     = 3
}

variable "node_desired_size" {
  description = "Initial desired count of worker nodes (1 node for POC to minimize cost)."
  type        = number
  default     = 1
}

# ------------------------------------------------------------------------------
# Observability & Monitoring Toggles (POC Defaults)
# ------------------------------------------------------------------------------
variable "enable_cloudwatch_logging" {
  description = "Enable EKS control plane log streams to CloudWatch."
  type        = bool
  default     = true
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period in days for CloudWatch log groups (7 days for POC to minimize log costs)."
  type        = number
  default     = 7
}

variable "enable_managed_prometheus" {
  description = "Provision an Amazon Managed Service for Prometheus (AMP) workspace (set false for POC to save cost)."
  type        = bool
  default     = false
}

variable "enable_managed_grafana" {
  description = "Provision an Amazon Managed Grafana (AMG) workspace (set false for POC to save cost; use local Grafana instead)."
  type        = bool
  default     = false
}
