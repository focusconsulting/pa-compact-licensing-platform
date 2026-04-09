variable "tf_state_bucket" {
  description = "The name of the S3 bucket to store Terraform state"
  default= "focus-dev-pacompact-terraform-state"
}

variable "aws_region" {
  description = "The AWS region where the infrastructure will be deployed"
  default= "us-east-1"
}

variable "environment_name" {
  description = "The environment where the infrastructure will be deployed (dev, stage, prod)"
}

variable "repositories" {
  description = "A list of ECR repositories to be created"
  type = list(object({
    name                 = string
    image_tag_mutability = string
    scan_on_push         = bool  # Optional, defaults to true if not provided
  }))
}
