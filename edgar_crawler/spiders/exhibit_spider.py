import itertools
import json
import math
import tempfile
import zipfile
from datetime import datetime
from typing import AsyncGenerator, Generator

import scrapy
from scrapy.http import Response


class ExhibitSpider(scrapy.Spider):
    name = "exhibit"
    base_url = "https://www.sec.gov"
    index_url = "https://www.sec.gov/Archives/edgar/full-index"
    filing_types = ["10-K", "10-Q", "8-K"]
    custom_settings = {
        "FEEDS": {
            # You can replace it with file:///local/path to store the exported data locally
            "gs://sec-exhibit10/exhibits__%(start_year)s__%(end_year)s.jsonl": {
                "format": "jsonlines",
                "overwrite": True,
            },
        },
    }

    async def start(self) -> AsyncGenerator[scrapy.Request, None]:
        """Start the spider by generating requests for each quarter's master index file within the specified year range."""
        quarters = [1, 2, 3, 4]
        curr_year = datetime.now().year
        curr_quarter = math.ceil(datetime.now().month / 3)
        # both start_year and end_year are passed from the command line arguments
        for year in range(int(self.start_year), int(self.end_year) + 1):  # pyright: ignore[reportAttributeAccessIssue]
            for quarter in quarters:
                if year == curr_year and quarter > curr_quarter:
                    break
                url = f"{self.index_url}/{year}/QTR{quarter}/master.zip"
                yield scrapy.Request(url=url, callback=self.parse_index)

    def parse_index(self, response: Response):
        """Parse the master index file to extract all filing index pages."""
        try:
            with tempfile.TemporaryFile(mode="w+b") as tmp:
                content = response.body
                tmp.write(content)
                with zipfile.ZipFile(tmp).open("master.idx") as f:
                    for line in itertools.islice(f, 11, None):
                        line = line.decode("latin-1").strip()
                        cik, name, type, filing_date, index_text_url = line.split("|")
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
                                "filing_date": filing_date,
                                "index_text_url": index_text_url,
                                "index_html_url": index_html_url,
                            },
                        )
        except Exception as e:
            self.logger.error(f"Error parsing index text URL {response.url}: {e}")

    def parse_index_html(self, response: Response) -> Generator[dict[str, str | None | list[str]], None, None]:
        """Extract all exhibit data from the table."""
        tables = response.css("table.tableFile")
        if len(tables) == 0:
            return
        metadata: dict[str, str] | None = self.parse_metadata(response)
        if metadata is None:
            return

        for table in tables:
            if table.attrib["summary"] != "Document Format Files":
                continue
            for tr in table.css("tr")[1:]:
                seq, desc, doc_link, doc_type, size = tr.css("td")
                doc_type = doc_type.css("*::text").get("").upper()
                if doc_type != "EX-10" and not doc_type.startswith("EX-10."):
                    continue
                link = doc_link.css("a").attrib["href"]
                if link is None:
                    continue
                filename = doc_link.css("a::text").get()
                yield {
                    "index_html_url": response.meta["index_html_url"],
                    "index_text_url": response.meta["index_text_url"],
                    "cik": response.meta["cik"],
                    "name": response.meta["name"],
                    "type": response.meta["type"],
                    "filing_date": response.meta["filing_date"],
                    "report_date": metadata["Period of Report"],
                    "seq": seq.css("*::text").get(),
                    "desc": desc.css("*::text").get(),
                    "doc_type": doc_type,
                    "size": size.css("*::text").get(),
                    "filename": filename,
                    "file_urls": [self.base_url + link],
                    "filing_metadata": json.dumps(metadata),
                }

    def parse_metadata(self, response: Response) -> dict[str, str] | None:
        """Extract filing metadata from the content above the table."""
        forms = response.css("div.formDiv")
        if not forms:
            return None

        groups = forms[0].css("div.formGrouping")
        if not groups:
            return None

        metadata = {}

        for group in groups:
            divs = group.css("[class*='info']")
            curr_header = None

            for div in divs:
                if 'class="infoHead"' in str(div):
                    if curr_header is not None:
                        metadata[curr_header] = "na"
                    curr_header = div.css("*::text").get("").strip() or None
                elif 'class="info"' in str(div) and curr_header:
                    metadata[curr_header] = div.css("*::text").get("na").strip()
                    curr_header = None

            if curr_header is not None:
                metadata[curr_header] = "na"

        return metadata
