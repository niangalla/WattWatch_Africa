-- Bootstrap WattWatch Africa — à exécuter une fois dans un worksheet Snowsight,
-- connecté avec le rôle ACCOUNTADMIN (celui de l'utilisateur créé à l'inscription
-- de l'essai gratuit).
--
-- Crée les objets de base : warehouse, base, schéma Bronze, rôle applicatif,
-- table brute (tout en VARCHAR — le typage se fait en Silver via dbt, jamais
-- en Bronze). N'inclut PAS le stage externe S3 : celui-ci dépend de la storage
-- integration créée par Terraform (voir 02_stage.sql, à exécuter après le
-- `terraform apply` qui provisionne l'integration).

USE ROLE ACCOUNTADMIN;

-- Warehouse minimal : XS, auto-suspend agressif (60s) pour un compte d'essai.
CREATE WAREHOUSE IF NOT EXISTS WATTWATCH_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS WATTWATCH;
CREATE SCHEMA IF NOT EXISTS WATTWATCH.BRONZE;

-- Rôle applicatif unique, utilisé à la fois par Airflow (COPY INTO) et dbt
-- (Bronze -> Silver -> Gold) — cf. AIRFLOW_CONN_SNOWFLAKE_WATTWATCH et
-- SNOWFLAKE_ROLE dans .env.
CREATE ROLE IF NOT EXISTS WATTWATCH_TRANSFORM;

GRANT USAGE ON WAREHOUSE WATTWATCH_WH TO ROLE WATTWATCH_TRANSFORM;
GRANT USAGE ON DATABASE WATTWATCH TO ROLE WATTWATCH_TRANSFORM;
-- CREATE SCHEMA : dbt crée lui-même staging/silver/gold au premier `dbt run`.
GRANT CREATE SCHEMA ON DATABASE WATTWATCH TO ROLE WATTWATCH_TRANSFORM;
GRANT USAGE, CREATE TABLE, CREATE STAGE ON SCHEMA WATTWATCH.BRONZE TO ROLE WATTWATCH_TRANSFORM;

-- Table Bronze : reflet brut du CSV tidy produit par pdf_parser.py
-- (TARIFF_FIELDS dans scrapers/pdf_parser.py). Tout en VARCHAR à dessein.
CREATE TABLE IF NOT EXISTS WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE (
  country_code                 VARCHAR,
  utility                      VARCHAR,
  effective_date                VARCHAR,
  voltage_level                VARCHAR,
  section                      VARCHAR,
  category                    VARCHAR,
  category_code                VARCHAR,
  payment_mode                 VARCHAR,
  band                         VARCHAR,
  price_fcfa_kwh                VARCHAR,
  prime_fixe_fcfa_kw_month      VARCHAR,
  source_file                  VARCHAR,
  parsed_at                    VARCHAR
);

GRANT SELECT, INSERT ON TABLE WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE TO ROLE WATTWATCH_TRANSFORM;
-- Pour que dbt voie les futures tables créées dans le schéma sans regrant manuel.
GRANT SELECT ON FUTURE TABLES IN SCHEMA WATTWATCH.BRONZE TO ROLE WATTWATCH_TRANSFORM;

-- Attribue le rôle à l'utilisateur courant (remplacer <ton_user> si un autre
-- utilisateur/service account exécute Airflow et dbt).
-- IDENTIFIER() n'accepte pas un appel de fonction directement : on passe
-- par une variable de session.
SET my_user = CURRENT_USER();
GRANT ROLE WATTWATCH_TRANSFORM TO USER IDENTIFIER($my_user);
