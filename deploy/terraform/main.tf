terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_key_pair" "existing" {
  key_name = var.key_name
}

data "aws_security_group" "ec2_sg" {
  id = var.ec2_sg_id
}

locals {
  user_data = <<-EOF
    #!/bin/bash
    set -e
    dnf update -y
    dnf install -y docker git mariadb105

    systemctl enable docker
    systemctl start docker
    usermod -aG docker ec2-user

    mkdir -p /usr/local/lib/docker/cli-plugins

    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

    curl -SL https://github.com/docker/buildx/releases/download/v0.21.2/buildx-v0.21.2.linux-amd64 \
      -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
  EOF
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_ami.value
  instance_type          = var.instance_type
  key_name               = data.aws_key_pair.existing.key_name
  vpc_security_group_ids = [data.aws_security_group.ec2_sg.id]
  user_data              = local.user_data

  tags = {
    Name = var.instance_name
  }
}
