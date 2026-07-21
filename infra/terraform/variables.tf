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

# Identifiant de compte Snowflake GRZRNLR-RF61166 = organisation-compte.
# Pas un secret (c'est un nom d'hôte, pas un credential) : safe en dur ici.
# L'authentification elle-même (user/password/role) passe par les variables
# d'env standard du provider (SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
# SNOWFLAKE_ROLE) — jamais dans un fichier .tf.
variable "snowflake_organization_name" {
  description = "Partie organisation de l'identifiant de compte Snowflake"
  type        = string
  default     = "GRZRNLR"
}

variable "snowflake_account_name" {
  description = "Partie compte de l'identifiant de compte Snowflake"
  type        = string
  default     = "RF61166"
}
