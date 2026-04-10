This is the terraform code for standing up the PA Compact in AWS.  First it creates an ECR repository for the build pipeline to publish the packages.  Then it stands up the whole application, front end, backend and database.

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
