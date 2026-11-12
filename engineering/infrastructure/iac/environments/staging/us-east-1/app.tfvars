# Identity
environment_name = "staging"
aws_region       = "us-east-1"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"
dns_name         = "site.dev-pacompact.aws.focusconsulting.io"

# Database
db_username             = "licensing"
db_instance_class       = "db.t4g.medium"
backup_retention_period = 1

# FSMB: the demo server outside prod
fsmb_api_url = "https://services-pdc-demo.fsmb.org"

# Compute: the ecr component's repository_url output for this environment; `just deploy` passes image_tag
repo_name = "126942145463.dkr.ecr.us-east-1.amazonaws.com/pacompact-app-staging"
