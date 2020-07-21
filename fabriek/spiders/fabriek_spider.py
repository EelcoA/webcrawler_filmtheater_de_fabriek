# -*- coding: utf-8 -*-
import os
from typing import Dict, List
import csv
import datetime
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from fabriek.spiders import fabriek_helper as fh

def get_text_from_movie(response, param):
    text = response.xpath("//div[@class='film__content__meta']/p/strong[text()='" + param + "']/../text()").get()
    if text is not None:
        text = text.strip()
    return text


class FabriekSpider(CrawlSpider):
    name = 'fabriek'
    allowed_domains = ['www.de-fabriek.nl']
    start_urls = ['https://www.de-fabriek.nl']

    def parse(self, response):
        day_urls = response.xpath("//a[@class='day-selector__day']/@href").getall()
        for day_url in day_urls:
            day = day_url[-10:]  # yyyy-mm-dd
            complete_url = self.start_urls[0] + day_url
            yield scrapy.Request(url=complete_url, callback=self.parse_day,
                                 priority=10,
                                 cb_kwargs=dict(day=day))

    def parse_day(self, response, day: str):
        self.logger.debug("PARSE_DAY: " + day)
        movie_urls: List[str] = response.xpath("//div[@class='main-agenda-movie-info']/h4/a/@href").getall()
        movie_times: List[str] = response.xpath("//div[@class='main-agenda-movie-time']/a/text()").getall()
        movie_titles: List[str] = response.xpath("//div[@class='main-agenda-movie-info']/h4/a/text()").getall()
        movie_tickets: List[str] = response.xpath("//a[@class='button ticket-button']/@href").getall()
        i: int = 0
        for movie_title in movie_titles:
            yield scrapy.Request(url=self.start_urls[0] + movie_urls[i], callback=self.parse_movie,
                                 priority=10,
                                 dont_filter=True,
                                 cb_kwargs=dict(title=movie_title,
                                                day=day,
                                                time=movie_times[i],
                                                ticket_url=movie_tickets[i],
                                                movie_url=self.start_urls[0] + movie_urls[i]))
            i += 1

    def parse_movie(self, response, title, day, time, ticket_url, movie_url):
        self.logger.debug("PARSE_MOVIE: " + title)
        title: str = response.xpath("//div[@class='hero-slide-content']/h1/text()").get()
        language: str = get_text_from_movie(response, "Gesproken taal:")
        genres: str = get_text_from_movie(response, "Genre:")
        playing_time: str = get_text_from_movie(response, "Speelduur:")
        cast: str = get_text_from_movie(response, "Cast:")
        synopsis: str = response.xpath("//p[@class='film__synopsis__intro']/strong/text()").get()
        content_detail1 = response.xpath("//div[@class='film__content__details__left']/p[1]/text()").get()
        content_detail2 = response.xpath("//div[@class='film__content__details__left']/p[2]/text()").get()
        content_detail3 = response.xpath("//div[@class='film__content__details__left']/p[3]/text()").get()
        content_detail = ""
        if content_detail1 is not None:
            content_detail += content_detail1
        if content_detail2 is not None:
            content_detail += content_detail2
        if content_detail3 is not None:
            content_detail += content_detail3

        yield {'datum': day,
               'tijd': time,
               'titel': title,
               'taal': language,
               'genre': genres,
               'speelduur': playing_time,
               'cast': cast,
               'synopsis': synopsis,
               'beschrijving': content_detail,
               'ticket-url': ticket_url,
               'film-url': movie_url
               }


# ----------------------------------------------------------------------------
# Start here
# ----------------------------------------------------------------------------

datetime = datetime.datetime.now()
output_csv_file: str = f"output/fabriek_{datetime:%Y-%m-%d_%H%M%S}_01.csv"
output_csv_file_sorted: str = f"output/fabriek_{datetime:%Y-%m-%d_%H%M%S}_02_sorted.csv"
output_csv_file_event_manager: str = f"output/fabriek_{datetime:%Y-%m-%d_%H%M%S}_03_event_manager.csv"
process = CrawlerProcess(settings={
    "FEEDS": {
        output_csv_file: {"format": "csv"},
    }
})

process.crawl(FabriekSpider)
process.start()  # the script will block here until the crawling is finished

# open and read the file

header_row: List[str]
movie_list: List[List[str]] = []

with open(output_csv_file) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count == 0:
            header_row = row
        else:
            movie_list.append(row)
        line_count += 1

movie_list.sort()
output_file = open(output_csv_file_sorted, mode="w")
output_file.write(",".join(header_row) + "\n")
for row in movie_list:
    row_nr = 0
    for field in row:
        if "," in field:
            row[row_nr] = f'"{row[row_nr]}"'
        row_nr += 1
    output_file.write(",".join(row) + "\n")
output_file.close()

# write the file for Event Manager

header_row = ["event_start_date", "event_start_time", "event_end_date", "event_end_time", "event_name", "event_slug",
              "post_content", "location", "category"]
output_file = open(output_csv_file_event_manager, mode="w")
output_file.write(",".join(header_row) + "\n")

with open(output_csv_file_sorted) as input_file:
    reader = csv.reader(input_file, delimiter=',')
    line_count = 0
    for row in reader:
        if line_count != 0:
            try:
                event_row = fh.create_event_row(row)
                output_file.write(",".join(event_row) + "\n")
            except ValueError as e:
                print("Foutieve data van de website gehaald/gekregen, regel " + str(line_count+1) + ", fout= " + e)
        line_count += 1
output_file.close()


