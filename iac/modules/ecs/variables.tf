variable "name" { type = string }
variable "aws_region" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }

variable "ecr_repository_url" { type = string }

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "container_name" {
  type    = string
  default = "api"
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "task_cpu" {
  type    = string
  default = "256"
}

variable "task_memory" {
  type    = string
  default = "512"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "log_level" {
  type    = string
  default = "INFO"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "db_host" { type = string }

variable "db_port" {
  type    = number
  default = 5432
}

variable "db_name" {
  type    = string
  default = "licensing"
}

variable "db_user" {
  type    = string
  default = "licensing"
}

variable "secret_arn" { type = string }

variable "task_security_group_id" {
  type        = string
  description = "Security group ID for ECS tasks (created at environment level to avoid circular deps)"
}
