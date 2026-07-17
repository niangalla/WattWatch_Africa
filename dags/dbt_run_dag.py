"""DAG dbt : transformations Bronze → Silver → Gold dans Snowflake.

Phase 2 : squelette. dbt ne charge jamais de données (ELT strict).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "wattwatch",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="wattwatch_dbt",
    description="dbt run + test (Bronze → Silver → Gold)",
    schedule=None,  # déclenché après wattwatch_load
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["wattwatch", "dbt"],
) as dag:
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/wattwatch/dbt && dbt run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/wattwatch/dbt && dbt test --profiles-dir .",
    )

    dbt_run >> dbt_test
