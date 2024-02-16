FROM scrapinghub/scrapinghub-stack-scrapy:2.11-latest
ENV TERM xterm
ENV SCRAPY_SETTINGS_MODULE edgar_crawler.settings
RUN mkdir -p /app
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install -e .
RUN python -c "import edgar_crawler"
