import json
import os
import scrapy
from medical_scraper.items import MedicalDealerItem


class JustDialMedicalSpider(scrapy.Spider):
    """
    Scrape medical dealers/distributors from JustDial.
    Uses JSON-LD structured data embedded in page source - no browser needed.
    """
    name = "justdial"
    allowed_domains = ["justdial.com"]

    # Medical dealer categories on JustDial (slug, nct-code)
    CATEGORIES = [
        ("Medical-Equipment-Dealers", "nct-10316680"),
        ("Pharmaceutical-Dealers", "nct-10316817"),
        ("Surgical-Equipment-Dealers", "nct-10316682"),
        ("Medical-Shop", "nct-10316652"),
        ("Pharmaceutical-Distributors", "nct-10563330"),
        ("Hospital-Equipment-Dealers", "nct-10316675"),
        ("Lab-Equipment-Dealers", "nct-10316684"),
        ("Diagnostic-Equipment-Dealers", "nct-10563336"),
        ("Healthcare-Product-Distributors", "nct-11268457"),
        ("Orthopaedic-Implant-Dealers", "nct-10563356"),
    ]

    MAX_PAGES = 5

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
                for slug, nct in self.CATEGORIES:
                    city_slug = district.replace(" ", "-")
                    url = f"https://www.justdial.com/{city_slug}/{slug}/{nct}"
                    yield scrapy.Request(
                        url,
                        callback=self.parse,
                        meta={
                            "district": district,
                            "state": state,
                            "category_slug": slug,
                            "nct": nct,
                            "page": 1,
                        },
                        errback=self.handle_error,
                    )

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url}")

    def parse(self, response):
        district = response.meta["district"]
        state = response.meta["state"]
        category_slug = response.meta["category_slug"]
        nct = response.meta["nct"]
        page = response.meta["page"]

        items_found = 0

        # Extract from JSON-LD structured data
        json_ld_scripts = response.xpath(
            '//script[@type="application/ld+json"]/text()'
        ).getall()

        for script_text in json_ld_scripts:
            try:
                data = json.loads(script_text)
            except json.JSONDecodeError:
                continue

            entries = data if isinstance(data, list) else [data]

            for entry in entries:
                if entry.get("@type") == "LocalBusiness":
                    item = self._parse_business(entry, district, state, category_slug)
                    if item:
                        items_found += 1
                        yield item

                if entry.get("@type") == "ItemList":
                    for elem in entry.get("itemListElement", []):
                        biz = elem.get("item", elem)
                        if biz.get("@type") == "LocalBusiness":
                            item = self._parse_business(biz, district, state, category_slug)
                            if item:
                                items_found += 1
                                yield item

        # Fallback to HTML parsing
        if items_found == 0:
            items_found = yield from self._parse_html(response, district, state, category_slug)

        self.logger.info(
            f"[{state}/{district}] {category_slug} page {page}: {items_found} found"
        )

        # Pagination
        if items_found > 0 and page < self.MAX_PAGES:
            next_page = page + 1
            city_slug = district.replace(" ", "-")
            next_url = f"https://www.justdial.com/{city_slug}/{category_slug}/{nct}/page-{next_page}"
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={
                    "district": district,
                    "state": state,
                    "category_slug": category_slug,
                    "nct": nct,
                    "page": next_page,
                },
                errback=self.handle_error,
            )

    def _parse_business(self, entry, district, state, category_slug):
        name = entry.get("name", "").strip()
        if not name:
            return None

        # Skip category/summary entries
        name_lower = name.lower()
        if " in " in name_lower and any(
            kw in name_lower for kw in ["dealers", "distributors", "shop"]
        ):
            return None

        address_obj = entry.get("address", {})
        street = address_obj.get("streetAddress", "")
        locality = address_obj.get("addressLocality") or address_obj.get("addresslocality", "")
        region = address_obj.get("addressRegion", "")
        pincode = address_obj.get("postalCode", "")
        full_address = ", ".join(filter(None, [street, locality, region]))

        agg_rating = entry.get("aggregateRating", {})
        rating = agg_rating.get("ratingValue", "")
        reviews = agg_rating.get("ratingCount") or agg_rating.get("reviewCount", "")
        phone = entry.get("telephone", "")

        return MedicalDealerItem(
            name=name,
            address=full_address,
            city=locality or district,
            district=district,
            state=state,
            area=locality,
            pincode=str(pincode),
            phone=str(phone),
            rating=str(rating),
            reviews=str(reviews),
            category=category_slug.replace("-", " "),
            source="JustDial",
            source_url=entry.get("url", ""),
        )

    def _parse_html(self, response, district, state, category_slug):
        count = 0
        listings = response.css("div.resultbox_info")

        for listing in listings:
            name = listing.css("span.resultbox_title_anchor::text").get("").strip()
            if not name:
                continue

            address = listing.css("span.resultbox_address::text").get("").strip()

            # Extract phone from the listing text
            text = listing.get()
            phone = ""
            import re
            phone_match = re.search(r'[6-9]\d{9}', text)
            if phone_match:
                phone = phone_match.group()

            yield MedicalDealerItem(
                name=name,
                address=address,
                city=district,
                district=district,
                state=state,
                area="",
                pincode="",
                phone=phone,
                rating="",
                reviews="",
                category=category_slug.replace("-", " "),
                source="JustDial",
                source_url=response.url,
            )
            count += 1

        return count
