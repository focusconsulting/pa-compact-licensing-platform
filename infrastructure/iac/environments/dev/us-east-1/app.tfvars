aws_region       = "us-east-1"
environment_name = "dev"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"

# Database
db_username = "licensing"
db_password = "password"
db_instance_class       = "db.t4g.medium"
backup_retention_period = 1

# ECS — ECR image URI, e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/licensing-api
repo_name = "126942145463.dkr.ecr.us-east-1.amazonaws.com/pacompact-app-dev"

# Optional: supply an ACM certificate ARN to enable HTTPS on the ALB listener
# acm_certificate_arn = "arn:aws:acm:REGION:ACCOUNT_ID:certificate/CERTIFICATE_ID"
