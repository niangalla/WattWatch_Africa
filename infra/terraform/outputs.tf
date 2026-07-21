# Valeurs affichées après `terraform apply` (et via `terraform output`).

output "bucket_name" {
  description = "À reporter dans .env → WATTWATCH_S3_BUCKET"
  value       = aws_s3_bucket.landing.id
}

output "bucket_arn" {
  description = "Servira à la storage integration Snowflake (Phase 1)"
  value       = aws_s3_bucket.landing.arn
}

output "pipeline_user" {
  description = "Utilisateur IAM dont il faut générer la clé d'accès pour .env"
  value       = aws_iam_user.pipeline.name
}

output "snowflake_storage_integration_name" {
  description = "À utiliser dans le CREATE STAGE (infra/snowflake/02_stage.sql)"
  value       = snowflake_storage_integration_aws.wattwatch.name
}
