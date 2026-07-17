"""Spider SENELEC — communiqués et grilles complémentaires (Phase 1).

Squelette : la source principale du POC est la CRSE (autorité qui approuve
les grilles). SENELEC viendra compléter avec ses communiqués HTML.
"""

import scrapy


class SenelecSpider(scrapy.Spider):
    name = "senelec"
    allowed_domains = ["senelec.sn"]
    start_urls = ["https://www.senelec.sn"]

    def parse(self, response):
        # TODO(Phase 1) : extraire les communiqués tarifaires
        raise NotImplementedError("Spider SENELEC prévu en Phase 1")
