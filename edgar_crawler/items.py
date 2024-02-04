# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ExhibitItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    index_html_url = scrapy.Field()
    index_text_url = scrapy.Field()
    cik = scrapy.Field()
    name = scrapy.Field()
    type = scrapy.Field()
    date = scrapy.Field()
    seq = scrapy.Field()
    desc = scrapy.Field()
    doc_type = scrapy.Field()
    size = scrapy.Field()
    filename = scrapy.Field()
    file_url = scrapy.Field()
    file = scrapy.Field()
