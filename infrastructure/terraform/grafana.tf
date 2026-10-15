# ==============================================================================
# Amazon Managed Grafana (AMG) Workspace & IAM Roles
# ==============================================================================

# ------------------------------------------------------------------------------
# IAM Role for Amazon Managed Grafana to Query CloudWatch and AMP
# ------------------------------------------------------------------------------
resource "aws_iam_role" "grafana" {
  count = var.enable_managed_grafana ? 1 : 0
  name  = "${local.name_prefix}-grafana-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "grafana.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_policy" "grafana_cloudwatch_query" {
  count       = var.enable_managed_grafana ? 1 : 0
  name        = "${local.name_prefix}-grafana-cloudwatch-policy"
  description = "Allows Grafana workspace to query metrics and logs from CloudWatch and AMP"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchMetricsAndLogsRead"
        Effect = "Allow"
        Action = [
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:ListMetrics",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "logs:DescribeLogGroups",
          "logs:GetLogGroupFields",
          "logs:StartQuery",
          "logs:StopQuery",
          "logs:GetQueryResults",
          "logs:GetLogEvents"
        ]
        Resource = "*"
      },
      {
        Sid    = "PrometheusQueryAccess"
        Effect = "Allow"
        Action = [
          "aps:QueryMetrics",
          "aps:GetSeries",
          "aps:GetLabels",
          "aps:GetMetricMetadata"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "grafana_cloudwatch" {
  count      = var.enable_managed_grafana ? 1 : 0
  policy_arn = aws_iam_policy.grafana_cloudwatch_query[0].arn
  role       = aws_iam_role.grafana[0].name
}

# ------------------------------------------------------------------------------
# Amazon Managed Grafana Workspace
# ------------------------------------------------------------------------------
resource "aws_grafana_workspace" "main" {
  count                    = var.enable_managed_grafana ? 1 : 0
  name                     = "${local.name_prefix}-grafana"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = aws_iam_role.grafana[0].arn
  data_sources             = ["CLOUDWATCH", "PROMETHEUS"]

  tags = local.common_tags
}
