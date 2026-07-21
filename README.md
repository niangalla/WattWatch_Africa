# WattWatch Africa

Observatoire de l'affordabilité énergétique en Afrique de l'Ouest.

## Le sujet

Au Sénégal, le prix de l'électricité change régulièrement par décision du régulateur (la CRSE), mais ces changements sont difficiles à suivre dans la durée : les grilles tarifaires sortent en PDF, sans API ni historique exploitable, et personne ne les croise vraiment avec les revenus des ménages ou le taux d'accès à l'électricité. Ce projet part de ce constat : collecter ces grilles au fil du temps, les normaliser, et en tirer des indicateurs qui répondent à des questions concrètes. Une hausse de tarif représente combien d'heures de SMIG en plus ? Le prépaiement Woyofal coûte-t-il vraiment plus cher que le post-paiement ? Comment le Sénégal se compare-t-il à ses voisins une fois les prix ramenés en dollars PPA ?

C'est un projet personnel, construit comme un vrai pipeline de données de bout en bout plutôt qu'un notebook d'analyse ponctuelle : ingestion automatisée, stockage versionné, transformation testée, indicateurs reproductibles.

## Architecture

Flux ELT en 4 étapes, avec les undercurrents habituels (sécurité, orchestration, qualité, observabilité, FinOps) en toile de fond. Le modèle suit *Fundamentals of Data Engineering* (Reis & Housley).

![Architecture_Watt_Watch_Africa](docs/Architecture_WattWatch_Africa_V0.png)

- **Ingestion** : Scrapy (API REST WordPress de crse.sn, pages HTML) et pdfplumber pour les grilles tarifaires PDF
- **Landing zone** : AWS S3, dépôt brut des fichiers scrapés
- **Chargement** : `COPY INTO` orchestré par Airflow, S3 vers Snowflake (Bronze)
- **Transformation** : dbt, exécuté entièrement dans Snowflake (Bronze, Silver, Gold)
- **Serving** : Power BI
- **Orchestration** : Apache Airflow, **CI/CD** : GitHub Actions

## Statut

### Phase 0, POC : terminée

La preuve de bout en bout est faite sur la source principale.

1. **Découverte** : crse.sn expose ses documents via l'API REST WordPress (`/wp-json/wp/v2/crse_document`, environ 530 documents, dont la catégorie `grilles-tarifaires`).
2. **Ingestion** : le spider `crse` pagine l'API, filtre par catégorie et secteur, télécharge les PDF (throttling actif, le site renvoie des 503 en cas de requêtes trop rapides).
3. **Parsing** : `pdf_parser.py` extrait la grille SENELEC du 1er janvier 2026 (celle de la baisse de 10 %) en format tidy : tarifs BT par tranche, prépaiement Woyofal, MT/HT heures pointe et hors pointe, primes fixes et bornes des tranches.

### Phase 1, Chargement : terminée

- [x] Stack Docker locale (Airflow + MinIO) opérationnelle, 3 DAGs en place
- [x] Infrastructure AWS provisionnée en Terraform (`infra/terraform/`) : bucket `wattwatch-raw` (privé, versionné) et utilisateur IAM `wattwatch-pipeline` restreint au seul bucket
- [x] Ingestion validée sur le vrai S3 : PDF CRSE dans `landing/crse/`, CSV tidy dans `processed/`
- [x] Compte Snowflake (essai gratuit, AWS eu-west-1) : warehouse, base, schéma Bronze, rôle applicatif provisionnés via `infra/snowflake/01_bootstrap.sql`
- [x] Storage integration Snowflake-S3 en Terraform (`infra/terraform/snowflake.tf`) : un rôle IAM assumé via STS, aucune clé d'accès échangée. Stage externe `WATTWATCH.BRONZE.LANDING_STAGE` créé (`infra/snowflake/02_stage.sql`)
- [x] `COPY INTO` validé : le DAG `wattwatch_load` charge les CSV tidy de S3 dans `WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE`

## Démarrage rapide

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 1. Scraper les grilles tarifaires CRSE (PDF -> data/landing/crse/)
scrapy crawl crse -a cats=grilles-tarifaires -O data/landing/crse/manifest.json

# 2. Parser une grille en CSV tidy
python -m scrapers.pdf_parser data/landing/crse/full/<fichier>.pdf -o data/processed/

# Tests
pytest
```

Pour pousser la landing zone vers S3, définir dans `.env` (voir `.env.example`) : `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `WATTWATCH_S3_BUCKET`. Le spider écrit alors directement `FILES_STORE=s3://...`.

## Infrastructure AWS + Snowflake (Terraform)

L'infra de production est décrite en IaC dans `infra/terraform/`, avec deux providers.

- **AWS** : bucket `wattwatch-raw` (versioning activé, accès public bloqué) et utilisateur IAM `wattwatch-pipeline` dont la politique se limite à lire et écrire dans ce bucket
- **Snowflake** : storage integration `WATTWATCH_S3_INTEGRATION` et rôle IAM `wattwatch-snowflake-integration`, assumé via STS. Snowflake lit le bucket sans jamais recevoir de clé d'accès : la confiance passe par une identité IAM et un external ID générés par Snowflake, verrouillés dans la trust policy du rôle

```bash
cd infra/terraform
terraform init      # télécharge les providers AWS et Snowflake (une seule fois)
terraform plan      # aperçu des changements, ne touche à rien
terraform apply     # crée ou met à jour l'infra (auth Snowflake via $env:SNOWFLAKE_USER/PASSWORD/ROLE)
terraform destroy   # supprime tout (reproductible : apply recrée à l'identique)
```

Conventions : le tfstate n'est jamais commité (il peut contenir des secrets), le `.terraform.lock.hcl` l'est (il fige la version des providers). La clé d'accès du pipeline AWS est créée hors Terraform (`aws iam create-access-key --user-name wattwatch-pipeline`) pour ne pas finir en clair dans l'état, à régénérer après chaque destroy/recreate puis à reporter dans `.env`.

Les objets Snowflake qui ne dépendent pas de l'IAM (warehouse, base, schéma Bronze, rôle applicatif, stage externe) sont bootstrappés à part via des scripts SQL dans `infra/snowflake/` (`01_bootstrap.sql` une fois le compte créé, `02_stage.sql` une fois la storage integration provisionnée par Terraform), à exécuter dans un worksheet Snowsight avec le rôle `ACCOUNTADMIN`.

## Tester le pipeline complet avec Docker

La stack locale dockerise tout ce qui peut l'être : Airflow (webserver, scheduler, Postgres, LocalExecutor) et MinIO qui émule la landing zone S3. Snowflake et Power BI restent des services externes.

```bash
docker compose up -d --build
```

| Service | URL | Identifiants |
|---|---|---|
| Airflow UI | http://localhost:8080 | admin / admin |
| Console MinIO | http://localhost:9001 | minioadmin / minioadmin |

Le repo est monté sur `/opt/wattwatch` dans les conteneurs : toute modification de code ou de DAG est prise en compte sans rebuild. Dans ce mode, le spider écrit ses PDF dans `s3://wattwatch/landing/crse/` (MinIO) et `scrapers/process_landing.py` les parse vers `s3://wattwatch/processed/`, exactement le contrat qu'aura le vrai S3.

Tester un DAG sans attendre le scheduler :

```bash
docker compose exec airflow-scheduler airflow dags test wattwatch_ingestion 2026-07-17
```

Les DAGs `wattwatch_load` (COPY INTO) et `wattwatch_dbt` s'activent en renseignant `AIRFLOW_CONN_SNOWFLAKE_WATTWATCH` dans `.env` (compte d'essai Snowflake suffisant). Note : Snowflake ne peut pas lire un MinIO local, pour le `COPY INTO` il faut pointer `WATTWATCH_S3_BUCKET` vers un vrai bucket S3 (juste un changement de variables d'environnement, aucun changement de code).

## Structure

```
wattwatch-africa/
├── scrapers/          # Spiders Scrapy + parseur PDF (package Scrapy)
├── dags/              # DAGs Airflow : ingestion, chargement, dbt
├── dbt/               # Modèles Bronze/Silver/Gold + tests
├── infra/terraform/   # IaC AWS + Snowflake : bucket S3, IAM, storage integration
├── infra/snowflake/   # Scripts SQL de bootstrap (warehouse, rôle, stage)
├── tests/             # pytest (fixtures : vraie grille SENELEC 2026)
├── data/              # landing/ (brut, non versionné) et processed/
├── .github/workflows/ # CI : lint + tests Python, dbt parse
└── docs/
```

## Indicateurs d'affordabilité (couche Gold, Phase 2)

- Coût unitaire par kWh et par tranche
- Part du revenu des ménages pour un panier électrique de base (seuil ESMAP autour de 5 à 10 %)
- Équivalent en kWh du salaire minimum (SMIG)
- Indice de progressivité tarifaire (1ère tranche vs suivantes)
- Écart prépaiement (Woyofal) vs post-paiement
- Prix normalisé en USD PPP (comparaison inter-pays)
- Indice d'évolution temporelle (base 100), pour capter la baisse de 10 % du 1er janvier 2026
- Croisement prix / taux d'accès à l'électricité (World Bank `EG.ELC.ACCS.ZS`)

## Sources de données

| Source | Apport | Format |
|---|---|---|
| [CRSE](https://www.crse.sn) | Grilles tarifaires officielles, décisions | PDF (API REST WP) |
| [SENELEC](https://www.senelec.sn) | Communiqués, grilles complémentaires | HTML |
| ANSD | Revenu des ménages, pauvreté | CSV |
| World Bank Open Data | Taux d'accès à l'électricité (SDG7) | API |
| Africa Energy Portal, ANARE-CI/CIE | Extension régionale (Phase 4) | Web/PDF |
