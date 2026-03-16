import scrapy


class MedicalDealerItem(scrapy.Item):
    name = scrapy.Field()
    address = scrapy.Field()
    city = scrapy.Field()
    district = scrapy.Field()
    state = scrapy.Field()
    area = scrapy.Field()
    pincode = scrapy.Field()
    phone = scrapy.Field()
    rating = scrapy.Field()
    reviews = scrapy.Field()
    category = scrapy.Field()
    source = scrapy.Field()
    source_url = scrapy.Field()
