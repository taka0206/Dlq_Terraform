variable "region" {
  description = "デプロイ先リージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "name_prefix" {
  description = "リソース名の接頭辞"
  type        = string
  default     = "dlq-demo"
}

variable "subnet_ids" {
  description = "ECS タスクを起動するサブネット ID"
  type        = list(string)
}

variable "security_group_ids" {
  description = "ECS タスクにアタッチするセキュリティグループ ID"
  type        = list(string)
}

variable "assign_public_ip" {
  description = "ECS タスクにパブリック IP を割り当てるか"
  type        = bool
  default     = false
}

variable "container_image" {
  description = "ワーカーのコンテナイメージ"
  type        = string
}
