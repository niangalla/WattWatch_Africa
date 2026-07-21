-- À exécuter une fois APRÈS `terraform apply` (storage integration créée).
-- Connecté en ACCOUNTADMIN, dans le même worksheet que 01_bootstrap.sql.

USE ROLE ACCOUNTADMIN;

-- GRANT USAGE ON INTEGRATION nécessite ACCOUNTADMIN (ou un rôle avec le
-- privilège MANAGE INTEGRATION) — c'est pour ça qu'on ne peut pas le faire
-- avec WATTWATCH_TRANSFORM directement.
GRANT USAGE ON INTEGRATION WATTWATCH_S3_INTEGRATION TO ROLE WATTWATCH_TRANSFORM;

USE ROLE WATTWATCH_TRANSFORM;

-- Le stage pointe sur la racine du bucket : @LANDING_STAGE/processed/ dans
-- load_dag.py résout donc vers s3://wattwatch-raw/processed/.
CREATE STAGE IF NOT EXISTS WATTWATCH.BRONZE.LANDING_STAGE
  URL = 's3://wattwatch-raw/'
  STORAGE_INTEGRATION = WATTWATCH_S3_INTEGRATION
  FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');

-- Vérification : doit lister les CSV déjà présents dans le bucket, sans
-- erreur de permission. Si erreur "not authorized", la trust policy IAM
-- ou le GRANT USAGE ci-dessus n'est pas encore propagé (réessayer après
-- quelques secondes).
LIST @WATTWATCH.BRONZE.LANDING_STAGE/processed/;
