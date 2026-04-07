variable "name" {
  description = "Name prefix for all VPC resources"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
}

variable "single_nat" {
  description = "Use a single NAT gateway (cost savings for non-prod)"
  type        = bool
  default     = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}
