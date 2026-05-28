variable "region" {
  description = "AWS region to deploy the instance (e.g. us-east-1)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "server_name" {
  description = "Name tag applied to all AWS resources"
  type        = string
}

variable "ssh_key_name" {
  description = "Name of the AWS key pair used for SSH access"
  type        = string
}
