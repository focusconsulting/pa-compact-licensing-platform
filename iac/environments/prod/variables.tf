variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "pa-compact-licensing"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.2.0.0/16"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "task_cpu" {
  type    = string
  default = "512"
}

variable "task_memory" {
  type    = string
  default = "1024"
}

variable "desired_count" {
  type    = number
  default = 2
}

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.small"
}

variable "elasticache_node_type" {
  type    = string
  default = "cache.t4g.small"
}
