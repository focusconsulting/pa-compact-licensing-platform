This is the terraform code for standing up the PA Compact in AWS.  First it creates an ECR repository for the build pipeline to publish the packages.  Then it stands up the whole application, front end, backend and database.

Until a pipeline has been created to run this, it must be run manually with the following steps

```
cd infrastructure/iac/components/ecr/terraform
terraform init -backend-config=../../../environments/dev/us-east-1/ecr.backend.hcl
terraform  plan -var-file=../../../environments/dev/us-east-1/ecr.tfvars
terraform apply -var-file=../../../environments/dev/us-east-1/ecr.tfvars
cd ../../app/terraform
terraform init -backend-config=../../../environments/dev/us-east-1/app.backend.hcl
terraform  plan -var-file=../../../environments/dev/us-east-1/app.tfvars
terraform apply -var-file=../../../environments/dev/us-east-1/app.tfvars
```
