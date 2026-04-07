resource "aws_secretsmanager_secret" "app" {
  name = "${var.name}/app-config"
  tags = { Name = "${var.name}-app-config" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DB_PASSWORD = var.db_password
    REDIS_URL   = var.redis_url
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
