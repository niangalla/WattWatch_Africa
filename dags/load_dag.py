"""DAG de chargement : S3 → Snowflake Bronze via COPY INTO.

Phase 1 : squelette. Pattern ELT strict — le chargement est fait ici
(jamais par dbt), la transformation est faite par dbt dans Snowflake.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

default_args = {
    "owner": "wattwatch",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

COPY_TARIFS = """
COPY INTO WATTWATCH.BRONZE.RAW_TARIFS_ELECTRICITE
FROM @WATTWATCH.BRONZE.LANDING_STAGE/processed/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
PATTERN = '.*_tarifs[.]csv'
ON_ERROR = 'ABORT_STATEMENT';
"""

with DAG(
    dag_id="wattwatch_load",
    description="Chargement landing S3 vers Snowflake Bronze (COPY INTO)",
    schedule=None,  # déclenché par wattwatch_ingestion (Dataset/TriggerDagRun en Phase 3)
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["wattwatch", "load"],
) as dag:
    copy_tarifs = SnowflakeOperator(
        task_id="copy_into_bronze_tarifs",
        snowflake_conn_id="snowflake_wattwatch",
        sql=COPY_TARIFS,
    )
