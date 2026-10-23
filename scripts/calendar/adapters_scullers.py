"""Read the bounded public MusicIDB calendar embedded by Scullers Jazz Club."""

import datetime as dt
import re
from urllib.parse import parse_qs, urlsplit

from adapters_boston_html import Tree, _clock, _event, _text


MAX_EVENTS = 200


def supported(host_or_url):
    if "://" not in host_or_url:
        return host_or_url.lower() in {"scullersjazz.com", "www.scullersjazz.com"}
    parts = urlsplit(host_or_url)
    if parts.hostname in {"scullersjazz.com", "www.scullersjazz.com"}:
        return True
    return (parts.hostname in {"musicidb.com", "www.musicidb.com"}
            and parse_qs(parts.query).get("venueId") == ["715"])


def _show_times(subtitle):
    """Read explicit show labels; 'Shows at 7 & 9pm' reports two PM sets."""
    match = re.search(r"\bshows?\s+at\s+(.+)", subtitle, re.I)
    if not match:
        return []
    text = match.group(1).strip()
    # A doors label, biography, or unrelated sentence cannot supply the show time.
    text = re.split(r"[;|]|\bdoors\b", text, maxsplit=1, flags=re.I)[0].strip()
    values = [part.strip() for part in re.split(r"\s*(?:&|,|\band\b)\s*", text, flags=re.I)]
    suffix = re.search(r"([ap]m)\s*$", values[-1], re.I)
    if not suffix:
        return []
    result, inherited = [], False
    for value in values:
        if re.fullmatch(r"\d{1,2}(?::\d{2})?", value):
            value += suffix.group(1)
            inherited = True
        result.append(_clock(value))
    if inherited and result != sorted(result):
        raise ValueError("Ambiguous shared AM/PM label")
    return list(dict.fromkeys(result))


def extract(html, source_url, retrieved_at=None):
    diag = {"adapter": "scullers_musicidb_html", "html_candidates": 0,
            "rejected_events": 0, "malformed_scripts": 0, "missing_show_time_events": 0,
            "notes": ["Only the bounded first public calendar page was collected."]}
    if not supported(source_url):
        diag["notes"].append("Source is not Scullers or its explicitly identified MusicIDB venue 715.")
        return [], diag
    result, seen = [], set()
    root = Tree(html).root
    for card in root.all(cls="listEvent"):
        if diag["html_candidates"] >= MAX_EVENTS:
            diag["notes"].append("Calendar event limit reached.")
            break
        diag["html_candidates"] += 1
        try:
            date_node = card.first(cls="date")
            if date_node is None:
                raise ValueError("Missing date")
            month = next((_text(node) for node in date_node.all(cls="monthName")
                          if not node.has("dayNameAbb")), "")
            date = dt.datetime.strptime(" ".join([month, _text(date_node.first(cls="dayNum")),
                                                  _text(date_node.first(cls="yearNum"))]), "%b %d %Y").date().isoformat()
            title = _text(card.first(cls="titleofevent"))
            link = card.first("a", "TicketLink")
            if link is None:
                raise ValueError("No public event URL")
            locations = [_text(node) for cls in ("eventVenue", "venueName") for node in card.all(cls=cls)
                         if _text(node)]
            venue_id = card.attrs.get("data-venue-id")
            if not locations and venue_id and venue_id != "715":
                locations = [venue_id]  # Preserve the exact unrecognized reported value.
            subtitle = _text(card.first(cls="subtitleEvent"))
            times = _show_times(subtitle)
            if not times:
                diag["missing_show_time_events"] += 1
            ages = _text(card.first(cls="eventLogistics"))
            genre = re.sub(r"^Genres:\s*", "", _text(card.first(cls="genresOnEvent")), flags=re.I)
            for clock in times or [""]:
                start = date + ("T" + clock if clock else "")
                event = _event(title, start, link.attrs.get("href"), source_url,
                               "Scullers Jazz Club", locations,
                               _text(card.first(cls="eventStatus")) or title,
                               ages=ages[:100], genre=genre[:100])
                if re.fullmatch(r"event-\d+", card.attrs.get("id", "")):
                    event["external_identity"] = "musicidb:" + card.attrs["id"] + "#" + start
                if event["external_identity"] not in seen:
                    seen.add(event["external_identity"])
                    result.append(event)
        except (ValueError, TypeError):
            diag["rejected_events"] += 1
    diag["missing_location_events"] = sum(not event["_reported_locations"] for event in result)
    return result, diag
