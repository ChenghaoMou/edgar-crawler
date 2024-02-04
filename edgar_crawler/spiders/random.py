
import scrapy


class RandomSpider(scrapy.Spider):
    name = "random"
    custom_settings = {
        "FEEDS": {
            "gs://sec-exhibit10/exhibits.jsonl": {"format": "jsonlines", "overwrite": False},
        },
    }

    def start_requests(self):
        urls = [
            f"https://quotes.toscrape.com/page/{page}/"
            for page in range(1, 11)
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
    
    def parse(self, response):
        yield {
            "index_html_url": "random_index_html_url",
            "index_text_url": "random_index_text_url",
            "file_urls": [response.url],
            "random_field": "random_value",
            "cik": "random_cik",
            "name": "random_name",
            "type": "random_type",
            "date": "random_date",
            "seq": "random_seq",
            "desc": "random_desc",
            "doc_type": "random_doc_type",
            "size": "random_size",
            "filename": "random_filename",
        }
        