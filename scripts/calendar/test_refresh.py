import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refresh
import threading
from collector import CalendarCollector, CITY_FEED, TICKETMASTER_VENUES
from urllib.parse import urlsplit, parse_qs

class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'cal.json'
        self.event=dict(date='2026-11-01',time='19:00',venue='Royale',artists='Example',url='https://royaleboston.com/calendar',source_url='https://royaleboston.com/calendar',external_identity='royale:event:one',last_retrieved_at='2026-10-23T22:00:00+00:00')
        self.other=dict(date='2026-11-01',time='20:00',venue='Other Venue',artists='Preserve',url='https://example.com')
        self.path.write_text(json.dumps({'events':[self.event,self.other]}))
    def tearDown(self): self.tmp.cleanup()
    def test_total_failure_preserves_exact_published_bytes(self):
        before=self.path.read_bytes()
        class Failed:
            def __init__(self,*a,**k): pass
            def fetch(self,*a): raise RuntimeError('offline')
        with patch.object(refresh,'CalendarCollector',Failed):
            with self.assertRaises(RuntimeError):refresh.refresh(self.path,today='2026-10-23')
        self.assertEqual(before,self.path.read_bytes())
    def test_cancelled_removed_other_venues_retained_partial_failures_recorded(self):
        event=dict(self.event,reported_status='EventCancelled',_reported_locations=['Royale'])
        class Partial:
            def __init__(self,*a,**k): pass
            def fetch(self,url,stop):
                if url!='https://royaleboston.com/calendar':raise RuntimeError('offline')
                return SimpleNamespace(parsed_events=[event],parsing={'rejected_events':0,'malformed_scripts':0},status=200,final_url=url,retrieved_at='2026-10-24T10:00:00+00:00')
        with patch.object(refresh,'CalendarCollector',Partial): result=refresh.refresh(self.path,today='2026-10-23')
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['events'],[self.other]); self.assertEqual(result['sources_failed'],19)

class DirectFeedTests(unittest.TestCase):
    def test_wilbur_early_and_late_performances_keep_separate_existing_ids(self):
        source='https://thewilbur.com/calendar/'
        class Transport:
            def fetch(self,url,stop,public_headers=None):
                events=[]
                for ticket,clock in [('0100654FA86FCA06','19:00'),('0100654FA86CC9F7','21:45')]:
                    events.append({'id':ticket,'name':'Anthony Jeselnik: Wrath of Man',
                        'url':'https://www.ticketmaster.com/event/'+ticket,
                        'dates':{'start':{'localDate':'2027-01-16','localTime':clock+':00'}},
                        '_embedded':{'venues':[{'name':'The Wilbur'}]}})
                return SimpleNamespace(body=json.dumps({'_embedded':{'events':events}}).encode(),final_url=url,status=200,retrieved_at='2026-10-23T23:00:00+00:00')
        result=CalendarCollector({source:{'fallback_venue':'Wilbur Theatre'}},transport=Transport(),minimum_spacing=0).fetch(source,threading.Event())
        self.assertEqual([e['external_identity'] for e in result.parsed_events],[
            'html:https://thewilbur.com/event/anthony-jeselnik-wrath-of-man/#2027-01-16T19:00',
            'html:https://thewilbur.com/event/anthony-jeselnik-wrath-of-man/#2027-01-16T21:45'])

    def test_ticketmaster_routes_and_existing_big_night_identity(self):
        for source, venue_id in TICKETMASTER_VENUES.items():
            calls=[]
            class Transport:
                def fetch(self,url,stop,public_headers=None):
                    calls.append(url)
                    body=json.dumps({'_embedded':{'events':[{
                        'id':'provider-id','name':'Example',
                        'url':'https://www.ticketmaster.com/event/0100651F7DBE59B7',
                        'dates':{'start':{'localDate':'2026-11-01','localTime':'19:00:00'},'timezone':'America/New_York'},
                        'info':'Doors 7pm / Show 8pm',
                        '_embedded':{'venues':[{'name':'Big Night Live'}]}
                    }]}}).encode()
                    return SimpleNamespace(body=body,final_url=url,status=200,retrieved_at='2026-10-23T23:00:00+00:00')
            venue='Big Night Live' if '/9293' in source else 'Example Venue'
            collector=CalendarCollector({source:{'fallback_venue':venue}},transport=Transport(),minimum_spacing=0)
            result=collector.fetch(source,threading.Event())
            self.assertEqual(len(calls),1)
            self.assertEqual(urlsplit(calls[0]).hostname,'app.ticketmaster.com')
            self.assertEqual(parse_qs(urlsplit(calls[0]).query)['venueId'],[venue_id])
            event=result.parsed_events[0]
            self.assertEqual((event['time'],event['doors_time']),('20:00','19:00'))
            if venue=='Big Night Live':
                self.assertEqual(event['external_identity'],'event-url:'+event['url'])

    def test_city_winery_direct_feed_preserves_explicit_room(self):
        calls=[]
        class Transport:
            def fetch(self,url,stop,public_headers=None):
                calls.append(url)
                body=b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:test\nDTSTART;TZID=America/New_York:20261101T190000\nSUMMARY:Example\nLOCATION:Haymarket Lounge at City Winery Boston\nURL:https://citywinery.com/example\nEND:VEVENT\nEND:VCALENDAR\n'
                return SimpleNamespace(body=body,final_url=url,status=200,retrieved_at='2026-10-23T23:00:00+00:00')
        source='https://citywinery.com/pages/events/boston'
        result=CalendarCollector({source:{}},transport=Transport(),minimum_spacing=0).fetch(source,threading.Event())
        self.assertEqual(calls,[CITY_FEED])
        self.assertEqual(result.parsed_events[0]['_reported_locations'],['City Winery Haymarket Lounge'])

if __name__=='__main__':unittest.main()
