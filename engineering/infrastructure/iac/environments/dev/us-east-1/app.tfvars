# Identity
environment_name = "dev"
aws_region       = "us-east-1"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"
dns_name         = "site.dev-pacompact.aws.focusconsulting.io"

# Database
db_username             = "licensing"
db_instance_class       = "db.t4g.medium"
backup_retention_period = 1

# Compute: the ecr component's repository_url output for this environment
repo_name = "126942145463.dkr.ecr.us-east-1.amazonaws.com/pacompact-app-dev"

# Access: dev has a jumpbox for SSM tunnels; its security group ID is in the dev-jumpbox-sgid-tfvar secret
jumpbox_enabled = true
