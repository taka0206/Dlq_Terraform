terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.60.0"
    }
  }

  # 本番運用ではリモートステートを推奨
  # backend "s3" {
  #   bucket = "your-tfstate-bucket"
  #   key    = "dlq-demo/dev/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.name_prefix
      ManagedBy = "Terraform"
    }
  }
}

module "pipeline" {
  source = "../../modules/sqs-lambda-ecs"

  name_prefix = var.name_prefix

  # ネットワーク
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids
  assign_public_ip   = var.assign_public_ip

  # ECS
  container_image = var.container_image

  # SQS: 3 回失敗したら DLQ へ。可視性タイムアウトは Lambda タイムアウト 30 秒の 6 倍
  max_receive_count          = 3
  lambda_timeout_seconds     = 30
  visibility_timeout_seconds = 180

  # 監視 (通知連携は行わず、ダッシュボード / CLI で状態を確認する)
  dlq_depth_alarm_threshold = 0

  tags = {
    Environment = "dev"
  }
}
