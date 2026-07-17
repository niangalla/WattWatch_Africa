"""Réglages Scrapy du projet WattWatch Africa.

Politesse obligatoire : crse.sn renvoie des 503 dès que les requêtes
s'enchaînent trop vite (constaté lors du POC). AutoThrottle + retry sur 503.
"""

import os

from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "wattwatch"

SPIDER_MODULES = ["scrapers"]
NEWSPIDER_MODULE = "scrapers"

USER_AGENT = (
    "WattWatchAfrica/0.1 (+https://github.com/wattwatch-africa; "
    "observatoire open source de l'affordabilite energetique)"
)

ROBOTSTXT_OBEY = True

# Politesse — le site rate-limite (503)
DOWNLOAD_DELAY = 2.0
CONCURRENT_REQUESTS_PER_DOMAIN = 1
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

RETRY_ENABLED = True
RETRY_TIMES = 4
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Téléchargement des PDF : landing zone locale par défaut, S3 si bucket défini
ITEM_PIPELINES = {
    "scrapy.pipelines.files.FilesPipeline": 1,
}

# Les PDF non rattachés sont servis via /?view_doc=… qui redirige (302) vers le fichier
MEDIA_ALLOW_REDIRECTS = True

_s3_bucket = os.getenv("WATTWATCH_S3_BUCKET")
if _s3_bucket:
    FILES_STORE = f"s3://{_s3_bucket}/landing/crse/"
else:
    FILES_STORE = "data/landing/crse/"

# MinIO local (docker-compose) : même API que S3, seul l'endpoint change
_endpoint = os.getenv("AWS_ENDPOINT_URL")
if _endpoint:
    AWS_ENDPOINT_URL = _endpoint

FEED_EXPORT_ENCODING = "utf-8"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
