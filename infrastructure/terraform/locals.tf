# ==============================================================================
# Local Constants and Computed Values
# ==============================================================================

locals {
  name_prefix = "${var.cluster_name}-${var.environment}"

  # Availability zones derived dynamically from the selected AWS region
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = {
    Project     = "qa-chatbot"
    Environment = var.environment
    ManagedBy   = "terraform"
    Platform    = "ai-observability"
  }
}
