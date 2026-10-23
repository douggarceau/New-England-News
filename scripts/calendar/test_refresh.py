import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import refresh

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

if __name__=='__main__':unittest.main()
