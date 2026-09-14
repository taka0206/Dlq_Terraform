"""SQS のメッセージを受け取り、ECS (Fargate) タスクを起動するディスパッチャ。

処理の流れ:
    SQS メインキュー
      -> イベントソースマッピングが Lambda を起動
      -> 本ハンドラが 1 メッセージにつき 1 つの ECS タスクを RunTask
      -> 起動に失敗したメッセージだけを batchItemFailures として返す
      -> 返されたメッセージはキューに残り、再配信される
      -> maxReceiveCount 回失敗すると SQS が DLQ へ退避する

重要:
    例外を送出して Lambda 全体を失敗させると、バッチ内の成功済みメッセージまで
    再配信され ECS タスクが二重起動する。そのため必ず batchItemFailures を返す
    (イベントソースマッピングの ReportBatchItemFailures と対で機能する)。
"""

import json
import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# RunTask はスロットリングされやすいため、SDK 側の再試行を厚めにする
ecs = boto3.client(
    "ecs",
    config=Config(retries={"max_attempts": 5, "mode": "standard"}),
)

CLUSTER_ARN = os.environ["ECS_CLUSTER_ARN"]
TASK_DEF_ARN = os.environ["ECS_TASK_DEF_ARN"]
CONTAINER_NAME = os.environ["ECS_CONTAINER_NAME"]
SUBNET_IDS = [s for s in os.environ["ECS_SUBNET_IDS"].split(",") if s]
SECURITY_GROUP_IDS = [s for s in os.environ["ECS_SECURITY_GROUP_IDS"].split(",") if s]
ASSIGN_PUBLIC_IP = os.environ.get("ECS_ASSIGN_PUBLIC_IP", "DISABLED")
QUEUE_URL = os.environ.get("QUEUE_URL", "")


def lambda_handler(event, context):
    failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            task_arns = _run_task(record)
            logger.info(
                "started ecs task: %s",
                json.dumps({"messageId": message_id, "taskArns": task_arns}),
            )
        except Exception:  # noqa: BLE001 - 1 件の失敗で他を巻き込まない
            logger.exception("failed to start ecs task: messageId=%s", message_id)
            failures.append({"itemIdentifier": message_id})

    # 空リストを返せば「全件成功」。SQS 側でメッセージが削除される。
    return {"batchItemFailures": failures}


def _run_task(record):
    """1 メッセージにつき 1 タスクを起動し、起動したタスクの ARN を返す。"""
    response = ecs.run_task(
        cluster=CLUSTER_ARN,
        taskDefinition=TASK_DEF_ARN,
        launchType="FARGATE",
        count=1,
        # 冪等性のため、同じ受信に対しては同じキーを使う
        clientToken=record["messageId"],
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": SUBNET_IDS,
                "securityGroups": SECURITY_GROUP_IDS,
                "assignPublicIp": ASSIGN_PUBLIC_IP,
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": CONTAINER_NAME,
                    "environment": [
                        {"name": "MESSAGE_ID", "value": record["messageId"]},
                        {"name": "MESSAGE_BODY", "value": record["body"]},
                        {"name": "RECEIPT_HANDLE", "value": record["receiptHandle"]},
                        {"name": "QUEUE_URL", "value": QUEUE_URL},
                    ],
                }
            ]
        },
        propagateTags="TASK_DEFINITION",
    )

    # RunTask は HTTP 200 でも failures にタスク起動失敗が入ることがある
    # (キャパシティ不足、サブネットの IP 枯渇など)。ここを見落とすと
    # 「成功扱いなのにタスクが動かない」メッセージロストになる。
    if response.get("failures"):
        raise RuntimeError(f"RunTask returned failures: {response['failures']}")

    return [task["taskArn"] for task in response.get("tasks", [])]
