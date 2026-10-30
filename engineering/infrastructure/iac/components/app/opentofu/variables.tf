variable "tf_state_bucket" {
  description = "The state bucket this environment's components and its network bootstrap state live in"
  type        = string
}

variable "network_state_key" {
  description = "Key in tf_state_bucket of the bootstrap state that exports vpc_id and private_subnet_ids"
  type        = string
  default     = "bootstrap/network/default/terraform.tfstate"
}

variable "aws_region" {
  description = "The region to deploy to"
  type        = string
}

variable "environment_name" {
  description = "The environment: dev, staging, or prod. Names resources and secrets, and is the ENVIRONMENT the containers run with."
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment_name)
    error_message = "environment_name must be dev, staging, or prod."
  }
}

variable "db_instance_class" {
  description = "Aurora RDS instance class (must be Aurora-compatible, e.g. db.t3.medium)"
  type        = string
  default     = "db.t4g.medium"
}

variable "instance_count" {
  description = "Number of Aurora cluster instances to create"
  type        = number
  default     = 1
}

variable "backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 30
}

variable "db_username" {
  type        = string
  description = "Database master username"
}

variable "repo_name" {
  type        = string
  description = "ECR repository URI for the API container image"
}

variable "dns_name" {
  type        = string
  description = "Fully-qualified domain name for the site (e.g. site.dev-pacompact.aws.focusconsulting.io). This assumes there already exists a Route 53 hosted zone for the parent domain in this account and a wildcard certificate that will cover this dns name."
}

variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for HTTPS on the ALB listener (optional; HTTP-only if not set)"
  default     = null
}

variable "ecs_max_capacity" {
  type        = number
  description = "Maximum number of ECS Fargate tasks to scale to"
  default     = 2
}

variable "cognito_callback_url" {
  type        = string
  description = "Cognito OAuth callback URL (frontend login redirect). Defaults to https://<dns_name> if not set."
  default     = null
}

variable "cognito_logout_url" {
  type        = string
  description = "Cognito logout redirect URL. Defaults to https://<dns_name> if not set."
  default     = null
}

variable "jumpbox_enabled" {
  type        = bool
  description = "Allow ingress from the jumpbox whose security group ID is in the <environment>-jumpbox-sgid-tfvar secret. Only DEV has a jumpbox."
  default     = false
}

variable "commission_ops_email" {
  description = "The Commission mailbox for operational notifications (open question Q-14); empty sends none"
  type        = string
  default     = ""
}

variable "log_level" {
  description = "Log level for the API, the Worker, and scheduled jobs"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL."
  }
}
