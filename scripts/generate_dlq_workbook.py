#!/usr/bin/env python3
"""DLQ 運用手順書 (Excel) を生成するスクリプト。

使い方:
    python3 scripts/generate_dlq_workbook.py [出力パス]

docs/DLQ運用ガイド.md と同じ内容を、現場で配布しやすいブック形式にまとめる。
"""

import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

# --- 配色 -------------------------------------------------------------------
NAVY = "1F3864"      # タイトル帯
BLUE = "2E5C8A"      # 見出し行
LIGHT = "DCE6F1"     # 小見出し / 強調
STRIPE = "F2F6FB"    # 縞模様
WARN = "FFF2CC"      # 注意
DANGER = "F8CBAD"    # 警告
OK = "E2EFDA"        # 正常 / 完了

FONT = "Meiryo"

THIN = Side(style="thin", color="B7C4D6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# --- 共通ヘルパ -------------------------------------------------------------
def title(ws, text, subtitle, width):
    """シート冒頭のタイトル帯を描画し、次に書き込むべき行番号を返す。"""
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(name=FONT, size=16, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 34

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    c = ws.cell(row=2, column=1, value=subtitle)
    c.font = Font(name=FONT, size=10, color="44546A")
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20
    return 4


def header(ws, row, values):
    for i, v in enumerate(values, start=1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLUE)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = 30
    return row + 1


def row_out(ws, row, values, fill=None, bold_first=False, wrap=True, height=None):
    for i, v in enumerate(values, start=1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = Font(name=FONT, size=10, bold=(bold_first and i == 1))
        c.alignment = Alignment(
            horizontal="left", vertical="top", wrap_text=wrap, indent=1
        )
        c.border = BORDER
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
    if height:
        ws.row_dimensions[row].height = height
    return row + 1


def section(ws, row, text, width):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=FONT, size=11, bold=True, color=NAVY)
    c.fill = PatternFill("solid", fgColor=LIGHT)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 24
    return row + 1


def note(ws, row, text, width, fill=WARN):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=FONT, size=10, bold=True, color="7F3F00")
    c.fill = PatternFill("solid", fgColor=fill)
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
    c.border = BORDER
    ws.row_dimensions[row].height = 32
    return row + 1


def widths(ws, spec):
    for i, w in enumerate(spec, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def mono(ws, cell_ref):
    """コマンド欄を等幅フォントにする。"""
    c = ws[cell_ref]
    c.font = Font(name="Consolas", size=9)
    c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)


def freeze(ws, ref="A5"):
    """ウィンドウ枠の固定と、A4 横・幅 1 ページに収める印刷設定を行う。"""
    ws.freeze_panes = ref
    ws.sheet_view.showGridLines = False

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    # 1〜3 行目 (タイトル帯) を各ページに繰り返し印刷する
    ws.print_title_rows = "1:3"


# ===========================================================================
# 1. はじめに
# ===========================================================================
def sheet_intro(wb):
    ws = wb.create_sheet("01_はじめに")
    widths(ws, [4, 26, 34, 62])
    r = title(
        ws,
        "SQS → Lambda → ECS  DLQ 運用手順書",
        "メッセージが DLQ に入ってから、アラームで気づき、件数を確認し、再投入して復旧するまでの全手順",
        4,
    )

    r = section(ws, r, "このブックの目的", 4)
    r = row_out(
        ws, r,
        ["",
         "目的",
         "DLQ 障害対応を、担当者が代わっても同じ品質で実施できるようにする",
         "本番障害時にこのブックだけを見れば対応が完了する状態を目指しています。"],
        height=34,
    )
    r = row_out(
        ws, r,
        ["", "対象読者", "本パイプラインの運用担当者",
         "AWS マネジメントコンソールと AWS CLI の基本操作ができれば読めます。"],
        fill=STRIPE, height=34,
    )
    r = row_out(
        ws, r,
        ["", "使い方", "障害時は「06_対応手順」から読む",
         "平常時は「09_チェックリスト」で日次・月次点検を行ってください。"],
        height=34,
    )
    r += 1

    r = section(ws, r, "シート一覧", 4)
    r = header(ws, r, ["", "シート", "内容", "どんなときに見るか"])
    sheets = [
        ("01_はじめに", "本ブックの読み方とシート一覧", "最初に一度だけ"),
        ("02_全体構成", "正常時と異常時のメッセージの流れ、構成要素の一覧", "仕組みを理解したいとき"),
        ("03_構築手順", "Terraform でのデプロイと適用直後の必須作業", "環境を新規構築するとき"),
        ("04_設定リファレンス", "SQS / Lambda / ECS の全設定値とその決め方", "設定値を変更・レビューするとき"),
        ("05_アラーム設定", "CloudWatch アラーム 4 本の詳細設定", "監視設計を確認・調整するとき"),
        ("06_対応手順", "★本編★ STEP1〜7 の障害対応フロー", "アラームが鳴ったとき（最重要）"),
        ("07_コマンド集", "コピペで使える AWS CLI コマンド一覧", "対応手順と併用する"),
        ("08_トラブルシュート", "症状別の原因と対処", "手順どおりに進まないとき"),
        ("09_チェックリスト", "導入時 / 日次 / 月次の点検項目", "定期点検・導入判定時"),
        ("10_用語集", "DLQ 関連用語の日本語解説", "用語がわからないとき"),
    ]
    stripe = False
    for name, desc, when in sheets:
        r = row_out(ws, r, ["", name, desc, when],
                    fill=STRIPE if stripe else None, bold_first=False, height=22)
        ws.cell(row=r - 1, column=2).font = Font(name=FONT, size=10, bold=True)
        stripe = not stripe
    r += 1

    r = note(
        ws, r,
        "【最重要】原因を修正する前に再投入してはいけません。原因が残ったまま戻すと、また規定回数失敗して DLQ に返ってくるだけです。",
        4, DANGER,
    )
    r += 1

    r = section(ws, r, "3 行でわかる DLQ", 4)
    r = row_out(ws, r, ["", "DLQ とは", "処理に失敗したメッセージの一時保管場所",
                        "ゴミ箱ではありません。「要調査の待合室」です。中身は必ず調査してください。"], height=32)
    r = row_out(ws, r, ["", "なぜ入るのか", "同じメッセージの受信回数が maxReceiveCount (既定 3) を超えたから",
                        "SQS が自動で移動させます。Lambda や Terraform が動くわけではありません。"],
                fill=STRIPE, height=32)
    r = row_out(ws, r, ["", "どう直すのか", "① 気づく → ② 数える → ③ 中身を見る → ④ 原因を直す → ⑤ 戻す → ⑥ 確認する",
                        "この順番を守ることが復旧の全てです。順番を飛ばすと必ず再発します。"], height=32)

    freeze(ws, "A4")
    return ws


# ===========================================================================
# 2. 全体構成
# ===========================================================================
def sheet_architecture(wb):
    ws = wb.create_sheet("02_全体構成")
    widths(ws, [4, 22, 30, 64])
    r = title(ws, "全体構成", "正常時と異常時、それぞれのメッセージの流れ", 4)

    r = section(ws, r, "① 正常時の流れ", 4)
    r = header(ws, r, ["", "手順", "何が起きるか", "補足"])
    flow = [
        ("1. 送信", "送信元アプリが SQS メインキューへメッセージを送る", "aws sqs send-message、または他の AWS サービスからの連携"),
        ("2. ポーリング", "Lambda イベントソースマッピングが自動でキューを読み、Lambda を起動する",
         "Lambda 側の設定。SQS 側には何も設定しません"),
        ("3. タスク起動", "Lambda が ecs:RunTask で Fargate タスクを 1 つ起動する",
         "メッセージ本文は containerOverrides の環境変数として渡されます"),
        ("4. 削除", "Lambda が正常終了すると SQS がメッセージを自動削除する",
         "アプリが明示的に削除する必要はありません"),
    ]
    stripe = False
    for a, b, c in flow:
        r = row_out(ws, r, ["", a, b, c], fill=STRIPE if stripe else None,
                    bold_first=True, height=34)
        stripe = not stripe
    r += 1

    r = section(ws, r, "② 異常時 ― DLQ に落ちるまで", 4)
    r = header(ws, r, ["", "手順", "何が起きるか", "補足"])
    flow2 = [
        ("1. 失敗", "Lambda が例外を投げる / タイムアウトする / RunTask が失敗を返す",
         "受信回数 (ApproximateReceiveCount) が 1 増えます"),
        ("2. 再配信", "可視性タイムアウト (既定 180 秒) が経過するとメッセージが再び見えるようになる",
         "SQS が自動で再配信します"),
        ("3. 繰り返し", "1〜2 を maxReceiveCount (既定 3) 回くり返す",
         "一時的な障害ならこの間に自然復旧します"),
        ("4. DLQ 退避", "受信回数が maxReceiveCount を超えると SQS が DLQ へ移動する",
         "★ ここが DLQ 行きの瞬間。redrive_policy の設定に基づきます"),
        ("5. 発報", "CloudWatch アラームが ALARM 状態になり、SNS 経由でメールが届く",
         "DLQ 件数 > 0 を 1 分周期で監視しています"),
    ]
    stripe = False
    for a, b, c in flow2:
        r = row_out(ws, r, ["", a, b, c], fill=STRIPE if stripe else None,
                    bold_first=True, height=34)
        stripe = not stripe
    r += 1

    r = note(ws, r,
             "DLQ 行きの判定条件はただ 1 つ「受信回数が maxReceiveCount を超えること」です。エラーの種類は関係ありません。",
             4)
    r += 1

    r = section(ws, r, "③ 構成要素と役割", 4)
    r = header(ws, r, ["", "リソース", "名前 (既定)", "役割"])
    comps = [
        ("SQS メインキュー", "<prefix>-queue", "処理待ちメッセージを受け取る。redrive_policy で DLQ を紐付け"),
        ("SQS DLQ", "<prefix>-dlq", "規定回数失敗したメッセージを退避。保持期間は最大 14 日"),
        ("Lambda 関数", "<prefix>-dispatcher", "メッセージを受けて ECS タスクを起動するディスパッチャ"),
        ("イベントソースマッピング", "(Lambda に内包)", "SQS を自動ポーリングして Lambda を起動。同時実行数の上限もここで設定"),
        ("ECS クラスター", "<prefix>-cluster", "Fargate タスクの実行基盤"),
        ("ECS タスク定義", "<prefix>-worker", "実際の業務処理を行うコンテナの定義"),
        ("SNS トピック", "<prefix>-alarm-topic", "アラーム通知の配信先。メール購読の承認が必須"),
        ("CloudWatch アラーム", "<prefix>-dlq-messages-visible ほか計 4 本", "DLQ 滞留・流入・遅延・Lambda エラーを監視"),
        ("CloudWatch ダッシュボード", "<prefix>-dashboard", "件数・エラーを 1 画面で確認する運用画面"),
        ("CloudWatch Logs", "/aws/lambda/<prefix>-dispatcher, /ecs/<prefix>-worker", "障害調査のログ出力先"),
    ]
    stripe = False
    for a, b, c in comps:
        r = row_out(ws, r, ["", a, b, c], fill=STRIPE if stripe else None,
                    bold_first=True, height=30)
        ws.cell(row=r - 1, column=3).font = Font(name="Consolas", size=9)
        stripe = not stripe

    freeze(ws)
    return ws


# ===========================================================================
# 3. 構築手順
# ===========================================================================
def sheet_build(wb):
    ws = wb.create_sheet("03_構築手順")
    widths(ws, [4, 8, 34, 52, 30])
    r = title(ws, "構築手順", "Terraform でのデプロイと、適用直後に必ず行う作業", 5)

    r = section(ws, r, "前提条件", 5)
    r = header(ws, r, ["", "#", "項目", "内容", "確認方法"])
    pre = [
        ("1", "Terraform", "1.5 以上", "terraform version"),
        ("2", "AWS CLI", "v2。対象アカウントへの認証が通ること", "aws sts get-caller-identity"),
        ("3", "ネットワーク", "VPC・サブネット・セキュリティグループが構築済み", "aws ec2 describe-subnets"),
        ("4", "コンテナイメージ", "ワーカーのイメージが ECR に push 済み", "aws ecr describe-images"),
        ("5", "外部疎通", "プライベートサブネットの場合、NAT GW または VPC エンドポイントが必要",
         "未整備だと CannotPullContainerError が多発"),
    ]
    stripe = False
    for a, b, c, d in pre:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None, height=30)
        stripe = not stripe
    r += 1

    r = section(ws, r, "デプロイ手順", 5)
    r = header(ws, r, ["", "#", "作業", "コマンド", "確認ポイント"])
    steps = [
        ("1", "作業ディレクトリへ移動", "cd terraform/envs/dev", "―"),
        ("2", "設定ファイルを作成", "cp terraform.tfvars.example terraform.tfvars", "―"),
        ("3", "自環境に合わせて編集",
         "vi terraform.tfvars", "subnet_ids / security_group_ids / container_image を設定"),
        ("4", "初期化", "terraform init", "プロバイダの取得が成功すること"),
        ("5", "差分確認", "terraform plan", "作成されるリソース数を必ず目視する"),
        ("6", "適用", "terraform apply", "Apply complete! と表示されること"),
        ("7", "出力値の確認", "terraform output", "queue_url / dlq_arn などを控える"),
    ]
    stripe = False
    for a, b, c, d in steps:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None, height=26)
        mono(ws, f"D{r - 1}")
        stripe = not stripe
    r += 1

    r = note(ws, r,
             "【必須】apply 後、SNS から届く確認メールの「Confirm subscription」を必ずクリックしてください。承認しないとアラームが鳴っても通知が届きません。",
             5, DANGER)
    r += 1

    r = section(ws, r, "適用直後の必須作業", 5)
    r = header(ws, r, ["", "#", "作業", "コマンド / 操作", "完了条件"])
    post = [
        ("1", "SNS メール購読の承認", "受信メール内の Confirm subscription をクリック",
         "SubscriptionArn が PendingConfirmation でないこと"),
        ("2", "購読状態の確認",
         'aws sns list-subscriptions-by-topic --topic-arn "$(terraform output -raw sns_topic_arn)"',
         "Endpoint が一覧に表示される"),
        ("3", "出力値の記録", "terraform output", "main_queue_url / dlq_url / dlq_arn / main_queue_arn を控える"),
        ("4", "ダッシュボード登録", "CloudWatch → ダッシュボード → <prefix>-dashboard", "ブックマークに追加"),
        ("5", "疎通テスト",
         'aws sqs send-message --queue-url "$MAIN_URL" --message-body \'{"test": true}\'',
         "ECS タスクが起動しログが出ること"),
        ("6", "DLQ 到達テスト", "わざと失敗するメッセージを送る", "3 回失敗して DLQ に入ること"),
        ("7", "アラーム発報テスト", "上記 6 の後、メール受信を待つ", "ALARM メールが届くこと"),
        ("8", "再投入テスト", "07_コマンド集の再投入コマンドを実行", "DLQ が 0 件に戻ること"),
    ]
    stripe = False
    for a, b, c, d in post:
        fill = OK if a in ("6", "7", "8") else (STRIPE if stripe else None)
        r = row_out(ws, r, ["", a, b, c, d], fill=fill, height=30)
        mono(ws, f"D{r - 1}")
        stripe = not stripe
    r += 1

    r = note(ws, r,
             "緑色の 6〜8 は「訓練」です。本番投入前に必ず実施してください。『アラームが飛ぶはずだった』で気づけないのが最悪のパターンです。",
             5)

    freeze(ws)
    return ws


# ===========================================================================
# 4. 設定リファレンス
# ===========================================================================
def sheet_config(wb):
    ws = wb.create_sheet("04_設定リファレンス")
    widths(ws, [4, 30, 36, 16, 60])
    r = title(ws, "設定リファレンス", "各設定値の意味と、値の決め方", 5)

    r = section(ws, r, "SQS ― DLQ 動作を決める最重要パラメータ", 5)
    r = header(ws, r, ["", "設定項目", "Terraform 変数名", "既定値", "意味と決め方"])
    sqs = [
        ("最大受信回数", "max_receive_count", "3",
         "何回失敗したら DLQ へ送るか。小さすぎると一時障害で DLQ 行きが多発し、大きすぎると異常の発見が遅れる。3〜5 が目安"),
        ("可視性タイムアウト", "visibility_timeout_seconds", "180 秒",
         "処理中のメッセージを他から見えなくする時間。Lambda タイムアウトの 6 倍以上が AWS 推奨 (30 秒 × 6 = 180 秒)"),
        ("メインキュー保持期間", "message_retention_seconds", "345,600 秒 (4 日)",
         "メインキューにメッセージを保持する期間"),
        ("DLQ 保持期間", "dlq_message_retention_seconds", "1,209,600 秒 (14 日)",
         "★最大値を推奨。この期間を過ぎると DLQ のメッセージは消え、二度と再投入できない"),
        ("暗号化", "(sqs_managed_sse_enabled)", "true",
         "SQS 管理キーによる保存時暗号化。追加コストなし"),
        ("再投入許可", "(redrive_allow_policy)", "byQueue",
         "DLQ から戻せる先をメインキューだけに限定。未設定だと再投入が AccessDenied で失敗する"),
    ]
    stripe = False
    for a, b, c, d in sqs:
        fill = WARN if b == "dlq_message_retention_seconds" else (STRIPE if stripe else None)
        r = row_out(ws, r, ["", a, b, c, d], fill=fill, bold_first=True, height=36)
        ws.cell(row=r - 1, column=3).font = Font(name="Consolas", size=9)
        stripe = not stripe
    r += 1

    r = note(ws, r,
             "【可視性タイムアウトの罠】Lambda のタイムアウトより短いと、処理中なのに再配信され、ECS タスクが多重起動したうえで受信回数だけが増え、正常な処理でも DLQ 行きになります。必ず「可視性タイムアウト ≧ Lambda タイムアウト × 6」を守ること。",
             5, DANGER)
    r += 1

    r = section(ws, r, "Lambda", 5)
    r = header(ws, r, ["", "設定項目", "Terraform 変数名", "既定値", "意味と決め方"])
    lam = [
        ("タイムアウト", "lambda_timeout_seconds", "30 秒", "RunTask は通常 1 秒以内。余裕を見て 30 秒"),
        ("メモリ", "lambda_memory_size", "256 MB", "API 呼び出しのみのため小さくてよい"),
        ("バッチサイズ", "lambda_batch_size", "1", "1 メッセージ = 1 ECS タスク。増やすと 1 回の呼び出しで複数タスクを起動する"),
        ("最大同時実行数", "lambda_maximum_concurrency", "10",
         "ECS RunTask のスロットリングとサブネット IP 枯渇を防ぐ上限。下流の処理能力に合わせる"),
        ("部分バッチ応答", "(function_response_types)", "ReportBatchItemFailures",
         "★失敗したメッセージだけをキューに残す設定。無いとバッチ内の成功分まで再処理され ECS タスクが二重起動する"),
        ("ログ保持日数", "log_retention_in_days", "30 日", "調査に必要な期間とコストのバランスで決める"),
    ]
    stripe = False
    for a, b, c, d in lam:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None,
                    bold_first=True, height=32)
        ws.cell(row=r - 1, column=3).font = Font(name="Consolas", size=9)
        stripe = not stripe
    r += 1

    r = section(ws, r, "ECS", 5)
    r = header(ws, r, ["", "設定項目", "Terraform 変数名", "既定値", "意味と決め方"])
    ecs = [
        ("コンテナイメージ", "container_image", "(必須)", "ECR のイメージ URI。タグは latest ではなくバージョン固定を推奨"),
        ("CPU", "task_cpu", "256", "Fargate の CPU ユニット。256 = 0.25 vCPU"),
        ("メモリ", "task_memory", "512", "MB 単位。CPU との組み合わせに制約がある"),
        ("サブネット", "subnet_ids", "(必須)", "プライベートサブネット推奨。NAT GW か VPC エンドポイントが必要"),
        ("セキュリティグループ", "security_group_ids", "(必須)", "アウトバウンドで ECR / Logs / SQS に到達できること"),
        ("パブリック IP", "assign_public_ip", "false", "パブリックサブネットを使う場合のみ true"),
        ("Container Insights", "enable_container_insights", "true", "タスク単位のメトリクス収集。有効化推奨"),
    ]
    stripe = False
    for a, b, c, d in ecs:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None,
                    bold_first=True, height=30)
        ws.cell(row=r - 1, column=3).font = Font(name="Consolas", size=9)
        stripe = not stripe
    r += 1

    r = section(ws, r, "設定値の相互関係 ― ここだけは覚える", 5)
    r = header(ws, r, ["", "ルール", "式", "既定値での確認", "破ると何が起きるか"])
    rules = [
        ("可視性タイムアウト", "≧ Lambda タイムアウト × 6", "180 ≧ 30 × 6 = 180 ✔",
         "処理中に再配信され、ECS タスク二重起動＋誤 DLQ 行き"),
        ("DLQ 保持期間", "≧ 調査に必要な日数", "14 日 (最大値) ✔",
         "調査中にメッセージが消滅し、再投入不可能になる"),
        ("最大同時実行数", "≦ 下流の処理能力", "10 ✔",
         "RunTask がスロットリングされ、サブネットの IP が枯渇する"),
        ("最大受信回数", "3〜5", "3 ✔",
         "小さい → 一時障害で DLQ 多発 / 大きい → 異常検知が遅れる"),
    ]
    for a, b, c, d in rules:
        r = row_out(ws, r, ["", a, b, c, d], fill=OK, bold_first=True, height=30)

    freeze(ws)
    return ws


# ===========================================================================
# 5. アラーム設定
# ===========================================================================
def sheet_alarms(wb):
    ws = wb.create_sheet("05_アラーム設定")
    widths(ws, [4, 30, 34, 12, 12, 16, 46])
    r = title(ws, "CloudWatch アラーム設定", "DLQ の件数に気づくための監視 4 本", 7)

    r = header(ws, r, ["", "アラーム名", "メトリクス", "統計", "期間", "しきい値", "何を意味するか / 鳴ったらどうするか"])
    alarms = [
        ("<prefix>-dlq-messages-visible\n★最重要",
         "ApproximateNumberOfMessagesVisible\n(AWS/SQS)", "Maximum", "60 秒", "> 0",
         "DLQ に未処理メッセージが滞留している。1 件でも残る限り発報し続ける。→ 06_対応手順 STEP1 へ"),
        ("<prefix>-dlq-messages-sent",
         "NumberOfMessagesSent\n(AWS/SQS)", "Sum", "300 秒", "> 0",
         "新たに DLQ へ流入した。増加の「瞬間」を捉える。→ 流入が続いているかを確認"),
        ("<prefix>-main-queue-age",
         "ApproximateAgeOfOldestMessage\n(AWS/SQS)", "Maximum", "300 秒 × 2 回", "> 900 秒",
         "メインキューの消化が遅れている。DLQ 大量発生の前兆。→ Lambda 同時実行数と ECS の状況を確認"),
        ("<prefix>-lambda-errors",
         "Errors\n(AWS/Lambda)", "Sum", "300 秒", "≧ 1",
         "Lambda が失敗した。DLQ 行きの根本原因を最初に見る場所。→ CloudWatch Logs を確認"),
    ]
    for i, (a, b, c, d, e, f) in enumerate(alarms):
        fill = DANGER if i == 0 else (STRIPE if i % 2 else None)
        r = row_out(ws, r, ["", a, b, c, d, e, f], fill=fill, bold_first=True, height=58)
        for col in (4, 5, 6):
            ws.cell(row=r - 1, column=col).alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True)
    r += 1

    r = section(ws, r, "なぜ統計が Maximum と Sum で違うのか ― 間違えやすい最重要ポイント", 7)
    r = header(ws, r, ["", "メトリクス", "性質", "正しい統計", "誤った統計", "その結果", "解説"])
    r = row_out(ws, r,
                ["", "ApproximateNumberOfMessagesVisible", "その瞬間の残高 (ストック)", "Maximum", "Sum",
                 "件数が水増しされる",
                 "1 分ごとに「3 件」「3 件」「3 件」と同じ値が記録される。Sum にすると 9 件と誤って合算される"],
                fill=WARN, bold_first=True, height=46)
    r = row_out(ws, r,
                ["", "NumberOfMessagesSent", "期間内の発生件数 (フロー)", "Sum", "Maximum",
                 "流入の合計がわからない",
                 "その期間に何件流入したかを知りたいので合計を取る"],
                fill=WARN, bold_first=True, height=46)
    r += 1

    r = section(ws, r, "その他の重要設定", 7)
    r = header(ws, r, ["", "設定", "値 / 内容", "", "", "", "理由"])
    others = [
        ("treat_missing_data", "notBreaching",
         "DLQ が空のとき SQS はメトリクスを送信しないことがある。「データなし＝正常」と扱い、誤発報を防ぐ"),
        ("alarm_actions", "SNS トピック ARN", "ALARM 状態になったときにメール通知する"),
        ("ok_actions (滞留アラームのみ)", "SNS トピック ARN",
         "OK に戻ったときも通知する。復旧を確実に把握するため"),
        ("dlq_depth_alarm_threshold", "0 (既定)",
         "0 件超＝1 件以上で発報。ある程度の失敗を許容するなら 5 などに変更する"),
        ("dlq_depth_alarm_evaluation_periods", "1 (既定)",
         "1 回でも超えたら発報。瞬間的なスパイクを無視したい場合は 2 以上にする"),
    ]
    stripe = False
    for item in others:
        a, b, d = item
        r = row_out(ws, r, ["", a, b, "", "", "", d], fill=STRIPE if stripe else None,
                    bold_first=True, height=30)
        ws.cell(row=r - 1, column=2).font = Font(name="Consolas", size=9, bold=True)
        ws.merge_cells(start_row=r - 1, start_column=3, end_row=r - 1, end_column=6)
        stripe = not stripe
    r += 1

    r = section(ws, r, "しきい値の変更例", 7)
    r = header(ws, r, ["", "やりたいこと", "設定 (terraform.tfvars)", "", "", "", "効果"])
    r = row_out(ws, r, ["", "1 件でも入ったら即通知 (既定)",
                        "dlq_depth_alarm_threshold = 0\ndlq_depth_alarm_evaluation_periods = 1",
                        "", "", "", "最速で検知できる。小規模・重要度の高いシステム向け"],
                bold_first=True, height=42)
    ws.merge_cells(start_row=r - 1, start_column=3, end_row=r - 1, end_column=6)
    mono(ws, f"C{r - 1}")
    r = row_out(ws, r, ["", "5 件を超えたら通知",
                        "dlq_depth_alarm_threshold = 5\ndlq_depth_alarm_evaluation_periods = 2",
                        "", "", "", "2 分連続で 5 件超のときだけ発報。ノイズを抑えたい大規模システム向け"],
                fill=STRIPE, bold_first=True, height=42)
    ws.merge_cells(start_row=r - 1, start_column=3, end_row=r - 1, end_column=6)
    mono(ws, f"C{r - 1}")

    freeze(ws)
    return ws


# ===========================================================================
# 6. 対応手順 (本編)
# ===========================================================================
def sheet_procedure(wb):
    ws = wb.create_sheet("06_対応手順")
    widths(ws, [4, 10, 26, 54, 54])
    r = title(ws, "★障害対応手順★  STEP 1 〜 7",
              "アラーム受信から復旧確認まで。上から順に実施してください", 5)

    r = note(ws, r,
             "【鉄則】STEP 5「原因を修正する」を飛ばして STEP 6「再投入」に進まないこと。原因が残ったまま戻すと、また規定回数失敗して DLQ に返ってくるだけです。",
             5, DANGER)
    r += 1

    def step(row, no, name, purpose):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        c = ws.cell(row=row, column=1, value=f"  STEP {no}:  {name}   ―   {purpose}")
        c.font = Font(name=FONT, size=12, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLUE)
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[row].height = 28
        return row + 1

    def steps_header(row):
        return header(ws, row, ["", "#", "作業", "コマンド / 操作", "確認ポイント・注意"])

    def s(row, n, work, cmd, check, fill=None, h=40):
        row = row_out(ws, row, ["", n, work, cmd, check], fill=fill, height=h)
        mono(ws, f"D{row - 1}")
        return row

    # STEP 1
    r = step(r, 1, "アラームで気づく", "通知を受け取り、事実を確認する")
    r = steps_header(r)
    r = s(r, "1-1", "SNS のアラームメールを受信する",
          'ALARM: "dlq-demo-dlq-messages-visible"\nThreshold Crossed: 1 datapoint [3.0] was\ngreater than the threshold (0.0).',
          "[3.0] の部分が現在の DLQ 件数。この例では 3 件が滞留している", h=58)
    r = s(r, "1-2", "アラーム状態をコマンドで確認する",
          'aws cloudwatch describe-alarms \\\n  --alarm-names dlq-demo-dlq-messages-visible \\\n  --query "MetricAlarms[].[AlarmName,StateValue,StateReason]" \\\n  --output table',
          "StateValue が ALARM であること。メールを見逃した場合もこれで確認できる",
          fill=STRIPE, h=64)
    r = s(r, "1-3", "ダッシュボードで推移を見る",
          "CloudWatch → ダッシュボード → dlq-demo-dashboard",
          "いつから増え始めたか / 増え続けているか止まったか を把握する", h=32)
    r += 1

    # STEP 2
    r = step(r, 2, "件数を確認する", "今 DLQ に何件あるのかを正確に把握する")
    r = steps_header(r)
    r = s(r, "2-1", "【方法A】ダッシュボード (推移を見る)",
          "CloudWatch → ダッシュボード → dlq-demo-dashboard\n→ 左上「DLQ 滞留件数」パネル",
          "まずここを見る。増加が止まっているか継続中かで緊急度が変わる", h=44)
    r = s(r, "2-2", "【方法B】AWS CLI (正確な即時値・推奨)",
          'DLQ_URL=$(terraform output -raw dlq_url)\n\naws sqs get-queue-attributes \\\n  --queue-url "$DLQ_URL" \\\n  --attribute-names ApproximateNumberOfMessages \\\n                    ApproximateNumberOfMessagesNotVisible \\\n                    ApproximateNumberOfMessagesDelayed',
          "3 つの属性の合計が DLQ の実際の総件数。ApproximateNumberOfMessages だけ見ると受信中の分を見落とす",
          fill=STRIPE, h=96)
    r = s(r, "2-3", "【方法C】メトリクスを過去に遡って取得",
          'aws cloudwatch get-metric-statistics \\\n  --namespace AWS/SQS \\\n  --metric-name ApproximateNumberOfMessagesVisible \\\n  --dimensions Name=QueueName,Value=dlq-demo-dlq \\\n  --start-time "$(date -u -d \'24 hours ago\' +%Y-%m-%dT%H:%M:%SZ)" \\\n  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \\\n  --period 300 --statistics Maximum --output table',
          "発生時刻の特定に使う。デプロイ時刻と突き合わせると原因が絞れる", h=104)
    r = row_out(ws, r, ["", "属性の意味", "ApproximateNumberOfMessages",
                        "受信可能な件数。通常はこれを見る", "「今すぐ処理できる状態で待っている件数」"],
                fill=LIGHT, height=26)
    r = row_out(ws, r, ["", "", "ApproximateNumberOfMessagesNotVisible",
                        "誰かが受信中でまだ削除されていない件数", "調査で receive-message した直後はここに移動する"],
                fill=LIGHT, height=26)
    r = row_out(ws, r, ["", "", "ApproximateNumberOfMessagesDelayed",
                        "遅延設定でまだ配信されていない件数", "本構成では通常 0"],
                fill=LIGHT, height=26)
    r = note(ws, r,
             "「Approximate (およそ)」は飾りではありません。SQS は分散システムのため件数はわずかに前後します。「0 件かどうか」の判定には使えますが、厳密な会計には使わないでください。",
             5)
    r += 1

    # STEP 3
    r = step(r, 3, "中身を確認する", "何が失敗しているのかを実際のメッセージで見る")
    r = steps_header(r)
    r = s(r, "3-1", "DLQ のメッセージを覗く (削除しない)",
          'aws sqs receive-message \\\n  --queue-url "$DLQ_URL" \\\n  --max-number-of-messages 10 \\\n  --visibility-timeout 0 \\\n  --message-attribute-names All \\\n  --message-system-attribute-names All',
          "★--visibility-timeout 0 を必ず付ける。省くとメッセージがロックされ、その間は再投入できない",
          fill=DANGER, h=96)
    r = s(r, "3-2", "調査用に全件をファイル保存",
          'aws sqs receive-message --queue-url "$DLQ_URL" \\\n  --max-number-of-messages 10 --visibility-timeout 0 \\\n  --message-system-attribute-names All \\\n  > dlq_snapshot_$(date +%Y%m%d_%H%M%S).json',
          "1 回で最大 10 件。多い場合は繰り返す。証跡として必ず残す", fill=STRIPE, h=72)
    r = row_out(ws, r, ["", "読み方", "Body", "実際のペイロード",
                        '例: {"orderId":"12345","amount":"abc"} → amount が数値でない = データ不正'],
                fill=LIGHT, height=30)
    r = row_out(ws, r, ["", "", "ApproximateReceiveCount", "実際に受信された回数",
                        "maxReceiveCount (3) を超えて 4 になっていれば、確かに規定回数失敗した証拠"],
                fill=LIGHT, height=30)
    r = row_out(ws, r, ["", "", "SentTimestamp", "元々いつ送信されたか", "ミリ秒 UNIX 時間。障害発生時刻の特定に使う"],
                fill=LIGHT, height=26)
    r = row_out(ws, r, ["", "", "MessageId", "メッセージの一意 ID",
                        "★この ID で STEP 4 の Lambda ログ検索を行う。必ず控えること"],
                fill=LIGHT, height=30)
    r = note(ws, r,
             "【禁止】調査中に delete-message を実行しないこと。削除するとメッセージは永久に失われ、再投入できなくなります。",
             5, DANGER)
    r += 1

    # STEP 4
    r = step(r, 4, "原因を特定する", "ログから根本原因を突き止める")
    r = steps_header(r)
    r = s(r, "4-1", "MessageId で Lambda ログを絞り込む",
          'LOG_GROUP=$(terraform output -raw lambda_log_group_name)\n\naws logs filter-log-events \\\n  --log-group-name "$LOG_GROUP" \\\n  --start-time "$(($(date +%s) - 86400))000" \\\n  --filter-pattern \'"a1b2c3d4-"\' \\\n  --query "events[].message" --output text',
          "STEP 3 で控えた MessageId を filter-pattern に指定する", h=96)
    r = s(r, "4-2", "Logs Insights でエラー一覧 (推奨)",
          "fields @timestamp, @message\n| filter @message like /ERROR/ or @message like /Traceback/\n| sort @timestamp desc\n| limit 50",
          "コンソール → CloudWatch → ログ → Logs Insights で実行", fill=STRIPE, h=64)
    r = s(r, "4-3", "エラー種別ごとに集計して傾向を見る",
          "fields @message\n| filter @message like /ERROR/\n| parse @message /(?<errType>[A-Za-z]+Error|[A-Za-z]+Exception)/\n| stats count(*) as 件数 by errType\n| sort 件数 desc",
          "単発の障害か、同一原因の大量発生かを判断する", h=78)
    r = s(r, "4-4", "ECS タスク側のログも確認する",
          'ECS_LOG_GROUP=$(terraform output -raw ecs_log_group_name)\naws logs tail "$ECS_LOG_GROUP" --since 1h --format short',
          "Lambda が正常でもコンテナ内で失敗している場合がある", fill=STRIPE, h=44)
    r += 1

    r = section(ws, r, "エラーメッセージ別・原因早見表", 5)
    r = header(ws, r, ["", "#", "ログに出る文字列", "原因", "対処"])
    errs = [
        ("1", "AccessDeniedException ... ecs:RunTask", "Lambda ロールの権限不足",
         "IAM ポリシーを確認。iam:PassRole の付け忘れが最多"),
        ("2", "InvalidParameterException ... subnet", "サブネット ID の誤り、AZ 不一致",
         "subnet_ids を見直す"),
        ("3", "CannotPullContainerError", "ECR に到達できない / イメージが存在しない",
         "NAT GW・VPC エンドポイント・イメージタグを確認"),
        ("4", "Task timed out after 30.00 seconds", "Lambda のタイムアウト",
         "lambda_timeout_seconds を延長し、可視性タイムアウトも 6 倍に追随させる"),
        ("5", "RunTask returned failures ... RESOURCE:ENI", "サブネットの IP アドレス枯渇",
         "サブネットを増やす、lambda_maximum_concurrency を下げる"),
        ("6", "ThrottlingException", "RunTask の API 制限",
         "lambda_maximum_concurrency を下げる"),
        ("7", "JSONDecodeError / KeyError", "メッセージ自体が不正 (ポイズンピル)",
         "★再投入しても直らない。送信元を修正し、該当メッセージは破棄する"),
    ]
    stripe = False
    for a, b, c, d in errs:
        fill = DANGER if a == "7" else (STRIPE if stripe else None)
        r = row_out(ws, r, ["", a, b, c, d], fill=fill, height=32)
        ws.cell(row=r - 1, column=3).font = Font(name="Consolas", size=9)
        stripe = not stripe
    r += 1

    # STEP 5
    r = step(r, 5, "原因を修正する", "再投入で直るのか、直らないのかを見極める")
    r = header(ws, r, ["", "原因の種類", "具体例", "対応", "再投入で直るか"])
    fixes = [
        ("一時的な障害", "スロットリング、Fargate キャパシティ不足、AWS 側の瞬断",
         "復旧を待つだけ。追加作業は不要", "○ 直る → STEP 6 へ"),
        ("設定ミス", "IAM 権限、サブネット、環境変数の誤り",
         "Terraform を修正して terraform apply", "○ 直る → STEP 6 へ"),
        ("アプリのバグ", "コンテナ内の処理が例外を投げる",
         "コードを修正し、新イメージを push してタスク定義を更新", "○ 直る → STEP 6 へ"),
        ("メッセージが不正", "JSON が壊れている、必須項目がない (ポイズンピル)",
         "送信元アプリのバリデーションを修正する", "× 直らない → 下記参照"),
    ]
    for a, b, c, d in fixes:
        fill = DANGER if d.startswith("×") else OK
        r = row_out(ws, r, ["", a, b, c, d], fill=fill, bold_first=True, height=34)
    r += 1

    r = section(ws, r, "ポイズンピル (何度戻しても失敗するメッセージ) の扱い", 5)
    r = steps_header(r)
    r = s(r, "5-1", "証跡を保存する", "STEP 3-2 の dlq_snapshot_*.json を保管",
          "削除前に必ず内容を残す", h=26)
    r = s(r, "5-2", "業務影響を関係者に確認する", "―",
          "そのデータは再作成が必要か？ 破棄してよいか？ を必ず合意する", fill=STRIPE, h=32)
    r = s(r, "5-3", "送信元アプリを修正する", "―", "根本原因。ここを直さないと再発する", h=26)
    r = s(r, "5-4", "該当メッセージを削除する",
          'aws sqs delete-message \\\n  --queue-url "$DLQ_URL" \\\n  --receipt-handle "<ReceiptHandle>"',
          "ReceiptHandle は receive-message のたびに変わる。取得した直後に実行すること",
          fill=WARN, h=58)
    r += 1

    r = section(ws, r, "再投入の前に ― スモークテスト (必須)", 5)
    r = steps_header(r)
    r = s(r, "5-5", "テストメッセージを 1 件だけ送る",
          'MAIN_URL=$(terraform output -raw main_queue_url)\n\naws sqs send-message --queue-url "$MAIN_URL" \\\n  --message-body \'{"test": true, "note": "recovery smoke test"}\'',
          "★これを怠ると、大量のメッセージを再投入して再び全滅させることになる",
          fill=WARN, h=72)
    r = s(r, "5-6", "30 秒待って ECS タスクを確認",
          'aws logs tail "$ECS_LOG_GROUP" --since 5m --format short',
          "タスクが起動し、正常終了のログが出ていること", fill=WARN, h=32)
    r += 1

    # STEP 6
    r = step(r, 6, "再投入する (リドライブ)", "DLQ のメッセージをメインキューへ戻す")
    r = section(ws, r, "【方法A】マネジメントコンソール ― 少量・手軽 (初心者向け)", 5)
    r = steps_header(r)
    cons = [
        ("6A-1", "SQS コンソールで DLQ を開く", "SQS → キュー → dlq-demo-dlq", "―"),
        ("6A-2", "再処理を開始する", "右上「DLQ の再処理を開始」をクリック", "Start DLQ redrive"),
        ("6A-3", "送信先を選ぶ", "「送信元キューへの再処理」を選択", "Redrive to source queue"),
        ("6A-4", "速度制限を設定する", "1 秒あたりのメッセージ数を入力", "★必ず設定する。10〜50 件/秒から始める"),
        ("6A-5", "実行する", "「DLQ の再処理」をクリック", "―"),
        ("6A-6", "進捗を確認する", "画面上の移動済み件数を確認", "完了まで待つ"),
    ]
    stripe = False
    for a, b, c, d in cons:
        r = s(r, a, b, c, d, fill=STRIPE if stripe else None, h=26)
        stripe = not stripe
    r += 1

    r = section(ws, r, "【方法B】AWS CLI ― 件数が多い・記録に残したい (推奨)", 5)
    r = steps_header(r)
    r = s(r, "6B-1", "ARN を取得する",
          "cd terraform/envs/dev\nDLQ_ARN=$(terraform output -raw dlq_arn)\nMAIN_ARN=$(terraform output -raw main_queue_arn)",
          "―", h=58)
    r = s(r, "6B-2", "再投入タスクを開始する",
          'aws sqs start-message-move-task \\\n  --source-arn "$DLQ_ARN" \\\n  --destination-arn "$MAIN_ARN" \\\n  --max-number-of-messages-per-second 10',
          "★--max-number-of-messages-per-second を必ず指定する。省くと最大速度で流れ込み下流を圧迫する",
          fill=WARN, h=72)
    r = s(r, "6B-3", "進捗を確認する",
          'aws sqs list-message-move-tasks \\\n  --source-arn "$DLQ_ARN" --max-results 1',
          "Status が COMPLETED、ApproximateNumberOfMessagesMoved が期待件数と一致すること",
          fill=STRIPE, h=44)
    r = s(r, "6B-4", "途中で止めたい場合",
          'aws sqs cancel-message-move-task \\\n  --task-handle "<TaskHandle>"',
          "TaskHandle は 6B-2 の出力に含まれる", h=40)
    r += 1

    r = header(ws, r, ["", "Status", "意味", "対応", ""])
    ws.merge_cells(start_row=r - 1, start_column=4, end_row=r - 1, end_column=5)
    sts = [
        ("RUNNING", "移動中", "完了まで待つ"),
        ("COMPLETED", "正常に完了", "STEP 7 へ進む"),
        ("FAILED", "失敗", "FailureReason を確認。redrive_allow_policy 未設定が最多"),
        ("CANCELLING / CANCELLED", "キャンセル処理中 / 済み", "必要なら再実行する"),
    ]
    for a, b, c in sts:
        fill = OK if a == "COMPLETED" else (DANGER if a == "FAILED" else STRIPE)
        r = row_out(ws, r, ["", a, b, c, ""], fill=fill, bold_first=True, height=26)
        ws.cell(row=r - 1, column=2).font = Font(name="Consolas", size=9, bold=True)
        ws.merge_cells(start_row=r - 1, start_column=4, end_row=r - 1, end_column=5)
    r += 1

    r = section(ws, r, "再投入時の注意点", 5)
    r = header(ws, r, ["", "#", "注意点", "内容", "守らないと"])
    cautions = [
        ("1", "速度制限を必ず入れる", "10〜50 件/秒から始める",
         "ECS タスクが一気に起動し、下流の DB などを圧迫する"),
        ("2", "同時に 1 タスクだけ", "1 つの DLQ に対して実行できる移動タスクは同時に 1 つ",
         "2 つ目の開始がエラーになる"),
        ("3", "受信回数はリセットされる", "再投入後は新しいメッセージ扱いで受信回数が 1 から数え直し",
         "(仕様。再び規定回数のチャンスがある)"),
        ("4", "DLQ の DLQ は無い", "再投入先はメインキュー。失敗すれば同じ DLQ に戻る",
         "原因未修正だと無限ループになりコストが増える"),
        ("5", "保持期間に注意", "元の SentTimestamp を基準に保持期間が判定される",
         "14 日近く経過したメッセージは移動後すぐ消える可能性がある"),
    ]
    stripe = False
    for a, b, c, d in cautions:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None, height=32)
        stripe = not stripe
    r += 1

    # STEP 7
    r = step(r, 7, "復旧を確認する", "本当に処理されたかを確かめ、記録を残す")
    r = steps_header(r)
    r = s(r, "7-1", "DLQ が 0 件になったか",
          'aws sqs get-queue-attributes --queue-url "$DLQ_URL" \\\n  --attribute-names ApproximateNumberOfMessages \\\n                    ApproximateNumberOfMessagesNotVisible',
          "両方とも \"0\" であること", fill=OK, h=58)
    r = s(r, "7-2", "メインキューも消化されたか",
          'aws sqs get-queue-attributes --queue-url "$MAIN_URL" \\\n  --attribute-names ApproximateNumberOfMessages',
          "0 に向かって減っていること", h=44)
    r = s(r, "7-3", "アラームが OK に戻ったか",
          'aws cloudwatch describe-alarms \\\n  --alarm-names dlq-demo-dlq-messages-visible \\\n  --query "MetricAlarms[].[AlarmName,StateValue]" --output table',
          "StateValue が OK。SNS からも「OK:」で始まる復旧メールが届く (最大 1〜2 分遅れる)",
          fill=OK, h=58)
    r = s(r, "7-4", "ECS タスクが正常終了したか",
          'aws logs tail "$ECS_LOG_GROUP" --since 15m --format short',
          "業務処理の完了ログが出ていること", h=32)
    r = s(r, "7-5", "障害記録を残す", "―",
          "発生・検知・復旧日時 / DLQ 件数 / 根本原因 / 実施した対処 / 再発防止策", fill=OK, h=32)

    freeze(ws)
    return ws


# ===========================================================================
# 7. コマンド集
# ===========================================================================
def sheet_commands(wb):
    ws = wb.create_sheet("07_コマンド集")
    widths(ws, [4, 8, 30, 76, 40])
    r = title(ws, "コマンド集", "コピー&ペーストで使える AWS CLI コマンド (06_対応手順と併用)", 5)

    r = note(ws, r,
             "先に環境変数を設定してください。以降のコマンドはこの変数を前提にしています。",
             5, LIGHT)
    r += 1

    r = header(ws, r, ["", "#", "用途", "コマンド", "備考"])

    cmds = [
        ("準備", "0-1", "環境変数の設定",
         'cd terraform/envs/dev\nDLQ_URL=$(terraform output -raw dlq_url)\nMAIN_URL=$(terraform output -raw main_queue_url)\nDLQ_ARN=$(terraform output -raw dlq_arn)\nMAIN_ARN=$(terraform output -raw main_queue_arn)\nLOG_GROUP=$(terraform output -raw lambda_log_group_name)\nECS_LOG_GROUP=$(terraform output -raw ecs_log_group_name)',
         "最初に 1 回だけ実行する"),

        ("件数確認", "1-1", "DLQ の件数を確認",
         'aws sqs get-queue-attributes --queue-url "$DLQ_URL" \\\n  --attribute-names ApproximateNumberOfMessages \\\n                    ApproximateNumberOfMessagesNotVisible \\\n                    ApproximateNumberOfMessagesDelayed',
         "3 つの合計が実際の総件数"),
        ("件数確認", "1-2", "メインキューの件数を確認",
         'aws sqs get-queue-attributes --queue-url "$MAIN_URL" \\\n  --attribute-names ApproximateNumberOfMessages \\\n                    ApproximateAgeOfOldestMessage',
         "滞留時間も併せて確認する"),
        ("件数確認", "1-3", "過去 24 時間の DLQ 件数推移",
         'aws cloudwatch get-metric-statistics --namespace AWS/SQS \\\n  --metric-name ApproximateNumberOfMessagesVisible \\\n  --dimensions Name=QueueName,Value=dlq-demo-dlq \\\n  --start-time "$(date -u -d \'24 hours ago\' +%Y-%m-%dT%H:%M:%SZ)" \\\n  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \\\n  --period 300 --statistics Maximum --output table',
         "発生時刻の特定に使う"),

        ("アラーム", "2-1", "アラームの現在状態を確認",
         'aws cloudwatch describe-alarms \\\n  --alarm-name-prefix dlq-demo \\\n  --query "MetricAlarms[].[AlarmName,StateValue,StateUpdatedTimestamp]" \\\n  --output table',
         "4 本まとめて確認できる"),
        ("アラーム", "2-2", "アラームの状態変化履歴",
         'aws cloudwatch describe-alarm-history \\\n  --alarm-name dlq-demo-dlq-messages-visible \\\n  --history-item-type StateUpdate --max-records 20',
         "いつ ALARM になったかを調べる"),
        ("アラーム", "2-3", "SNS 購読状態を確認",
         'aws sns list-subscriptions-by-topic \\\n  --topic-arn "$(terraform output -raw sns_topic_arn)" \\\n  --query "Subscriptions[].[Endpoint,SubscriptionArn]" --output table',
         "PendingConfirmation でないこと"),

        ("中身確認", "3-1", "DLQ のメッセージを覗く (削除しない)",
         'aws sqs receive-message --queue-url "$DLQ_URL" \\\n  --max-number-of-messages 10 \\\n  --visibility-timeout 0 \\\n  --message-attribute-names All \\\n  --message-system-attribute-names All',
         "★--visibility-timeout 0 を必ず付ける"),
        ("中身確認", "3-2", "DLQ の中身をファイルに保存",
         'aws sqs receive-message --queue-url "$DLQ_URL" \\\n  --max-number-of-messages 10 --visibility-timeout 0 \\\n  --message-system-attribute-names All \\\n  > dlq_snapshot_$(date +%Y%m%d_%H%M%S).json',
         "証跡として必ず残す"),

        ("原因調査", "4-1", "Lambda ログを MessageId で検索",
         'aws logs filter-log-events --log-group-name "$LOG_GROUP" \\\n  --start-time "$(($(date +%s) - 86400))000" \\\n  --filter-pattern \'"<MessageId>"\' \\\n  --query "events[].message" --output text',
         "<MessageId> を実際の値に置き換える"),
        ("原因調査", "4-2", "Lambda ログを追尾",
         'aws logs tail "$LOG_GROUP" --since 1h --follow --format short',
         "リアルタイムで監視する"),
        ("原因調査", "4-3", "ECS タスクのログを確認",
         'aws logs tail "$ECS_LOG_GROUP" --since 1h --format short',
         "コンテナ内の処理を確認する"),
        ("原因調査", "4-4", "直近の ECS タスク一覧",
         'aws ecs list-tasks --cluster dlq-demo-cluster \\\n  --desired-status STOPPED --max-items 10',
         "停止理由は describe-tasks で確認"),

        ("修正確認", "5-1", "テストメッセージを 1 件送る",
         'aws sqs send-message --queue-url "$MAIN_URL" \\\n  --message-body \'{"test": true, "note": "recovery smoke test"}\'',
         "★再投入の前に必ず実施する"),

        ("再投入", "6-1", "再投入タスクを開始 (速度制限付き)",
         'aws sqs start-message-move-task \\\n  --source-arn "$DLQ_ARN" \\\n  --destination-arn "$MAIN_ARN" \\\n  --max-number-of-messages-per-second 10',
         "★速度制限を必ず指定する"),
        ("再投入", "6-2", "再投入の進捗を確認",
         'aws sqs list-message-move-tasks \\\n  --source-arn "$DLQ_ARN" --max-results 1',
         "Status が COMPLETED になるまで確認"),
        ("再投入", "6-3", "再投入をキャンセル",
         'aws sqs cancel-message-move-task --task-handle "<TaskHandle>"',
         "流量が多すぎた場合の緊急停止"),

        ("危険", "X-1", "DLQ のメッセージを削除 (ポイズンピル用)",
         'aws sqs delete-message --queue-url "$DLQ_URL" \\\n  --receipt-handle "<ReceiptHandle>"',
         "★業務影響を確認したうえで実施。復元不可"),
        ("危険", "X-2", "DLQ を空にする (全件削除)",
         'aws sqs purge-queue --queue-url "$DLQ_URL"',
         "★★原則使用禁止。全メッセージが永久に失われる"),
    ]

    current_cat = None
    for cat, no, use, cmd, memo in cmds:
        if cat != current_cat:
            r = section(ws, r, f"　{cat}", 5)
            current_cat = cat
        fill = DANGER if cat == "危険" else None
        r = row_out(ws, r, ["", no, use, cmd, memo], fill=fill, height=None)
        mono(ws, f"D{r - 1}")
        ws.row_dimensions[r - 1].height = max(26, 13 * (cmd.count("\n") + 1) + 8)

    freeze(ws)
    return ws


# ===========================================================================
# 8. トラブルシュート
# ===========================================================================
def sheet_troubleshoot(wb):
    ws = wb.create_sheet("08_トラブルシュート")
    widths(ws, [4, 6, 40, 38, 56])
    r = title(ws, "トラブルシュート", "手順どおりに進まないときの症状別・原因と対処", 5)

    r = header(ws, r, ["", "#", "症状", "原因", "対処"])
    rows = [
        ("1", "アラームが発報しない", "SNS の購読が未承認",
         "確認メールの「Confirm subscription」をクリック。list-subscriptions-by-topic で PendingConfirmation でないことを確認"),
        ("2", "アラームが INSUFFICIENT_DATA のまま", "DLQ が空でメトリクスが未送信",
         "treat_missing_data = notBreaching を設定済みなら正常。一度メッセージを流すとメトリクスが出る"),
        ("3", "DLQ が空なのにアラームが鳴り続ける", "統計が Sum になっている",
         "ApproximateNumberOfMessagesVisible は Maximum を使う (05_アラーム設定 参照)"),
        ("4", "再投入が AccessDenied で失敗", "DLQ に redrive_allow_policy が無い",
         "aws_sqs_queue_redrive_allow_policy を適用する"),
        ("5", "再投入したのにすぐ DLQ に戻る", "原因が未修正",
         "06_対応手順 STEP 4〜5 に戻る。ポイズンピルなら再投入では直らない"),
        ("6", "同じメッセージが何度も ECS タスクを起動する", "可視性タイムアウトが短すぎる",
         "可視性タイムアウト ≧ Lambda タイムアウト × 6 に設定する"),
        ("7", "DLQ のメッセージが消えた", "保持期間を超過した",
         "dlq_message_retention_seconds を 14 日 (最大値) に設定して再発防止"),
        ("8", "receive-message したら件数が減った", "受信中で NotVisible に移動しただけ",
         "ApproximateNumberOfMessages + NotVisible の合計で見る"),
        ("9", "再投入したら下流の DB が落ちた", "速度制限なしで一気に流した",
         "--max-number-of-messages-per-second を指定する。10〜50 件/秒から始める"),
        ("10", "terraform apply で ResourceConflictException", "同名のリソースが既に存在する",
         "name_prefix を変えるか、既存リソースを terraform import する"),
        ("11", "ECS タスクが CannotPullContainerError で起動しない", "ECR に到達できない",
         "NAT Gateway または VPC エンドポイント (ecr.api / ecr.dkr / s3 / logs) を確認"),
        ("12", "RunTask が ThrottlingException を返す", "API 呼び出しが多すぎる",
         "lambda_maximum_concurrency を下げる。バッチサイズの見直しも検討"),
        ("13", "RESOURCE:ENI で起動に失敗する", "サブネットの IP アドレス枯渇",
         "サブネットを追加するか CIDR を拡張する。同時実行数も下げる"),
        ("14", "Lambda は成功しているのにタスクが動かない", "RunTask の failures を見落としている",
         "本実装では failures を検知して例外にしている。ログで RunTask returned failures を検索"),
        ("15", "バッチ内の成功分まで再処理される", "ReportBatchItemFailures が未設定",
         "イベントソースマッピングの function_response_types と、Lambda が返す batchItemFailures を両方確認"),
    ]
    stripe = False
    for a, b, c, d in rows:
        r = row_out(ws, r, ["", a, b, c, d], fill=STRIPE if stripe else None, height=34)
        stripe = not stripe

    freeze(ws)
    return ws


# ===========================================================================
# 9. チェックリスト
# ===========================================================================
def sheet_checklist(wb):
    ws = wb.create_sheet("09_チェックリスト")
    widths(ws, [4, 6, 46, 56, 14, 20])
    r = title(ws, "チェックリスト", "導入時 / 日次 / 月次の点検項目。E 列に「済」を入力してください", 6)

    dv = DataValidation(type="list", formula1='"済,未,対象外"', allow_blank=True)
    dv.error = "済 / 未 / 対象外 のいずれかを選択してください"
    ws.add_data_validation(dv)

    r = note(ws, r,
             "E 列のプルダウンから「済」を選ぶと、各セクションの進捗が自動集計されます。",
             6, LIGHT)
    r += 1

    def block(row, heading, items, note_text=None):
        row = section(ws, row, heading, 6)
        row = header(ws, row, ["", "#", "点検項目", "確認方法・完了条件", "状態", "実施日"])
        first = row
        stripe = False
        for i, (item, how, critical) in enumerate(items, start=1):
            fill = OK if critical else (STRIPE if stripe else None)
            row = row_out(ws, row, ["", str(i), item, how, "未", None],
                          fill=fill, height=30)
            cell = ws.cell(row=row - 1, column=5)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            dv.add(cell)
            dcell = ws.cell(row=row - 1, column=6)
            dcell.number_format = "yyyy/mm/dd"
            dcell.alignment = Alignment(horizontal="center", vertical="center")
            stripe = not stripe
        last = row - 1

        # 進捗の自動集計 (COUNTIF / COUNTA で算出)
        ws.cell(row=row, column=3, value="進捗（済 / 対象項目）").font = Font(
            name=FONT, size=10, bold=True)
        ws.cell(row=row, column=3).alignment = Alignment(horizontal="right", indent=1)
        c = ws.cell(row=row, column=4,
                    value=f'=COUNTIF(E{first}:E{last},"済")&" / "&'
                          f'(COUNTA(E{first}:E{last})-COUNTIF(E{first}:E{last},"対象外"))'
                          f'&"  ("&TEXT(IFERROR(COUNTIF(E{first}:E{last},"済")/'
                          f'MAX(1,COUNTA(E{first}:E{last})-COUNTIF(E{first}:E{last},"対象外")),0),"0%")&")"')
        c.font = Font(name=FONT, size=10, bold=True, color=NAVY)
        c.fill = PatternFill("solid", fgColor=LIGHT)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        row += 1
        if note_text:
            row = note(ws, row, note_text, 6)
        return row + 1

    r = block(r, "導入時（一度だけ）", [
        ("terraform apply が成功した", "Apply complete! が表示されること", False),
        ("SNS のメール購読を承認した", "SubscriptionArn が PendingConfirmation でないこと", True),
        ("terraform output の値を控えた", "main_queue_url / dlq_url / dlq_arn / main_queue_arn", False),
        ("CloudWatch ダッシュボードをブックマークした", "<prefix>-dashboard", False),
        ("疎通テストを実施した", "テストメッセージで ECS タスクが起動しログが出ること", False),
        ("【訓練】わざと失敗させ DLQ に入ることを確認した", "3 回失敗して DLQ の件数が増えること", True),
        ("【訓練】アラームが発報しメールが届くことを確認した", "ALARM メールを実際に受信すること", True),
        ("【訓練】再投入できることを確認した", "start-message-move-task で DLQ が 0 件に戻ること", True),
        ("本ドキュメントを運用チームへ共有した", "担当者全員が参照できる場所に配置", False),
    ], "緑色の項目は必ず本番投入前に実施してください。特に【訓練】3 項目を省略すると、本番障害時に『アラームが飛ぶはずだった』で気づけません。")

    r = block(r, "日次", [
        ("DLQ が 0 件であることを確認", "ダッシュボード または get-queue-attributes", False),
        ("メインキューの滞留時間が伸びていないか確認", "ApproximateAgeOfOldestMessage が閾値以下", False),
        ("Lambda のエラー件数を確認", "ダッシュボードの Lambda パネル", False),
        ("前日に発報したアラームの有無を確認", "describe-alarm-history", False),
    ])

    r = block(r, "月次", [
        ("過去 1 か月の DLQ 流入件数と原因を棚卸し", "NumberOfMessagesSent の合計と障害記録を突き合わせる", False),
        ("max_receive_count が実態に合っているか見直し", "一時障害で DLQ 行きが多発していないか", False),
        ("アラームのしきい値を見直し", "誤発報・見落としの有無を確認", False),
        ("ログ保持期間とコストを確認", "log_retention_in_days と CloudWatch の課金額", False),
        ("DLQ 保持期間が 14 日であることを確認", "dlq_message_retention_seconds = 1209600", False),
        ("対応手順書の内容が最新か確認", "構成変更があれば本ブックを更新する", False),
    ])

    freeze(ws)
    return ws


# ===========================================================================
# 10. 用語集
# ===========================================================================
def sheet_glossary(wb):
    ws = wb.create_sheet("10_用語集")
    widths(ws, [4, 34, 34, 72])
    r = title(ws, "用語集", "本ブックに出てくる用語の日本語解説", 4)

    r = header(ws, r, ["", "用語", "正式名称・読み", "意味"])
    terms = [
        ("DLQ", "Dead Letter Queue / デッドレターキュー",
         "規定回数処理に失敗したメッセージを退避する専用キュー。「ゴミ箱」ではなく「要調査の一時保管場所」"),
        ("リドライブ", "Redrive",
         "DLQ のメッセージを元のキューへ戻すこと。＝再投入。コンソールでは「DLQ の再処理」"),
        ("可視性タイムアウト", "Visibility Timeout",
         "あるコンシューマが受信したメッセージを他から見えなくする時間。この間に削除されないと再配信される"),
        ("maxReceiveCount", "最大受信回数",
         "この回数受信されても削除されなかったメッセージが DLQ 行きになる。本構成の既定値は 3"),
        ("ApproximateReceiveCount", "受信回数 (概算)",
         "そのメッセージが実際に受信された回数。DLQ のメッセージでは maxReceiveCount を超えている"),
        ("ポイズンピル", "Poison Pill",
         "何度処理しても必ず失敗する不正なメッセージ。再投入では解決しない。送信元の修正が必要"),
        ("イベントソースマッピング", "Event Source Mapping",
         "Lambda が SQS を自動でポーリングする仕組み。Lambda 側の設定で、SQS 側には何も設定しない"),
        ("batchItemFailures", "部分バッチ応答",
         "バッチ内の失敗したメッセージだけを SQS に報告する仕組み。成功分の再処理 (ECS タスク二重起動) を防ぐ"),
        ("ApproximateNumberOfMessagesVisible", "受信可能メッセージ数",
         "今すぐ受信できるメッセージ数。DLQ の「件数」として最もよく見る値。統計は Maximum を使う"),
        ("ApproximateNumberOfMessagesNotVisible", "処理中メッセージ数",
         "誰かが受信していて、まだ削除も再配信もされていないメッセージ数"),
        ("ApproximateAgeOfOldestMessage", "最古メッセージ経過時間",
         "キュー内で最も古いメッセージが滞留している秒数。処理遅延の指標"),
        ("NumberOfMessagesSent", "送信メッセージ数",
         "その期間にキューへ送られた件数。DLQ では「新規流入件数」を意味する。統計は Sum を使う"),
        ("redrive_policy", "リドライブポリシー",
         "メインキューに設定する。「何回失敗したらどの DLQ へ送るか」を定義する"),
        ("redrive_allow_policy", "リドライブ許可ポリシー",
         "DLQ に設定する。「どのキューへ戻すことを許可するか」を定義する。未設定だと再投入が失敗する"),
        ("RunTask", "ECS RunTask API",
         "ECS タスクを 1 回だけ起動する API。HTTP 200 でも failures にタスク起動失敗が入ることがある点に注意"),
        ("containerOverrides", "コンテナオーバーライド",
         "RunTask 時にタスク定義の設定 (環境変数・コマンドなど) を上書きする仕組み。メッセージ本文の受け渡しに使う"),
        ("iam:PassRole", "ロールの受け渡し権限",
         "Lambda が ECS にタスクロール / 実行ロールを渡すために必須の権限。付け忘れると RunTask が AccessDenied になる"),
        ("Fargate", "AWS Fargate",
         "サーバーレスのコンテナ実行環境。EC2 インスタンスの管理が不要"),
        ("treat_missing_data", "欠落データの扱い",
         "メトリクスのデータポイントが無い場合のアラーム挙動。notBreaching は「データなし＝正常」"),
        ("スモークテスト", "Smoke Test",
         "本格的な作業の前に、最小限の動作確認を行うこと。本手順では再投入前にテストメッセージを 1 件送る"),
    ]
    stripe = False
    for a, b, c in terms:
        r = row_out(ws, r, ["", a, b, c], fill=STRIPE if stripe else None,
                    bold_first=True, height=32)
        stripe = not stripe

    freeze(ws)
    return ws


# ===========================================================================
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/DLQ運用手順書.xlsx"

    wb = Workbook()
    wb.remove(wb.active)

    sheet_intro(wb)
    sheet_architecture(wb)
    sheet_build(wb)
    sheet_config(wb)
    sheet_alarms(wb)
    sheet_procedure(wb)
    sheet_commands(wb)
    sheet_troubleshoot(wb)
    sheet_checklist(wb)
    sheet_glossary(wb)

    wb.active = 0
    wb.save(out)
    print(f"wrote {out}  ({len(wb.sheetnames)} sheets)")


if __name__ == "__main__":
    main()
