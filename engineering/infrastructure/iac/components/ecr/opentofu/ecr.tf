
# Create ECR repositories based on the list of repositories provided
resource "aws_ecr_repository" "repos" {
  for_each = { for repo in var.repositories : repo.name => repo }

  name                 = each.value.name
  image_tag_mutability = each.value.image_tag_mutability
  image_scanning_configuration {
    scan_on_push = try(each.value.scan_on_push, true)
  }
}

# Deploys tag every image with its commit; superseded builds and old releases are pruned.
resource "aws_ecr_lifecycle_policy" "repos" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Untagged layers from superseded builds"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the newest 30 releases"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = { type = "expire" }
      },
    ]
  })
}
