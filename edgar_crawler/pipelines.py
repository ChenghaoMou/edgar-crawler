# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline

from edgar_crawler.items import ExhibitItem


class WebPagePipeline(FilesPipeline):
    def item_completed(self, results, item, info):
        file_paths = [x["path"] for ok, x in results if ok]
        adapter = ItemAdapter(item)
        return ExhibitItem(
            index_html_url = adapter["index_html_url"],
            index_text_url = adapter["index_text_url"],
            cik = adapter["cik"],
            name = adapter["name"],
            type = adapter["type"],
            date = adapter["date"],
            seq = adapter["seq"],
            desc = adapter["desc"],
            doc_type = adapter["doc_type"],
            size = adapter["size"],
            filename = adapter["filename"],
            file_url = adapter["file_urls"][0],
            file = "gs://sec-exhibit10/files/" + file_paths[0] if file_paths else None
        )
        

        
