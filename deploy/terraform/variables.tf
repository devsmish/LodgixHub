variable "aws_region" {
  description = "aws_region"
  type        = string
  default     = "eu-central-1"
}

variable "ec2_sg_id" {
  description = "ID существующей Security Group для EC2 (создана вручную, IAM-пользователь лабы не может создавать SG)"
  type        = string
}

variable "key_name" {
  description = "Имя существующего EC2 key pair (создан вручную через aws ec2 create-key-pair)"
  type        = string
  default     = "lodgixhub-key"
}

variable "instance_type" {
  description = "Тип EC2-инстанса"
  type        = string
  default     = "t3.micro"
}

variable "instance_name" {
  description = "Тег Name для инстанса"
  type        = string
  default     = "lodgixhub-ec2"
}
