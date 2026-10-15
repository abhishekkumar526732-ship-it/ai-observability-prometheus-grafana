# ==============================================================================
# Terraform Outputs
# ==============================================================================

output "aws_region" {
  description = "Target AWS deployment region."
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS Cluster identifier."
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint for the EKS control plane."
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to authenticate with the cluster."
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC provider used for IAM Roles for Service Accounts (IRSA)."
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "vpc_id" {
  description = "Identifier of the provisioned VPC."
  value       = aws_vpc.main.id
}

output "private_subnets" {
  description = "List of private subnet identifiers used by EKS worker nodes."
  value       = aws_subnet.private[*].id
}

output "public_subnets" {
  description = "List of public subnet identifiers used by ALBs."
  value       = aws_subnet.public[*].id
}

output "otel_collector_role_arn" {
  description = "IAM Role ARN for OpenTelemetry Collector IRSA (substitute into k8s manifests)."
  value       = aws_iam_role.otel_collector.arn
}

output "amp_workspace_id" {
  description = "Amazon Managed Service for Prometheus (AMP) workspace ID."
  value       = var.enable_managed_prometheus ? aws_prometheus_workspace.main[0].id : null
}

output "amp_remote_write_endpoint" {
  description = "AMP Prometheus remote write endpoint for OpenTelemetry Collector export."
  value       = var.enable_managed_prometheus ? "${aws_prometheus_workspace.main[0].prometheus_endpoint}api/v1/remote_write" : null
}

output "grafana_workspace_id" {
  description = "Amazon Managed Grafana (AMG) workspace ID."
  value       = var.enable_managed_grafana ? aws_grafana_workspace.main[0].id : null
}

output "grafana_endpoint" {
  description = "Amazon Managed Grafana URL."
  value       = var.enable_managed_grafana ? "https://${aws_grafana_workspace.main[0].endpoint}" : null
}
