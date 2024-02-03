import base64
import itertools
import math
import tempfile
import zipfile
import zlib
from datetime import datetime

import scrapy


class ExhibitSpider(scrapy.Spider):
    name = "exhibit"
    base_url = "https://www.sec.gov"
    index_url = "https://www.sec.gov/Archives/edgar/full-index"
    filing_types = ["10-K", "10-Q", "8-K"]
    custom_settings = {
        "FEEDS": {
            "exhibits.jsonl": {"format": "jsonlines", "overwrite": True},
        },
    }

    def start_requests(self):
        quarters = [1, 2, 3, 4]
        for year in range(int(self.start_year), int(self.end_year) + 1):
            for quarter in quarters:
                curr_quarter = math.ceil(datetime.now().month / 3)
                if year == datetime.now().year and quarter > curr_quarter:
                    break
                url = f"{self.index_url}/{year}/QTR{quarter}/master.zip"
                yield scrapy.Request(url=url, callback=self.parse_index)
    
    def parse_index(self, response):
        with tempfile.TemporaryFile(mode="w+b") as tmp:
            content = response.body
            tmp.write(content)
            with zipfile.ZipFile(tmp).open("master.idx") as f:
                for line in itertools.islice(f, 11, None):
                    line = line.decode("latin-1").strip()
                    cik, name, type, date, index_text_url = line.split("|")
                    if type not in self.filing_types:
                        continue
                    index_text_url = "https://www.sec.gov/Archives/" + index_text_url
                    index_html_url = index_text_url.replace(".txt", "-index.html")
                    yield scrapy.Request(
                        url=index_html_url,
                        callback=self.parse_index_html,
                        meta={
                            "cik": cik,
                            "name": name,
                            "type": type,
                            "date": date,
                            "index_text_url": index_text_url,
                            "index_html_url": index_html_url,
                        }
                    )

    def parse_index_html(self, response):
        tables = response.css("table.tableFile")
        if len(tables) == 0:
            return
        for table in tables:
            if table.attrib["summary"] != "Document Format Files":
                continue
            for tr in table.css("tr")[1:]:
                seq, desc, doc_link, doc_type, size = tr.css("td")
                doc_type = doc_type.css("*::text").get().upper()
                if doc_type != "EX-10" and not doc_type.startswith("EX-10."):
                    continue
                link = doc_link.css("a").attrib["href"]
                if link is None:
                    continue
                filename = doc_link.css("a::text").get()
                yield scrapy.Request(
                    url=self.base_url + link,
                    callback=self.save_html,
                    meta={
                        "index_html_url": response.meta["index_html_url"],
                        "index_text_url": response.meta["index_text_url"],
                        "cik": response.meta["cik"],
                        "name": response.meta["name"],
                        "type": response.meta["type"],
                        "date": response.meta["date"],
                        "seq": seq.css("*::text").get(),
                        "desc": desc.css("*::text").get(),
                        "doc_type": doc_type,
                        "size": size.css("*::text").get(),
                        "filename": filename,
                    },
                )
    
    def save_html(self, response):
        yield {
            "index_html_url": response.meta["index_html_url"],
            "index_text_url": response.meta["index_text_url"],
            "cik": response.meta["cik"],
            "name": response.meta["name"],
            "type": response.meta["type"],
            "date": response.meta["date"],
            "seq": response.meta["seq"],
            "desc": response.meta["desc"],
            "doc_link": response.url,
            "doc_type": response.meta["doc_type"],
            "size": response.meta["size"],
            "filename": response.meta["filename"],
            "html": base64.b64encode(zlib.compress(response.body)).decode()
        }