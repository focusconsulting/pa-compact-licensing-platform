variable "tf_state_bucket" {
  description = "The state bucket this environment's components live in"
  type        = string
}

variable "aws_region" {
  description = "The region to deploy to"
  type        = string
}

variable "environment_name" {
  description = "The environment: dev, test, or prod. Names the repositories."
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment_name)
    error_message = "environment_name must be dev, test, or prod."
  }
}

variable "repositories" {
  description = "The ECR repositories to create"
  type = list(object({
    name                 = string
    image_tag_mutability = string
    scan_on_push         = bool
  }))
}
