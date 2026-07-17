# Image Airflow de WattWatch : Airflow + Scrapy/pdfplumber (ingestion) + dbt (transformation).
# Le code du projet n'est pas copié dans l'image : docker-compose monte le repo sur /opt/wattwatch.
FROM apache/airflow:2.10.5-python3.12

COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt
