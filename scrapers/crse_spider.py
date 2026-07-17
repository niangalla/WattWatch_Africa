"""Spider CRSE — collecte les documents réglementaires et leurs PDF.

crse.sn est un WordPress dont les documents sont exposés via l'API REST :
    /wp-json/wp/v2/crse_document          (~530 documents, paginé)
    /wp-json/wp/v2/media?parent=<doc_id>  (le PDF attaché à chaque document)

Les catégories et secteurs ne sont pas des taxonomies REST publiques mais
apparaissent dans ``class_list`` de chaque document, sous la forme
``crse_document_cat-<slug>`` et ``crse_secteur-<slug>``.

Usage :
    scrapy crawl crse -a cats=grilles-tarifaires -O data/landing/crse/manifest.json
    scrapy crawl crse -a cats=grilles-tarifaires,decisions -a sectors=electricite

Par défaut : catégorie ``grilles-tarifaires``, tous secteurs.
"""

import base64
import json
from datetime import UTC, datetime

import scrapy

from scrapers.items import CrseDocumentItem

API_BASE = "https://www.crse.sn/wp-json/wp/v2"
PER_PAGE = 100

CAT_PREFIX = "crse_document_cat-"
SECTOR_PREFIX = "crse_secteur-"


class CrseSpider(scrapy.Spider):
    name = "crse"
    allowed_domains = ["crse.sn"]

    def __init__(self, cats="grilles-tarifaires", sectors=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cats = set(cats.split(",")) if cats else set()
        self.sectors = set(sectors.split(",")) if sectors else set()

    async def start(self):
        yield scrapy.Request(
            f"{API_BASE}/crse_document?per_page={PER_PAGE}&page=1",
            callback=self.parse_document_page,
            cb_kwargs={"page": 1},
        )

    def parse_document_page(self, response, page):
        docs = json.loads(response.text)

        for doc in docs:
            class_list = doc.get("class_list", [])
            doc_cats = [c.removeprefix(CAT_PREFIX) for c in class_list if c.startswith(CAT_PREFIX)]
            doc_sectors = [
                c.removeprefix(SECTOR_PREFIX) for c in class_list if c.startswith(SECTOR_PREFIX)
            ]

            if self.cats and not self.cats.intersection(doc_cats):
                continue
            if self.sectors and not self.sectors.intersection(doc_sectors):
                continue

            item = CrseDocumentItem(
                doc_id=doc["id"],
                title=doc["title"]["rendered"],
                slug=doc["slug"],
                date_published=doc["date"],
                date_modified=doc["modified"],
                link=doc["link"],
                categories=doc_cats,
                sectors=doc_sectors,
                scraped_at=datetime.now(UTC).isoformat(),
                source="crse.sn",
            )
            yield scrapy.Request(
                f"{API_BASE}/media?parent={doc['id']}",
                callback=self.parse_media,
                cb_kwargs={"item": item},
            )

        if len(docs) == PER_PAGE:
            next_page = page + 1
            yield scrapy.Request(
                f"{API_BASE}/crse_document?per_page={PER_PAGE}&page={next_page}",
                callback=self.parse_document_page,
                cb_kwargs={"page": next_page},
            )

    def parse_media(self, response, item):
        media = json.loads(response.text)
        pdf_urls = [
            m["source_url"] for m in media if m.get("mime_type") == "application/pdf"
        ]
        if not pdf_urls:
            # Certains documents (ex. grilles harmonisées des concessions rurales)
            # ont leur PDF dans la médiathèque sans rattachement parent. Le site
            # les sert via /?view_doc=<base64(doc_id)>, qui redirige vers le PDF.
            doc_id_b64 = base64.b64encode(str(item["doc_id"]).encode()).decode()
            pdf_urls = [f"https://www.crse.sn/?view_doc={doc_id_b64}"]
            self.logger.info(
                "Document %s (%s) sans PDF attaché, fallback view_doc",
                item["doc_id"], item["slug"],
            )
        item["file_urls"] = pdf_urls
        yield item
