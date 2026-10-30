aws_region       = "us-east-1"
environment_name = "staging"
tf_state_bucket  = "focus-dev-pacompact-terraform-state"
repositories = [
  {
    name                 = "pacompact-app-staging"
    image_tag_mutability = "MUTABLE"
    scan_on_push         = true
  }
]
