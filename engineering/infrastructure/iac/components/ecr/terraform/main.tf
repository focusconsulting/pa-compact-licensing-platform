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
  required_version = "1.14.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.42"

    }
  }

  backend "s3" {}
}
