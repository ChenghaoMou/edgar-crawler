# EDGAR-CRAWLER: Unlock the Power of Financial Documents 🚀

This is a modified version of [EDGAR-CRAWLER](https://github.com/nlpaueb/edgar-crawler) to crawl specific material contracts using [scrapy](https://scrapy.org/).

## Usage
```bash
pip install -r requirements.txt
# Update the settings in edgar_crawler/settings.py to match your needs
scrapy crawl exhibit -a start_year=2023 -a end_year=2023
# Deploy the spider to a cloud service
shub deploy
```

## License
[GNU General Public License v3.0](https://github.com/nlpaueb/edgar-crawler/blob/main/LICENSE)

## Citation
An EDGAR-CRAWLER paper is on its way. Until then, please cite the relevant EDGAR-CORPUS paper published at the [3rd Economics and Natural Language Processing (ECONLP) workshop](https://lt3.ugent.be/econlp/) at EMNLP 2021 (Punta Cana, Dominican Republic):
```
@inproceedings{loukas-etal-2021-edgar,
    title = "{EDGAR}-{CORPUS}: Billions of Tokens Make The World Go Round",
    author = "Loukas, Lefteris  and
      Fergadiotis, Manos  and
      Androutsopoulos, Ion  and
      Malakasiotis, Prodromos",
    booktitle = "Proceedings of the Third Workshop on Economics and Natural Language Processing",
    month = nov,
    year = "2021",
    address = "Punta Cana, Dominican Republic",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.econlp-1.2",
    pages = "13--18",
}
```
Read the paper here: [https://aclanthology.org/2021.econlp-1.2/](https://aclanthology.org/2021.econlp-1.2/)
