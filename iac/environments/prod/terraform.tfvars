aws_region            = "us-east-1"
environment           = "prod"
vpc_cidr              = "10.2.0.0/16"
task_cpu              = "512"
task_memory           = "1024"
desired_count         = 2
rds_instance_class    = "db.t4g.small"
elasticache_node_type = "cache.t4g.small"
