# Identity
environment_name = "staging"
aws_region       = "us-east-1"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"
dns_name         = "site.dev-pacompact.aws.focusconsulting.io"

# The wildcard certificate for the zone, in this environment's region, for the load balancer
acm_certificate_arn = "arn:aws:acm:us-east-1:126942145463:certificate/9445a6cd-f7f8-46eb-9a13-eeccc6d57a4b"

# Staging is spun up and torn down by design
deletion_protection = false

# Database
db_username             = "licensing"
db_instance_class       = "db.t4g.medium"
backup_retention_period = 1

# FSMB: the demo server outside prod
fsmb_api_url = "https://services-pdc-demo.fsmb.org"

# Compute: the ecr component's repository_url output for this environment; `just deploy` passes image_tag
repo_name = "126942145463.dkr.ecr.us-east-1.amazonaws.com/pacompact-app-staging"
