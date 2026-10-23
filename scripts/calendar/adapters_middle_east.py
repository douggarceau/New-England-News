"""Offline reader for the Middle East's public TicketWeb event-list cards.

No page or ticket link is fetched here. Full calendar dates and room labels
must come from their own fields in each card; titles never establish a room.
The caller must apply core's explicit-location policy before saving events.
"""

import datetime as dt
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit


_HOSTS = {"www.mideastclub.com", "mideastclub.com", "www.mideastoffers.com", "mideastoffers.com"}
_TICKET_HOSTS = {"www.ticketweb.com", "ticketweb.com"}
_MONTHS = {}
for _number, _name in enumerate(("january", "february", "march", "april", "may", "june",
                                "july", "august", "september", "october", "november", "december"), 1):
    _MONTHS[_name] = _MONTHS[_name[:3]] = _number


class _Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def has_class(self, value):
        return value in self.attrs.get("class", "").split()

    def descendants(self, tag=None, class_name=None):
        stack = list(reversed(self.children))
        while stack:
            child = stack.pop()
            if isinstance(child, _Node):
                if (tag is None or child.tag == tag) and (class_name is None or child.has_class(class_name)):
                    yield child
                stack.extend(reversed(child.children))

    def text(self):
        parts, stack = [], list(reversed(self.children))
        while stack:
            child = stack.pop()
            if isinstance(child, _Node):
                if child.tag not in {"script", "style"}:
                    stack.extend(reversed(child.children))
            else:
                parts.append(child)
        return re.sub(r"\s+", " ", " ".join(parts)).strip()


class _Tree(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, value):
        if self.stack[-1].tag not in {"script", "style"}:
            self.stack[-1].children.append(value)


def _first(node, class_name=None, tag=None):
    return next(node.descendants(tag, class_name), None)


def _field(card, class_name):
    node = _first(card, class_name)
    return node.text() if node is not None else ""


def _date(value):
    match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", value)
    if not match or match[1].casefold() not in _MONTHS:
        raise ValueError("missing_or_invalid_explicit_date")
    try:
        return dt.date(int(match[3]), _MONTHS[match[1].casefold()], int(match[2])).isoformat()
    except ValueError as exc:
        raise ValueError("invalid_calendar_date") from exc


def _time(value):
    if not value:
        return ""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)", value, re.I)
    if not match:
        raise ValueError("invalid_explicit_time")
    hour, minute, second = int(match[1]), int(match[2]), int(match[3] or "0")
    if not 1 <= hour <= 12 or not 0 <= minute <= 59 or not 0 <= second <= 59:
        raise ValueError("invalid_explicit_time")
    hour = hour % 12 + (12 if match[4].upper() == "PM" else 0)
    return "%02d:%02d" % (hour, minute)


def _url(value, base, hosts):
    if not isinstance(value, str) or not value.strip():
        return ""
    value = urljoin(base, value.strip())
    try:
        parsed = urlsplit(value)
        if (len(value) > 2048 or parsed.scheme != "https" or parsed.hostname not in hosts
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)):
            return ""
    except ValueError:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def extract(html, source_url, retrieved_at=None):
    """Return (events, diagnostics) from this page only; no network or clock use.

    Missing/unknown rooms stay in _reported_locations for caller-side review.
    Dates include an explicit source year. Doors times never replace show times.
    TicketWeb IDs identify shows across pagination and official URL variants.
    """
    diagnostics = {
        "adapter": "middle_east_ticketweb_html_v1", "scripts": 0,
        "malformed_scripts": 0, "event_cards": 0, "parsed_events": 0,
        "rejected_events": 0, "duplicate_cards": 0, "rejection_reasons": {},
        "missing_location_events": 0, "missing_show_time_events": 0,
        "invalid_doors_time_events": 0, "coverage": "fetched_page_only",
        "pagination_detected": False, "pagination_urls": [], "next_page_url": None,
        "retrieved_at": retrieved_at,
        "coverage_note": "Only cards in this response were read; later pages have not been checked.",
    }
    if not _url(source_url, source_url, _HOSTS):
        diagnostics["unsupported_source"] = True
        return [], diagnostics
    if not isinstance(html, str) or len(html) > 4_000_000:
        diagnostics["invalid_or_oversized_html"] = True
        return [], diagnostics
    tree = _Tree()
    tree.feed(html)
    tree.close()
    calendar = _first(tree.root, "tw-plugin-upcoming-event-list")
    if calendar is None:
        diagnostics["unrecognized_page_structure"] = True
        return [], diagnostics
    for link in tree.root.descendants("a", "page-numbers"):
        url = _url(link.attrs.get("href"), source_url, _HOSTS)
        if not url or not re.fullmatch(r"/all-shows-list/(?:page/\d+/)?", urlsplit(url).path):
            continue
        diagnostics["pagination_detected"] = True
        if url not in diagnostics["pagination_urls"] and len(diagnostics["pagination_urls"]) < 30:
            diagnostics["pagination_urls"].append(url)
        if link.has_class("next"):
            diagnostics["next_page_url"] = url
    events, seen = [], set()
    for card in calendar.descendants("div", "tw-section"):
        if diagnostics["event_cards"] >= 500:
            diagnostics["card_limit_reached"] = True
            break
        diagnostics["event_cards"] += 1
        try:
            title_node = _first(card, "tw-name")
            title = title_node.text() if title_node is not None else ""
            if not title or len(title) > 500:
                raise ValueError("missing_or_invalid_title")
            day = _date(_field(card, "tw-event-date"))
            clock = _time(_field(card, "tw-event-time"))
            try:
                doors = _time(_field(card, "tw-event-door-time"))
            except ValueError:
                doors = ""
                diagnostics["invalid_doors_time_events"] += 1
            locations = []
            for venue in card.descendants(class_name="tw-venue-name"):
                name = venue.text()
                if len(name) > 300:
                    raise ValueError("invalid_location_length")
                if name and name.casefold() not in {v.casefold() for v in locations}:
                    locations.append(name)
                    if len(locations) == 2:
                        break
            title_link = _first(title_node, tag="a") if title_node is not None else None
            detail_url = _url(title_link.attrs.get("href") if title_link else "", source_url, _HOSTS)
            if detail_url and not re.fullmatch(r"/tm-event/[^/]+/?", urlsplit(detail_url).path):
                detail_url = ""
            button = _first(card, "tw-buy-tix-btn")
            ticket_url = _url(button.attrs.get("href") if button else "", source_url, _TICKET_HOSTS)
            ticket_id = re.fullmatch(r"/event/[^/]+/tickets/(\d+)/?", urlsplit(ticket_url).path) if ticket_url else None
            if not detail_url and not ticket_id:
                raise ValueError("missing_or_invalid_event_url")
            identity = ("ticketweb:event:" + ticket_id[1] if ticket_id else
                        "mideastclub:event:" + urlsplit(detail_url).path.rstrip("/"))
            button_text = button.text() if button is not None else ""
            button_classes = set(button.attrs.get("class", "").split()) if button is not None else set()
            status = "EventScheduled"
            if "tw_cancelled" in button_classes or re.fullmatch(r"cancel(?:led|ed)", button_text, re.I):
                status = "EventCancelled"
            elif "tw_postponed" in button_classes or re.fullmatch(r"postponed", button_text, re.I):
                status = "EventPostponed"
            elif "tw_rescheduled" in button_classes or re.fullmatch(r"rescheduled", button_text, re.I):
                status = "EventRescheduled"
            event = {
                "date": day, "time": clock, "doors_time": doors,
                "venue": locations[0] if len(locations) == 1 else "Middle East (room not reported)",
                "artists": title, "url": detail_url or ticket_url, "source_url": source_url,
                "external_identity": identity, "start_date_raw": day + ("T" + clock if clock else ""),
                "reported_status": status, "ages": _field(card, "tw-age-restriction"),
                "price": _field(card, "tw-price"), "ticket_url": ticket_url,
                "ticket_status": button_text, "_reported_locations": locations,
            }
            key = (identity, day, clock, tuple(locations), status)
            if key in seen:
                diagnostics["duplicate_cards"] += 1
                continue
            seen.add(key)
            events.append(event)
            if not locations:
                diagnostics["missing_location_events"] += 1
            if not clock:
                diagnostics["missing_show_time_events"] += 1
        except ValueError as exc:
            diagnostics["rejected_events"] += 1
            reason = str(exc)
            reasons = diagnostics["rejection_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
    diagnostics["parsed_events"] = len(events)
    if events:
        diagnostics["earliest_date"] = min(e["date"] for e in events)
        diagnostics["latest_date"] = max(e["date"] for e in events)
    return events, diagnostics
