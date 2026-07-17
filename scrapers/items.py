"""Items Scrapy : un document réglementaire CRSE et son PDF."""

import scrapy


class CrseDocumentItem(scrapy.Item):
    # Métadonnées du document (API REST WordPress de crse.sn)
    doc_id = scrapy.Field()
    title = scrapy.Field()
    slug = scrapy.Field()
    date_published = scrapy.Field()
    date_modified = scrapy.Field()
    link = scrapy.Field()
    categories = scrapy.Field()  # ex. ["grilles-tarifaires"]
    sectors = scrapy.Field()  # ex. ["electricite"]
    scraped_at = scrapy.Field()
    source = scrapy.Field()  # "crse.sn"

    # Champs consommés par FilesPipeline
    file_urls = scrapy.Field()
    files = scrapy.Field()
