# WattWatch Africa — Contexte projet

Projet portfolio personnel d'Alla (data engineer, en stage chez Cuberfit — repo distinct,
ne pas mélanger les deux). Observatoire de l'affordabilité énergétique en Afrique de
l'Ouest : collecte des grilles tarifaires électriques du Sénégal, normalisation,
indicateurs d'affordabilité, comparaisons régionales. Langue de travail : français.

## Architecture (décisions verrouillées — ne pas rediscuter)

Pipeline **ELT strict** (modèle *Fundamentals of Data Engineering*, Reis & Housley) :

Scrapy/pdfplumber → S3 (landing) → `COPY INTO` Snowflake Bronze → dbt (Bronze → Silver → Gold) → Power BI

- **Orchestrateur : Airflow** (choisi contre Prefect/Dagster, décision actée)
- **dbt ne charge jamais de données** — le chargement est fait par le DAG `wattwatch_load` (COPY INTO)
- Nom du projet fixé : WattWatch Africa

## Stack locale (docker-compose)

Airflow (webserver + scheduler + Postgres, LocalExecutor) + MinIO qui émule S3.
Snowflake et Power BI restent externes. Le repo est monté sur `/opt/wattwatch` dans
les conteneurs (pas de rebuild pour les changements de code/DAG).

```bash
docker compose up -d --build
# Airflow UI : localhost:8080 · Console MinIO : localhost:9001
docker compose exec airflow-scheduler airflow dags test wattwatch_ingestion 2026-07-17
```

Limite connue : Snowflake ne peut pas lire un MinIO local — pour tester `COPY INTO`,
pointer `WATTWATCH_S3_BUCKET` vers un vrai bucket S3 (variables d'env uniquement,
aucun changement de code).

## Structure

- `scrapers/` — package Scrapy : spider `crse` (API REST WordPress de crse.sn) + `pdf_parser.py`
  (pdfplumber → CSV tidy) + `process_landing.py`. Détails techniques (endpoint
  `/wp-json/wp/v2/crse_document`, fallback `?view_doc=`, throttling anti-503) dans les docstrings.
- `dags/` — 3 DAGs : `wattwatch_ingestion` (@weekly) → `wattwatch_load` (COPY INTO, schedule None)
  → `wattwatch_dbt` (dbt run + test, schedule None). Chaînage Dataset/TriggerDagRun prévu Phase 3.
- `dbt/` — profil `wattwatch` (Snowflake, credentials via `env_var()`, jamais en dur).
  Couches : staging (view) / silver (table) / gold (table). Source Bronze :
  `WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE`.
- `tests/` — pytest, fixtures sur la vraie grille SENELEC du 2026-01-01 (baisse de 10 %).
- `infra/terraform/` — IaC AWS + Snowflake (2 providers). AWS : bucket `wattwatch-raw`
  (versionné, privé) + utilisateur IAM `wattwatch-pipeline` (policy limitée au bucket,
  `force_destroy = true`). Snowflake : `snowflake_storage_integration_aws` (attention,
  pas `snowflake_storage_integration` — déprécié) + rôle IAM `wattwatch-snowflake-integration`
  assumé via STS (trust policy verrouillée sur `describe_output[0].iam_user_arn` +
  `external_id`, pas de clé d'accès échangée). Provider Snowflake : source
  `snowflakedb/snowflake` (a migré depuis `Snowflake-Labs/snowflake`), auth par
  `$env:SNOWFLAKE_USER/PASSWORD/ROLE` (jamais dans les fichiers .tf). Le tfstate est
  gitignoré, le lock file versionné. La clé d'accès du pipeline AWS est créée hors
  Terraform (jamais dans le tfstate) → à régénérer après chaque destroy/recreate et
  reporter dans `.env`.
- `infra/snowflake/` — scripts SQL à exécuter à la main dans Snowsight (rôle
  ACCOUNTADMIN) : `01_bootstrap.sql` (warehouse/base/schéma Bronze/rôle applicatif/table,
  une fois le compte créé) et `02_stage.sql` (stage externe `LANDING_STAGE`, une fois la
  storage integration provisionnée par Terraform).

⚠️ Convention : les fichiers dbt utilisent l'extension **`.yml`** (jamais `.yaml`) —
dbt ignore silencieusement `dbt_project.yaml`/`profiles.yaml` et les property files `.yaml`.

## État d'avancement (2026-07-21)

- ✅ Phase 0 (POC, commit `7cf4258`) : spider CRSE + parseur PDF opérationnels de bout en bout
- ✅ Stack Docker locale (commit `f7e06ea`) : Airflow + MinIO, squelettes des 3 DAGs,
  projet dbt initial (`stg_tarifs_electricite`)
- ✅ Refactor config : tout passe par `env_file: .env` (zéro credential en dur dans le
  compose), providers Airflow installés sous contraintes officielles,
  `SQLExecuteQueryOperator` remplace `SnowflakeOperator` déprécié. Stack validée le
  2026-07-20 : `dags test wattwatch_ingestion` OK de bout en bout (SENELEC → MinIO)
- ✅ Infra AWS en Terraform (2026-07-20) : compte AWS opérationnel (utilisateur admin
  `alla-admin`, clé root supprimée), bucket `wattwatch-raw` + IAM `wattwatch-pipeline`
  provisionnés via `infra/terraform/`. Ingestion validée sur le vrai S3 le même jour
  (PDF dans `landing/crse/`, CSV tidy dans `processed/`)
- ✅ Compte Snowflake (essai gratuit 1 mois, AWS eu-west-1) + bootstrap SQL
  (`infra/snowflake/01_bootstrap.sql`) : warehouse `WATTWATCH_WH`, base `WATTWATCH`,
  schéma `BRONZE`, rôle `WATTWATCH_TRANSFORM`, table `RAW_TARIFS_ELECTRICITE`
- ✅ Storage integration Snowflake↔S3 en Terraform (2026-07-21, `snowflake.tf`) + stage
  externe `LANDING_STAGE` (`infra/snowflake/02_stage.sql`) — accès en lecture par rôle
  IAM assumé via STS, aucune clé d'accès échangée
- ✅ **Phase 1 terminée** : DAG `wattwatch_load` validé (2026-07-21), `COPY INTO` charge
  les CSV S3 dans `WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE`
- ⏳ Prochaine étape : DAG `wattwatch_dbt` (staging `stg_tarifs_electricite` déjà
  scaffoldé), puis Phase 2 — modèles Silver/Gold et indicateurs d'affordabilité

⚠️ Le Docker Engine natif dans WSL Ubuntu a été purgé le 2026-07-20 (disque C: plein) :
images et cache supprimés, volumes conservés. Les stacks du projet tournent sous
Docker Desktop — ne pas rebuilder depuis l'intérieur de WSL.

## Roadmap (phases du brief)

1. **Phase 1** — Chargement : S3 réel + Snowflake Bronze via COPY INTO orchestré
2. **Phase 2** — Transformation : modèles Silver/Gold + indicateurs d'affordabilité
   (liste complète dans le README : seuil ESMAP, kWh/SMIG, progressivité, Woyofal vs
   post-paiement, USD PPP, base 100, croisement World Bank `EG.ELC.ACCS.ZS`)
3. **Phase 3** — Orchestration complète : chaînage des DAGs, capteurs/Datasets
4. **Phase 4** — Extension régionale : autres pays (ANARE-CI/CIE, Africa Energy Portal)
5. **Phase 5** — Serving : Power BI + CI/CD GitHub Actions

## Commandes utiles

```bash
scrapy crawl crse -a cats=grilles-tarifaires -O data/landing/crse/manifest.json
python -m scrapers.pdf_parser data/landing/crse/full/<fichier>.pdf -o data/processed/
pytest
cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir .
```
