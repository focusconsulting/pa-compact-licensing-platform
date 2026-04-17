resource "aws_iam_role" "cognito_user_import" {
  name = "${var.environment_name}-cognito-user-import"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cognito-idp.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "cognito_user_import_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.cognito_user_import.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents",
        "logs:GetLogEvents",
        "logs:FilterLogEvents",
      ]
      Resource = "arn:aws:logs:${data.aws_region.current.name}:*:log-group:/aws/cognito/*"
    }]
  })
}

resource "aws_cognito_user_pool" "main" {
  name = "${var.environment_name}-licensing"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.environment_name}-licensing-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  callback_urls = [var.cognito_callback_url]
  logout_urls   = [var.cognito_logout_url]

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",      # used by amazon-cognito-identity-js in the browser
    "ALLOW_USER_PASSWORD_AUTH", # enables AWS CLI token fetch for local testing — remove in production
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}
