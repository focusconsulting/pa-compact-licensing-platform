output "ecr_repositories" {
  description = "A map of created ECR repositories with their names as keys and details as values."
  value = {
    for repo in aws_ecr_repository.repos : repo.name => {
      repository_url = repo.repository_url
      repository_arn = repo.arn
    }
  }
}
