# ---------------------------------------------------------------------------
# 通知先 SNS トピック
# ---------------------------------------------------------------------------
resource "aws_sns_topic" "alarm" {
  name = "${var.name_prefix}-alarm-topic"
  tags = var.tags
}

resource "aws_sns_topic_subscription" "alarm_email" {
  for_each = toset(var.alarm_email_addresses)

  topic_arn = aws_sns_topic.alarm.arn
  protocol  = "email"
  endpoint  = each.value
}

# ---------------------------------------------------------------------------
# アラーム 1: DLQ の滞留件数  ★ 最重要
#   ApproximateNumberOfMessagesVisible は「今すぐ受信できるメッセージ数」。
#   DLQ では 0 件が正常なので、しきい値 0 超過 = 異常として検知する。
#   Sum ではなく Maximum を使う点に注意 (Sum だと 1 分ごとの値が合算され、
#   同じメッセージを重複カウントしてしまう)。
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  alarm_name          = "${var.name_prefix}-dlq-messages-visible"
  alarm_description   = "DLQ にメッセージが滞留しています。原因を調査のうえ再投入してください。"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = var.dlq_depth_alarm_evaluation_periods
  threshold           = var.dlq_depth_alarm_threshold
  comparison_operator = "GreaterThanThreshold"

  # DLQ が空のときメトリクスが欠落することがあるため、欠落は正常扱いにする
  treat_missing_data = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = [aws_sns_topic.alarm.arn]
  ok_actions    = [aws_sns_topic.alarm.arn]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# アラーム 2: DLQ に入った瞬間を検知
#   NumberOfMessagesSent は「DLQ へ送られた件数」。
#   件数の増分 (=新規流入) を捉えるため統計は Sum。
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "dlq_incoming" {
  alarm_name          = "${var.name_prefix}-dlq-messages-sent"
  alarm_description   = "新たに DLQ へ退避されたメッセージがあります。"
  namespace           = "AWS/SQS"
  metric_name         = "NumberOfMessagesSent"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = [aws_sns_topic.alarm.arn]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# アラーム 3: メインキューの滞留時間
#   ApproximateAgeOfOldestMessage が伸びる = 消化が追いついていない兆候。
#   DLQ 行きが大量発生する前の早期検知に使う。
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "main_queue_age" {
  alarm_name          = "${var.name_prefix}-main-queue-age"
  alarm_description   = "メインキューのメッセージ滞留時間がしきい値を超えました。処理遅延の可能性があります。"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  threshold           = var.main_queue_age_alarm_threshold_seconds
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  alarm_actions = [aws_sns_topic.alarm.arn]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# アラーム 4: Lambda のエラー
#   DLQ 行きの根本原因を最初に確認する場所。
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.name_prefix}-lambda-errors"
  alarm_description   = "ディスパッチャ Lambda がエラーを返しました。CloudWatch Logs を確認してください。"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.lambda_error_alarm_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.dispatcher.function_name
  }

  alarm_actions = [aws_sns_topic.alarm.arn]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# 運用ダッシュボード
#   「件数の確認」を GUI で一目で行うための画面。
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "DLQ 滞留件数 (0 件が正常)"
          region = data.aws_region.current.name
          view   = "timeSeries"
          stat   = "Maximum"
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.dlq.name],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "メインキュー 滞留件数 / 滞留時間"
          region = data.aws_region.current.name
          view   = "timeSeries"
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.main.name, { stat = "Maximum" }],
            ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", aws_sqs_queue.main.name, { stat = "Maximum", yAxis = "right" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Lambda 呼び出し / エラー"
          region = data.aws_region.current.name
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.dispatcher.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.dispatcher.function_name],
          ]
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Lambda エラーログ (直近)"
          region = data.aws_region.current.name
          query  = "SOURCE '${aws_cloudwatch_log_group.lambda.name}' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          view   = "table"
        }
      },
    ]
  })
}
