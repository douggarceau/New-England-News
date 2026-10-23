"""Bounded, offline parser for the Sinclair's public HTML event cards.

The adapter makes no requests. It reads the dates explicitly printed in the
downloaded page and never derives a year from retrieval time or artwork URLs.
Sinclair's calendar also contains other-room and unidentified-room listings;
the caller must apply a strict location policy using _reported_locations.
"""

import datetime as dt
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


class _Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def has_class(self, value):
        return value in self.attrs.get("class", "").split()

    def text(self):
        value = " ".join(child.text() if isinstance(child, _Node) else child
                         for child in self.children)
        return re.sub(r"\s+", " ", value).strip()

    def descendants(self, tag=None, class_name=None):
        for child in self.children:
            if isinstance(child, _Node):
                if (tag is None or child.tag == tag) and (class_name is None or child.has_class(class_name)):
                    yield child
                yield from child.descendants(tag, class_name)


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
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def _first(node, tag=None, class_name=None):
    return next(node.descendants(tag, class_name), None)


def _date(value):
    match = re.fullmatch(
        r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+)?"
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", value)
    if not match:
        raise ValueError("missing_or_invalid_explicit_date")
    months = {}
    for number, name in enumerate(["january", "february", "march", "april", "may", "june",
                                   "july", "august", "september", "october", "november", "december"], 1):
        months[name] = months[name[:3]] = number
    month = months.get(match[1].lower())
    if month is None:
        raise ValueError("invalid_month")
    return dt.date(int(match[3]), month, int(match[2])).isoformat()


def _time(value):
    """Return (show_time, doors_time), retaining only explicit labels."""
    match = re.fullmatch(r"(Doors|Show|Show Time)\s*:?\s*(\d{1,2}):(\d{2})\s*(AM|PM)", value, re.I)
    if not match:
        return "", ""
    hour, minute = int(match[2]), int(match[3])
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        return "", ""
    hour = hour % 12 + (12 if match[4].upper() == "PM" else 0)
    clock = "%02d:%02d" % (hour, minute)
    return ("", clock) if match[1].lower() == "doors" else (clock, "")


def _locations(card):
    explicit = []
    for node in card.descendants():
        if node.has_class("venue") or node.has_class("location"):
            name = node.text()
            if name and name not in explicit:
                explicit.append(name)
    if explicit:
        return explicit[:2]
    # This is the source's own venue marker on its event card, not an
    # inference that every event on the domain takes place in the main room.
    if card.has_class("sinclair"):
        return ["The Sinclair"]
    tour = _first(card, class_name="tour")
    if tour is not None and tour.text().casefold() == "52 church":
        return ["52 Church"]
    return []


def extract(html, source_url, retrieved_at=None):
    """Return (event observations, diagnostics) for only this fetched page.

    Events include _reported_locations for core's location policy. Doors are
    returned as doors_time; an absent show time remains empty. More pages are
    never fetched or claimed covered. retrieved_at is provenance only.
    """
    diagnostics = {
        "adapter": "sinclair_html_v1", "scripts": 0, "malformed_scripts": 0,
        "rejected_events": 0, "event_cards": 0, "parsed_events": 0,
        "rejection_reasons": {}, "missing_location_events": 0,
        "coverage": "fetched_page_only", "pagination_detected": False,
        "view_all_url": None, "retrieved_at": retrieved_at,
    }
    target = urlsplit(source_url)
    if target.scheme != "https" or target.hostname not in {"www.sinclaircambridge.com", "sinclaircambridge.com"}:
        diagnostics["unsupported_source"] = True
        return [], diagnostics
    tree = _Tree()
    tree.feed(html)
    tree.close()
    events_list = next((n for n in tree.root.descendants() if n.attrs.get("id") == "eventsList"), None)
    if events_list is None:
        diagnostics["unrecognized_page_structure"] = True
        return [], diagnostics
    for node in tree.root.descendants():
        if node.attrs.get("id") == "loadMoreEvents":
            diagnostics["pagination_detected"] = True
            diagnostics["pagination_note"] = "Load More control present; later pages were not fetched."
        if node.tag == "a" and node.has_class("view-all"):
            url = urljoin(source_url, node.attrs.get("href", ""))
            if urlsplit(url).hostname == target.hostname and urlsplit(url).scheme == "https":
                diagnostics["view_all_url"] = url
    events = []
    seen = set()
    for card in events_list.descendants("div", "entry"):
        diagnostics["event_cards"] += 1
        try:
            title_node = _first(card, "h3", "carousel_item_title_small")
            title_link = _first(title_node, "a") if title_node else None
            title = title_link.text() if title_link else ""
            if not title or len(title) > 500:
                raise ValueError("missing_or_invalid_title")
            detail_url = urljoin(source_url, title_link.attrs.get("href", ""))
            detail = urlsplit(detail_url)
            identity = re.fullmatch(r"/events/detail/(\d+)/?", detail.path)
            if detail.scheme != "https" or detail.hostname not in {"www.sinclaircambridge.com", "sinclaircambridge.com"} or not identity:
                raise ValueError("invalid_event_detail_url")
            date_node = _first(card, "span", "date")
            date = _date(date_node.text() if date_node else "")
            time_node = _first(card, "span", "time")
            show_time, doors_time = _time(time_node.text() if time_node else "")
            age_node = _first(card, "span", "age")
            locations = _locations(card)
            buttons = _first(card, "div", "buttons")
            button_text = buttons.text().casefold() if buttons else ""
            status = "EventScheduled"
            if re.search(r"\bcancel(?:led|ed)\b", button_text):
                status = "EventCancelled"
            elif re.search(r"\bpostponed\b", button_text):
                status = "EventPostponed"
            elif re.search(r"\brescheduled\b", button_text):
                status = "EventRescheduled"
            event = {
                "date": date, "time": show_time, "doors_time": doors_time,
                "venue": locations[0] if len(locations) == 1 else "The Sinclair",
                "artists": title, "url": detail_url, "source_url": source_url,
                "external_identity": "sinclair:event:" + identity[1],
                "start_date_raw": date, "reported_status": status,
                "ages": age_node.text() if age_node else "",
                "_reported_locations": locations,
            }
            dedup = (event["external_identity"], date, show_time, doors_time)
            if dedup in seen:
                continue
            seen.add(dedup)
            events.append(event)
            if not locations:
                diagnostics["missing_location_events"] += 1
        except ValueError as exc:
            diagnostics["rejected_events"] += 1
            reason = str(exc)
            reasons = diagnostics["rejection_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
    diagnostics["parsed_events"] = len(events)
    diagnostics["page_title"] = "Upcoming Shows — The Sinclair"
    if events:
        diagnostics["earliest_date"] = min(e["date"] for e in events)
        diagnostics["latest_date"] = max(e["date"] for e in events)
    return events, diagnostics
