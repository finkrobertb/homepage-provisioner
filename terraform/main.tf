terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Bucket name and region are passed as -backend-config flags in the workflow
  # so they do not need to be hardcoded here.
  backend "s3" {
    key = "homepage/terraform.tfstate"
  }
}

provider "aws" {
  region = var.region
}

# Look up the latest Ubuntu 22.04 LTS AMI published by Canonical.
# This means we always get the latest security-patched image without
# having to update a hardcoded AMI ID when new ones are released.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "homepage" {
  name        = "${var.server_name}-sg"
  description = "Homepage server - allow SSH, HTTP, HTTPS"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.server_name}-sg"
  }
}

resource "aws_instance" "homepage" {
  ami                          = data.aws_ami.ubuntu.id
  instance_type                = var.instance_type
  key_name                     = var.ssh_key_name
  vpc_security_group_ids       = [aws_security_group.homepage.id]
  user_data_replace_on_change  = true

  # templatefile() reads the .tftpl script and substitutes the ${...} variables.
  # The config files are base64-encoded so that special characters (quotes,
  # newlines, $-signs) in the YAML do not break the shell heredoc syntax.
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    settings_yaml_b64  = base64encode(file("${path.root}/../homepage/config/settings.yaml"))
    widgets_yaml_b64   = base64encode(file("${path.root}/../homepage/config/widgets.yaml"))
    services_yaml_b64  = base64encode(file("${path.root}/../homepage/config/services.yaml"))
    docker_compose_b64 = base64encode(file("${path.root}/../homepage/docker-compose.yml"))
    nginx_conf_b64     = base64encode(file("${path.root}/../homepage/nginx/nginx.conf"))
  })

  tags = {
    Name = var.server_name
  }
}

# Elastic IP gives the server a fixed public address that does not change
# when the instance is stopped and restarted.
resource "aws_eip" "homepage" {
  instance = aws_instance.homepage.id
  domain   = "vpc"

  tags = {
    Name = "${var.server_name}-eip"
  }
}
