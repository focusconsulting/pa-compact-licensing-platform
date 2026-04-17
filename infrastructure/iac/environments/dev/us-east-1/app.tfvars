aws_region       = "us-east-1"
environment_name = "dev"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"
dns_name        = "site.dev-pacompact.aws.focusconsulting.io"

# Database
db_username = "licensing"
db_password = "password"
db_instance_class       = "db.t4g.medium"
backup_retention_period = 1

# ECS — ECR image URI, e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/licensing-api
repo_name = "126942145463.dkr.ecr.us-east-1.amazonaws.com/pacompact-app-dev"

# Cognito
# cognito_callback_url = "https://d1kdkdkddk.cloudfront.net"
# cognito_logout_url   = "https://d1kdkdkddk.cloudfront.net"

# Optional: supply an ACM certificate ARN to enable HTTPS on the ALB listener
# acm_certificate_arn = "arn:aws:acm:REGION:ACCOUNT_ID:certificate/CERTIFICATE_ID"

# Slack alerting via AWS Chatbot — authorize workspace in Chatbot console first, then fill in IDs
# slack_team_id  = "TXXXXXXXXX"
# slack_channel_id = "CXXXXXXXXX"
