provider "aws" {
  region = "ap-south-1" # Change if needed
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
