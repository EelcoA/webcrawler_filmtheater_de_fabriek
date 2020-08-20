import csv
import datetime as dt
from typing import List, IO

import definitions
import settings
from fabriek.csv_convert import event_helper

event_data_header_row = ["event_start_date", "event_start_time", "event_end_date", "event_end_time", "event_name",
                         "post_excerpt", "post_content", "location-slug", "category-slug"]


def create_event_manager_file(input_file: IO, output_file: IO):
    writer = csv.writer(output_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)

    writer.writerow(event_data_header_row)

    with input_file as input_file:
        reader = csv.reader(input_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        line_count = 0
        for row in reader:
            if line_count != 0:
                try:
                    event_row = create_event_row(row)
                    writer.writerow(event_row)
                except ValueError as e:
                    msg = "Foutieve data van de website, regel " + str(line_count) + ", fout= " + str(e)
                    output_file.write(msg + "\n")
            line_count += 1

    if output_file.name != definitions.FLAG_TO_SKIP_CLOSING_OF_IN_MEMORY_TEST_FILE:
        output_file.close()


def create_event_row(row: List[str]):
    # get all fields out of the List
    datum = row[0]
    tijd = row[1]
    titel = row[2]
    taal = row[3]
    genre = row[4]
    speelduur = row[5]
    cast = row[6]
    synopsis = row[7]
    beschrijving_incl_HTML = row[8]
    ticket_url = row[9]
    film_url = row[10]

    if not event_helper.is_valid_date_string(datum):
        raise ValueError("\"datum bevat geen of geen geldige waarde: " + ("Leeg" if datum is None else datum) + "\"")
    event_start_date = datum

    if not event_helper.is_valid_begintijd(tijd):
        raise ValueError("\"tijd bevat geen, of geen geldige waarde: " + ("Leeg" if tijd is None else tijd) + "\"")
    event_start_time = tijd + ":00"

    # add 10 minutes for trailers, when no playtime found, we use zero,
    # so that end time = start time, showing we don't know
    try:
        playtime_minutes = event_helper.get_minutes(speelduur) + 10
    except ValueError:
        playtime_minutes = 0

    start_date_time: dt.datetime = event_helper.create_date_time(event_start_date, event_start_time)
    end_date_time: dt.datetime = event_helper.add_minutes_to_datetime(start_date_time, playtime_minutes)

    event_end_date = event_helper.get_date_str(end_date_time)
    event_end_time = event_helper.get_time_str(end_date_time)

    event_name = titel
    post_excerpt = event_helper.clean_text_from_HTML_and_other_shit(synopsis)
    # beschrijving_clean = event_helper.clean_text_from_HTML_and_other_shit(beschrijving)
    # if post_excerpt in beschrijving_clean:
    #     beschrijving_clean = event_helper.remove_redundant_expert(beschrijving_clean, post_excerpt)
    post_content = beschrijving_incl_HTML + "<br>" + \
                   "<br>" + \
                   event_helper.to_strong("Gesproken taal: ") + taal + "<br>" + \
                   event_helper.to_strong("Genre: ") + genre + "<br>" + \
                   event_helper.to_strong("Speelduur: ") + speelduur + "<br>" + \
                   event_helper.to_strong("Cast: ") + cast + "<br>" + \
                   "<br>" + \
                   '<a href=\'' + film_url + '\'>' + film_url + '</a>'
    location = settings.LOCATION
    category = settings.CATEGORY

    event_row = [event_start_date, event_start_time, event_end_date, event_end_time,
                 event_name, post_excerpt, post_content, location, category]

    return event_row


