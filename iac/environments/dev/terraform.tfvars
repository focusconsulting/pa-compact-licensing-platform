aws_region            = "us-east-1"
environment           = "dev"
vpc_cidr              = "10.0.0.0/16"
task_cpu              = "256"
task_memory           = "512"
desired_count         = 1
rds_instance_class    = "db.t4g.micro"
elasticache_node_type = "cache.t4g.micro"
