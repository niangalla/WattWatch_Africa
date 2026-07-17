"""DAG d'ingestion : scrape CRSE → landing zone S3.

Phase 1 : squelette validé, à brancher sur un déploiement Airflow.
Le spider écrit directement dans S3 quand WATTWATCH_S3_BUCKET est défini
(voir scrapers/settings.py) — le DAG ne fait qu'orchestrer.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "wattwatch",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="wattwatch_ingestion",
    description="Scrape des grilles tarifaires CRSE vers la landing zone S3",
    schedule="@weekly",  # les grilles changent rarement (révisions tarifaires)
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["wattwatch", "ingestion"],
) as dag:
    scrape_crse = BashOperator(
        task_id="scrape_crse_grilles",
        bash_command=(
            "cd /opt/wattwatch && "
            "scrapy crawl crse -a cats=grilles-tarifaires "
            "-O data/landing/crse/manifest.json"
        ),
    )

    parse_pdfs = BashOperator(
        task_id="parse_grilles_pdf",
        # Lit la landing zone (S3/MinIO si WATTWATCH_S3_BUCKET est défini, sinon
        # data/landing/) et publie les CSV tidy dans processed/
        bash_command="cd /opt/wattwatch && python -m scrapers.process_landing",
    )

    scrape_crse >> parse_pdfs
