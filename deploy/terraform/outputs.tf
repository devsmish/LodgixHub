output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Public IP (changes on stop/start — Elastic IP is unavailable in the educational account)"
  value       = aws_instance.app.public_ip
}

output "ssh_command" {
  description = "Ready-to-use connection command"
  value       = "ssh -i lodgixhub-key.pem ec2-user@${aws_instance.app.public_ip}"
}
