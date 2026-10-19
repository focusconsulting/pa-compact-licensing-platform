resource "aws_secretsmanager_secret" "cognito_config" {
  name = "${var.environment_name}-cognito-config"
}

resource "aws_secretsmanager_secret_version" "cognito_config_version" {
  secret_id = aws_secretsmanager_secret.cognito_config.id
  secret_string = jsonencode({
    user_pool_id = aws_cognito_user_pool.main.id
    client_id    = aws_cognito_user_pool_client.web.id
    region       = var.aws_region
  })
}

# Create the secret in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "${var.environment_name}-db-credentials"
}

# The master password is generated here and lives only in Secrets Manager (and
# the encrypted state). To rotate it, replace the resource:
#   terraform apply -replace=random_password.db_master
# then force a new ECS deployment so tasks pick up the new secret.
resource "random_password" "db_master" {
  length  = 32
  special = true
  # RDS rejects '/', '@', '"' and spaces in master passwords.
  override_special = "!#$%^&*()-_=+[]{}<>:?"
}

# Store the secret values (DB Username & Password)
resource "aws_secretsmanager_secret_version" "db_credentials_version" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_master.result
  })
}
