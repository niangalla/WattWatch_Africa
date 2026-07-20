# Les variables rendent la config réutilisable sans la modifier.
# Ordre de priorité des valeurs : -var CLI > terraform.tfvars > default.

variable "aws_region" {
  description = "Région AWS (eu-west-1 = Irlande, cohérente avec .env.example)"
  type        = string
  default     = "eu-west-1"
}

variable "bucket_name" {
  description = "Nom du bucket landing. Global à tout AWS : si 'wattwatch-raw' est déjà pris, surcharger dans terraform.tfvars (ex. wattwatch-raw-alla)"
  type        = string
  default     = "wattwatch-raw"
}
