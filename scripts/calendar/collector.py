"""Bounded official-calendar collection. Ordinary Python only; no model calls."""
import datetime as dt
import html as html_module
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import adapters_boston_html
import adapters_hob
import adapters_middle_east
import adapters_scullers
import adapters_sinclair
import adapters_remaining
from core import ValidationError, Stopped, extract_events, now
from network import LocalNetworkHTTP, approved_hosts_from_urls

BOSTON_ZONE = ZoneInfo("America/New_York")
MIDDLE_LIST = "https://www.mideastoffers.com/all-shows-list/"
CITY_FEED = "https://awsapi.citywinery.com/feeds/Boston/events.ics"
# Public Discovery widget configuration observed on the official Crossroads
# venue pages and homepage on 2026-10-23. These are public browser widget
# parameters, not account credentials. Read the feed directly: Shopify's page
# shell returns 404 to the scheduled runner even while the feed remains live.
# Wilbur's Discovery venue ID was verified against its official Ticketmaster
# listing (venue 8252); its own website endorses Ticketmaster as its seller.
TICKETMASTER_ENDPOINT = "https://app.ticketmaster.com/discovery/v2/events.json"
CROSSROADS_PUBLIC_WIDGET_KEY = "oo1qd0wzLe7WJpm61ALQuUCTMXGK7U5z"
TICKETMASTER_VENUES = {
    "https://crossroadspresents.com/pages/brighton-music-hall": "KovZpapwne",
    "https://crossroadspresents.com/pages/paradise-rock-club": "KovZpZA11JtA",
    "https://crossroadspresents.com/pages/mgm-fenway-music-hall": "KovZ917AEJz",
    "https://www.ticketmaster.com/big-night-live-tickets-boston/venue/9293": "KovZ917AxdQ",
    "https://thewilbur.com/calendar/": "KovZpZAEAIvA",
    "https://www.ticketweb.com/venue/regattabar-cambridge-ma/748814?pl=regatta": "KovZ917AYuX",
}
ROAD_FEED = "https://aegwebprod.blob.core.windows.net/json/events/219/events.json"
SCULLERS_FEED = "https://musicidb.com/venue/getVenueEvents.htm?listType=upcoming&page=0&frameType=listWidget&descrip=1&venueId=715"
BSO_ENDPOINT = "https://go8f04wi19tuvlyrp-1.a1.typesense.net/collections/performances/documents/search"
DICE_ENDPOINT = "https://partners-endpoint.dice.fm/api/v2/events"
FEED_URLS = [MIDDLE_LIST, CITY_FEED, ROAD_FEED, SCULLERS_FEED, BSO_ENDPOINT, DICE_ENDPOINT,
             adapters_remaining.ROYALE_ORIGIN, adapters_remaining.WAREHOUSE_URL,
             "https://www.mideastclub.com/all-shows-list/",
             "https://app.ticketmaster.com/discovery/v2/events.json"]

def redact_url(url):
    parts = urlsplit(url)
    query = [(k, "PUBLIC_EMBEDDED_KEY" if k.lower() in ("apikey", "api_key", "key") else v)
             for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))

def decode_page(page):
    try:
        return page.body.decode("utf-8-sig")
    except UnicodeDecodeError:
        kind = getattr(page, "content_type", "")
        charset = re.search(r"charset=([\w-]+)", kind, re.I)
        encoding = charset[1] if charset else "windows-1252"
        try:
            return page.body.decode(encoding, "replace")
        except LookupError:
            return page.body.decode("utf-8", "replace")

def parse_dice(text, source_url, retrieved_at):
    data = json.loads(text)
    rows = data.get("data", [])
    if not isinstance(rows, list) or len(rows) > 500:
        raise ValidationError("Unexpected public widget event response.")
    events = []
    diagnostics = {"adapter": "dice_public_widget", "malformed_scripts": 0,
                   "rejected_events": 0, "coverage": "first_page_only",
                   "pagination_detected": bool(data.get("links", {}).get("next")),
                   "notes": ["UTC timestamps converted to the physical Boston-area venue timezone."]}
    for row in rows:
        try:
            start = dt.datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                raise ValueError("Missing UTC offset")
            local = start.astimezone(BOSTON_ZONE)
            flags = row.get("flags", [])
            if not isinstance(flags, list):
                flags = []
            reported = str(row.get("status") or "").casefold()
            if reported in ("cancelled", "canceled", "postponed", "rescheduled"):
                flags = flags + ["cancelled" if reported == "canceled" else reported]
            status = "EventCancelled" if "cancelled" in flags else "EventPostponed" if "postponed" in flags else "EventRescheduled" if "rescheduled" in flags else "EventScheduled"
            locations = [v["name"] for v in row.get("venues", []) if isinstance(v, dict) and isinstance(v.get("name"), str)]
            if not locations and isinstance(row.get("venue"), str):
                locations = [row["venue"]]
            if row.get("is_multi_days_event"):
                diagnostics["rejected_events"] += 1
                continue
            event = {"date": local.date().isoformat(), "time": local.strftime("%H:%M"),
                     "timezone": "America/New_York", "venue": "Deep Cuts", "artists": row["name"],
                     "url": row.get("url") or source_url, "source_url": source_url,
                     "external_identity": "dice:event:" + str(row["id"]),
                     "start_date_raw": row["date"], "reported_status": status,
                     "ticket_status": "sold_out" if row.get("sold_out") else str(row.get("status", "")),
                     "ages": str(row.get("age_limit") or ""), "_reported_locations": locations}
            # A provider's generic start timestamp can be the explicitly labeled
            # doors time. Preserve that label rather than invent a show start.
            desc = row.get("raw_description") or ""
            doors = re.search(r"\bDoors\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b", desc, re.I)
            if doors:
                hour = int(doors[1]) % 12 + (12 if doors[3].upper() == "PM" else 0)
                event["doors_time"] = f"{hour:02d}:{int(doors[2] or 0):02d}"
                if event["doors_time"] == event["time"]:
                    event["time"] = ""
            show = re.search(r"\bShow\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b", desc, re.I)
            if show and 1 <= int(show[1]) <= 12 and 0 <= int(show[2] or 0) <= 59:
                hour = int(show[1]) % 12 + (12 if show[3].upper() == "PM" else 0)
                event["time"] = f"{hour:02d}:{int(show[2] or 0):02d}"
            events.append(event)
        except (KeyError, TypeError, ValueError):
            diagnostics["rejected_events"] += 1
    return events, diagnostics

class CalendarCollector:
    """Fetch each source and its bounded configured public feed, sequentially.

    Known Middle East list and Scullers list routes directly serve the same
    official calendar, avoiding their slower calendar shells. No pagination loops
    are run. A timeout receives one retry. Royale reads its page, script and published feed.
    A transport may be injected to replay captured bytes.
    """
    def __init__(self, source_policies, transport=None, minimum_spacing=2.0):
        self.policies = source_policies
        self.transport = transport or LocalNetworkHTTP(
            approved_hosts=approved_hosts_from_urls(list(source_policies) + FEED_URLS),
            page_limit=3_000_000, compressed_limit=2_000_000,
            request_timeout=25, total_timeout=40,
            accepted_content_types={"text/html", "application/xhtml+xml", "application/json", "text/calendar", "text/plain", "text/javascript", "application/javascript"})
        self.minimum_spacing = minimum_spacing
        self.last_request = 0.0
        self.requests = []

    def _get(self, url, stopped, public_headers=None):
        for attempt in range(2):
            delay = self.minimum_spacing - (time.monotonic() - self.last_request)
            if delay > 0 and stopped.wait(delay):
                raise Stopped()
            if stopped.is_set():
                raise Stopped()
            self.last_request = time.monotonic()
            try:
                page = self.transport.fetch(url, stopped, public_headers=public_headers)
            except ValidationError as exc:
                # One bounded retry for transient timeouts only. Never retry
                # access denials, rate limits, TLS failures or validation errors.
                if attempt or str(exc) not in ("Source request timed out.",
                                               "Source request exceeded its time limit."):
                    raise
                self.requests.append({"url": redact_url(url), "retrieved_at": now(),
                                      "http_status": None, "error": str(exc), "retry": 1})
                continue
            self.requests.append({"url": redact_url(url), "final_url": redact_url(page.final_url),
                                  "retrieved_at": page.retrieved_at, "http_status": page.status})
            return page

    def fetch(self, source_url, stop_event):
        from feed_parsers import parse_ical, parse_axs, parse_ticketmaster
        host = urlsplit(source_url).hostname
        policy = self.policies.get(source_url, {})
        venue = policy.get("fallback_venue") or "Shared calendar"
        offset = len(self.requests)
        fetch_url = MIDDLE_LIST if host == "www.mideastoffers.com" else SCULLERS_FEED if host == "scullersjazz.com" else CITY_FEED if host == "citywinery.com" else source_url
        if source_url in TICKETMASTER_VENUES:
            params = {
                "size": 100, "page": 0, "sort": "date,asc",
                "venueId": TICKETMASTER_VENUES[source_url],
                "apikey": CROSSROADS_PUBLIC_WIDGET_KEY}
            # Regattabar's official TicketWeb events are syndicated through
            # Discovery. A ticketmaster-only filter would exclude those rows.
            if venue != "Regattabar":
                params["source"] = "ticketmaster"
            fetch_url = TICKETMASTER_ENDPOINT + "?" + urlencode(params)
        page = self._get(fetch_url, stop_event)
        text = decode_page(page)
        if source_url in TICKETMASTER_VENUES:
            events, parsing = parse_ticketmaster(text, source_url, page.retrieved_at)
            if venue in ("Big Night Live", "Regattabar"):
                # Keep the original provider URL identity while enriching its
                # former doors-only timestamp with the explicit show time.
                for event in events:
                    event["external_identity"] = "event-url:" + event["url"]
            elif source_url == "https://thewilbur.com/calendar/":
                identities = json.loads((Path(__file__).parent / "wilbur-performance-identities.json").read_text())["identities"]
                for event in events:
                    ticket_id = re.search(r"/event/([0-9A-Fa-f]+)(?:[/?#]|$)", event["url"])
                    if not ticket_id:
                        raise ValidationError("Wilbur performance is missing its provider ticket ID.")
                    provider_id = ticket_id[1].upper()
                    event["external_identity"] = identities.get(provider_id, "ticketmaster:event:" + provider_id)
        elif host in ("www.mideastoffers.com", "www.mideastclub.com"):
            events, parsing = adapters_middle_east.extract(text, fetch_url, page.retrieved_at)
        elif host == "scullersjazz.com":
            events, parsing = adapters_scullers.extract(text, SCULLERS_FEED, page.retrieved_at)
        elif host == "www.sinclaircambridge.com":
            events, parsing = adapters_sinclair.extract(text, source_url, page.retrieved_at)
        elif host == "boston.houseofblues.com":
            events, parsing = adapters_hob.extract(text, source_url, page.retrieved_at)
        elif host == "citywinery.com":
            events, parsing = parse_ical(text, source_url, page.retrieved_at)
        elif host == "roadrunnerboston.com":
            if ROAD_FEED not in text:
                raise ValidationError("Roadrunner's prepared public event feed is no longer linked.")
            page = self._get(ROAD_FEED, stop_event)
            events, parsing = parse_axs(decode_page(page), source_url, page.retrieved_at)
        elif host == "crossroadspresents.com":
            # The actual event-list variable is authoritative. MGM's hidden
            # monthly widget currently contains a different venue's ID.
            match = re.search(r"var\s+stringVenueIds[^=]+\s*=\s*['\"]([^'\"]+)['\"]", text)
            key = re.search(r"w-tmapikey=['\"]([^'\"]+)['\"]", text)
            if not match or not key or not re.fullmatch(r"[A-Za-z0-9]+", match[1].strip()):
                raise ValidationError("Official promoter calendar's single venue feed could not be identified.")
            params = {"size":100,"page":0,"sort":"date,asc","venueId":match[1].strip(),"apikey":key[1],"source":"ticketmaster"}
            page = self._get("https://app.ticketmaster.com/discovery/v2/events.json?" + urlencode(params), stop_event)
            events, parsing = parse_ticketmaster(decode_page(page), source_url, page.retrieved_at)
        elif host == "www.bso.org":
            # These are the public read-only search settings observed in the
            # official calendar's main.js on 2026-10-23, not a user API account.
            timestamp = int(dt.datetime.fromisoformat(page.retrieved_at).timestamp())
            params = {"q":"*", "query_by":"title,excerpt,subhead,content_keywords,performance_categories",
                      "sort_by":"performance_date:asc", "filter_by":"show_in_cal:true && performance_venue.display_name:=[`Symphony Hall, Boston, MA`] && performance_date:>=" + str(timestamp), "per_page":100,"page":1}
            page = self._get(BSO_ENDPOINT + "?" + urlencode(params), stop_event,
                             {"X-TYPESENSE-API-KEY":"qoWHCTjesGfIaxdXbw9vOgod1VToEXNI"})
            events, parsing = adapters_boston_html.parse_bso_json(decode_page(page), source_url, page.retrieved_at)
        elif host == "www.deepcuts.rocks":
            key = re.search(r"\\u0022apiKey\\u0022:\\u0022([^\\]+)\\u0022", text)
            if not key:
                raise ValidationError("Deep Cuts public event-widget configuration is unavailable.")
            params = [("page[size]","24"),("types","linkout,event"),("filter[promoters][]","Deep Cuts LLC")]
            page = self._get(DICE_ENDPOINT + "?" + urlencode(params), stop_event, {"x-api-key":key[1]})
            events, parsing = parse_dice(decode_page(page), source_url, page.retrieved_at)
        elif host == 'royaleboston.com':
            match = re.search(r'<script[^>]+src=[\"\x27](/assets/index-[A-Za-z0-9_-]+\.js)[\"\x27]', text)
            if not match:
                raise ValidationError('Royale calendar script is unavailable.')
            script = self._get(urljoin(source_url, match[1]), stop_event)
            key = adapters_remaining.royale_config(decode_page(script))
            params = {'select':'id,title,description,event_date,event_time,ticket_url,is_published,age_restriction',
                      'is_published':'eq.true', 'order':'event_date.asc,event_time.asc', 'limit':1000}
            page = self._get(adapters_remaining.ROYALE_ORIGIN + '/rest/v1/events?' + urlencode(params),
                             stop_event, {'apikey': key})
            events, parsing = adapters_remaining.parse_royale(decode_page(page), source_url)
        elif source_url == adapters_remaining.WAREHOUSE_URL:
            events, parsing = adapters_remaining.parse_warehouse(text, source_url)
        elif adapters_boston_html.supported(source_url):
            events, parsing = adapters_boston_html.extract(text, source_url, page.retrieved_at)
        else:
            events, parsing = extract_events(text, source_url, venue, capture_location=True)
            parsing["adapter"] = "schema_org_event"
            parsing["coverage"] = "fetched_page_only"
        for event in events:
            event["source_url"] = source_url
        parsing.setdefault("rejected_events", 0)
        parsing.setdefault("malformed_scripts", 0)
        parsing["fetches"] = self.requests[offset:]
        parsing["scope"] = "Bounded captured pages; further pagination was not collected."
        if not events:
            parsing["coverage_gap"] = "No supported event records extracted; this does not mean no shows."
        page.parsed_events, page.parsing = events, parsing
        page.final_url = redact_url(page.final_url)
        return page
