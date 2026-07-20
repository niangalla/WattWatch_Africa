# Verrouille les versions : Terraform lui-même et le provider AWS.
# Sans ces contraintes, un poste avec des versions différentes pourrait
# produire un plan différent — on fige donc les majeures.
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0" # accepte 6.x, refuse 7.0 (breaking changes potentiels)
    }
  }
}
