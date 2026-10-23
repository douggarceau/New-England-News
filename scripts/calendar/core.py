"""Manual, local research storage and bounded public HTTPS collection (Python 3.9+)."""

import contextlib
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import sqlite3
import ssl
import threading
import time
import uuid
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

MAX_PAGE_BYTES = 1_000_000
MAX_IMPORT_BYTES = 8_000_000
MAX_EVENTS_PER_IMPORT = 20_000
MAX_SOURCES = 100
MAX_LOCATION_REVIEW_SAMPLES = 10
EVENT_TYPES = {
    "Event", "BusinessEvent", "ChildrensEvent", "ComedyEvent", "CourseInstance",
    "DanceEvent", "DeliveryEvent", "EducationEvent", "EventSeries", "ExhibitionEvent",
    "Festival", "FoodEvent", "Hackathon", "LiteraryEvent", "MusicEvent",
    "PublicationEvent", "SaleEvent", "ScreeningEvent", "SocialEvent", "SportsEvent",
    "TheaterEvent", "VisualArtsEvent",
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def normalized(text):
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ValidationError(ValueError):
    pass


class Stopped(Exception):
    pass


@dataclass(frozen=True)
class Target:
    url: str
    host: str
    ips: tuple
    path: str


def public_address(value):
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            return public_address(str(address.ipv4_mapped))
        if address.sixtofour or address.teredo:
            return False
    return (address.is_global and not address.is_private and not address.is_reserved
            and not address.is_loopback and not address.is_link_local
            and not address.is_multicast and not address.is_unspecified)


def validate_source_url(value, resolver=None):
    """Resolve once, reject mixed public/private answers, and return pinned IPs."""
    resolver = resolver or socket.getaddrinfo
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValidationError("A public HTTPS source URL of at most 2048 characters is required.")
    if re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValidationError("Source URL contains whitespace or invalid characters.")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.hostname:
            raise ValidationError("Only public HTTPS sources are supported.")
        if parts.username is not None or parts.password is not None or parts.port not in (None, 443):
            raise ValidationError("Credentials and nonstandard source ports are not allowed.")
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except (ValueError, UnicodeError) as exc:
        raise ValidationError("Invalid HTTPS source URL.") from exc
    if not host or "%" in host:
        raise ValidationError("Invalid source hostname.")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".test", ".invalid", ".example")):
        raise ValidationError("Local or reserved source names are not allowed.")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is None:
        if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host) or any(not p or len(p) > 63 or p.startswith("-") or p.endswith("-") for p in host.split(".")):
            raise ValidationError("A valid public hostname is required.")
        try:
            answers = resolver(host, 443, type=socket.SOCK_STREAM)
            ips = tuple(dict.fromkeys(answer[4][0] for answer in answers))
        except (OSError, ValueError) as exc:
            raise ValidationError("Could not resolve the source hostname.") from exc
    else:
        ips = (str(literal),)
    try:
        acceptable = ips and all(public_address(ip) for ip in ips)
    except ValueError:
        acceptable = False
    if not acceptable:
        raise ValidationError("The source resolves to a private, local, or reserved address.")
    netloc = "[" + host + "]" if ":" in host else host
    path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    clean = urlunsplit(("https", netloc, parts.path or "/", parts.query, ""))
    return Target(clean, host, ips, path)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect directly to a validated IP; TLS still authenticates the original host."""
    def __init__(self, target, timeout):
        super().__init__(target.host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.target = target

    def connect(self):
        last_error = None
        for ip in self.target.ips:
            raw = None
            try:
                raw = socket.create_connection((ip, 443), self.timeout)
                self.sock = self._context.wrap_socket(raw, server_hostname=self.target.host)
                return
            except OSError as exc:
                last_error = exc
                if raw:
                    raw.close()
        raise last_error or OSError("Connection failed")


@dataclass
class Page:
    body: bytes
    final_url: str
    status: int
    retrieved_at: str


class SafeHTTP:
    def __init__(self, resolver=None, connection_factory=PinnedHTTPSConnection,
                 page_limit=MAX_PAGE_BYTES, request_timeout=12, total_timeout=30):
        self.resolver = resolver or socket.getaddrinfo
        self.connection_factory = connection_factory
        self.page_limit = page_limit
        self.request_timeout = request_timeout
        self.total_timeout = total_timeout

    def fetch(self, url, stop_event):
        deadline = time.monotonic() + self.total_timeout
        for hop in range(4):
            if stop_event.is_set():
                raise Stopped()
            if time.monotonic() >= deadline:
                raise ValidationError("Source request exceeded its time limit.")
            target = validate_source_url(url, self.resolver)
            if stop_event.is_set():
                raise Stopped()
            connection = self.connection_factory(target, min(self.request_timeout, max(0.1, deadline - time.monotonic())))
            try:
                connection.request("GET", target.path, headers={
                    "User-Agent": "BostonRamblerManualPilot/0.2", "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "identity", "Connection": "close",
                })
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location or hop == 3:
                        raise ValidationError("Missing redirect target or too many redirects.")
                    url = urljoin(target.url, location)
                    continue  # Every redirect is independently resolved and pinned.
                if response.status != 200:
                    raise ValidationError("Source returned HTTP " + str(response.status) + ".")
                kind = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
                if kind not in ("text/html", "application/xhtml+xml"):
                    raise ValidationError("Source did not return an HTML page.")
                encoding = response.getheader("Content-Encoding", "identity").lower().strip()
                if encoding not in ("", "identity"):
                    raise ValidationError("Compressed responses are not supported by this pilot.")
                length = response.getheader("Content-Length")
                if length is not None:
                    try:
                        size = int(length)
                    except ValueError as exc:
                        raise ValidationError("Invalid source Content-Length.") from exc
                    if size < 0 or size > self.page_limit:
                        raise ValidationError("Source page exceeds the byte limit.")
                chunks, size = [], 0
                while True:
                    if stop_event.is_set():
                        raise Stopped()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValidationError("Source request exceeded its time limit.")
                    if getattr(connection, "sock", None):
                        connection.sock.settimeout(min(self.request_timeout, remaining))
                    chunk = response.read1(min(65536, self.page_limit + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.page_limit:
                        raise ValidationError("Source page exceeds the byte limit.")
                    chunks.append(chunk)
                return Page(b"".join(chunks), target.url, response.status, now())
            finally:
                connection.close()
        raise ValidationError("Too many redirects.")


class JSONLDParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts, self.parts = [], None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            kind = dict(attrs).get("type", "").split(";", 1)[0].strip().lower()
            self.parts = [] if kind == "application/ld+json" else None

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.parts is not None:
            self.scripts.append("".join(self.parts))
            self.parts = None


def nodes(value):
    stack, count = [value], 0
    while stack:
        current = stack.pop()
        count += 1
        if count > 20_000:
            raise ValidationError("JSON-LD structure is too large.")
        if isinstance(current, dict):
            yield current
            stack.extend(v for v in current.values() if isinstance(v, (dict, list)))
        elif isinstance(current, list):
            stack.extend(reversed(current))


def type_name(value):
    return str(value).rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]


def event_start(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?)?", value):
        raise ValidationError("Event startDate must be an ISO date or date-time.")
    try:
        if "T" in value:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.date().isoformat(), parsed.strftime("%H:%M")
        return dt.date.fromisoformat(value).isoformat(), ""
    except ValueError as exc:
        raise ValidationError("Event startDate is not a valid calendar date/time.") from exc


def extract_events(html, source_url, fallback_venue, capture_location=False):
    parser = JSONLDParser()
    parser.feed(html)
    parser.close()
    parsed_nodes, malformed = [], 0
    for script in parser.scripts:
        try:
            parsed_nodes.extend(nodes(json.loads(script)))
        except (ValueError, TypeError, RecursionError):
            malformed += 1
    graph = {}
    for node in parsed_nodes:
        if isinstance(node.get("@id"), str):
            graph[node["@id"]] = {**graph.get(node["@id"], {}), **node}
    events, rejected = [], 0
    for item in parsed_nodes:
        types = item.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if not isinstance(types, list) or not any(type_name(t) in EVENT_TYPES for t in types):
            continue
        try:
            date, clock = event_start(item.get("startDate"))
            name = item.get("name")
            if not isinstance(name, str) or not name.strip() or len(name) > 500:
                raise ValidationError("Event name missing or too long.")
            raw_location = item.get("location", {})
            location_names = []
            if capture_location:
                locations = raw_location if isinstance(raw_location, list) else [raw_location]
                for reported in locations:
                    if isinstance(reported, dict):
                        if isinstance(reported.get("@id"), str):
                            reported = {**graph.get(reported["@id"], {}), **reported}
                        reported = reported.get("name")
                    if isinstance(reported, str) and reported.strip():
                        reported = reported.strip()
                        if not any(normalized(reported) == normalized(existing) for existing in location_names):
                            location_names.append(reported)
                            if len(location_names) == 2:
                                break  # Two distinct names suffice to flag ambiguous locations.
            location = raw_location
            if isinstance(location, list):
                location = next((loc for loc in location if isinstance(loc, dict)), {})
            if isinstance(location, dict) and isinstance(location.get("@id"), str):
                location = {**graph.get(location["@id"], {}), **location}
            venue = location.get("name", fallback_venue) if isinstance(location, dict) else fallback_venue
            if capture_location:
                # The policy will assign a canonical venue or reject this observation.
                # Keeping this temporary fallback permits missing/invalid names to be
                # recorded as location-review gaps instead of generic parse failures.
                venue = fallback_venue
            if not isinstance(venue, str) or not venue.strip() or len(venue) > 300:
                raise ValidationError("Venue missing or invalid.")
            identity = item.get("@id")
            if isinstance(identity, str) and identity:
                identity = "jsonld:" + urljoin(source_url, identity)
            else:
                identifier = item.get("identifier")
                if isinstance(identifier, dict):
                    identifier = identifier.get("value")
                identity = "provider:" + source_url + ":" + str(identifier) if isinstance(identifier, (str, int)) and str(identifier) else ""
            url = item.get("url")
            url = urljoin(source_url, url) if isinstance(url, str) else source_url
            if urlsplit(url).scheme not in ("https", "http") or len(url) > 2048:
                url = source_url
            if not identity and url != source_url:
                # Ticket/detail URLs distinguish same-artist performances on one
                # date and remain stable when a provider reschedules a show.
                identity = "event-url:" + url
            event = {"date": date, "time": clock, "venue": venue.strip(), "artists": name.strip(),
                     "url": url, "source_url": source_url, "external_identity": identity,
                     "start_date_raw": item["startDate"], "reported_status": type_name(item.get("eventStatus", "EventScheduled"))}
            if capture_location:
                event["_reported_locations"] = location_names
            events.append(event)
        except (ValueError, TypeError):
            rejected += 1
    return events, {"scripts": len(parser.scripts), "malformed_scripts": malformed, "rejected_events": rejected}


def _prepare_source_policies(policies):
    """Copy and normalize trusted local attribution rules without network access."""
    if policies is None:
        return {}
    if not isinstance(policies, dict) or len(policies) > MAX_SOURCES:
        raise ValidationError("Source policies must be a mapping of at most 100 URLs.")
    prepared = {}
    for url, policy in policies.items():
        if not isinstance(url, str) or not url or len(url) > 2048 or not isinstance(policy, dict):
            raise ValidationError("Each source policy needs a source URL and a rule object.")
        required = policy.get("require_explicit_location", True)
        fallback = policy.get("fallback_venue", "")
        aliases = policy.get("aliases", {})
        if not isinstance(required, bool) or not isinstance(fallback, str) or len(fallback) > 300:
            raise ValidationError("Invalid location requirement or fallback venue in source policy.")
        if not isinstance(aliases, dict):
            raise ValidationError("Source policy aliases must map reported names to canonical venues.")
        names = {}
        canonical_names = set()
        for alias, canonical in aliases.items():
            if (not isinstance(alias, str) or not alias.strip() or len(alias) > 300
                    or not isinstance(canonical, str) or not canonical.strip() or len(canonical) > 300):
                raise ValidationError("Venue aliases and canonical names must contain 1 to 300 characters.")
            key, value = normalized(alias), canonical.strip()
            if key in names and names[key] != value:
                raise ValidationError("Conflicting source policy aliases for one reported venue.")
            names[key] = value
            canonical_names.add(value)
        # Canonical storage names are not necessarily evidence of a specific room.
        # Accept only explicitly configured observed aliases; e.g. a generic
        # "City Winery Boston" location must not imply the Main Stage.
        fallback = fallback.strip()
        if not required and (not fallback or fallback not in canonical_names):
            raise ValidationError("A permitted location fallback must be one of the configured canonical venues.")
        calendar_default = policy.get('calendar_default', '')
        if calendar_default and calendar_default not in canonical_names:
            raise ValidationError('Calendar default must identify a configured venue.')
        prepared[url] = {"require_explicit_location": required, "fallback_venue": fallback,
                         "aliases": names, "calendar_default": calendar_default}
    return prepared


def location_conflict(event):
    """Hold explicit other-room assertions without inventing a replacement venue."""
    source = urlsplit(event.get("source_url", "")).hostname
    title = event.get("artists", "")
    return (source in {"therockwell.org", "www.therockwell.org"}
            and event.get("venue") == "The Rockwell"
            and bool(re.search(r"(?:@|\bat)\s+Saloon\b", title, re.I)))


def _apply_source_policy(event, policy):
    """Return an attributed copy or a review reason; never infer a room from a title."""
    if location_conflict(event):
        return None, "conflicting_room_in_listing"
    names = event.get("_reported_locations", [])
    if len(names) > 1:
        return None, "ambiguous_location"
    if names:
        canonical = policy["aliases"].get(normalized(names[0]))
        if canonical is None:
            return None, "unknown_or_offsite_location"
    elif (policy.get('calendar_default') and
          event.get('_calendar_location') == policy['calendar_default']):
        canonical = policy['calendar_default']
    elif policy["require_explicit_location"]:
        return None, "missing_location"
    else:
        canonical = policy["fallback_venue"]
    attributed = dict(event)
    attributed["venue"] = canonical
    return attributed, None


def _source_counts():
    return {"added": 0, "updated": 0, "unchanged": 0, "rejected": 0,
            "extracted_events": 0, "accepted_events": 0, "location_rejected_events": 0,
            "location_rejection_reasons": {}, "location_review_samples": []}


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, identity_key TEXT UNIQUE NOT NULL, identity_kind TEXT NOT NULL,
 natural_key TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL, venue TEXT NOT NULL,
 artists TEXT NOT NULL, url TEXT NOT NULL, detail TEXT NOT NULL, fingerprint TEXT NOT NULL,
 status TEXT NOT NULL, first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 last_retrieved_at TEXT, source_url TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS event_natural_key ON events(natural_key);
CREATE TABLE IF NOT EXISTS event_changes (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL, changed_at TEXT NOT NULL,
 kind TEXT NOT NULL, previous_detail TEXT, new_detail TEXT NOT NULL,
 FOREIGN KEY(event_id) REFERENCES events(id)
);
CREATE TABLE IF NOT EXISTS sources (
 url TEXT PRIMARY KEY, venue TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'never_checked',
 last_attempt_at TEXT, last_success_at TEXT, last_finished_at TEXT,
 failure_count INTEGER NOT NULL DEFAULT 0, last_error TEXT, last_final_url TEXT
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, state TEXT NOT NULL,
 summary TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS source_runs (
 id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, source_url TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, state TEXT NOT NULL,
 http_status INTEGER, final_url TEXT, summary TEXT NOT NULL DEFAULT '{}', error TEXT,
 FOREIGN KEY(run_id) REFERENCES runs(id)
);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA)
        # Recover a process interruption without claiming that research completed.
        with self.connection() as connection:
            timestamp = now()
            connection.execute("UPDATE runs SET state='interrupted',finished_at=? WHERE state='running'", (timestamp,))
            connection.execute("UPDATE source_runs SET state='interrupted',finished_at=? WHERE state='running'", (timestamp,))
            connection.execute("UPDATE sources SET state='interrupted',last_finished_at=? WHERE state='running'", (timestamp,))

    @contextlib.contextmanager
    def connection(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save_source(self, url, venue):
        if not isinstance(venue, str) or not venue.strip() or len(venue) > 150:
            raise ValidationError("A venue name of 1 to 150 characters is required.")
        with self.connection() as connection:
            exists = connection.execute("SELECT 1 FROM sources WHERE url=?", (url,)).fetchone()
            if not exists and connection.execute("SELECT count(*) FROM sources").fetchone()[0] >= MAX_SOURCES:
                raise ValidationError("This manual pilot supports at most 100 sources.")
            connection.execute("INSERT INTO sources(url,venue) VALUES(?,?) ON CONFLICT(url) DO UPDATE SET venue=excluded.venue", (url, venue.strip()))

    def source_list(self):
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM sources ORDER BY venue,url")]

    def ingest(self, connection, raw, retrieved_at=None):
        if not isinstance(raw, dict):
            raise ValidationError("An event must be a JSON object.")
        date = raw.get("date")
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValidationError("Event date must use YYYY-MM-DD.")
        try:
            dt.date.fromisoformat(date)
        except ValueError as exc:
            raise ValidationError("Invalid event calendar date.") from exc
        event = {}
        for key, limit in (("date", 10), ("time", 80), ("venue", 300), ("artists", 500), ("url", 2048),
                           ("source_url", 2048), ("external_identity", 4096), ("start_date_raw", 100),
                           ("reported_status", 100), ("genre", 100), ("hood", 200), ("price", 300), ("ages", 100), ("src", 300),
                           ("doors_time", 80), ("ticket_status", 100), ("timezone", 100),
                           ("location_evidence", 300)):
            value = raw.get(key, "")
            if value is None:
                value = ""
            if not isinstance(value, str) or len(value) > limit:
                raise ValidationError("Invalid or oversized event field: " + key)
            event[key] = value.strip()
        if not event["venue"] or not event["artists"]:
            raise ValidationError("Event venue and title are required.")
        natural = canonical_json([date, normalized(event["venue"]), normalized(event["artists"])])
        external = event["external_identity"]
        identity = external or "natural:" + natural
        row = connection.execute("SELECT * FROM events WHERE identity_key=?", (identity,)).fetchone()
        if row is None:
            candidates = connection.execute("SELECT * FROM events WHERE natural_key=?", (natural,)).fetchall()
            if external:
                candidates = [row for row in candidates if row["identity_kind"] == "natural"]
            if len(candidates) == 1:
                row = candidates[0]
            elif len(candidates) > 1:
                raise ValidationError("Event identity is ambiguous; retain separate identified performances for review.")
        if row is not None:
            # Sparse observations must not erase details absent from the new input.
            previous = json.loads(row["detail"])
            event = {key: event[key] if key in raw else previous.get(key, "") for key in event}
            if row["identity_kind"] == "external" and not external:
                identity = row["identity_key"]
                external = identity
                event["external_identity"] = identity
        detail = canonical_json(event)
        fingerprint = hashlib.sha256(detail.encode()).hexdigest()
        timestamp = now()
        source = event.get("source_url", "")
        if row is None:
            event_id = uuid.uuid4().hex
            connection.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                event_id, identity, "external" if external else "natural", natural, event["date"], event["time"],
                event["venue"], event["artists"], event["url"], detail, fingerprint,
                "needs_review" if retrieved_at else "imported", timestamp, timestamp, retrieved_at, source))
            connection.execute("INSERT INTO event_changes(event_id,changed_at,kind,new_detail) VALUES(?,?,?,?)", (event_id, timestamp, "added", detail))
            return "added"
        event_id = row["id"]
        if fingerprint == row["fingerprint"]:
            if retrieved_at:
                connection.execute("UPDATE events SET last_retrieved_at=? WHERE id=?", (retrieved_at, event_id))
            return "unchanged"
        connection.execute("UPDATE events SET identity_key=?,identity_kind=?,natural_key=?,date=?,time=?,venue=?,artists=?,url=?,detail=?,fingerprint=?,status='needs_review',updated_at=?,last_retrieved_at=COALESCE(?,last_retrieved_at),source_url=? WHERE id=?", (
            identity, "external" if external else "natural", natural, event["date"], event["time"], event["venue"],
            event["artists"], event["url"], detail, fingerprint, timestamp, retrieved_at, source, event_id))
        connection.execute("INSERT INTO event_changes(event_id,changed_at,kind,previous_detail,new_detail) VALUES(?,?,?,?,?)", (event_id, timestamp, "updated", row["detail"], detail))
        return "updated"

    def import_data(self, data):
        rows = data.get("events") if isinstance(data, dict) else data
        if not isinstance(rows, list) or len(rows) > MAX_EVENTS_PER_IMPORT:
            raise ValidationError("Import must contain an events list with at most 20,000 records.")
        counts = {"total": len(rows), "added": 0, "updated": 0, "unchanged": 0, "rejected": 0, "errors": []}
        with self.connection() as connection:
            for number, event in enumerate(rows, 1):
                try:
                    counts[self.ingest(connection, event)] += 1
                except ValidationError as exc:
                    counts["rejected"] += 1
                    if len(counts["errors"]) < 10:
                        counts["errors"].append("Record " + str(number) + ": " + str(exc))
        return counts

    def import_file(self, filename):
        path = Path(filename)
        if path.stat().st_size > MAX_IMPORT_BYTES:
            raise ValidationError("Import file exceeds the 8 MB limit.")
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise ValidationError("Import file is not valid JSON.") from exc
        return self.import_data(data)

    def collected_events(self):
        with self.connection() as connection:
            rows = connection.execute("SELECT id,detail,last_retrieved_at,status FROM events WHERE last_retrieved_at IS NOT NULL ORDER BY date,time,venue,artists")
            result = []
            for row in rows:
                event = json.loads(row["detail"])
                event.update(id=row["id"], last_retrieved_at=row["last_retrieved_at"], review_state=row["status"])
                result.append(event)
            return result

    def upcoming_events(self, today=None):
        today = today or dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        return [e for e in self.collected_events() if e["date"] >= today
                and e.get("reported_status") != "EventCancelled" and not location_conflict(e)]

    def review(self, upcoming_only=False):
        with self.connection() as connection:
            count = connection.execute("SELECT count(*) FROM events").fetchone()[0]
            events = [dict(row) for row in connection.execute("SELECT id,date,time,artists,venue,status,last_retrieved_at FROM events ORDER BY date,venue,artists LIMIT 200")]
            latest = connection.execute("SELECT * FROM runs ORDER BY started_at DESC,rowid DESC LIMIT 1").fetchone()
            if upcoming_only:
                events = [{**e, "status":e["review_state"]} for e in self.upcoming_events()[:200]]
            return {"count": count, "shown": len(events), "events": events, "sources": self.source_list(), "last_run": dict(latest) if latest else None}


class Research:
    def __init__(self, store, fetcher=None, source_policies=None):
        self.store = store
        self.fetcher = fetcher or SafeHTTP()
        self.source_policies = _prepare_source_policies(source_policies)
        self._lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.running = False
        self.current_source = None
        self.last_error = None

    def status(self):
        with self._lock:
            return {"running": self.running, "stopping": self.running and self.stop_event.is_set(),
                    "current_source": self.current_source, "last_error": self.last_error}

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True  # Claim synchronously, before starting the thread.
            self.last_error = None
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, name="manual-research", daemon=True)
            try:
                self.thread.start()
            except Exception:
                self.running = False
                raise
            return True

    def stop(self):
        self.stop_event.set()

    def _run(self):
        run_id, run_state = uuid.uuid4().hex, "completed"
        totals = {"sources_checked": 0, "sources_failed": 0, "added": 0, "updated": 0,
                  "unchanged": 0, "rejected": 0, "extracted_events": 0,
                  "accepted_events": 0, "location_rejected_events": 0}
        try:
            with self.store.connection() as connection:
                connection.execute("INSERT INTO runs(id,started_at,state) VALUES(?,?,'running')", (run_id, now()))
            for source in self.store.source_list():
                if self.stop_event.is_set():
                    run_state = "stopped"
                    break
                with self._lock:
                    self.current_source = source["url"]
                started = now()
                with self.store.connection() as connection:
                    connection.execute("UPDATE sources SET state='running',last_attempt_at=?,last_error=NULL WHERE url=?", (started, source["url"]))
                    cursor = connection.execute("INSERT INTO source_runs(run_id,source_url,started_at,state) VALUES(?,?,?,'running')", (run_id, source["url"], started))
                    source_run = cursor.lastrowid
                page, error, source_state = None, None, "success"
                counts = _source_counts()
                try:
                    page = self.fetcher.fetch(source["url"], self.stop_event)
                    policy = self.source_policies.get(source["url"])
                    if hasattr(page, "parsed_events"):
                        events, parsing = page.parsed_events, page.parsing
                    else:
                        events, parsing = extract_events(page.body.decode("utf-8", "replace"), page.final_url,
                                                         source["venue"], capture_location=policy is not None)
                    if self.stop_event.is_set():
                        raise Stopped()
                    counts.update(parsing)
                    counts["rejected"] += parsing["rejected_events"]
                    counts["extracted_events"] = len(events)
                    with self.store.connection() as connection:
                        for event in events:
                            if self.stop_event.is_set():
                                raise Stopped()
                            if policy is not None:
                                attributed, reason = _apply_source_policy(event, policy)
                                if reason:
                                    counts["rejected"] += 1
                                    counts["location_rejected_events"] += 1
                                    reasons = counts["location_rejection_reasons"]
                                    reasons[reason] = reasons.get(reason, 0) + 1
                                    if len(counts["location_review_samples"]) < MAX_LOCATION_REVIEW_SAMPLES:
                                        counts["location_review_samples"].append({
                                            "reason": reason, "date": event["date"],
                                            "artists": event["artists"][:300],
                                            "reported_venue": " | ".join(event.get("_reported_locations", []))[:300],
                                            "url": event["url"][:2048],
                                        })
                                    continue
                                event = attributed
                            try:
                                counts[self.store.ingest(connection, event, page.retrieved_at)] += 1
                                counts["accepted_events"] += 1
                            except ValidationError:
                                counts["rejected"] += 1
                    if parsing.get("malformed_scripts", 0) or counts["rejected"]:
                        source_state = "parse_warning"
                    elif not events:
                        source_state = "success_no_events"
                    totals["sources_checked"] += 1
                    for key in ("added", "updated", "unchanged", "rejected", "extracted_events",
                                "accepted_events", "location_rejected_events"):
                        totals[key] += counts[key]
                except Stopped:
                    source_state, run_state = "stopped", "stopped"
                    counts = _source_counts()
                except Exception as exc:
                    source_state = "error"
                    error = str(exc)[:300] or type(exc).__name__
                    counts = _source_counts()
                    totals["sources_failed"] += 1
                finished = now()
                with self.store.connection() as connection:
                    connection.execute("UPDATE source_runs SET finished_at=?,state=?,http_status=?,final_url=?,summary=?,error=? WHERE id=?", (finished, source_state, page.status if page else None, page.final_url if page else None, canonical_json(counts), error, source_run))
                    if source_state in ("success", "success_no_events", "parse_warning"):
                        connection.execute("UPDATE sources SET state=?,last_success_at=?,last_finished_at=?,failure_count=0,last_error=NULL,last_final_url=? WHERE url=?", (source_state, page.retrieved_at, finished, page.final_url, source["url"]))
                    else:
                        connection.execute("UPDATE sources SET state=?,last_finished_at=?,failure_count=failure_count+?,last_error=? WHERE url=?", (source_state, finished, 1 if source_state == "error" else 0, error, source["url"]))
                if run_state == "stopped":
                    break
            if self.stop_event.is_set():
                run_state = "stopped"
            elif totals["sources_failed"]:
                run_state = "completed_with_errors"
        except Exception as exc:
            run_state = "error"
            with self._lock:
                self.last_error = str(exc)[:300]
        finally:
            try:
                with self.store.connection() as connection:
                    connection.execute("UPDATE runs SET finished_at=?,state=?,summary=? WHERE id=?", (now(), run_state, canonical_json(totals), run_id))
            finally:
                with self._lock:
                    self.running = False
                    self.current_source = None
