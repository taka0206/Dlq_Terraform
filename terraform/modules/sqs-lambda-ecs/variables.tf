variable "name_prefix" {
  description = "全リソース名の接頭辞 (例: dlq-demo)"
  type        = string
}

variable "tags" {
  description = "全リソースに付与する共通タグ"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# ネットワーク (ECS タスクを起動する VPC 情報)
# ---------------------------------------------------------------------------
variable "subnet_ids" {
  description = "ECS タスクを起動するサブネット ID。NAT Gateway 経由で外部疎通できるプライベートサブネットを推奨"
  type        = list(string)
}

variable "security_group_ids" {
  description = "ECS タスクにアタッチするセキュリティグループ ID"
  type        = list(string)
}

variable "assign_public_ip" {
  description = "ECS タスクにパブリック IP を割り当てるか。パブリックサブネットを使う場合のみ true"
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# SQS
# ---------------------------------------------------------------------------
variable "visibility_timeout_seconds" {
  description = "メインキューの可視性タイムアウト秒。Lambda タイムアウトの 6 倍以上が AWS 推奨"
  type        = number
  default     = 180

  validation {
    condition     = var.visibility_timeout_seconds >= 0 && var.visibility_timeout_seconds <= 43200
    error_message = "visibility_timeout_seconds は 0〜43200 の範囲で指定してください。"
  }
}

variable "message_retention_seconds" {
  description = "メインキューのメッセージ保持期間 (秒)"
  type        = number
  default     = 345600 # 4 日
}

variable "dlq_message_retention_seconds" {
  description = "DLQ のメッセージ保持期間 (秒)。調査と再投入の時間を確保するため最大値 14 日を既定とする"
  type        = number
  default     = 1209600 # 14 日
}

variable "max_receive_count" {
  description = "この回数だけ受信しても削除されなかったメッセージを DLQ へ退避する"
  type        = number
  default     = 3

  validation {
    condition     = var.max_receive_count >= 1 && var.max_receive_count <= 1000
    error_message = "max_receive_count は 1〜1000 の範囲で指定してください。"
  }
}

# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------
variable "lambda_timeout_seconds" {
  description = "Lambda のタイムアウト秒"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda のメモリ (MB)"
  type        = number
  default     = 256
}

variable "lambda_batch_size" {
  description = "1 回の Lambda 呼び出しで処理する SQS メッセージ数"
  type        = number
  default     = 1
}

variable "lambda_maximum_concurrency" {
  description = "SQS イベントソースの最大同時実行数。ECS の RunTask スロットリングを避けるために制限する"
  type        = number
  default     = 10

  validation {
    condition     = var.lambda_maximum_concurrency >= 2 && var.lambda_maximum_concurrency <= 1000
    error_message = "lambda_maximum_concurrency は 2〜1000 の範囲で指定してください。"
  }
}

variable "log_retention_in_days" {
  description = "CloudWatch Logs の保持日数"
  type        = number
  default     = 30
}

# ---------------------------------------------------------------------------
# ECS
# ---------------------------------------------------------------------------
variable "container_image" {
  description = "ECS タスクで実行するコンテナイメージ (例: 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/worker:latest)"
  type        = string
}

variable "task_cpu" {
  description = "Fargate タスクの CPU ユニット"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Fargate タスクのメモリ (MB)"
  type        = string
  default     = "512"
}

variable "enable_container_insights" {
  description = "ECS クラスターで Container Insights を有効化するか"
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# 監視 / アラーム
# ---------------------------------------------------------------------------
variable "alarm_email_addresses" {
  description = "アラート通知先メールアドレス。指定すると SNS サブスクリプションを作成する (確認メールの承認が必要)"
  type        = list(string)
  default     = []
}

variable "dlq_depth_alarm_threshold" {
  description = "DLQ 件数アラームのしきい値。この件数を超えるとアラーム状態になる"
  type        = number
  default     = 0
}

variable "dlq_depth_alarm_evaluation_periods" {
  description = "DLQ 件数アラームの評価期間数"
  type        = number
  default     = 1
}

variable "main_queue_age_alarm_threshold_seconds" {
  description = "メインキューの最古メッセージ経過時間アラームのしきい値 (秒)"
  type        = number
  default     = 900
}

variable "lambda_error_alarm_threshold" {
  description = "Lambda エラー件数アラームのしきい値"
  type        = number
  default     = 1
}
