output "main_queue_url" {
  description = "メインキュー URL"
  value       = module.pipeline.main_queue_url
}

output "dlq_url" {
  description = "DLQ URL"
  value       = module.pipeline.dlq_url
}

output "dlq_arn" {
  description = "DLQ ARN (再投入コマンドで使用)"
  value       = module.pipeline.dlq_arn
}

output "main_queue_arn" {
  description = "メインキュー ARN (再投入コマンドで使用)"
  value       = module.pipeline.main_queue_arn
}

output "lambda_log_group_name" {
  description = "Lambda ロググループ名"
  value       = module.pipeline.lambda_log_group_name
}

output "ecs_log_group_name" {
  description = "ECS ロググループ名"
  value       = module.pipeline.ecs_log_group_name
}

output "dashboard_name" {
  description = "CloudWatch ダッシュボード名"
  value       = module.pipeline.dashboard_name
}

output "dlq_alarm_names" {
  description = "CloudWatch アラーム名一覧"
  value       = module.pipeline.dlq_alarm_names
}
