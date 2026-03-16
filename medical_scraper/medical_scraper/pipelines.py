import re
import json
import os


class CleanDataPipeline:
    """Clean and normalize scraped data."""

    def process_item(self, item, spider):
        for field in item.fields:
            val = item.get(field, "")
            if isinstance(val, str):
                val = re.sub(r"\s+", " ", val).strip()
                item[field] = val

        # Clean phone
        phone = item.get("phone", "")
        if phone:
            phone = re.sub(r"[^\d+\-,\s]", "", phone).strip()
            item["phone"] = phone

        # Normalize rating
        rating = item.get("rating", "")
        if rating:
            try:
                item["rating"] = str(round(float(rating), 1))
            except (ValueError, TypeError):
                pass

        return item


class DuplicateFilterPipeline:
    """Filter duplicate dealers by name+district or phone."""

    def __init__(self):
        self.seen_name_district = set()
        self.seen_phones = set()

    def process_item(self, item, spider):
        from scrapy.exceptions import DropItem

        name = item.get("name", "").lower().strip()
        district = item.get("district", "").lower().strip()
        key = f"{name}|{district}"

        if key in self.seen_name_district:
            raise DropItem(f"Duplicate: {name} in {district}")
        self.seen_name_district.add(key)

        phone = item.get("phone", "")
        if phone:
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                core = digits[-10:]
                if core in self.seen_phones:
                    raise DropItem(f"Duplicate phone: {phone}")
                self.seen_phones.add(core)

        return item


class JsonExportPipeline:
    """Export items to a JSON file for post-processing into Excel."""

    def __init__(self):
        self.items = []
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "output",
        )

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, "scraped_data.json")

        # Append to existing data
        existing = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        existing.extend(self.items)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        spider.logger.info(f"Saved {len(self.items)} items ({len(existing)} total) to {filepath}")
