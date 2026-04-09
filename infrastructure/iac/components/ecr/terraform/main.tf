provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      environment          = "${var.environment_name}"
      created_by_terraform = "true"
    }
  }
}

terraform {
  required_version = "1.14.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"

    }
  }

  backend "s3" {}
}
