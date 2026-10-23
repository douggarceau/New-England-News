"""Read public Royale and AXS calendar data; never execute source JavaScript."""
import base64
import datetime as dt
import json
import re
from urllib.parse import urlsplit

from adapters_boston_html import Tree, _event, _clock, _clean
from core import ValidationError

ROYALE_ORIGIN = "https://pggdjlwzqcnvjmmajjuj.supabase.co"
WAREHOUSE_URL = "https://www.axs.com/venues/131937/warehouse-xi-somerville-tickets?page=2"


def royale_config(script):
    if ROYALE_ORIGIN not in script or '.from("events")' not in script:
        raise ValidationError("Royale public calendar configuration changed.")
    for token in re.findall(r'"(eyJ[A-Za-z0-9_.-]+)"', script):
        try:
            payload = token.split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        except (ValueError, IndexError):
            continue
        if claims.get('role') == 'anon' and claims.get('ref') == 'pggdjlwzqcnvjmmajjuj':
            return token
    raise ValidationError("Royale anonymous public calendar key is unavailable.")


def _label_clock(text, label):
    match = re.search(r'\b' + label + r'\s*(?:at\s+|:\s*)?(\d{1,2}(?::\d{2})?\s*[ap]m)\b', text, re.I)
    return _clock(match[1]) if match else ''


def parse_royale(data, source_url):
    if isinstance(data, (str, bytes)):
        data = json.loads(data)
    if not isinstance(data, list) or len(data) > 1000:
        raise ValidationError("Unexpected Royale calendar response.")
    diag = {'adapter': 'royale_published_calendar', 'rejected_events': 0,
            'malformed_scripts': 0, 'relocated_events': 0,
            'coverage': 'published_feed', 'received_records': len(data),
            'pagination_detected': len(data) == 1000}
    events, seen = [], set()
    for row in data:
        try:
            if row.get('is_published') is not True:
                diag['rejected_events'] += 1
                continue
            title = _clean(row['title'])
            desc = _clean(row.get('description'))
            # Relocation is explicit; never relabel a moved show as Royale.
            if re.search(r'\bmoved\s+(?:from\s+Royale\s+)?to\b', title + ' ' + desc, re.I):
                diag['relocated_events'] += 1
                continue
            date = dt.date.fromisoformat(row['event_date']).isoformat()
            reported_time = row.get('event_time') or ''
            clock = dt.time.fromisoformat(reported_time).strftime('%H:%M') if reported_time else ''
            doors, show = _label_clock(desc, 'doors?'), _label_clock(desc, 'show')
            if show:
                clock = show
            elif doors and doors == clock:
                clock = ''
            status = re.sub(r'^[\[\s]+', '', title)
            event = _event(title, date + ('T' + clock if clock else ''),
                           row.get('ticket_url') or 'https://royaleboston.com/c/' + row['id'],
                           source_url, 'Royale', ['Royale'], status,
                           doors_time=doors, timezone='America/New_York',
                           location_evidence='official_venue_published_feed')
            event['external_identity'] = 'royale:event:' + str(row['id'])
            age = row.get('age_restriction')
            if age:
                event['ages'] = str(age)
            elif re.search(r'\ball ages\b', title + ' ' + desc, re.I):
                event['ages'] = 'All ages'
            if event['external_identity'] not in seen:
                seen.add(event['external_identity'])
                events.append(event)
        except (ValueError, TypeError, KeyError):
            diag['rejected_events'] += 1
    return events, diag


def parse_warehouse(text, source_url):
    root = Tree(text).root
    script = next((n for n in root.all('script') if n.attrs.get('id') == '__NEXT_DATA__'), None)
    if script is None:
        raise ValidationError('AXS public calendar data is missing.')
    data = json.loads(''.join(x for x in script.children if isinstance(x, str)))['props']['pageProps']
    venue = data['discoveryVenueData']
    if (str(venue.get('venueId')) != '131937' or venue.get('title') != 'Warehouse XI'
            or venue.get('city') != 'Somerville' or venue.get('state') != 'MA'):
        raise ValidationError('AXS page does not identify Warehouse XI in Somerville.')
    rows = data['venueEventsData']['eventItems']
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValidationError('Unexpected AXS calendar size.')
    diag = {'adapter': 'warehouse_axs_public_calendar', 'rejected_events': 0,
            'malformed_scripts': 0, 'received_records': len(rows),
            'available_records': data['venueEventsData'].get('totalEvents'),
            'pagination_detected': bool(data.get('nextPageUrl')),
            'coverage': 'published_ticketing_calendar'}
    events, seen = [], set()
    for row in rows:
        try:
            if (str(row.get('venueId')) != '131937' or row.get('venueTitle') != 'Warehouse XI'
                    or row.get('city') != 'Somerville' or row.get('state') != 'MA'):
                raise ValueError('Other venue')
            # Unknown status codes are held for review rather than called scheduled.
            if row.get('statusId') != 1:
                raise ValueError('Unrecognized ticketing status')
            start = row['date']
            if row.get('eventDateOnly') or row.get('hideEventTime'):
                start = start[:10]
            event = _event(row['title'], start, 'https://www.axs.com/events/' + str(row['id']),
                           source_url, 'Warehouse XI', ['Warehouse XI'],
                           timezone='America/New_York', location_evidence='explicit_ticketing_venue')
            event['external_identity'] = 'axs:event:' + str(row['id'])
            if event['external_identity'] not in seen:
                events.append(event)
                seen.add(event['external_identity'])
        except (ValueError, TypeError, KeyError):
            diag['rejected_events'] += 1
    return events, diag
