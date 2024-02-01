import hashlib
import itertools
import math
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import typer
from bs4 import BeautifulSoup
from cachier import cachier
from loguru import logger
from tqdm import tqdm
from urllib3.util import Retry

from ratelimit import LimiterSession


def hash_args(args, kwargs):
    signature = ",".join(sorted(f"{arg}" for arg in args)) + \
        ",".join(sorted(f"{key}={value}" for key, value in kwargs.items() if key not in {"session", "user_agent"}))
    return hashlib.md5(signature.encode("utf-8")).hexdigest()


def create_session():
    return LimiterSession(
        per_second=5,
        retries=Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.5,
            status_forcelist=(400, 401, 403, 500, 502, 503, 504, 505),
        ),
    )

@cachier(cache_dir=".cache", allow_none=False, hash_func=hash_args)
def crawl_url(url, user_agent, *, session):
    try:
        response = session.get(url=url, headers={"User-agent": user_agent})
    except Exception as e:
        logger.debug(f"Request for {url} failed due to: {e}")
        return None
    return response.content

@cachier(cache_dir=".cache", allow_none=False, hash_func=hash_args)
def download_index(
    url, user_agent, *, session
) -> pd.DataFrame:
    logger.info(f"Downloading {url}")
    with tempfile.TemporaryFile(mode="w+b") as tmp:
        content = crawl_url(url, user_agent, session=session)
        if content is None:
            return None
        tmp.write(content)
        records = []
        with zipfile.ZipFile(tmp).open("master.idx") as f:
            for line in itertools.islice(f, 11, None):
                line = line.decode("latin-1").strip()
                records.append(
                    {
                        "original": line,
                        "index_html_url": line.rsplit("|", 1)[-1].replace(
                            ".txt", "-index.html"
                        ),
                    }
                )
    return pd.DataFrame(records)


def download_indices(
    start_year: int,
    end_year: int,
    user_agent: str,
    *,
    session,
    quarters: List[int] | None = None,
) -> pd.DataFrame:
    """
    Downloads EDGAR Index files for the specified years and quarters.

    Parameters
    ----------
    start_year : int
        The first year to download indices for.
    end_year : int
        The last year to download indices for, inclusive.
    user_agent : str
        The User-Agent string to use when making the request.
    quarters : List[int], optional
        The quarters to download indices for. If None, all quarters will be downloaded.
    skip : bool, optional
        If True, existing indices will be skipped.
    output_folder : str, optional
        The folder to save the indices in.
    """
    base_url = "https://www.sec.gov/Archives/edgar/full-index"

    if quarters is None:
        quarters = [1, 2, 3, 4]

    for quarter in quarters:
        if quarter not in {1, 2, 3, 4}:
            raise Exception(f'Invalid quarter "{quarter}"')

    output = []
    failed_indices = []
    for year in range(start_year, end_year + 1):
        for quarter in quarters:
            if year == datetime.now().year and quarter > math.ceil(
                datetime.now().month / 3
            ):
                break
            url = f"{base_url}/{year}/QTR{quarter}/master.zip"
            if (df := download_index(
                url=url,
                user_agent=user_agent,
                session=session,
            )) is None:
                failed_indices.append(url)
            else:
                output.append(df)

    while len(failed_indices) > 0:
        results = []
        for url in failed_indices:
            if (df := download_index(
                url, 
                user_agent,
                session=session,
                verbose_cache=True,
            )) is None:
                results.append(url)
            else:
                output.append(df)
        failed_indices = results
    
    return pd.concat(output, ignore_index=True)



def filter_indices(
    df: pd.DataFrame,
    filing_types: List[str] | None = None,
):
    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K"]
    logger.info(f"Filtering indices for {filing_types}")
    df[
        [
            "cik",
            "name",
            "type",
            "date",
            "index_text_url",
        ]
    ] = df.original.str.split("|", expand=True)
    df = df.assign(
        index_text_url=df["index_text_url"].map(
            lambda x: "https://www.sec.gov/Archives/" + x
        ),
        index_html_url=df["index_html_url"].map(
            lambda x: "https://www.sec.gov/Archives/" + x
        ),
    )
    subset = df[df.type.isin(filing_types)]
    subset = subset.drop(columns=["original"])
    return subset


@cachier(cache_dir=".cache", allow_none=False, hash_func=hash_args)
def parse_index(
    index_html_url: str,
    user_agent: str,
    *,
    session,
):
    md5 = hashlib.md5(index_html_url.encode("utf-8")).hexdigest()
    content = crawl_url(index_html_url, user_agent, session=session)
    if content is None:
        return None, md5
    soup = BeautifulSoup(content, "lxml")
    table = soup.find(
        "table", {"summary": "Document Format Files", "class": "tableFile"}
    )
    if table is None:
        return None, md5
    records = []
    for tr in table.find_all("tr")[1:]:
        seq, desc, doc_link, doc_type, size = tr.find_all("td")
        if doc_type.text.upper() != "EX-10" and not doc_type.text.upper().startswith("EX-10."):
            continue
        doc_link = doc_link.find("a")
        if doc_link is None:
            continue
        link = doc_link["href"]
        filename = doc_link.text
        records.append(
            {
                "index_html_url": index_html_url,
                "seq": seq.text,
                "desc": desc.text,
                "doc_link": "https://www.sec.gov" + link,
                "doc_type": doc_type.text,
                "size": size.text,
                "filename": filename,
            }
        )

    results = pd.DataFrame(records)
    return results, md5


def download_exhibits(
    records: pd.DataFrame,
    md5: str,
    user_agent: str,
    *,
    session,
    output_dir: str = "exhibits",
    skip: bool = True,
):
    if len(records) == 0:
        return None
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(Path(output_dir) / f"{md5}.jsonl") and skip:
        exhibits = pd.read_json(
            Path(output_dir) / f"{md5}.jsonl", orient="records", lines=True
        )
    else:
        exhibits = records.assign(
            doc_content=records["doc_link"].map(
                lambda x: crawl_url(x, user_agent, session=session)
            ),
        )

    while len(exhibits[exhibits.doc_content.isna()]) > 0:
        logger.info(f"Retrying {len(exhibits[exhibits.doc_content.isna()])} exhibits")
        for _, row in exhibits[exhibits.doc_content.isna()].iterrows():
            exhibits.loc[
                exhibits.index_html_url == row["index_html_url"], "doc_content"
            ] = crawl_url(row["doc_link"], user_agent, session=session)

    exhibits.to_json(Path(output_dir) / f"{md5}.jsonl", orient="records", lines=True)
    return exhibits


if __name__ == "__main__":
    

    def run(
        start_year: int,
        end_year: int,
        user_agent: str,
    ):

        session = create_session()

        df = download_indices(
            start_year=start_year,
            end_year=end_year,
            user_agent=user_agent,
            session=session,
        )
        df = filter_indices(df)
        curr = 0
        pbar = tqdm(df.index_html_url[:50], dynamic_ncols=True)
        for url in pbar:
            exhibit_urls, md5 = parse_index(url, user_agent, session=session)
            if exhibit_urls is None:
                continue
            results = download_exhibits(exhibit_urls, md5, user_agent, session=session)
            found = len(results[results.doc_content.notna()]) if results is not None else 0
            curr += found
            pbar.set_description(f"Found {curr} exhibits")

    typer.run(run)