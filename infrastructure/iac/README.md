# PA Compact infrastructure

This is the terraform code for standing up the PA Compact in AWS.

## Pre-requesite

Your terminal AWS client must be authenticated to the account associated with
the environment you will be working with.

## Viewing and Applying Terraform

Until a pipeline has been created to run this, use the interactive helper script:

```
infrastructure/gen-tf-plan.py
```

Run it from anywhere. It will:
1. Prompt you to select a component (`app`, `ecr`, etc.) and environment
2. Run `terraform init` automatically if it has not been run yet
3. Prompt for any required variables not present in the tfvars file
4. Print the full `terraform plan` command it will run, followed by the equivalent `apply` command
5. Offer to run the plan immediately

To make changes, substitute `plan` → `apply` in the printed command and run it from the same directory.

## Viewing details

To see details such as:
- alb_dns_name
- client_assets_bucket
- cloudfront_distribution_id
- cloudfront_domain_name
- cloudwatch_log_group
- ecs_cluster_name
- rds_endpoint
- rds_reader_endpoint
- redis_endpoint

Execute `terraform output` in the appropriate component directory. For example:

```
cd /infrastructure/iac/components/[app|ecr]/terraform
terraform output
```
