"""Read factual events from bounded, already-downloaded public calendar feeds.

No requests or AI calls occur here. Provider IDs, explicit venue/room labels,
show and doors times survive independently. Pagination is reported, not fetched.
"""

import datetime as dt
import json
import re
from html import unescape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _text(value):
    return re.sub(r"\s+", " ", unescape(value)).strip() if isinstance(value, str) else ""


def _url(value):
    value = _text(value)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("missing_or_invalid_https_event_url")
    return value


def _identity(value):
    if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
        return str(value).strip()
    raise ValueError("missing_provider_identity")


def _diagnostics(adapter, retrieved_at):
    return {
        "adapter": adapter, "scripts": 0, "malformed_scripts": 0,
        "event_objects": 0, "parsed_events": 0, "rejected_events": 0,
        "missing_location_events": 0, "rejection_reasons": {},
        "coverage": "fetched_feed_only", "retrieved_at": retrieved_at,
        "coverage_note": "Only this downloaded response was parsed; complete venue-calendar coverage is unverified.",
    }


def _reject(report, reason):
    report["rejected_events"] += 1
    reasons = report["rejection_reasons"]
    reasons[reason] = reasons.get(reason, 0) + 1


def _finish(events, report):
    report["parsed_events"] = len(events)
    report["missing_location_events"] = sum(not e["_reported_locations"] for e in events)
    if events:
        report["earliest_date"] = min(e["date"] for e in events)
        report["latest_date"] = max(e["date"] for e in events)
    return events, report


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("missing_or_invalid_explicit_date")
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("missing_or_invalid_explicit_date") from None


def _clock(value):
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", value):
        raise ValueError("invalid_explicit_time")
    try:
        return dt.time.fromisoformat(value).strftime("%H:%M")
    except ValueError:
        raise ValueError("invalid_explicit_time") from None


def _local_raw(day, clock, timezone):
    if not clock:
        return day
    stamp = dt.datetime.fromisoformat(day + "T" + clock)
    if timezone:
        try:
            stamp = stamp.replace(tzinfo=ZoneInfo(timezone))
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown_explicit_timezone") from None
    return stamp.isoformat(timespec="seconds")


def _event(title, day, clock, raw, venue_names, identity, url, source_url, status, timezone="", doors="", ticket_status=""):
    title = _text(title)
    if not title:
        raise ValueError("missing_event_title")
    names = list(dict.fromkeys(_text(n) for n in venue_names if _text(n)))
    return {
        "date": day, "time": clock, "doors_time": doors,
        "artists": title, "venue": names[0] if len(names) == 1 else "Unverified venue",
        "url": _url(url), "source_url": source_url,
        "external_identity": identity, "start_date_raw": raw,
        "reported_status": status, "ticket_status": ticket_status,
        "timezone": timezone, "_reported_locations": names,
    }


def _ical_unescape(value):
    return re.sub(r"\\([nN,;\\])", lambda m: "\n" if m[1] in "nN" else m[1], value)


def _ical_start(value, params, calendar_timezone):
    if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", value):
        try:
            day = dt.datetime.strptime(value, "%Y%m%d").date().isoformat()
        except ValueError:
            raise ValueError("missing_or_invalid_explicit_date") from None
        return day, "", day, ""
    if not re.fullmatch(r"\d{8}T\d{6}Z?", value):
        raise ValueError("missing_or_invalid_explicit_datetime")
    timezone = params.get("TZID", calendar_timezone)
    try:
        stamp = dt.datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
        if value.endswith("Z"):
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
            if timezone:
                stamp = stamp.astimezone(ZoneInfo(timezone))
            else:
                timezone = "UTC"
        elif timezone:
            stamp = stamp.replace(tzinfo=ZoneInfo(timezone))
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError("invalid_explicit_datetime_or_timezone") from None
    return stamp.date().isoformat(), stamp.strftime("%H:%M"), stamp.isoformat(timespec="seconds"), timezone


def _ical_location(location):
    location = _text(location)
    # These mappings use explicit source room names AND Boston venue identity.
    if re.match(r"^Main Stage\s*,\s*City Winery Boston(?:\s*,|$)", location, re.I):
        return ["City Winery Boston Main Stage"]
    if re.match(r"^Haymarket Lounge at City Winery Boston(?:\s*,|$)", location, re.I):
        return ["City Winery Haymarket Lounge"]
    if not location or re.match(r"^City Winery Boston(?:\s*,|$)", location, re.I):
        return []  # Generic venue/address does not establish a particular room.
    return [location]  # Preserve other explicit rooms for the caller's policy.


def parse_ical(text, source_url, retrieved_at=None):
    """Parse VEVENT observations; do not synthesize recurring occurrences."""
    report = _diagnostics("ical_explicit_rooms_v1", retrieved_at)
    report["pagination"] = "No pagination metadata in this iCalendar response."
    report["unexpanded_recurrence_events"] = 0
    unfolded = re.sub(r"\r?\n[ \t]", "", text)
    blocks, current, calendar_timezone = [], None, ""
    depth = 0
    for line in unfolded.splitlines():
        if line.upper() == "BEGIN:VEVENT":
            current, depth = {}, 0
            continue
        if current is not None and line.upper() == "END:VEVENT":
            blocks.append(current)
            current = None
            continue
        if current is not None and line.upper().startswith("BEGIN:"):
            depth += 1
            continue
        if current is not None and line.upper().startswith("END:"):
            depth = max(0, depth - 1)
            continue
        if depth:
            continue  # Alarm descriptions/times are not event fields.
        left, sep, value = line.partition(":")
        if not sep:
            continue
        segments = left.split(";")
        name, params = segments[0].upper(), {}
        for part in segments[1:]:
            key, equal, parameter = part.partition("=")
            if equal:
                params[key.upper()] = parameter.strip('"')
        if current is None and name == "X-WR-TIMEZONE":
            calendar_timezone = value.strip()
        elif current is not None:
            current.setdefault(name, []).append((params, value))
    if current is not None:
        report["truncated_event_block"] = True
    if "BEGIN:VCALENDAR" not in text.upper():
        report["malformed_feed"] = True
    report["event_objects"] = len(blocks)
    events = []
    for item in blocks:
        try:
            if "RRULE" in item or "RDATE" in item:
                report["unexpanded_recurrence_events"] += 1
                raise ValueError("recurrence_rule_requires_review")
            if len(item.get("DTSTART", [])) != 1:
                raise ValueError("missing_or_ambiguous_start_date")
            def value(name):
                return _ical_unescape(item.get(name, [({}, "")])[0][1])
            uid = _identity(value("UID"))
            identity = "ical:uid:" + uid
            if value("RECURRENCE-ID"):
                identity += ":instance:" + value("RECURRENCE-ID")
            params, raw_start = item["DTSTART"][0]
            day, clock, raw, timezone = _ical_start(raw_start, params, calendar_timezone)
            raw_status = value("STATUS").upper()
            status = {"CONFIRMED": "EventScheduled", "CANCELLED": "EventCancelled"}.get(raw_status, "EventStatusUnknown")
            event = _event(value("SUMMARY"), day, clock, raw, _ical_location(value("LOCATION")),
                           identity, value("URL"), source_url, status, timezone)
            events.append(event)
        except (ValueError, TypeError, AttributeError) as exc:
            _reject(report, str(exc) if isinstance(exc, ValueError) else "malformed_event_object")
    if len(blocks) >= 100:
        report["possible_response_cap"] = True
        report["coverage_note"] += " The response contains at least 100 events and may be capped."
    return _finish(events, report)


def _load_json(text, report):
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, TypeError, RecursionError):
        report["malformed_feed"] = True
        return {}


def parse_axs(text, source_url, retrieved_at=None):
    """Read explicit AXS event records from one public venue-feed response."""
    report = _diagnostics("axs_venue_feed_v1", retrieved_at)
    data = _load_json(text, report)
    candidates = data.get("events", [])
    if not isinstance(candidates, list):
        report["malformed_feed"] = True
        candidates = []
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    report["pagination"] = {key: meta[key] for key in ("page", "rows", "total") if key in meta}
    total = meta.get("total")
    report["response_matches_reported_total"] = isinstance(total, int) and len(candidates) == total
    report["additional_dates_unexpanded"] = 0
    report["event_objects"] = len(candidates)
    events = []
    for item in candidates:
        try:
            if not isinstance(item, dict):
                raise ValueError("malformed_event_object")
            if item.get("private") is True:
                raise ValueError("private_event_requires_review")
            identity = "axs:event:" + _identity(item.get("eventId"))
            raw = item.get("eventDateTimeISO")
            if not isinstance(raw, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
                raise ValueError("missing_explicit_iso_datetime")
            stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
            timezone = _text(item.get("eventDateTimeZone")) or _text(venue.get("timezone"))
            if stamp.tzinfo is None:
                raise ValueError("missing_explicit_iso_offset")
            if timezone:
                try:
                    local = stamp.astimezone(ZoneInfo(timezone))
                except (ZoneInfoNotFoundError, ValueError):
                    raise ValueError("unknown_explicit_timezone") from None
                if local.replace(tzinfo=None) != stamp.replace(tzinfo=None):
                    raise ValueError("conflicting_iso_offset_and_timezone")
            doors = ""
            if item.get("doorDateTime"):
                doors_stamp = dt.datetime.fromisoformat(item["doorDateTime"].replace("Z", "+00:00"))
                doors = doors_stamp.strftime("%H:%M")
            title = item.get("title") if isinstance(item.get("title"), dict) else {}
            ticket = item.get("ticketing") if isinstance(item.get("ticketing"), dict) else {}
            ticket_status = _text(ticket.get("status"))
            status = {"cancelled": "EventCancelled", "canceled": "EventCancelled", "postponed": "EventPostponed", "rescheduled": "EventRescheduled"}.get(ticket_status.casefold(), "EventScheduled")
            event = _event(title.get("eventTitleText"), stamp.date().isoformat(), stamp.strftime("%H:%M"), raw,
                           [venue.get("title")], identity, ticket.get("eventUrl") or ticket.get("url"), source_url,
                           status, timezone, doors, ticket_status)
            event["ages"] = _text(item.get("age"))
            if item.get("additionalDates"):
                report["additional_dates_unexpanded"] += 1
            events.append(event)
        except (ValueError, TypeError, AttributeError) as exc:
            _reject(report, str(exc) if isinstance(exc, ValueError) else "malformed_event_object")
    return _finish(events, report)


def _ticket_lines(item):
    value = item.get("ticketTextLines", {})
    if not isinstance(value, dict):
        return ""
    return " ".join(str(line) for language in value.values() if isinstance(language, dict) for line in language.values() if isinstance(line, str))


def _labelled_time(texts, label):
    # Both "SHOW: 8:00 PM" and the printed ticket's "DRS 700PM" are explicit.
    marker = r"(?:doors?|drs)" if label == "doors" else r"show"
    pattern = r"\b" + marker + r"(?:\s*time)?\s*:?\s*(\d{1,4}(?::\d{2})?)\s*([ap])\.?m\.?\b"
    for text in texts:
        times = []
        for match in re.finditer(pattern, text, re.I):
            token, period = match.groups()
            if ":" in token:
                hour, minute = map(int, token.split(":"))
            elif len(token) > 2:
                hour, minute = int(token[:-2]), int(token[-2:])
            else:
                hour, minute = int(token), 0
            if not 1 <= hour <= 12 or not 0 <= minute <= 59:
                continue
            value = "%02d:%02d" % ((hour % 12) + (12 if period.lower() == "p" else 0), minute)
            if value not in times:
                times.append(value)
        if len(times) > 1:
            raise ValueError("conflicting_explicit_" + label + "_times")
        if times:
            return times[0]
    return ""


def parse_ticketmaster(text, source_url, retrieved_at=None):
    """Read only top-level Discovery events, excluding nested add-on products."""
    report = _diagnostics("ticketmaster_discovery_v1", retrieved_at)
    data = _load_json(text, report)
    embedded = data.get("_embedded") if isinstance(data.get("_embedded"), dict) else {}
    candidates = embedded.get("events", [])
    if not isinstance(candidates, list):
        candidates = []
        report["malformed_feed"] = True
    page = data.get("page") if isinstance(data.get("page"), dict) else {}
    report["pagination"] = {key: page[key] for key in ("size", "totalElements", "totalPages", "number") if key in page}
    links = data.get("_links") if isinstance(data.get("_links"), dict) else {}
    report["more_pages_reported"] = bool(links.get("next")) or (isinstance(page.get("totalPages"), int) and page["totalPages"] > (page.get("number", 0) + 1))
    report["explicit_show_times"] = 0
    report["event_objects"] = len(candidates)
    events = []
    for item in candidates:
        try:
            if not isinstance(item, dict):
                raise ValueError("malformed_event_object")
            if item.get("test") is True:
                raise ValueError("test_event")
            if item.get("type", "event") != "event":
                raise ValueError("non_event_product")
            if _text(item.get("name")).casefold() == "wilbur theatre gift certificate":
                raise ValueError("non_event_product")
            identity = "ticketmaster:discovery:" + _identity(item.get("id"))
            dates = item.get("dates") if isinstance(item.get("dates"), dict) else {}
            start = dates.get("start") if isinstance(dates.get("start"), dict) else {}
            end = dates.get("end") if isinstance(dates.get("end"), dict) else {}
            notes = [_text(item.get("info")), _text(item.get("pleaseNote")), _ticket_lines(item)]
            bundle_text = " ".join([_text(item.get("name"))] + notes)
            if end.get("localDate") and end.get("localDate") != start.get("localDate") and re.search(r"\b(?:two|2)[ -]day\s+(?:ticket|pass)\b", bundle_text, re.I):
                raise ValueError("multi_day_ticket_bundle_requires_review")
            if start.get("dateTBD") or start.get("dateTBA"):
                raise ValueError("date_to_be_announced")
            day = _day(start.get("localDate"))
            timezone = _text(dates.get("timezone"))
            doors, show, clock = "", "", ""
            if not start.get("timeTBA") and not start.get("noSpecificTime"):
                doors = _labelled_time(notes, "doors")
                show = _labelled_time(notes, "show")
                advertised = _clock(start.get("localTime"))
                # A time explicitly labelled doors must never become the show time.
                clock = show or (advertised if not doors or advertised != doors else "")
            raw = _local_raw(day, clock, timezone)
            event_embedded = item.get("_embedded") if isinstance(item.get("_embedded"), dict) else {}
            venues = event_embedded.get("venues", [])
            names = [v.get("name") for v in venues if isinstance(v, dict)] if isinstance(venues, list) else []
            status_obj = dates.get("status") if isinstance(dates.get("status"), dict) else {}
            ticket_status = _text(status_obj.get("code"))
            status = {"onsale": "EventScheduled", "cancelled": "EventCancelled", "canceled": "EventCancelled", "rescheduled": "EventRescheduled", "postponed": "EventPostponed"}.get(ticket_status.casefold(), "EventStatusUnknown")
            event = _event(item.get("name"), day, clock, raw, names, identity,
                           item.get("url"), source_url, status, timezone, doors, ticket_status)
            if show:
                report["explicit_show_times"] += 1
            events.append(event)
        except (ValueError, TypeError, AttributeError) as exc:
            _reject(report, str(exc) if isinstance(exc, ValueError) else "malformed_event_object")
    return _finish(events, report)
