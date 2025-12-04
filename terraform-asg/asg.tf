# Fetch latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# Launch Template (The Blueprint for EC2s)
resource "aws_launch_template" "app" {
  name_prefix   = "movie-app-template"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = "t2.micro"

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.ec2_sg.id]
  }

  # User Data Script (Base64 Encoded)
  # This runs on first boot to install the app
  # Updated User Data Script
  user_data = base64encode(<<-EOF
              #!/bin/bash
              # 1. Update system
              dnf update -y
              
              # 2. Install Python, Pip, and Git explicitly
              dnf install -y python3 python3-pip git
              
              # 3. Create app directory
              cd /home/ec2-user
              git clone https://github.com/harshrajputgit/movie-review-app.git app
              cd app
              
              # 4. Install dependencies (using python3 -m pip to avoid path issues)
              python3 -m pip install -r requirements.txt
              python3 -m pip install gunicorn
              
              # 5. Start App
              # We use 'nohup' so it keeps running after the script exits
              nohup python3 -m gunicorn --bind 0.0.0.0:5000 app:app > app.log 2>&1 &
              EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = { Name = "movie-app-instance" }
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "bar" {
  desired_capacity    = 2
  max_size            = 3
  min_size            = 1
  vpc_zone_identifier = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  target_group_arns   = [aws_lb_target_group.app.arn]

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "movie-app-asg"
    propagate_at_launch = true
  }
}

# Scaling Policy (Scale Up if CPU > 50%)
resource "aws_autoscaling_policy" "cpu_policy" {
  name                   = "cpu-policy"
  autoscaling_group_name = aws_autoscaling_group.bar.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 50.0
  }
}
