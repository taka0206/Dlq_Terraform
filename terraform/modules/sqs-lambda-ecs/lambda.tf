data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/src"
  output_path = "${path.module}/.build/${var.name_prefix}-lambda.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name_prefix}-dispatcher"
  retention_in_days = var.log_retention_in_days
  tags              = var.tags
}

resource "aws_lambda_function" "dispatcher" {
  function_name    = "${var.name_prefix}-dispatcher"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ECS_CLUSTER_ARN        = aws_ecs_cluster.this.arn
      ECS_TASK_DEF_ARN       = aws_ecs_task_definition.worker.arn
      ECS_CONTAINER_NAME     = local.container_name
      ECS_SUBNET_IDS         = join(",", var.subnet_ids)
      ECS_SECURITY_GROUP_IDS = join(",", var.security_group_ids)
      ECS_ASSIGN_PUBLIC_IP   = var.assign_public_ip ? "ENABLED" : "DISABLED"
      QUEUE_URL              = aws_sqs_queue.main.url
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# SQS → Lambda イベントソースマッピング
#   function_response_types = ["ReportBatchItemFailures"] により、
#   バッチ内の失敗したメッセージだけをキューに残せる (成功分の再処理を防ぐ)。
# ---------------------------------------------------------------------------
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn                   = aws_sqs_queue.main.arn
  function_name                      = aws_lambda_function.dispatcher.arn
  batch_size                         = var.lambda_batch_size
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = var.lambda_maximum_concurrency
  }
}
