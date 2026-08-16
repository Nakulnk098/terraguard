terraform {
  backend "s3" {
    bucket = "terraguard-state-nakul-2026"
    key    = "terraform.tfstate"
    region = "ap-south-1"
  }
}
