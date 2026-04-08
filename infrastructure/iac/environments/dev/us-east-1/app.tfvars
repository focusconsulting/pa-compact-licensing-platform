aws_region       = "us-east-1"
environment_name = "dev"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"

# Database
db_username = "licensing"
db_password = "REPLACE_WITH_SECURE_PASSWORD"

# ECS — ECR image URI, e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/licensing-api
repo_name = "REPLACE_WITH_ECR_IMAGE_URI"

# Optional: supply an ACM certificate ARN to enable HTTPS on the ALB listener
# acm_certificate_arn = "arn:aws:acm:REGION:ACCOUNT_ID:certificate/CERTIFICATE_ID"

/*
The following vars existed in the focus-bootstrap repo version
but not sure if they apply here. We can add them back if needed.

db_instance_class       = "db.t3.medium"
allocated_storage       = "10"
backup_retention_period = 1
*/
