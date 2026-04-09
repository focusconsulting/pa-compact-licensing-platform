output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (public entry point for both frontend and API)"
  value       = aws_cloudfront_distribution.frontend_distribution.domain_name
}

output "alb_dns_name" {
  description = "Internal ALB DNS name (accessible only from within the VPC)"
  value       = aws_lb.api_alb.dns_name
}

output "rds_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.rds_aurora_cluster.endpoint
}

output "rds_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.rds_aurora_cluster.reader_endpoint
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.app_cluster.name
}

output "client_assets_bucket" {
  description = "S3 bucket name for deploying the Next.js static export"
  value       = aws_s3_bucket.client_assets.bucket
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for API container logs"
  value       = aws_cloudwatch_log_group.api_logs.name
}
