import re
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event


OUTPUT_FILE = "aceofcups.ics"

BASE_URL = "https://aceofcupsbar.com/"
LOCATION = "Ace of Cups, 2619 N High St, Columbus, OH"
TIMEZONE = ZoneInfo("America/New_York")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://aceofcupsbar.com/",
}

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def parse_date(text):
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d+)",
        text,
    )

    if not match:
        return None

    month = MONTHS[match.group(1)]
    day = int(match.group(2))

    now = datetime.now(TIMEZONE)

    event_date = datetime(now.year, month, day, 19, 0, tzinfo=TIMEZONE)

    if event_date < now - timedelta(days=30):
        event_date = event_date.replace(year=now.year + 1)

    return event_date


cal = Calendar()
cal.add("prodid", "-//Ace of Cups Calendar//")
cal.add("version", "2.0")
cal.add("X-WR-TIMEZONE", "America/New_York")
cal.add("X-WR-CALNAME", "Ace of Cups")

events_added = 0
seen = set()

session = requests.Session()
session.headers.update(HEADERS)

for page in range(1, 10):

    if page == 1:
        url = BASE_URL
    else:
        url = f"{BASE_URL}?list1page={page}"

    response = session.get(url, timeout=30)

    # Fail loudly (including on 403) so the Action turns red
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select(".seetickets-list-event-container")

    print(f"Page {page}: HTTP {response.status_code}, {len(cards)} event cards found")

    if not cards:
        break

    for card in cards:

        title_element = card.select_one(".event-title a")
        date_element = card.select_one(".event-date")

        if not title_element or not date_element:
            continue

        ticket_url = title_element.get("href", "")

        if ticket_url in seen:
            continue

        seen.add(ticket_url)

        headliner_element = card.select_one(".headliners")
        headliner = ""

        if headliner_element:
            headliner = clean(headliner_element.get_text())

        if headliner:
            title = headliner
        else:
            title = clean(title_element.get_text())

        title = re.sub(r"\s+at Ace of Cups$", "", title, flags=re.IGNORECASE)

        start = parse_date(date_element.get_text())

        if not start:
            continue

        description = []

        genre = card.select_one(".genre")
        ages = card.select_one(".ages")
        price = card.select_one(".price")

        if genre:
            description.append(f"Genre: {clean(genre.get_text())}")
        if ages:
            description.append(f"Age: {clean(ages.get_text())}")
        if price:
            description.append(f"Price: {clean(price.get_text())}")
        if ticket_url:
            description.append(f"Tickets: {ticket_url}")

        uid_source = ticket_url or title + str(start)
        uid = hashlib.md5(uid_source.encode()).hexdigest()

        event = Event()

        event.add("uid", f"aceofcups-{uid}@calendar")
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("summary", title)
        event.add("dtstart", start)
        event.add("dtend", start + timedelta(hours=3))
        event.add("location", LOCATION)
        event.add("description", "\n".join(description))

        cal.add_component(event)

        events_added += 1

# Never overwrite the existing calendar with an empty one
if events_added == 0:
    print("ERROR: 0 events parsed. Not overwriting the existing calendar. "
          "The site may be blocking requests or its HTML may have changed.")
    sys.exit(1)

with open(OUTPUT_FILE, "wb") as f:
    f.write(cal.to_ical())

print(f"Ace of Cups calendar updated with {events_added} events.")
