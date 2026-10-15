# ==============================================================================
# Terraform Provider Initializations
# ==============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Data source for current AWS caller identity (avoids hardcoding account IDs)
data "aws_caller_identity" "current" {}

# Data source for available availability zones in the chosen region
data "aws_availability_zones" "available" {
  state = "available"
}

# Optional Kubernetes provider authenticated against the provisioned EKS cluster
provider "kubernetes" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.main.name]
    command     = "aws"
  }
}
