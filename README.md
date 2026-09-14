# SQS → Lambda → ECS  DLQ パイプライン

SQS のメッセージを Lambda 経由で ECS (Fargate) タスクとして処理し、失敗したメッセージを
**DLQ に退避 → CloudWatch アラームで検知 → 件数を確認 → 再投入して復旧**するまでを
一式で構築する Terraform コードと運用ドキュメントです。

---

## 構成

```
 ①送信                ②ポーリング              ③RunTask
[送信元] ──→ [SQS メインキュー] ──→ [Lambda ディスパッチャ] ──→ [ECS Fargate タスク]
                    │
                    │ maxReceiveCount (既定 3) 回失敗
                    ↓
                 [SQS DLQ] ──→ [CloudWatch アラーム] ──→ 担当者が確認して気づく
                    ↑                                              │
                    └────── 原因修正後に再投入 (Redrive) ←──────────┘
```

作成されるリソース:

| カテゴリ | リソース |
|---|---|
| SQS | メインキュー、DLQ、redrive ポリシー、redrive 許可ポリシー |
| Lambda | ディスパッチャ関数、イベントソースマッピング、実行ロール |
| ECS | クラスター、Fargate タスク定義、タスクロール、タスク実行ロール |
| 監視 | CloudWatch アラーム 4 本、ダッシュボード、ロググループ 2 つ |

---

## ドキュメント

障害対応の手順は **こちらを読んでください**。どちらも内容は同じです。

| ファイル | 形式 | 用途 |
|---|---|---|
| [`docs/DLQ運用ガイド.md`](docs/DLQ運用ガイド.md) | Markdown | GitHub 上で読む・検索する・レビューする |
| [`docs/DLQ運用手順書.xlsx`](docs/DLQ運用手順書.xlsx) | Excel（全 10 シート） | 配布・印刷する、チェックリストに記入する |

### Excel の収録シート

| シート | 内容 |
|---|---|
| 01_はじめに | 読み方とシート一覧 |
| 02_全体構成 | 正常時・異常時のメッセージの流れ、構成要素 |
| 03_構築手順 | デプロイと適用直後の必須作業（訓練項目を含む） |
| 04_設定リファレンス | SQS / Lambda / ECS の全設定値と決め方 |
| 05_アラーム設定 | CloudWatch アラーム 4 本の詳細 |
| **06_対応手順** | **★本編★ STEP 1〜7 の障害対応フロー** |
| 07_コマンド集 | コピー&ペーストで使える AWS CLI コマンド |
| 08_トラブルシュート | 症状別の原因と対処 15 件 |
| 09_チェックリスト | 導入時 / 日次 / 月次（進捗が自動集計される） |
| 10_用語集 | DLQ 関連用語 20 件の日本語解説 |

Excel を再生成する場合:

```bash
pip install openpyxl
python3 scripts/generate_dlq_workbook.py docs/DLQ運用手順書.xlsx
```

---

## クイックスタート

```bash
cd terraform/envs/dev

cp terraform.tfvars.example terraform.tfvars
vi terraform.tfvars          # subnet_ids / security_group_ids / container_image を設定

terraform init
terraform plan               # 差分を必ず目視する
terraform apply
```

> ⚠️ **本構成は通知連携（SNS 等）を行いません。**
> アラームは `ALARM` 状態になるだけで、担当者への通知は飛びません。
> 検知は **日次点検で `describe-alarms` を確認する** プル型の運用になります。
> 点検が回らないと DLQ の滞留に気づけないため、当番制などで確実に実施してください。
> 通知が必要になった場合の追加方法は
> [`docs/DLQ運用ガイド.md` の補足](docs/DLQ運用ガイド.md#補足-通知が必要になった場合) を参照してください。

```bash
# 日次点検（ALARM 状態のアラームだけを抽出する）
aws cloudwatch describe-alarms --state-value ALARM \
  --alarm-name-prefix dlq-demo \
  --query 'MetricAlarms[].[AlarmName,StateReason]' --output table
```

---

## ディレクトリ構成

```
.
├── README.md
├── docs/
│   ├── DLQ運用ガイド.md          # 運用手順（Markdown 版）
│   └── DLQ運用手順書.xlsx        # 運用手順（Excel 版・全 10 シート）
├── lambda/
│   └── src/
│       └── handler.py            # SQS → ECS RunTask ディスパッチャ
├── scripts/
│   └── generate_dlq_workbook.py  # Excel 生成スクリプト
└── terraform/
    ├── envs/
    │   └── dev/                  # 環境固有の設定
    └── modules/
        └── sqs-lambda-ecs/       # 再利用可能なモジュール
            ├── sqs.tf            # メインキュー・DLQ・redrive 設定
            ├── lambda.tf         # Lambda とイベントソースマッピング
            ├── ecs.tf            # クラスターとタスク定義
            ├── iam.tf            # 各ロールと最小権限ポリシー
            ├── cloudwatch.tf     # アラーム 4 本・ダッシュボード
            └── outputs.tf        # 運用コマンドで使う出力値
```

---

## 設計上の重要ポイント

| 項目 | 設定 | 理由 |
|---|---|---|
| 可視性タイムアウト | Lambda タイムアウトの 6 倍（180 秒） | 短いと処理中に再配信され、ECS タスクの二重起動と誤 DLQ 行きを招く |
| DLQ 保持期間 | 14 日（最大値） | 調査に時間がかかっても再投入の機会を失わないため |
| `redrive_allow_policy` | メインキューのみ許可 | これがないと再投入が `AccessDenied` で失敗する |
| `ReportBatchItemFailures` | 有効 | バッチ内の失敗分だけをキューに残し、成功分の再処理を防ぐ |
| `RunTask` の `failures` 検査 | 例外化 | HTTP 200 でもタスク起動に失敗することがあり、見落とすとメッセージロストになる |
| DLQ 件数アラームの統計 | `Maximum` | 残高メトリクスを `Sum` にすると件数が水増しされる |
| `treat_missing_data` | `notBreaching` | DLQ が空だとメトリクスが欠落するため、誤検知を防ぐ |
| 通知連携 | 行わない | アラームは状態判定のみ。検知は日次点検によるプル型（上記の注意書きを参照） |
| Lambda 最大同時実行数 | 10 | `RunTask` のスロットリングとサブネットの IP 枯渇を防ぐ |

---

## 動作確認について

Terraform コードは `terraform validate` と `terraform fmt` を通しています。
AWS 認証情報が必要な `terraform plan` / `apply` による実環境でのデプロイ検証は行っていません。
初回適用時は必ず `terraform plan` の内容を確認してください。
