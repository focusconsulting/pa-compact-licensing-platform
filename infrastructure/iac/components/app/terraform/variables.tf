variable "tf_state_bucket" {
  description = "state bucket"
  type        = string
  default     = "focus-dev-pacompact-terraform-state"
}

variable "aws_region" {
  description = "The region to deploy to"
  type        = string
}

variable "environment_name" {
  description = "The environment to deploy to. (dev | stage | prod)"
  type        = string
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

variable "db_password" {
  type        = string
  description = "Database master password"
  sensitive   = true
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

variable "jumpbox_sg_id" {
  type        = string
  description = "Security group ID of the EC2 jumpbox. When set, allows SSM port-forward tunnels from the jumpbox to reach ECS tasks on port 8000."
  default     = null
}

variable "slack_team_id" {
  type        = string
  description = "Slack team (workspace) ID for AWS Chatbot (authorize workspace in Chatbot console first; format: TXXXXXXXXX)"
  default     = null
}

variable "slack_channel_id" {
  type        = string
  description = "Slack channel ID to receive API alerts (format: CXXXXXXXXX)"
  default     = null
}

variable "ecs_max_capacity" {
  type        = number
  description = "Maximum number of ECS Fargate tasks to scale to"
  default     = 2
}

variable "cognito_callback_url" {
  type        = string
  description = "Cognito OAuth callback URL (frontend login redirect)"
}

variable "cognito_logout_url" {
  type        = string
  description = "Cognito logout redirect URL"
}
