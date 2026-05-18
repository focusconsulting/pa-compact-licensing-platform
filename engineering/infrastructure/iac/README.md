# PA Compact infrastructure

This is the terraform code for standing up the PA Compact in AWS.

## Pre-requesite

Your terminal AWS client must be authenticated to the account associated with
the environment you will be working with.

## Viewing and Applying Terraform

Until a pipeline has been created to run this, you must run this manually

1. cd infrastructure/iac/components/<component>/terraform
2. terraform init -backend-config=../../../environments/dev/us-east-1/<component>.backend.hcl
3. terraform plan -var-file=../../../environments/dev/us-east-1/<component>.tfvars
4. terraform apply -var-file=../../../environments/dev/us-east-1/<component>.tfvars
