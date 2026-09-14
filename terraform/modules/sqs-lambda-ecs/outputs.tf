output "main_queue_url" {
  description = "メインキューの URL (メッセージ送信・再投入の対象)"
  value       = aws_sqs_queue.main.url
}

output "main_queue_arn" {
  description = "メインキューの ARN"
  value       = aws_sqs_queue.main.arn
}

output "dlq_url" {
  description = "DLQ の URL (件数確認・メッセージ取得の対象)"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "DLQ の ARN (再投入コマンドの SourceArn に指定する)"
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_name" {
  description = "DLQ 名 (CloudWatch メトリクスの QueueName ディメンション値)"
  value       = aws_sqs_queue.dlq.name
}

output "lambda_function_name" {
  description = "ディスパッチャ Lambda の関数名"
  value       = aws_lambda_function.dispatcher.function_name
}

output "lambda_log_group_name" {
  description = "Lambda のロググループ名 (障害調査の起点)"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "ecs_cluster_name" {
  description = "ECS クラスター名"
  value       = aws_ecs_cluster.this.name
}

output "ecs_task_definition_arn" {
  description = "ワーカータスク定義の ARN"
  value       = aws_ecs_task_definition.worker.arn
}

output "ecs_log_group_name" {
  description = "ECS タスクのロググループ名"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "sns_topic_arn" {
  description = "アラーム通知先 SNS トピックの ARN"
  value       = aws_sns_topic.alarm.arn
}

output "dashboard_name" {
  description = "CloudWatch ダッシュボード名"
  value       = aws_cloudwatch_dashboard.this.dashboard_name
}

output "dlq_alarm_names" {
  description = "作成した CloudWatch アラーム名の一覧"
  value = [
    aws_cloudwatch_metric_alarm.dlq_depth.alarm_name,
    aws_cloudwatch_metric_alarm.dlq_incoming.alarm_name,
    aws_cloudwatch_metric_alarm.main_queue_age.alarm_name,
    aws_cloudwatch_metric_alarm.lambda_errors.alarm_name,
  ]
}
