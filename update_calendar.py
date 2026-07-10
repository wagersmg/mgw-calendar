import re
from datetime import datetime, timedelta, timezone

import requests
from icalendar import Calendar, Event

SHOW_ID = 1453  # TVMaze Big Brother (US)
EPISODE_LENGTH = timedelta(hours=1)

# Only keep episodes from the last N days onward (plus all future episodes)
LOOKBACK_DAYS = 30

url = f"https://api.tvmaze.com/shows/{SHOW_ID}/episodes"
episodes = requests.get(url, timeout=30).json()

cal = Calendar()
cal.add("prodid", "-//Big Brother Calendar//")
cal.add("version", "2.0")

now_utc = datetime.now(timezone.utc)
cutoff = now_utc - timedelta(days=LOOKBACK_DAYS)

def strip_html(text: str) -> str:
    """TVMaze summaries come as HTML - strip tags for a plain-text description."""
    return re.sub(r"<[^>]+>", "", text or "").strip()

for ep in episodes:
    if not ep.get("airstamp"):
        continue

    start = datetime.fromisoformat(ep["airstamp"].replace("Z", "+00:00"))

    if start < cutoff:
        continue

    event = Event()

    event.add("uid", f'tvmaze-ep-{ep["id"]}@bigbrother-calendar')
    event.add("dtstamp", now_utc)
    event.add("summary", f'Big Brother S{ep["season"]:02d}E{ep["number"]:02d}')
    event.add("dtstart", start)
    event.add("dtend", start + EPISODE_LENGTH)
    event.add("description", strip_html(ep.get("summary", "")))

    cal.add_component(event)

with open("bigbrother.ics", "wb") as f:
    f.write(cal.to_ical())

print(f"Calendar updated with {len(cal.subcomponents)} events.")
