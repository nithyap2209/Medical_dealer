import json
import os
import scrapy
from medical_scraper.items import MedicalDealerItem


class IndiaMartMedicalSpider(scrapy.Spider):
    """
    Scrape medical dealers/distributors from IndiaMART.
    Uses __NEXT_DATA__ JSON embedded in page source - no browser needed.
    """
    name = "indiamart"
    allowed_domains = ["indiamart.com", "dir.indiamart.com"]

    SEARCH_QUERIES = [
        "medical dealer",
        "medicine distributor",
        "pharmaceutical distributor",
        "medical equipment distributor",
        "surgical equipment dealer",
        "hospital supply distributor",
        "medical consumables distributor",
        "lab equipment distributor",
        "pharma distributor",
        "healthcare product distributor",
        "diagnostic equipment dealer",
    ]

    BIZ_FILTER = "40"
    MAX_PAGES = 10

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,
    }

    def __init__(self, districts_file=None, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.districts_map = {}
        if districts_file and os.path.exists(districts_file):
            with open(districts_file, "r", encoding="utf-8") as f:
                self.districts_map = json.load(f)
        if max_pages is not None:
            self.MAX_PAGES = int(max_pages)

    def start_requests(self):
        for state, districts in self.districts_map.items():
            for district in districts:
                for keyword in self.SEARCH_QUERIES:
                    url = (
                        f"https://dir.indiamart.com/search.mp"
                        f"?ss={keyword.replace(' ', '+')}"
                        f"&city={district.replace(' ', '+')}"
                        f"&biz={self.BIZ_FILTER}"
                    )
                    yield scrapy.Request(
                        url,
                        callback=self.parse,
                        meta={
                            "keyword": keyword,
                            "district": district,
                            "state": state,
                            "page": 1,
                        },
                        errback=self.handle_error,
                    )

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url}")

    def parse(self, response):
        keyword = response.meta["keyword"]
        district = response.meta["district"]
        state = response.meta["state"]
        page = response.meta["page"]

        items_found = 0

        # Try __NEXT_DATA__ first
        next_data_text = response.xpath(
            '//script[@id="__NEXT_DATA__"]/text()'
        ).get()

        if next_data_text:
            items_found = yield from self._parse_next_data(
                next_data_text, keyword, district, state, response.url
            )
        else:
            items_found = yield from self._parse_script_json(
                response, keyword, district, state
            )

        # Fallback to HTML
        if items_found == 0:
            items_found = yield from self._parse_html(
                response, keyword, district, state
            )

        self.logger.info(f"[{state}/{district}] {keyword} page {page}: {items_found} found")

        # Pagination
        has_next = False
        if next_data_text:
            try:
                data = json.loads(next_data_text)
                search_resp = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("searchResponse", {})
                )
                has_next = search_resp.get("nextPage", False)
            except (json.JSONDecodeError, AttributeError):
                pass

        if has_next and page < self.MAX_PAGES and items_found > 0:
            next_page = page + 1
            base_url = response.url.split("&page=")[0]
            next_url = f"{base_url}&page={next_page}"
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={
                    "keyword": keyword,
                    "district": district,
                    "state": state,
                    "page": next_page,
                },
                errback=self.handle_error,
            )

    def _parse_next_data(self, json_text, keyword, district, state, page_url):
        count = 0
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return

        search_resp = (
            data.get("props", {})
            .get("pageProps", {})
            .get("searchResponse", {})
        )
        results = search_resp.get("results", [])

        for result in results:
            fields = result.get("fields", {})
            item = self._fields_to_item(fields, keyword, district, state, page_url)
            if item:
                count += 1
                yield item

            for sub in fields.get("more_results", []):
                sub_fields = sub.get("fields", sub)
                item = self._fields_to_item(sub_fields, keyword, district, state, page_url)
                if item:
                    count += 1
                    yield item

        return count

    def _fields_to_item(self, fields, keyword, district, state, page_url):
        name = fields.get("companyname", "").strip()
        if not name:
            return None

        phone = fields.get("phone", "")
        if isinstance(phone, list):
            phone = ", ".join(str(p) for p in phone if p)
        mobile = fields.get("mobile", "")
        if isinstance(mobile, list):
            mobile = ", ".join(str(m) for m in mobile if m)

        contact = ", ".join(filter(None, [str(phone), str(mobile)]))

        city = fields.get("city", district)
        source_url = fields.get("desktop_title_url", page_url)
        if "?" in source_url:
            source_url = source_url.split("?")[0]

        return MedicalDealerItem(
            name=name,
            address=fields.get("address", ""),
            city=city,
            district=district,
            state=state,
            area=fields.get("locality", ""),
            pincode=fields.get("zipcode", ""),
            phone=contact,
            rating=str(fields.get("supplier_rating", "")),
            reviews=str(fields.get("rating_count", "")),
            category=fields.get("title", keyword),
            source="IndiaMART",
            source_url=source_url,
        )

    def _parse_script_json(self, response, keyword, district, state):
        count = 0
        scripts = response.xpath("//script/text()").getall()

        for script in scripts:
            if "companyname" not in script:
                continue
            try:
                for prefix in ["window.__INITIAL_STATE__=", "window.__DATA__="]:
                    if prefix in script:
                        json_str = script.split(prefix, 1)[1].rstrip(";")
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            for key, val in data.items():
                                if isinstance(val, list):
                                    for entry in val:
                                        if isinstance(entry, dict) and "companyname" in entry:
                                            item = self._fields_to_item(
                                                entry, keyword, district, state, response.url
                                            )
                                            if item:
                                                count += 1
                                                yield item
            except (json.JSONDecodeError, IndexError):
                continue

        return count

    def _parse_html(self, response, keyword, district, state):
        count = 0
        for card in response.css(".lcnt, .prd-card, .card, div.supplierInfoDiv"):
            name = card.css(
                ".lcname::text, .company-name::text, .prd-card-name::text, span.companyname::text"
            ).get("").strip()
            if not name:
                continue

            city = card.css(".cloc::text, .city-name::text").get("").strip()
            address = card.css(".adr::text, .address::text").get("").strip()

            yield MedicalDealerItem(
                name=name,
                address=address,
                city=city or district,
                district=district,
                state=state,
                area="",
                pincode="",
                phone="",
                rating="",
                reviews="",
                category=keyword,
                source="IndiaMART",
                source_url=response.url,
            )
            count += 1

        return count
