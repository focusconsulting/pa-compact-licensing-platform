# Whether the environment is paused: it keeps its data and its address, and runs
# nothing that costs by the hour (no database instance, no tasks, no scheduled jobs).
# `just pause` and `just resume` write this parameter, then apply. The module creates
# it but never sets it back, so every apply, a deploy included, keeps the last choice.
resource "aws_ssm_parameter" "paused" {
  name           = "/${var.environment_name}/${local.application_name}/paused"
  type           = "String"
  insecure_value = "false"

  lifecycle {
    ignore_changes = [insecure_value]
  }
}

locals {
  paused = aws_ssm_parameter.paused.insecure_value == "true"
}
