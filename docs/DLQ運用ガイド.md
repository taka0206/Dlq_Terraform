# SQS → Lambda → ECS パイプライン DLQ 運用ガイド

このドキュメントは、**メッセージが DLQ に入ってから、CloudWatch アラームで気づき、件数を確認し、原因を調べ、再投入して復旧するまで**の一連の手順をまとめたものです。

> **対象読者**: 本パイプラインの運用担当者。AWS マネジメントコンソールと AWS CLI の基本操作ができれば読めるように書いています。

---

## 目次

1. [全体像 — 5 分で理解する](#1-全体像--5-分で理解する)
2. [なぜメッセージは DLQ に入るのか](#2-なぜメッセージは-dlq-に入るのか)
3. [構築手順](#3-構築手順)
4. [設定値リファレンス](#4-設定値リファレンス)
5. [障害対応フロー（本編）](#5-障害対応フロー本編)
   - [STEP 1: アラームで気づく](#step-1-アラームで気づく)
   - [STEP 2: 件数を確認する](#step-2-件数を確認する)
   - [STEP 3: 中身を確認する](#step-3-中身を確認する)
   - [STEP 4: 原因を特定する](#step-4-原因を特定する)
   - [STEP 5: 原因を修正する](#step-5-原因を修正する)
   - [STEP 6: 再投入する（リドライブ）](#step-6-再投入するリドライブ)
   - [STEP 7: 復旧を確認する](#step-7-復旧を確認する)
6. [よくあるトラブルと対処](#6-よくあるトラブルと対処)
7. [運用チェックリスト](#7-運用チェックリスト)
8. [用語集](#8-用語集)

---

## 1. 全体像 — 5 分で理解する

### 1-1. 正常時のメッセージの流れ

```
 ①送信                ②ポーリング              ③RunTask
[送信元] ──→ [SQS メインキュー] ──→ [Lambda ディスパッチャ] ──→ [ECS Fargate タスク]
                    │                                                  │
                    │                  ④処理成功 → DeleteMessage        │
                    └←─────────────────────────────────────────────────┘
                              メッセージがキューから消えて完了
```

| # | 何が起きるか |
|---|---|
| ① | アプリや他サービスがメインキューへメッセージを送る |
| ② | Lambda イベントソースマッピングが自動でキューをポーリングし、Lambda を起動する |
| ③ | Lambda は `ecs:RunTask` で Fargate タスクを 1 つ起動し、メッセージ本文を環境変数として渡す |
| ④ | Lambda が正常終了すると SQS がメッセージを自動削除する |

### 1-2. 異常時 — DLQ に落ちるまで

```
[メインキュー] ──→ [Lambda] ──✕ 失敗
      ↑                         │
      │  可視性タイムアウト経過後に再配信  │
      └─────────────────────────┘
                 これを maxReceiveCount (= 3) 回くり返すと…
                            ↓
                    [DLQ] ← ここに退避される
                            ↓
                 CloudWatch アラームが発報 → SNS → 担当者へメール
```

**ポイント**: DLQ 行きは SQS が自動で行います。Lambda や Terraform が何かをするわけではありません。「**受信回数が `maxReceiveCount` に達したメッセージを DLQ に移す**」という SQS の機能です。

### 1-3. 復旧の流れ（このドキュメントの主題）

```
 ①アラーム受信 → ②件数確認 → ③中身確認 → ④原因特定 → ⑤修正 → ⑥再投入 → ⑦復旧確認
   (SNS メール)  (CloudWatch) (SQS ポーリング) (Logs)   (デプロイ) (Redrive) (DLQ が 0 件)
```

> ⚠️ **最重要**: **⑤ の修正前に ⑥ の再投入をしてはいけません。** 原因が残ったまま再投入すると、また 3 回失敗して DLQ に戻るだけです（無限ループ・コスト増）。

---

## 2. なぜメッセージは DLQ に入るのか

DLQ 行きになる条件はただ 1 つ、**同じメッセージの受信回数（`ApproximateReceiveCount`）が `maxReceiveCount` を超えること**です。

受信回数が増えるのは次のいずれかが起きたときです。

| 原因の種類 | 具体例 | 最初に見る場所 |
|---|---|---|
| **Lambda が例外を投げた** | ECS の起動権限不足、環境変数の設定ミス | Lambda のロググループ |
| **Lambda がタイムアウトした** | RunTask API が遅延、同時実行数の上限 | Lambda のロググループ（`Task timed out`） |
| **RunTask が失敗を返した** | Fargate キャパシティ不足、サブネットの IP 枯渇 | Lambda のログ内の `RunTask returned failures` |
| **メッセージ自体が不正** | JSON が壊れている、必須項目がない（＝ポイズンピル） | DLQ のメッセージ本文 |
| **可視性タイムアウトが短すぎる** | 処理中なのに再配信されてしまう | キューの設定値 |

> 💡 本パイプラインの Lambda は `batchItemFailures` を返す実装になっています。バッチ内の一部だけが失敗した場合、**失敗したメッセージだけ**がキューに残り、成功したメッセージは再配信されません（ECS タスクの二重起動を防ぐため）。

---

## 3. 構築手順

### 3-1. 前提条件

- Terraform 1.5 以上
- AWS CLI v2（`aws sts get-caller-identity` が通ること）
- ECS タスクを起動する VPC・サブネット・セキュリティグループが既にあること
- ワーカーのコンテナイメージが ECR に push されていること

> サブネットはプライベートサブネット推奨です。その場合、ECR / CloudWatch Logs / SQS へ到達するため **NAT Gateway または VPC エンドポイント**が必要です。ここが未整備だとタスクが `CannotPullContainerError` で起動に失敗し、結果として DLQ 行きが多発します。

### 3-2. デプロイ

```bash
cd terraform/envs/dev

# 1) 設定ファイルを用意する
cp terraform.tfvars.example terraform.tfvars
vi terraform.tfvars          # subnet_ids / security_group_ids / container_image を自分の環境に合わせる

# 2) 初期化
terraform init

# 3) 差分確認（必ず目視する）
terraform plan

# 4) 適用
terraform apply
```

### 3-3. 適用直後にやること

1. **SNS のメール購読を承認する**
   `alarm_email_addresses` に指定したアドレスへ AWS から確認メールが届きます。本文中の **Confirm subscription** を必ずクリックしてください。
   これを忘れるとアラームが発報しても誰にも通知が届きません。

   承認済みかどうかは次のコマンドで確認できます（`PendingConfirmation` になっていないこと）。

   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn "$(terraform output -raw sns_topic_arn)" \
     --query 'Subscriptions[].[Endpoint,SubscriptionArn]' --output table
   ```

2. **出力値を控える**

   ```bash
   terraform output
   ```

   以降の手順で使うため、`main_queue_url` / `dlq_url` / `dlq_arn` / `main_queue_arn` をメモしておきます。

3. **ダッシュボードをブックマークする**
   CloudWatch → ダッシュボード → `<name_prefix>-dashboard`

---

## 4. 設定値リファレンス

### 4-1. SQS

| 設定項目 | 変数名 | 既定値 | 意味と決め方 |
|---|---|---|---|
| 最大受信回数 | `max_receive_count` | `3` | 何回失敗したら DLQ へ送るか。小さすぎると一時的な障害で DLQ 行きが多発し、大きすぎると異常の発見が遅れる。**3〜5 が目安** |
| 可視性タイムアウト | `visibility_timeout_seconds` | `180` | 処理中のメッセージを他から見えなくする時間。**Lambda タイムアウトの 6 倍以上**が AWS 推奨（30 秒 × 6 = 180 秒） |
| メインキュー保持期間 | `message_retention_seconds` | `345600`（4 日） | メインキューにメッセージを保持する期間 |
| **DLQ 保持期間** | `dlq_message_retention_seconds` | `1209600`（**14 日**） | ⚠️ **最大値を推奨**。この期間を過ぎると DLQ のメッセージは消え、二度と再投入できない。調査に時間がかかっても間に合うようにする |

> ⚠️ **可視性タイムアウトの罠**: 可視性タイムアウトが Lambda のタイムアウトより短いと、**まだ処理中なのにメッセージが再配信され**、ECS タスクが多重起動したうえで受信回数だけが増え、正常な処理でも DLQ 行きになります。必ず「可視性タイムアウト ≧ Lambda タイムアウト × 6」を守ってください。

### 4-2. 再投入（リドライブ）を可能にする設定

DLQ 側に `redrive_allow_policy` が必要です。これがないと再投入が `AccessDenied` で失敗します。

```hcl
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.main.arn]   # 戻せる先をメインキューだけに限定
  })
}
```

### 4-3. CloudWatch アラーム 4 本

| # | アラーム名 | メトリクス | 統計 | 期間 | しきい値 | 何を意味するか |
|---|---|---|---|---|---|---|
| 1 | `<prefix>-dlq-messages-visible` ★最重要 | `ApproximateNumberOfMessagesVisible` | **Maximum** | 60 秒 | `> 0` | **DLQ に未処理のメッセージが滞留している**。1 件でも残っていれば発報し続ける |
| 2 | `<prefix>-dlq-messages-sent` | `NumberOfMessagesSent` | **Sum** | 300 秒 | `> 0` | **新たに DLQ へ流入した**。増加の瞬間を捉える |
| 3 | `<prefix>-main-queue-age` | `ApproximateAgeOfOldestMessage` | Maximum | 300 秒 × 2 回 | `> 900` 秒 | メインキューの消化が遅れている。DLQ 大量発生の**前兆** |
| 4 | `<prefix>-lambda-errors` | `Errors`（AWS/Lambda） | Sum | 300 秒 | `>= 1` | Lambda が失敗した。**DLQ 行きの根本原因を最初に見る場所** |

#### なぜ統計が Maximum と Sum で違うのか

ここは間違えやすいポイントです。

- **`ApproximateNumberOfMessagesVisible` は「その瞬間の残高」** です。1 分ごとに「3 件」「3 件」「3 件」と同じ値が記録されます。これを **Sum** にすると 9 件と誤って合算されてしまうため、**Maximum**（または Average）を使います。
- **`NumberOfMessagesSent` は「その期間に発生した件数」** です。流入の合計を知りたいので **Sum** を使います。

#### `treat_missing_data = "notBreaching"` の意味

DLQ が空のとき、SQS はメトリクスを送信しないことがあります（データポイント欠落）。この設定により**「データがない＝正常」**と扱われ、誤発報を防ぎます。

### 4-4. アラームのしきい値を調整したい場合

DLQ に 1 件でも入ったら即通知したい（既定値）:

```hcl
dlq_depth_alarm_threshold = 0    # 0 件超 = 1 件以上で発報
```

ある程度の失敗は許容し、5 件を超えたら通知したい:

```hcl
dlq_depth_alarm_threshold          = 5
dlq_depth_alarm_evaluation_periods = 2   # 2 分連続で超えたら発報（瞬間的なスパイクを無視）
```

---

## 5. 障害対応フロー（本編）

### STEP 1: アラームで気づく

SNS から次のようなメールが届きます。

```
ALARM: "dlq-demo-dlq-messages-visible" in Asia Pacific (Tokyo)

Threshold Crossed: 1 datapoint [3.0] was greater than the threshold (0.0).
```

`[3.0]` の部分が**現在の DLQ 件数**です。この例では 3 件が DLQ に滞留しています。

メールを見逃した場合や、現在のアラーム状態を確認したい場合:

```bash
aws cloudwatch describe-alarms \
  --alarm-names dlq-demo-dlq-messages-visible \
  --query 'MetricAlarms[].[AlarmName,StateValue,StateReason]' --output table
```

---

### STEP 2: 件数を確認する

「今、DLQ に何件あるのか」を正確に把握します。**3 つの方法があり、目的で使い分けます。**

#### 方法 A: CloudWatch ダッシュボード（推移を見る／推奨）

CloudWatch → ダッシュボード → `dlq-demo-dashboard` → 左上の「DLQ 滞留件数」パネル。

いつから増え始めたか、増え続けているか止まったかが一目でわかります。**まずここを見ます。**

#### 方法 B: AWS CLI（正確な即時値／推奨）

```bash
DLQ_URL=$(cd terraform/envs/dev && terraform output -raw dlq_url)

aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
                    ApproximateNumberOfMessagesNotVisible \
                    ApproximateNumberOfMessagesDelayed
```

出力例:

```json
{
  "Attributes": {
    "ApproximateNumberOfMessages": "3",
    "ApproximateNumberOfMessagesNotVisible": "0",
    "ApproximateNumberOfMessagesDelayed": "0"
  }
}
```

| 属性名 | 意味 |
|---|---|
| `ApproximateNumberOfMessages` | **受信可能な件数**（通常はこれを見る） |
| `ApproximateNumberOfMessagesNotVisible` | 誰かが受信中で、まだ削除されていない件数 |
| `ApproximateNumberOfMessagesDelayed` | 遅延設定でまだ配信されていない件数 |

> 💡 **DLQ の実際の総件数** = 上記 3 つの合計。調査で `receive-message` した直後は `NotVisible` に移動するため、合計で見ないと「減った」と勘違いします。

#### 方法 C: CloudWatch メトリクスを直接取得（過去に遡って調べる）

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=dlq-demo-dlq \
  --start-time "$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time   "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 300 --statistics Maximum \
  --query 'sort_by(Datapoints,&Timestamp)[].[Timestamp,Maximum]' --output table
```

> ⚠️ **注意**: `ApproximateNumberOfMessages` の「Approximate（およそ）」は飾りではありません。SQS は分散システムのため、件数はわずかに前後することがあります。**「0 件かどうか」の判定には使えますが、「ちょうど 100 件処理した」といった厳密な会計には使わないでください。**

---

### STEP 3: 中身を確認する

件数がわかったら、**何が失敗しているのか**を実際のメッセージで確認します。

```bash
DLQ_URL=$(cd terraform/envs/dev && terraform output -raw dlq_url)

aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 \
  --visibility-timeout 0 \
  --message-attribute-names All \
  --message-system-attribute-names All
```

> ⚠️ **`--visibility-timeout 0` を必ず付けてください。** これを省くと、見たメッセージが既定の可視性タイムアウトの間ロックされ、その間は再投入できません。`0` を指定すれば見た直後にすぐ戻ります。
>
> ⚠️ **`delete-message` は絶対に実行しないでください。** 調査中に削除するとメッセージは永久に失われ、再投入できなくなります。

#### 出力から読み取るポイント

```json
{
  "Messages": [
    {
      "MessageId": "a1b2c3d4-...",
      "Body": "{\"orderId\": \"12345\", \"amount\": \"abc\"}",
      "Attributes": {
        "ApproximateReceiveCount": "4",
        "SentTimestamp": "1757808000000",
        "ApproximateFirstReceiveTimestamp": "1757808001000"
      }
    }
  ]
}
```

| 見る場所 | 読み取れること |
|---|---|
| `Body` | 実際のペイロード。この例では `amount` が数値でなく `"abc"` → **データ不正（ポイズンピル）** |
| `ApproximateReceiveCount` | `maxReceiveCount`(3) を超えて 4 になっている → 確かに規定回数失敗した |
| `SentTimestamp` | 元々いつ送信されたか（ミリ秒 UNIX 時間） |
| `MessageId` | **この ID で Lambda のログを検索できる**（次の STEP で使う） |

`MessageId` は必ず控えてください。

#### 全件をファイルに保存しておきたい場合

```bash
aws sqs receive-message --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 --visibility-timeout 0 \
  --message-system-attribute-names All \
  > dlq_snapshot_$(date +%Y%m%d_%H%M%S).json
```

> 1 回のリクエストで取得できるのは最大 10 件です。件数が多い場合は何度か繰り返します（同じメッセージが再取得されることもあります）。

---

### STEP 4: 原因を特定する

STEP 3 で控えた `MessageId` を使って Lambda のログを検索します。

#### 4-1. Lambda のログを MessageId で絞り込む

```bash
LOG_GROUP=$(cd terraform/envs/dev && terraform output -raw lambda_log_group_name)

aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(($(date +%s) - 86400))000" \
  --filter-pattern '"a1b2c3d4-"' \
  --query 'events[].message' --output text
```

#### 4-2. CloudWatch Logs Insights で調べる（推奨）

コンソール → CloudWatch → ログ → Logs Insights で対象ロググループを選び、次のクエリを実行します。

**エラーを新しい順に一覧:**

```
fields @timestamp, @message
| filter @message like /ERROR/ or @message like /Traceback/
| sort @timestamp desc
| limit 50
```

**特定のメッセージだけを追う:**

```
fields @timestamp, @message
| filter @message like /a1b2c3d4-/
| sort @timestamp asc
```

**エラー種別ごとに件数を集計する（傾向をつかむ）:**

```
fields @message
| filter @message like /ERROR/
| parse @message /(?<errType>[A-Za-z]+Error|[A-Za-z]+Exception)/
| stats count(*) as 件数 by errType
| sort 件数 desc
```

#### 4-3. ECS タスク側のログも確認する

Lambda が正常に起動していても、コンテナ内の処理で失敗している場合があります。

```bash
ECS_LOG_GROUP=$(cd terraform/envs/dev && terraform output -raw ecs_log_group_name)

aws logs tail "$ECS_LOG_GROUP" --since 1h --format short
```

#### 4-4. エラーメッセージ別の原因早見表

| ログに出る文字列 | 原因 | 対処 |
|---|---|---|
| `AccessDeniedException ... ecs:RunTask` | Lambda ロールの権限不足 | IAM ポリシーを確認。`iam:PassRole` の付け忘れが多い |
| `InvalidParameterException ... subnet` | サブネット ID の誤り、AZ 不一致 | `subnet_ids` を見直す |
| `CannotPullContainerError` | ECR に到達できない／イメージが存在しない | NAT Gateway・VPC エンドポイント・イメージタグを確認 |
| `Task timed out after 30.00 seconds` | Lambda のタイムアウト | `lambda_timeout_seconds` を延長（可視性タイムアウトも 6 倍に追随させる） |
| `RunTask returned failures ... RESOURCE:ENI` | サブネットの IP アドレス枯渇 | サブネットを増やす、`lambda_maximum_concurrency` を下げる |
| `ThrottlingException` | RunTask の API 制限 | `lambda_maximum_concurrency` を下げる |
| `JSONDecodeError` / `KeyError` | メッセージ自体が不正（ポイズンピル） | **再投入しても直らない。** 送信元を修正し、該当メッセージは破棄する |

---

### STEP 5: 原因を修正する

> 🚨 **このステップを飛ばして STEP 6 に進まないでください。** 原因が残ったまま再投入すると、また 3 回失敗して DLQ に戻るだけです。

原因の種類ごとに対応が分かれます。

| 原因の種類 | 対応 | 再投入して直るか |
|---|---|---|
| **一時的な障害**（スロットリング、キャパシティ不足、AWS 側の瞬断） | 復旧を待つだけ | ✅ **直る** → STEP 6 へ |
| **設定ミス**（IAM 権限、サブネット、環境変数） | Terraform を修正して `terraform apply` | ✅ **直る** → STEP 6 へ |
| **アプリのバグ** | コードを修正し、新しいイメージを push してタスク定義を更新 | ✅ **直る** → STEP 6 へ |
| **メッセージ自体が不正**（ポイズンピル） | 送信元アプリを修正する | ❌ **直らない** → 下記参照 |

#### ポイズンピルの扱い

メッセージの中身そのものが壊れている場合、何度再投入しても成功しません。

1. まずメッセージ内容を証跡として保存する（STEP 3 の `dlq_snapshot_*.json`）
2. 業務上の影響を関係者に確認する（そのデータは再作成が必要か？）
3. 送信元アプリのバリデーションを修正する
4. DLQ の該当メッセージを削除する

```bash
# 削除は「業務影響を確認したうえで」実施すること
aws sqs delete-message --queue-url "$DLQ_URL" --receipt-handle "<ReceiptHandle>"
```

> `ReceiptHandle` は `receive-message` のたびに変わります。**取得した直後**に削除してください。

#### 修正が反映されたことを確認する

再投入の前に、**テストメッセージを 1 件だけメインキューに送って成功するか**を確かめます。これを怠ると、大量のメッセージを再投入して再び全滅させることになります。

```bash
MAIN_URL=$(cd terraform/envs/dev && terraform output -raw main_queue_url)

aws sqs send-message --queue-url "$MAIN_URL" \
  --message-body '{"test": true, "note": "recovery smoke test"}'

# 30 秒ほど待ってから、ECS タスクが起動したか確認
aws logs tail "$ECS_LOG_GROUP" --since 5m --format short
```

---

### STEP 6: 再投入する（リドライブ）

原因が解消できたら、DLQ のメッセージをメインキューへ戻します。**方法は 2 つあります。**

#### 方法 A: マネジメントコンソール（少量・手軽／初心者向け）

1. SQS コンソール → DLQ（`dlq-demo-dlq`）を選択
2. 右上の **「DLQ の再処理を開始」**（Start DLQ redrive）をクリック
3. 送信先で **「送信元キューへの再処理」**（Redrive to source queue）を選択
4. 必要に応じて **1 秒あたりのメッセージ数**（速度制限）を設定
5. **「DLQ の再処理」** をクリック
6. 画面上で進捗（移動済み件数）を確認する

#### 方法 B: AWS CLI（件数が多い・手順を記録に残したい／推奨）

```bash
cd terraform/envs/dev
DLQ_ARN=$(terraform output -raw dlq_arn)
MAIN_ARN=$(terraform output -raw main_queue_arn)

# 再投入タスクを開始
aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$MAIN_ARN" \
  --max-number-of-messages-per-second 10
```

出力:

```json
{ "TaskHandle": "eyJ0YXNrSWQiOiI4M2M2Yj..." }
```

**進捗を確認する:**

```bash
aws sqs list-message-move-tasks --source-arn "$DLQ_ARN" --max-results 1
```

```json
{
  "Results": [
    {
      "TaskHandle": "eyJ0YXNrSWQiOiI4M2M2Yj...",
      "Status": "COMPLETED",
      "SourceArn": "arn:aws:sqs:ap-northeast-1:123456789012:dlq-demo-dlq",
      "DestinationArn": "arn:aws:sqs:ap-northeast-1:123456789012:dlq-demo-queue",
      "ApproximateNumberOfMessagesMoved": 3,
      "ApproximateNumberOfMessagesToMove": 3
    }
  ]
}
```

`Status` の意味:

| Status | 意味 |
|---|---|
| `RUNNING` | 移動中 |
| `COMPLETED` | 正常に完了 |
| `FAILED` | 失敗（`FailureReason` を確認。`redrive_allow_policy` 未設定が最多） |
| `CANCELLING` / `CANCELLED` | キャンセル処理中／キャンセル済み |

**途中で止めたい場合:**

```bash
aws sqs cancel-message-move-task --task-handle "<TaskHandle>"
```

#### 再投入時の注意点

| 注意点 | 内容 |
|---|---|
| **速度制限を必ず入れる** | `--max-number-of-messages-per-second` を省略すると最大速度で流れ込み、ECS タスクが一気に起動して下流（DB など）を圧迫します。**10〜50 件/秒から始める**のが安全です |
| **同時に 1 タスクだけ** | 1 つの DLQ に対して同時に実行できる移動タスクは 1 つだけです |
| **受信回数はリセットされる** | 再投入されたメッセージは新しいメッセージとして扱われ、`ApproximateReceiveCount` は 1 から数え直しになります。つまり再び 3 回のチャンスがあります |
| **DLQ の DLQ は無い** | 再投入先はメインキューです。失敗すればまた同じ DLQ に戻ります |
| **保持期間に注意** | 元の `SentTimestamp` を基準に保持期間が判定されます。14 日近く経過したメッセージは移動後すぐ消える可能性があります |

---

### STEP 7: 復旧を確認する

再投入して終わりではありません。**本当に処理されたか**を必ず確認します。

#### 7-1. DLQ が 0 件になったか

```bash
aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages \
                    ApproximateNumberOfMessagesNotVisible
```

両方 `"0"` になっていることを確認します。

#### 7-2. メインキューも消化されたか

```bash
MAIN_URL=$(cd terraform/envs/dev && terraform output -raw main_queue_url)
aws sqs get-queue-attributes --queue-url "$MAIN_URL" \
  --attribute-names ApproximateNumberOfMessages
```

#### 7-3. アラームが OK に戻ったか

```bash
aws cloudwatch describe-alarms \
  --alarm-names dlq-demo-dlq-messages-visible \
  --query 'MetricAlarms[].[AlarmName,StateValue,StateUpdatedTimestamp]' --output table
```

`StateValue` が `OK` になっていれば復旧完了です。SNS からも「OK:」で始まる復旧メールが届きます（`ok_actions` を設定しているため）。

> ⏱️ アラームの状態は最大 1〜2 分遅れて更新されます。すぐに `OK` にならなくても慌てないでください。

#### 7-4. ECS タスクが正常終了したか

```bash
aws logs tail "$ECS_LOG_GROUP" --since 15m --format short
```

#### 7-5. 記録を残す

次回に備えて、以下を障害記録に残します。

- 発生日時・検知日時・復旧日時
- DLQ に入った件数
- 根本原因
- 実施した対処
- 再発防止策（しきい値の見直し、バリデーション追加など）

---

## 6. よくあるトラブルと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| アラームが発報しない | SNS の購読が未承認 | 確認メールの **Confirm subscription** をクリック |
| アラームが `INSUFFICIENT_DATA` のまま | DLQ が空でメトリクスが未送信 | `treat_missing_data = "notBreaching"` を設定済みなら正常。一度メッセージを流すとメトリクスが出る |
| DLQ が空なのにアラームが鳴り続ける | 統計が `Sum` になっている | `ApproximateNumberOfMessagesVisible` は **Maximum** を使う |
| 再投入が `AccessDenied` で失敗 | DLQ に `redrive_allow_policy` が無い | `aws_sqs_queue_redrive_allow_policy` を適用する |
| 再投入したのにすぐ DLQ に戻る | 原因が未修正 | STEP 4〜5 に戻る。ポイズンピルなら再投入では直らない |
| 同じメッセージが何度も ECS タスクを起動する | 可視性タイムアウトが短すぎる | 可視性タイムアウト ≧ Lambda タイムアウト × 6 に設定 |
| DLQ のメッセージが消えた | 保持期間を超過した | `dlq_message_retention_seconds` を 14 日（最大値）に設定して再発防止 |
| `receive-message` したら件数が減った | 受信中で `NotVisible` に移動しただけ | `ApproximateNumberOfMessages` + `NotVisible` の合計で見る |
| 再投入したら下流の DB が落ちた | 速度制限なしで一気に流した | `--max-number-of-messages-per-second` を指定する |
| `terraform apply` で `ResourceConflictException` | 同名のリソースが既存 | `name_prefix` を変えるか、既存リソースを `terraform import` する |

---

## 7. 運用チェックリスト

### 導入時（一度だけ）

- [ ] `terraform apply` が成功した
- [ ] SNS の確認メールを承認した（`PendingConfirmation` でないこと）
- [ ] テストメッセージを送り、ECS タスクが起動してログが出ることを確認した
- [ ] **わざと失敗するメッセージを送り、3 回失敗して DLQ に入ることを確認した**
- [ ] **その DLQ 流入でアラームが発報し、メールが届くことを確認した**
- [ ] **その DLQ メッセージを再投入できることを確認した**
- [ ] CloudWatch ダッシュボードをブックマークした
- [ ] 本ドキュメントを運用チームへ共有した

> ⚠️ 上記の太字 3 項目（**訓練**）は必ず本番投入前に実施してください。「アラームが飛ぶはずだった」で気づかないのが最悪のパターンです。

### 日次

- [ ] ダッシュボードで DLQ が 0 件であることを確認
- [ ] メインキューの `ApproximateAgeOfOldestMessage` が伸びていないか確認

### 月次

- [ ] 過去 1 か月の DLQ 流入件数と原因を棚卸し
- [ ] `max_receive_count` としきい値が実態に合っているか見直し
- [ ] ログ保持期間とコストを確認

---

## 8. 用語集

| 用語 | 読み・略さない表記 | 意味 |
|---|---|---|
| **DLQ** | Dead Letter Queue（デッドレターキュー） | 規定回数処理に失敗したメッセージを退避する専用キュー。「ゴミ箱」ではなく「**要調査の一時保管場所**」 |
| **リドライブ** | Redrive | DLQ のメッセージを元のキューへ戻すこと。＝再投入 |
| **可視性タイムアウト** | Visibility Timeout | あるコンシューマが受信したメッセージを、他から見えなくする時間。この間に削除されないと再配信される |
| **maxReceiveCount** | 最大受信回数 | この回数受信されても削除されなかったメッセージが DLQ 行きになる |
| **ポイズンピル** | Poison Pill | 何度処理しても必ず失敗する不正なメッセージ。再投入では解決しない |
| **イベントソースマッピング** | Event Source Mapping | Lambda が SQS を自動でポーリングする仕組み。Lambda 側の設定 |
| **batchItemFailures** | 部分バッチ応答 | バッチ内の失敗したメッセージだけを SQS に報告する仕組み。成功分の再処理を防ぐ |
| **ApproximateNumberOfMessagesVisible** | 受信可能メッセージ数 | 今すぐ受信できるメッセージ数。DLQ の「件数」として最もよく見る値 |
| **ApproximateAgeOfOldestMessage** | 最古メッセージ経過時間 | キュー内で最も古いメッセージが滞留している秒数。処理遅延の指標 |

---

## 参考リンク

- [Amazon SQS デッドレターキュー](https://docs.aws.amazon.com/ja_jp/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- [デッドレターキューの再処理（リドライブ）](https://docs.aws.amazon.com/ja_jp/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-dead-letter-queue-redrive.html)
- [Amazon SQS の CloudWatch メトリクス](https://docs.aws.amazon.com/ja_jp/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- [Lambda と SQS のイベントソースマッピング](https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/with-sqs.html)
- [ECS RunTask API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)
