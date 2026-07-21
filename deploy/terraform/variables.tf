variable "aws_region" {
  description = "aws_region"
  type        = string
  default     = "eu-central-1"
}

variable "ec2_sg_id" {
  description = "ID of the existing security group for EC2"
  type        = string
}

variable "key_name" {
  description = "Name of an existing EC2 key pair"
  type        = string
  default     = "lodgixhub-key"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "instance_name" {
  description = "Name tag for the instance"
  type        = string
  default     = "lodgixhub-ec2"
}
