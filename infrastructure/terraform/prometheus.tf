# ==============================================================================
# Amazon Managed Service for Prometheus (AMP) Workspace
# Provides serverless, highly available Prometheus metric storage
# ==============================================================================

resource "aws_prometheus_workspace" "main" {
  count = var.enable_managed_prometheus ? 1 : 0

  alias = "${local.name_prefix}-amp"

  tags = local.common_tags
}
