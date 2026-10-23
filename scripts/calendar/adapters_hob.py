"""Read House of Blues event/room data already embedded in public HTML.

Only JSON literals inside Next flight chunks are decoded. No JavaScript is
evaluated and no endpoint is called. Room attribution uses explicit event
venue_room metadata, never titles, upsells, page navigation, or the domain.
"""

import datetime as dt
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = []
        self.active = False
        self.current = []
        self.kind = ""

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = True
            self.current = []
            self.kind = dict(attrs).get("type", "").split(";", 1)[0].lower().strip()

    def handle_data(self, text):
        if self.active:
            self.current.append(text)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.scripts.append((self.kind, "".join(self.current)))
            self.active = False


def _nodes(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nodes(item)


def _event_nodes(value):
    if isinstance(value, dict):
        if "event_data_type" in value and "start_date_local" in value:
            yield value
            # Nested artists, presales and upsells are not separate shows.
            return
        for item in value.values():
            yield from _event_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _event_nodes(item)


def _normal(value):
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _reported_locations(item):
    venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
    room = item.get("venue_room") if isinstance(item.get("venue_room"), dict) else {}
    venue_names = [name.strip() for name in (item.get("venue_name"), venue.get("name"))
                   if isinstance(name, str) and name.strip()]
    room_names = [name.strip() for name in (item.get("venue_room_name"), room.get("name"))
                  if isinstance(name, str) and name.strip()]
    venue_names = list({_normal(name): name for name in venue_names}.values())
    room_names = list({_normal(name): name for name in room_names}.values())
    if not venue_names or not room_names:
        return [], "missing_explicit_venue_or_room"
    flat_id, nested_id = item.get("ln_venue_room_id"), room.get("id")
    if flat_id is not None and nested_id is not None and str(flat_id) != str(nested_id):
        return [], "conflicting_room_ids"
    locations = [venue_name + " - " + room_name for venue_name in venue_names for room_name in room_names]
    return locations[:2], "ambiguous_venue_or_room" if len(locations) > 1 else None


def _start(item):
    day = item.get("start_date_local")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("missing_or_invalid_explicit_date")
    day = dt.date.fromisoformat(day).isoformat()
    clock = item.get("start_time_local")
    if clock in (None, ""):
        clock = ""
    elif not isinstance(clock, str) or not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", clock):
        raise ValueError("invalid_explicit_time")
    else:
        clock = dt.time.fromisoformat(clock).strftime("%H:%M")
    raw = item.get("datetime_local")
    if isinstance(raw, str) and raw:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.date().isoformat() != day or (clock and parsed.strftime("%H:%M") != clock):
            raise ValueError("conflicting_local_datetime")
    else:
        raw = day + ("T" + clock if clock else "")
    return day, clock, raw


def extract(html, source_url, retrieved_at=None):
    diagnostics = {
        "adapter": "house_of_blues_flight_v1", "scripts": 0,
        "malformed_scripts": 0, "rejected_events": 0,
        "flight_chunks": 0, "event_objects": 0, "parsed_events": 0,
        "missing_location_events": 0, "room_diagnostic_reasons": {},
        "rejection_reasons": {}, "coverage": "fetched_page_only",
        "coverage_note": "Only event objects embedded in this response were read; completeness and later refreshes are unverified.",
        "page_title": "House of Blues Boston — Shows", "retrieved_at": retrieved_at,
    }
    target = urlsplit(source_url)
    if target.scheme != "https" or target.hostname != "boston.houseofblues.com":
        diagnostics["unsupported_source"] = True
        return [], diagnostics
    parser = _Scripts()
    parser.feed(html)
    parser.close()
    chunks, jsonld_status = [], {}
    for kind, script in parser.scripts:
        if kind == "application/ld+json":
            diagnostics["scripts"] += 1
            try:
                for item in _nodes(json.loads(script)):
                    url, status = item.get("url"), item.get("eventStatus")
                    if isinstance(url, str) and isinstance(status, str):
                        jsonld_status[url] = status.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            except (ValueError, TypeError, RecursionError):
                diagnostics["malformed_scripts"] += 1
        elif "self.__next_f.push" in script:
            match = re.fullmatch(r"\s*self\.__next_f\.push\((\[.*\])\)\s*;?\s*", script, re.S)
            if not match:
                continue
            try:
                payload = json.loads(match[1])
                if isinstance(payload, list) and len(payload) >= 2 and payload[0] == 1 and isinstance(payload[1], str):
                    chunks.append(payload[1])
            except (ValueError, TypeError, RecursionError):
                diagnostics["malformed_scripts"] += 1
    diagnostics["flight_chunks"] = len(chunks)
    candidates = []
    for record in "".join(chunks).splitlines():
        key, separator, value = record.partition(":")
        if not separator or not re.fullmatch(r"[0-9a-f]+", key, re.I) or not value.startswith(("[", "{")):
            continue  # Flight module references and other records are not JSON data.
        try:
            candidates.extend(_event_nodes(json.loads(value)))
        except (ValueError, TypeError, RecursionError):
            diagnostics["malformed_scripts"] += 1
    diagnostics["event_objects"] = len(candidates)
    events, seen = [], set()
    for item in candidates:
        try:
            title = item.get("name")
            identity = item.get("tm_id")
            if not isinstance(title, str) or not title.strip() or len(title) > 500:
                raise ValueError("missing_or_invalid_title")
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identity):
                raise ValueError("missing_or_invalid_provider_identity")
            url = item.get("url")
            parsed_url = urlsplit(url) if isinstance(url, str) else None
            if not parsed_url or parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password or len(url) > 2048:
                raise ValueError("invalid_event_url")
            day, clock, raw = _start(item)
            locations, location_reason = _reported_locations(item)
            if location_reason:
                reasons = diagnostics["room_diagnostic_reasons"]
                reasons[location_reason] = reasons.get(location_reason, 0) + 1
            if not locations:
                diagnostics["missing_location_events"] += 1
            code = str(item.get("status_code", "")).casefold()
            status = {"canceled": "EventCancelled", "cancelled": "EventCancelled",
                      "postponed": "EventPostponed", "rescheduled": "EventRescheduled",
                      "onsale": "EventScheduled"}.get(code, jsonld_status.get(url, "EventStatusUnknown"))
            if identity in seen:
                continue
            seen.add(identity)
            events.append({
                "date": day, "time": clock, "doors_time": "",
                "venue": locations[0] if len(locations) == 1 else "House of Blues Boston",
                "artists": title.strip(), "url": url, "source_url": source_url,
                "external_identity": "ticketmaster:event:" + identity,
                "start_date_raw": raw, "reported_status": status,
                "genre": item.get("genre") if isinstance(item.get("genre"), str) else "",
                "ticket_status": code, "_reported_locations": locations,
            })
        except (ValueError, TypeError) as exc:
            diagnostics["rejected_events"] += 1
            reason = str(exc)
            reasons = diagnostics["rejection_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
    diagnostics["parsed_events"] = len(events)
    if events:
        diagnostics["earliest_date"] = min(e["date"] for e in events)
        diagnostics["latest_date"] = max(e["date"] for e in events)
    return events, diagnostics
