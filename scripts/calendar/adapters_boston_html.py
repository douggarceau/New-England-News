"""Bounded, read-only parsers for the public Boston venue calendar snapshots.

Only standard-library parsing is used. JavaScript is treated as data, never run.
Location evidence is returned separately for core's trusted source policy to apply.
"""

import datetime as dt
import html as html_module
import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MAX_EVENTS = 1000
HOSTS = {"berklee.edu", "www.berklee.edu", "passim.org", "www.passim.org",
         "thewilbur.com", "www.thewilbur.com", "bso.org", "www.bso.org"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def has(self, value):
        return value in self.attrs.get("class", "").split()

    def all(self, tag=None, cls=None):
        pending = list(reversed(self.children))
        while pending:
            item = pending.pop()
            if isinstance(item, Node):
                if (tag is None or item.tag == tag) and (cls is None or item.has(cls)):
                    yield item
                pending.extend(reversed(item.children))

    def first(self, tag=None, cls=None):
        return next(self.all(tag, cls), None)

    def text(self):
        parts, pending = [], list(reversed(self.children))
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                parts.append(item)
            elif item.tag not in {"script", "style"}:
                pending.extend(reversed(item.children))
        return re.sub(r"\s+", " ", " ".join(parts)).strip()


class Tree(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(content)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _text(node):
    return node.text() if node is not None else ""


def _clean(value):
    return Tree(str(value or "")).root.text()


def _status(value):
    value = _clean(value).strip().casefold()
    if re.match(r"^(?:eventcancelled|eventcanceled|cancelled|canceled|cancelation|cancellation)\b", value):
        return "EventCancelled"
    if re.match(r"^(?:eventpostponed|postponed)\b", value):
        return "EventPostponed"
    return "EventScheduled"


def _clock(value):
    value = str(value).replace(".", "").strip()
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AP]M)", value, re.I)
    if not match:
        raise ValueError("Missing explicit show time")
    hour, minute, period = match.groups()
    hour, minute = int(hour), int(minute or 0)
    if not 1 <= hour <= 12 or not 0 <= minute < 60:
        raise ValueError("Invalid show time")
    return "%02d:%02d" % ((hour % 12) + (12 if period.upper() == "PM" else 0), minute)


def _event(name, start, url, source_url, venue, locations, status="", **extra):
    name = _clean(name)
    if not name or len(name) > 500 or not isinstance(start, str):
        raise ValueError("Invalid event title or date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?", start):
        raise ValueError("Missing explicit ISO year/date")
    if "T" in start:
        parsed = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        date, clock = parsed.date().isoformat(), parsed.strftime("%H:%M")
    else:
        date, clock = dt.date.fromisoformat(start).isoformat(), ""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Missing event URL")
    url = urljoin(source_url, html_module.unescape(url))
    if urlsplit(url).scheme not in {"http", "https"} or len(url) > 2048:
        raise ValueError("Invalid event URL")
    locations = list(dict.fromkeys(_clean(x) for x in locations if _clean(x)))[:2]
    result = {"date": date, "time": clock, "venue": venue, "artists": name,
              "url": url, "source_url": source_url,
              "external_identity": "html:" + url + "#" + date + ("T" + clock if clock else ""),
              "start_date_raw": start, "reported_status": _status(status),
              "_reported_locations": locations}
    result.update({key: value for key, value in extra.items() if value})
    return result


def supported(host_or_url):
    host = urlsplit(host_or_url).hostname if "://" in host_or_url else host_or_url
    return str(host).lower().rstrip(".") in HOSTS


def _berklee(root, source_url, diag):
    result = []
    for card in root.all(cls="event"):
        if not card.has("teaser"):
            continue
        diag["html_candidates"] += 1
        title = card.first(cls="title")
        link = title.first("a") if title else None
        locations = [_text(x) for x in card.all(cls="field--name-field-event-venue-title")]
        # Each instance has a start in col1; a second time in col2 is an end time.
        starts = []
        instances = list(card.all(cls="paragraph--type--event-instance"))
        for instance in instances or [card]:
            first_col = instance.first(cls="col1")
            stamp = (first_col or instance).first("time")
            if stamp is not None:
                starts.append(stamp.attrs.get("datetime", ""))
        if not starts:
            diag["rejected_events"] += 1
        for start in starts:
            try:
                result.append(_event(_text(title), start, link.attrs.get("href") if link else "",
                                     source_url, "Berklee Performance Center", locations,
                                     _text(card.first(cls="event-status")) or _text(title)))
            except ValueError:
                diag["rejected_events"] += 1
    return result


def _wilbur(root, source_url, diag):
    result = []
    venue_ids = {}
    for card in root.all(cls="event-item"):
        name = card.first(cls="event-title")
        if name is not None:
            venue_ids[name.attrs.get("data-event-id", "")] = card.attrs.get("data-venue-id", "")
    for modal in root.all(cls="event-modal"):
        title = _text(modal.first(cls="modal-event-name"))
        info = modal.first("a", "modal-show-info")
        identifier = modal.attrs.get("id", "").removeprefix("event-modal-")
        locations = [_text(x) for x in modal.all(cls="modal-event-venue")]
        # An unexpected numeric venue is evidence against the venue-specific fallback.
        if not locations and venue_ids.get(identifier) not in (None, "", "1"):
            locations = [venue_ids[identifier]]  # Exact reported value; not a guessed room name.
        for row in modal.all(cls="modal-ticket-row"):
            diag["html_candidates"] += 1
            try:
                date = row.attrs.get("data-date", "")
                label = _text(row.first(cls="modal-ticket-when"))
                match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\s+at\s+(.+)", label)
                if not match:
                    raise ValueError("Unknown performance date format")
                printed = dt.datetime.strptime(" ".join(match.groups()[:3]), "%b %d %Y").date().isoformat()
                if printed != date:
                    raise ValueError("Conflicting performance dates")
                start = date + "T" + _clock(match.group(4))
                result.append(_event(title, start, info.attrs.get("href") if info else "",
                                     source_url, "Wilbur Theatre", locations,
                                     _text(row.first(cls="event-status")) or title))
            except ValueError:
                diag["rejected_events"] += 1
    return result


def _balanced(text, offset, opening="{", closing="}"):
    """Return one bracketed JS data literal, respecting quoted strings."""
    depth, quote, escaped = 0, None, False
    for index in range(offset, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[offset:index + 1], index + 1
    raise ValueError("Unterminated calendar literal")


def _calendar_objects(script):
    """Read only the first embedded FullCalendar array (subsequent arrays repeat it)."""
    match = re.search(r"\bevents\s*:\s*\[", script)
    if not match:
        return []
    literal, _ = _balanced(script, match.end() - 1, "[", "]")
    result, index = [], 1
    pair = re.compile(r'\b(\w+)\s*:\s*("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')')
    while index < len(literal) - 1 and len(result) < MAX_EVENTS:
        if literal[index] != "{":
            index += 1
            continue
        item, index = _balanced(literal, index)
        record = {}
        for field in pair.finditer(item):
            key, value = field.groups()
            if value.startswith('"'):
                try:
                    record[key] = json.loads(value)
                except ValueError:
                    pass
            elif key == "ticketButton":
                record[key] = value[1:-1].replace("\\'", "'").replace("\\/", "/")
        if record:
            result.append(record)
    return result


def _passim_locations(record):
    """Accept literal venue assertions, never infer a room from an opaque ID."""
    locations = []
    venue = record.get("venue_name") or record.get("location")
    if isinstance(venue, str) and venue.strip():
        locations.append(_clean(venue))
    venue = record.get("venue")
    if isinstance(venue, str) and " " in venue:
        locations.append(_clean(venue))
    for key in ("title", "detail"):
        text = _clean(record.get(key))
        match = re.search(r"\bat\s+((?:Club Passim|Passim|Crystal Ballroom|Arrow Street Arts|"
                          r"The Armory|Arts at the Armory|First Parish(?: in)? Cambridge))\b", text, re.I)
        if match:
            locations.append(match.group(1))
        elif re.search(r'\bat\s+', text, re.I):
            # Preserve unexpected named destinations for review, rather than
            # silently assuming that every promoter listing is at the club.
            other = re.search(r'\bat\s+(.+)', text, re.I)
            locations.append(other.group(1).strip()[:300])
    content = _clean(record.get("content"))
    # A direct location sentence has priority over biographical venue mentions.
    match = re.search(r"\b(?:This event|This show|This concert|This performance)\s+"
                      r"(?:takes place|will take place|is being held|will be held)\s+at\s+([^.;]+)", content, re.I)
    if match:
        locations.append(match.group(1).strip())
    return list(dict.fromkeys(locations))[:2]


def _passim(root, source_url, diag):
    # The venue's own Club Calendar declares its scope. Keep this separate
    # from an explicit per-event location, and never map opaque venue IDs.
    title_node = root.first('title')
    club_scope = (urlsplit(source_url).hostname in {'www.passim.org', 'passim.org'}
                  and urlsplit(source_url).path == '/live-music/'
                  and 'Club Passim' in _text(title_node)
                  and any(_text(a) == 'Club Calendar' and
                          urlsplit(urljoin(source_url, a.attrs.get('href', ''))).path == '/live-music/'
                          for a in root.all('a')))
    records, remaining, calendar = [], [], []
    for script in root.all("script"):
        text = "".join(x for x in script.children if isinstance(x, str))
        rem = re.search(r"\bvar\s+remEvents\s*=\s*", text)
        if rem:
            try:
                obj, _ = json.JSONDecoder().raw_decode(text[rem.end():])
                if isinstance(obj, dict):
                    remaining.extend(x for x in obj.values() if isinstance(x, dict))
            except (ValueError, TypeError, RecursionError):
                diag["malformed_scripts"] += 1
        if not calendar and "fullCalendar" in text:
            try:
                calendar = _calendar_objects(text)
            except ValueError:
                diag["malformed_scripts"] += 1
    records.extend(remaining)
    # The first displayed records are absent from remEvents but present in calendar.
    records.extend(calendar)
    result, seen = [], set()
    for record in records[:MAX_EVENTS * 2]:
        diag["html_candidates"] += 1
        try:
            title = _clean(record.get("title"))
            if title.casefold() in {"club closed", "closed"}:
                diag["non_event_records"] += 1
                continue
            if record.get("date_and_time"):
                parsed = dt.datetime.strptime(record["date_and_time"].strip(), "%m/%d/%Y %I:%M %p")
                start = parsed.isoformat(timespec="minutes")
                url = record.get("permalink")
            else:
                date = dt.date.fromisoformat(record.get("date", "")).isoformat()
                start = date + "T" + _clock(record.get("showtime", ""))
                url = record.get("link")
            identity = (url, start)
            if identity in seen:
                continue
            seen.add(identity)
            locations = _passim_locations(record)
            status = record.get("sale_status") or record.get("override_label") or title
            price = ("$" + str(record["cost"]) + str(record.get("cost_member", ""))) if record.get("cost") else ""
            genre = ", ".join(record.get("cats", {}).values()) if isinstance(record.get("cats"), dict) else record.get("categories", "")
            event = _event(title, start, url, source_url, "Club Passim", locations, status,
                           price=_clean(price)[:300], genre=_clean(genre)[:100])
            if not locations and club_scope:
                event['_calendar_location'] = 'Club Passim'
                event['location_evidence'] = 'official_club_calendar_default; not event-specific confirmation'
            elif locations:
                event['location_evidence'] = 'explicit_event_location'
            doors = record.get('doors_open_string') or record.get('doors')
            if isinstance(doors, str):
                try:
                    event['doors_time'] = _clock(doors)
                except ValueError:
                    pass
            result.append(event)
        except (ValueError, TypeError):
            diag["rejected_events"] += 1
    diag["notes"].append("Explicit offsite locations override the official Club Calendar's venue scope. Calendar-default assignments are labeled and remain for review; opaque venue IDs are never mapped.")
    return result


def parse_bso_json(data, source_url, retrieved_at=None):
    """Parse one bounded Typesense calendar response, including primary-room evidence.

    The official calendar renders performance_date in America/New_York. A parent
    building in performance_venue does not override an explicitly named main room.
    """
    diag = {"adapter": "bso_public_performances", "html_candidates": 0,
            "rejected_events": 0, "malformed_scripts": 0, "notes": []}
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            diag["malformed_scripts"] = 1
            return [], diag
    if not isinstance(data, dict) or not isinstance(data.get("hits"), list):
        diag["notes"].append("No performance hits in the public calendar response.")
        return [], diag
    hits = data["hits"]
    diag["available_hits"] = data.get("found")
    diag["received_hits"] = len(hits)
    if isinstance(data.get("found"), int) and data["found"] > len(hits):
        diag["notes"].append("Only the bounded first response page was collected; additional performances exist.")
    result, seen = [], set()
    for hit in hits[:MAX_EVENTS]:
        diag["html_candidates"] += 1
        try:
            item = hit.get("document", {})
            if not isinstance(item, dict):
                raise ValueError("Invalid performance record")
            stamp = item.get("performance_date")
            if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
                raise ValueError("Invalid performance timestamp")
            try:
                parsed = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).astimezone(ZoneInfo("America/New_York"))
                start = parsed.isoformat(timespec="seconds")
            except ZoneInfoNotFoundError:
                # The public performance URL carries an explicit local date/time.
                value = parse_qs(urlsplit(item.get("performance_link", "")).query).get("performance", [""])[0]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{2}:\d{2}", value):
                    raise ValueError("Timezone unavailable and local performance time missing")
                start = value[:10] + "T" + value[11:]
            places = item.get("performance_venue", [])
            if not isinstance(places, list):
                places = []
            named = [place for place in places if isinstance(place, dict)]
            primary = [place for place in named if place.get("main_venue") is True]
            locations = [place["name"] for place in (primary or named)
                         if isinstance(place.get("name"), str) and place["name"].strip()]
            status = ""
            for value in item.get("event_status", []) if isinstance(item.get("event_status"), list) else []:
                title = value.get("title", "") if isinstance(value, dict) else str(value)
                if _status(title) != "EventScheduled":
                    status = title
                    break
            url = item.get("performance_link") or item.get("event_link")
            event = _event(item.get("title"), start, url, source_url, "Symphony Hall", locations, status)
            if event["external_identity"] not in seen:
                seen.add(event["external_identity"])
                result.append(event)
        except (ValueError, TypeError, OverflowError, OSError, AttributeError):
            diag["rejected_events"] += 1
    diag["missing_location_events"] = sum(not event["_reported_locations"] for event in result)
    return result, diag


def extract(html, source_url, retrieved_at=None):
    """Return core-compatible observations and diagnostics; never make requests."""
    host = (urlsplit(source_url).hostname or "").lower()
    diag = {"adapter": "boston_html", "html_candidates": 0, "rejected_events": 0,
            "malformed_scripts": 0, "non_event_records": 0, "notes": []}
    if host not in HOSTS:
        diag["notes"].append("Unsupported hostname for this adapter.")
        return [], diag
    root = Tree(html).root
    if host.endswith("berklee.edu"):
        diag["adapter"] = "berklee_html"
        events = _berklee(root, source_url, diag)
    elif host.endswith("thewilbur.com"):
        diag["adapter"] = "wilbur_html"
        events = _wilbur(root, source_url, diag)
    elif host.endswith("passim.org"):
        diag["adapter"] = "passim_embedded_calendar"
        events = _passim(root, source_url, diag)
    else:
        diag["adapter"] = "bso_calendar_shell"
        diag["notes"].append("BSO calendar HTML requires its public Typesense performance feed; no dates inferred from the shell.")
        events = []
    deduped = {}
    for event in events:
        deduped.setdefault(event["external_identity"], event)
        if len(deduped) >= MAX_EVENTS:
            diag["notes"].append("Bounded calendar event limit reached.")
            break
    events = list(deduped.values())
    diag["missing_location_events"] = sum(not event["_reported_locations"] for event in events)
    return events, diag
