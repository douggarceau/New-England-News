"""Daily bounded collection; retains last observed rows when a source fails."""
import datetime as dt
import html
import json
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import bootstrap
import core
from collector import CalendarCollector

ROOT = Path(__file__).resolve().parents[2]


def refresh(feed_path, transport=None, today=None):
    previous = json.loads(feed_path.read_text())
    registry, groups, _ = bootstrap.load_registry(Path(__file__).parent)
    managed = {row['venue'] for row in registry['sources']}
    policies = bootstrap.source_policies(groups)
    today = today or dt.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    with tempfile.TemporaryDirectory() as temp:
        store = core.Store(Path(temp)/'calendar.sqlite')
        for url, rows in groups.items():
            store.save_source(url, rows[0]['venue'])
        # Preserve genuine observation timestamps; importing is not a fresh fetch.
        with store.connection() as connection:
            for event in previous['events']:
                if event['venue'] in managed:
                    stamp = event.get('last_retrieved_at')
                    if not stamp:
                        raise ValueError('Managed event lacks its observation timestamp')
                    store.ingest(connection, event, stamp)
        research = core.Research(store, CalendarCollector(policies, transport=transport,
                                 minimum_spacing=0 if transport else 2), policies)
        research._run()
        with store.connection() as connection:
            run = dict(connection.execute('SELECT * FROM runs ORDER BY started_at DESC LIMIT 1').fetchone())
            run['summary'] = json.loads(run['summary'])
            attempts = []
            for row in connection.execute('SELECT * FROM source_runs'):
                entry = dict(row); entry['summary'] = json.loads(entry['summary']); attempts.append(entry)
        if run['state'] not in ('completed', 'completed_with_errors') or not run['summary']['sources_checked']:
            raise RuntimeError('No source could be checked; published calendar left untouched')
        managed_events = store.upcoming_events(today=today)
        # Keep listings from other venues, including editorial work outside this collector.
        other = [e for e in previous['events'] if e['venue'] not in managed and e['date'] >= today]
        metadata = {e['venue']: e for e in previous['events']}
        for event in managed_events:
            event.pop('id', None)  # Temporary database IDs must not churn the public feed.
            event.pop('review_state', None)
            event['artists'] = html.unescape(html.unescape(event['artists']))
            event['hood'] = event.get('hood') or metadata.get(event['venue'], {}).get('hood', '')
            event['genre'] = event.get('genre') or 'other'
        events = sorted(other + managed_events, key=lambda e:(e['date'],e.get('time',''),e['venue'],e['artists']))
        if not events or len(events) > 20000:
            raise ValueError('Unexpected calendar size; existing file retained')
        result = dict(previous, asof=today, updated_at=core.now(), events=events,
                      managed_venues=sorted(managed), last_check=run)
        result['sources_last_run'] = dict(previous.get('sources_last_run', {}))
        for entry in attempts:
            if entry['state'] in ('success', 'parse_warning', 'success_no_events'):
                result['sources_last_run'][entry['source_url']] = entry['finished_at']
        result['source_status'] = [{k:e[k] for k in ('source_url','state','finished_at','error','summary')} for e in attempts]
        staged = feed_path.with_suffix('.tmp')
        staged.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        staged.replace(feed_path)
        return run['summary']


if __name__ == '__main__':
    print(json.dumps(refresh(ROOT/'data/cal.json'), sort_keys=True))
