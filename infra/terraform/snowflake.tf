# Storage integration Snowflake <-> S3 (Phase 1).
#
# Principe : Snowflake ne reçoit JAMAIS de clé d'accès AWS. Il obtient une
# identité IAM (un "utilisateur" géré par Snowflake, propre à ton compte) et
# assume un rôle IAM créé ici, qui donne un accès en lecture seule au bucket.
# C'est un échange à deux sens :
#   1. On crée la storage integration côté Snowflake -> il nous fournit une
#      identité IAM (storage_aws_iam_user_arn) et un "mot de passe à usage
#      unique" (storage_aws_external_id) pour la relation de confiance.
#   2. On crée le rôle IAM côté AWS dont la trust policy n'accepte QUE ces
#      deux valeurs précises -> aucune autre identité ne peut assumer ce rôle.
#
# Aucune boucle de dépendance : l'ARN du rôle est calculé à l'avance
# (organisation AWS + nom choisi), donc la storage integration peut le
# référencer avant même que le rôle existe.

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  # user / password / role : lus depuis les variables d'environnement
  # SNOWFLAKE_USER / SNOWFLAKE_PASSWORD / SNOWFLAKE_ROLE (jamais en dur ici).
}

data "aws_caller_identity" "current" {}

locals {
  snowflake_integration_role_name = "wattwatch-snowflake-integration"
  snowflake_integration_role_arn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.snowflake_integration_role_name}"
}

resource "snowflake_storage_integration_aws" "wattwatch" {
  name    = "WATTWATCH_S3_INTEGRATION"
  enabled = true

  storage_provider = "S3"
  # Tout le bucket : le stage externe (créé à la main, cf. infra/snowflake/02_stage.sql)
  # pointera sur sa racine, avec /processed/ et /landing/ en sous-préfixes.
  storage_allowed_locations = ["s3://${aws_s3_bucket.landing.bucket}/"]
  storage_aws_role_arn      = local.snowflake_integration_role_arn
}

# Rôle IAM que Snowflake assume via STS — accès en lecture seule au bucket,
# aucune credential longue durée. Distinct de wattwatch-pipeline (main.tf) :
# ce dernier écrit dans le bucket avec des clés d'accès, celui-ci ne fait
# que lire, via une identité temporaire.
data "aws_iam_policy_document" "snowflake_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [snowflake_storage_integration_aws.wattwatch.describe_output[0].iam_user_arn]
    }

    # Verrou anti-"confused deputy" : même en connaissant l'ARN Snowflake
    # (public), personne ne peut assumer ce rôle sans ce jeton exact.
    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [snowflake_storage_integration_aws.wattwatch.describe_output[0].external_id]
    }
  }
}

resource "aws_iam_role" "snowflake_integration" {
  name               = local.snowflake_integration_role_name
  assume_role_policy = data.aws_iam_policy_document.snowflake_assume_role.json
}

data "aws_iam_policy_document" "snowflake_s3_read" {
  statement {
    # GetObjectVersion : nécessaire car le bucket a le versioning activé.
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.landing.arn}/*"]
  }

  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.landing.arn]
  }
}

resource "aws_iam_role_policy" "snowflake_s3_read" {
  name   = "wattwatch-snowflake-s3-read"
  role   = aws_iam_role.snowflake_integration.id
  policy = data.aws_iam_policy_document.snowflake_s3_read.json
}
