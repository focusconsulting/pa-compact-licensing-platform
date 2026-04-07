variable "name" { type = string }

variable "db_password" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}
