# EventBridge Scheduler starts each job in licensing_api/jobs.py as a one-off ECS task
# (backlog D8). engineering/api/tests/test_jobs.py fails when a job has no schedule here.

locals {
  # Schedule expressions are UTC.
  job_schedules = {
    heartbeat = "rate(1 hour)"
  }
}

resource "aws_iam_role" "scheduler" {
  name = "${var.environment_name}-${local.application_name}-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_run_jobs" {
  name = "${var.environment_name}-${local.application_name}-scheduler-run-jobs"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "ecs:RunTask"
        # Any revision of the jobs task, since CI registers a new one on each deploy.
        Resource  = "${aws_ecs_task_definition.jobs_task.arn_without_revision}:*"
        Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.app_cluster.arn } }
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution_role.arn,
          aws_iam_role.ecs_task_role.arn,
        ]
      },
    ]
  })
}

resource "aws_scheduler_schedule" "job" {
  for_each = local.job_schedules

  name                = "${var.environment_name}-${local.application_name}-job-${replace(each.key, "_", "-")}"
  schedule_expression = each.value

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.app_cluster.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      # Without a revision, the latest one runs, so a deploy reaches the next run.
      task_definition_arn = aws_ecs_task_definition.jobs_task.arn_without_revision
      launch_type         = "FARGATE"

      network_configuration {
        subnets          = data.terraform_remote_state.network.outputs.private_subnet_ids
        security_groups  = [aws_security_group.ecs_sg.id]
        assign_public_ip = false
      }
    }

    input = jsonencode({
      containerOverrides = [{
        name    = local.jobs_container_name
        command = ["python", "-m", "licensing_api.jobs", "run", each.key]
      }]
    })

    # Retries a failure to start the task, never a job that ran and failed: that alarms instead.
    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}
