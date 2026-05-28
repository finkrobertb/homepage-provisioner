output "public_ip" {
  description = "Public IP address of the Homepage server"
  value       = aws_eip.homepage.public_ip
}

output "public_dns" {
  description = "Public DNS hostname of the Elastic IP"
  value       = aws_eip.homepage.public_dns
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.homepage.id
}

output "homepage_url" {
  description = "URL to open the Homepage dashboard"
  value       = "http://${aws_eip.homepage.public_ip}"
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_eip.homepage.public_ip}"
}
