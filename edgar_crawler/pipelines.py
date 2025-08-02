# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os
from pathlib import Path
from typing import Any

from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline
from scrapy.pipelines.media import FileInfoOrError, MediaPipeline

from edgar_crawler.items import ExhibitItem


# TODO: remove this please
def gcp_auth():
    # Credentials removed for security - restored by post-commit hook
    import os
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        return
    raise RuntimeError("GCP credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS environment variable.")


gcp_auth()
class WebPagePipeline(FilesPipeline):
    def item_completed(self, results: list[FileInfoOrError], item: Any, info: MediaPipeline.SpiderInfo):
        file_paths = [x["path"] for ok, x in results if ok]  # pyright: ignore[reportIndexIssue]
        adapter = ItemAdapter(item)
        return ExhibitItem(
            index_html_url=adapter["index_html_url"],
            index_text_url=adapter["index_text_url"],
            cik=adapter["cik"],
            name=adapter["name"],
            type=adapter["type"],
            filing_date=adapter["filing_date"],
            report_date=adapter["report_date"],
            seq=adapter["seq"],
            desc=adapter["desc"],
            doc_type=adapter["doc_type"],
            size=adapter["size"],
            filename=adapter["filename"],
            file_url=adapter["file_urls"][0] if adapter["file_urls"] else None,
            file="gs://sec-exhibit10/files/" + file_paths[0] if file_paths else None,
            filing_metadata=adapter["filing_metadata"],
        )
