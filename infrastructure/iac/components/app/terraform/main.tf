provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      environment          = "${var.environment_name}"
      created-by-terraform = "true"
    }
  }
}

terraform {
  required_version = "1.10.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.49.0"

    }
  }

  backend "s3" {}
}

# All Focus accounts are setup with a default VPC and this module will use that.
# The VPC's characteristics (e.g. vpc id, subnet cidrs, ...) can be read from the 
# terraform state bucket.
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = var.tf_state_bucket
    key    = "bootstrap/network/default/terraform.tfstate"
    region = var.aws_region
  }
}

locals {
  db_name            = "licensing"
  db_master_username = "postgres"
  db_port            = 5432
  application_name   = "licensing"
  cluster_identifier = "${var.environment_name}-${local.application_name}-rds"
  aurora_engine      = "aurora-postgresql"


  ## Available options: auto_explain,orafce,pgaudit,pg_ad_mapping,pg_bigm,pg_similarity,pg_stat_statements,pg_tle,pg_hint_plan,pg_prewarm,plprofiler,pglogical,pg_cron
  default_preload_libraries = "pg_stat_statements,pgaudit"
  optional_preload_library  = ""

  default_psql_cluster_parameters = {
    log_autovacuum_min_duration = { value = 10001 } # 10001 instead of 10000 since setting the default value results in Terraform not tracking this parameter in the state file, making it think this is always a proposed change.
    log_connections             = { value = 1 }
    log_disconnections          = { value = 1 }
    log_lock_waits              = { value = 1 }
    log_temp_files              = { value = 0 }
    log_statement               = { value = "none" }
    log_error_verbosity         = { value = "terse" }
    log_min_error_statement     = { value = "log" }
    log_rotation_age            = { value = 1440 }
    "pgaudit.log"               = { value = "DDL" }
    "pgaudit.role"              = { value = "rds_pgaudit" }
    "rds.log_retention_period"  = { value = 10080 }
    "shared_preload_libraries"  = { value = "${local.default_preload_libraries}${local.optional_preload_library}", apply_method = "pending-reboot" }
    "rds.force_ssl"             = { value = 1 }

  }

  cluster_parameters = merge(
    local.default_psql_cluster_parameters,
  )
}