# Image Airflow de WattWatch : Airflow + Scrapy/pdfplumber (ingestion) + dbt (transformation).
# Le code du projet n'est pas copié dans l'image : docker-compose monte le repo sur /opt/wattwatch.
FROM apache/airflow:2.10.5-python3.12

# 1. Installer les providers Airflow avec les contraintes strictes
RUN pip install --no-cache-dir "apache-airflow==2.10.5" apache-airflow-providers-amazon apache-airflow-providers-snowflake --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"

# 2. Installer les packages de Data Engineering (dbt, scrapy) sans les contraintes
COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt
