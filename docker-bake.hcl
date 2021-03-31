variable "IMAGE_NAME" {
  default = "rasa/rasa-sdk"
}

variable "IMAGE_TAG" {
  default = "main"
}

target "default" {
  dockerfile = "./Dockerfile"
  tags       = ["${IMAGE_NAME}:${IMAGE_TAG}"]
}
