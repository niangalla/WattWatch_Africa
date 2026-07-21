# Infrastructure WattWatch Africa — landing zone S3 (Phase 1).
# Périmètre volontairement minimal : 1 bucket + 1 utilisateur IAM pour le
# pipeline Airflow. L'intégration Snowflake (storage integration + rôle IAM)
# viendra dans un second temps, une fois le compte Snowflake créé.

provider "aws" {
  region = var.aws_region

  # Tags appliqués automatiquement à toutes les ressources du projet —
  # pratique pour retrouver/filtrer les coûts dans la console AWS.
  default_tags {
    tags = {
      Project   = "wattwatch-africa"
      ManagedBy = "terraform"
    }
  }
}

# ── Bucket landing ────────────────────────────────────────────────────────
# Reçoit les PDF bruts et manifests du spider CRSE (préfixe crse/),
# lus ensuite par le COPY INTO Snowflake.

resource "aws_s3_bucket" "landing" {
  bucket = var.bucket_name
}

# Versioning : un re-scrape qui écraserait un PDF n'efface jamais l'ancienne
# version — filet de sécurité pour une landing zone.
resource "aws_s3_bucket_versioning" "landing" {
  bucket = aws_s3_bucket.landing.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Verrouille tout accès public : ce bucket n'a aucune raison d'être exposé.
resource "aws_s3_bucket_public_access_block" "landing" {
  bucket = aws_s3_bucket.landing.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Utilisateur IAM du pipeline ───────────────────────────────────────────
# Identité dédiée pour Airflow/Scrapy : si ses clés fuitent, elles ne
# donnent accès qu'à ce bucket, pas au compte AWS entier.
# La clé d'accès n'est PAS créée ici : elle atterrirait en clair dans le
# tfstate. On la génère à la main (console ou `aws iam create-access-key`).

resource "aws_iam_user" "pipeline" {
  name = "wattwatch-pipeline"

  # Les clés d'accès sont créées à la main (hors Terraform) : sans ce flag,
  # AWS refuse de supprimer un utilisateur qui a encore des clés et le
  # destroy échoue (DeleteConflict 409).
  force_destroy = true

  # Traçabilité de la clé d'accès en cours (créée hors Terraform, cf. ci-dessus).
  # À régénérer après chaque destroy/recreate de l'utilisateur.
  tags = {
    "AKIA37P63XOIKUKDEGSR" = "for_wattwatch_pipeline"
  }
}

data "aws_iam_policy_document" "pipeline_s3" {
  # Lister le contenu du bucket (nécessaire à boto3 pour les checks d'existence)
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.landing.arn]
  }

  # Lire/écrire les objets — uniquement dans ce bucket
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.landing.arn}/*"]
  }
}

resource "aws_iam_user_policy" "pipeline_s3" {
  name   = "wattwatch-landing-rw"
  user   = aws_iam_user.pipeline.name
  policy = data.aws_iam_policy_document.pipeline_s3.json
}
