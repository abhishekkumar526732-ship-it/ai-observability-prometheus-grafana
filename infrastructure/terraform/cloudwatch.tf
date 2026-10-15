# ==============================================================================
# Amazon CloudWatch Log Groups & Telemetry Infrastructure
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. EKS Control Plane Log Group
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = local.common_tags
}

# ------------------------------------------------------------------------------
# 2. Application Container Logs Group (Written by OpenTelemetry Collector)
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "chatbot_app_logs" {
  name              = "/aws/eks/qa-chatbot/application"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = local.common_tags
}

# ------------------------------------------------------------------------------
# 3. CloudWatch EMF Metrics Log Group (Embedded Metric Format)
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "chatbot_metrics" {
  name              = "/aws/eks/qa-chatbot/metrics"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = local.common_tags
}
