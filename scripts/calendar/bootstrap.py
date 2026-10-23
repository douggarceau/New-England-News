"""Offline setup for the bundled Boston pilot. No network calls at startup."""

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit
from core import ValidationError, canonical_json, now
from network import LocalNetworkHTTP

SETUP_VERSION = "boston-live-v0.6-2026-10-23"
CALENDAR_HASH = "c454c00821811af68c32cf387914631d6ec5feb000bc82e460aab8a6899cd039"

# Exact, explicitly supported venue labels. Ambiguous operator names are excluded.
ALIASES = {
    "City Winery Boston": ["City Winery Boston Main Stage", "City Winery - Boston Main Stage", "Boston Main Stage", "Main Stage"],
    "City Winery Haymarket Lounge": ["City Winery Haymarket Lounge", "City Winery Boston Haymarket Lounge", "Haymarket Lounge", "Boston Haymarket Lounge"],
    "Middle East Upstairs": ["Middle East Upstairs", "The Middle East Upstairs", "Middle East - Upstairs"],
    "Middle East Downstairs": ["Middle East Downstairs", "The Middle East Downstairs", "Middle East - Downstairs"],
    "Middle East Corner": ["Middle East Corner", "Middle East Corner/Bakery", "Middle East Corner-Bakery", "The Middle East Corner", "Middle East - Corner", "Middle East - Corner/Bakery"],
    "Middle East ZuZu": ["Middle East ZuZu", "ZuZu", "Zuzu", "Middle East - ZuZu"],
    "Sonia": ["Sonia", "Sonia Live Music Venue"],
    "The Sinclair": ["The Sinclair", "Sinclair"],
    "Brighton Music Hall": ["Brighton Music Hall", "Brighton Music Hall presented by Citizens"],
    "Paradise Rock Club": ["Paradise Rock Club", "Paradise Rock Club presented by Citizens"],
    "House of Blues Boston": ["House of Blues Boston Music Hall", "House of Blues Boston - Music Hall", "Citizens House of Blues Boston Music Hall", "Citizens House of Blues Boston - Music Hall"],
    "Club Passim": ["Club Passim", "Passim"],
    "The Rockwell": ["The Rockwell", "Rockwell"],
    "Wilbur Theatre": ["Wilbur Theatre", "The Wilbur", "The Wilbur Theatre"],
    "MGM Music Hall at Fenway": ["MGM Music Hall at Fenway", "MGM Music Hall at Fenway presented by Jameson"],
}
REQUIRE_LOCATION = {"The Sinclair", "House of Blues Boston", "Club Passim", "The Rockwell", "Symphony Hall", "Deep Cuts", "Big Night Live"}


def load_registry(root):
    path = Path(root) / "venue-sources.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValidationError("The bundled venue list is missing or unreadable. Extract the complete ZIP again.") from exc
    rows = registry.get("sources") if isinstance(registry, dict) else None
    if not isinstance(rows, list) or len(rows) != 25:
        raise ValidationError("The prepared venue list must contain exactly 25 entries.")
    names = set()
    groups = OrderedDict()
    gaps = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("venue"), str) or not row["venue"].strip():
            raise ValidationError("The prepared venue list contains an invalid entry.")
        name = row["venue"]
        if name in names:
            raise ValidationError("The prepared venue list contains a duplicate venue.")
        names.add(name)
        url = row.get("calendar_url")
        if url is None:
            gaps.append(name)
            continue
        try:
            parts = urlsplit(url)
            valid = (isinstance(url, str) and len(url) <= 2048 and parts.scheme == "https"
                     and parts.hostname and parts.username is None and parts.password is None
                     and parts.port in (None, 443) and not parts.fragment)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValidationError("A bundled calendar URL is invalid.")
        groups.setdefault(url, []).append(row)
    if len(groups) != 20 or gaps:
        raise ValidationError("The bundled source totals do not match the prepared pilot.")
    return registry, groups, gaps


def source_policies(groups):
    result = {}
    for url, rows in groups.items():
        aliases = {}
        for row in rows:
            name = row["venue"]
            for alias in ALIASES.get(name, [name]):
                aliases[alias] = name
        shared = len(rows) > 1
        result[url] = {
            "require_explicit_location": shared or any(row["venue"] in REQUIRE_LOCATION for row in rows),
            "fallback_venue": "" if shared else rows[0]["venue"],
            "aliases": aliases,
            "calendar_default": "Club Passim" if rows[0]['venue'] == 'Club Passim' else '',
        }
    return result


def prepare_store(store, root):
    """Seed once, transactionally. Never reapply an old baseline on later launches."""
    registry, groups, gaps = load_registry(root)
    with store.connection() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS pilot_setup (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        existing = connection.execute("SELECT value FROM pilot_setup WHERE key='initial_setup'").fetchone()
        if existing:
            setup = json.loads(existing["value"])
            if setup.get('version') != SETUP_VERSION:
                # Add newly resolved sources without overwriting imported events
                # or user-edited source labels, and record the upgrade once.
                for url, rows in groups.items():
                    connection.execute('INSERT OR IGNORE INTO sources(url,venue) VALUES(?,?)',
                                       (url, rows[0]['venue']))
                setup.update(version=SETUP_VERSION, venues_with_calendar_routes=25,
                             bundled_source_count=len(groups), unresolved_venues=gaps)
                connection.execute("UPDATE pilot_setup SET value=? WHERE key='initial_setup'", (canonical_json(setup),))
            setup["initialized_this_launch"] = False
            return setup, source_policies(groups)

    path = Path(root) / "baseline-calendar.json"
    try:
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != CALENDAR_HASH:
            raise ValidationError("The bundled reference calendar failed its integrity check. Extract the complete ZIP again.")
        baseline = json.loads(content)
        events = baseline["events"]
        if not isinstance(events, list) or len(events) != 776:
            raise ValidationError("The bundled reference calendar must contain 776 records.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("The bundled reference calendar is missing or unreadable. Extract the complete ZIP again.") from exc

    # The application holds its process lock before calling this function.
    with store.connection() as connection:
        existing_count = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        imported = {"added": 0, "updated": 0, "unchanged": 0, "rejected": 0}
        if not existing_count:
            for event in events:
                imported[store.ingest(connection, event)] += 1
        sources_added = 0
        for url, rows in groups.items():
            if len(rows) == 1:
                label = rows[0]["venue"]
            elif rows[0].get("shared_source_key") == "city_winery_boston":
                label = "City Winery Boston — two rooms"
            else:
                label = "Middle East and Sonia — five rooms"
            cursor = connection.execute("INSERT OR IGNORE INTO sources(url,venue) VALUES(?,?)", (url, label))
            sources_added += cursor.rowcount
        setup = {
            "version": SETUP_VERSION,
            "initialized_at": now(),
            "venue_count": 25,
            "venues_with_calendar_routes": 25,
            "bundled_source_count": len(groups),
            "sources_added": sources_added,
            "unresolved_venues": gaps,
            "reference_record_count": 776,
            "baseline_import": imported,
            "baseline_skipped_to_preserve_existing_data": bool(existing_count),
            "calendar_sha256": CALENDAR_HASH,
            "parser_coverage": "Not established by setup; source collection must be tested.",
        }
        connection.execute("INSERT INTO pilot_setup(key,value) VALUES('initial_setup',?)", (canonical_json(setup),))
    setup["initialized_this_launch"] = True
    return setup, source_policies(groups)


def build_report(store, setup, research_status):
    with store.connection() as connection:
        latest = connection.execute("SELECT * FROM runs ORDER BY started_at DESC,rowid DESC LIMIT 1").fetchone()
        run = dict(latest) if latest else None
        attempts = []
        if run:
            run["summary"] = json.loads(run["summary"])
            for row in connection.execute("SELECT source_url,started_at,finished_at,state,http_status,final_url,summary,error FROM source_runs WHERE run_id=? ORDER BY id", (run["id"],)):
                item = dict(row)
                item["summary"] = json.loads(item["summary"])
                attempts.append(item)
        collected = connection.execute("SELECT count(*) FROM events WHERE last_retrieved_at IS NOT NULL").fetchone()[0]
        samples = []
        for row in connection.execute("SELECT detail,last_retrieved_at,status FROM events WHERE last_retrieved_at IS NOT NULL ORDER BY last_retrieved_at DESC LIMIT 50"):
            item = json.loads(row["detail"])
            item["last_retrieved_at"] = row["last_retrieved_at"]
            item["review_state"] = row["status"]
            samples.append(item)
        total = connection.execute("SELECT count(*) FROM events").fetchone()[0]
    return {
        "title": "Boston pilot collection report",
        "created_at": now(),
        "setup": setup,
        "research_status": research_status,
        "latest_run": run,
        "source_attempts": attempts,
        "sources": store.source_list(),
        "stored_event_count": total,
        "events_with_retrieval_time": collected,
        "collected_events": store.collected_events(),
        "upcoming_events": store.upcoming_events(),
        "upcoming_event_count": len(store.upcoming_events()),
        "collected_event_sample": samples,
        "sample_limit": 50,
        "sample_is_complete": collected <= 50,
        "interpretation": [
            "The baseline is historical imported data, not newly collected or independently verified listings.",
            "A completed pass does not establish complete calendar coverage. Prepared official pages and their public event feeds are read in a bounded pass; automatic pagination is not included.",
            "The upcoming view excludes past dates and explicit cancellations; the imported history and source observations are retained in the archive.",
            "A fetch failure, unsupported page or zero extracted events does not establish that a venue has no shows or that an event was cancelled.",
            "All collected changes remain for review. This program has no publishing, schedules or model API calls.",
        ],
    }
