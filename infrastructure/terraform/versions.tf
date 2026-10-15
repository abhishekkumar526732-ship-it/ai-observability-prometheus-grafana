# ==============================================================================
# Terraform Core and Provider Version Constraints
# ==============================================================================

terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.28"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Recommended Remote State Backend Configuration (Configure in backend.tf or CLI)
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "ai-platform/eks/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "your-terraform-locks-table"
  #   encrypt        = true
  # }
}
