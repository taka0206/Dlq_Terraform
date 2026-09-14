# ---------------------------------------------------------------------------
# DLQ (Dead Letter Queue)
#   max_receive_count 回処理に失敗したメッセージがここへ退避される。
#   保持期間を長め (既定 14 日) に取り、調査・再投入の猶予を確保する。
# ---------------------------------------------------------------------------
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-dlq"
  message_retention_seconds = var.dlq_message_retention_seconds
  sqs_managed_sse_enabled   = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-dlq"
    Role = "dead-letter-queue"
  })
}

# ---------------------------------------------------------------------------
# メインキュー
#   redrive_policy で DLQ を紐付ける。
#   visibility_timeout_seconds は Lambda タイムアウトの 6 倍以上にする
#   (短いと処理中のメッセージが再配信され、多重実行と誤 DLQ 行きの原因になる)。
# ---------------------------------------------------------------------------
resource "aws_sqs_queue" "main" {
  name                       = "${var.name_prefix}-queue"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-queue"
    Role = "main-queue"
  })
}

# ---------------------------------------------------------------------------
# 再投入 (redrive) の許可設定
#   DLQ から戻せる先をメインキューだけに限定する。
#   この設定がないと StartMessageMoveTask (コンソールの「DLQ の再処理」) が
#   AccessDenied で失敗する。
# ---------------------------------------------------------------------------
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.main.arn]
  })
}
