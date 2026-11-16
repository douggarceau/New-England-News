#!/usr/bin/env python3
"""Banned-words guard for every news site (owner rule, Nov. 16, 2026).

The words "art center" / "arts center" (and "art centre") must never appear on the sites.
This started because "Jamestown Arts Center" stories kept being written from jamestownarts.com,
which is an arts group in Jamestown, NORTH DAKOTA.

What it does, on index.html's STORIES array and every data/*.json file:
  1. Real venues whose names contain the words are renamed to a short name, so their shows stay
     (Providence Performing Arts Center -> PPAC, WaterFire Arts Center -> WaterFire Providence, ...).
  2. Any story, event, listing or row that still mentions an arts center, "JAC" or
     jamestownarts.com is removed. Text that is not part of a list loses just the sentence.
  3. Share pages (s/<slug>/) for removed stories are deleted.
Runs in the share-pages workflow after every push, before share_pages.py.

Usage: python3 tools/banned_words.py [repo_root] [--dry-run]
Standard library only. No AI.
"""
import json, os, re, shutil, sys

ROOT = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DRY = '--dry-run' in sys.argv

# Real venues: keep the event, use a name without the banned words. Longest first.
RENAMES = [
    (r'(?:the )?Providence Performing Arts Center \(PPAC\)', 'PPAC'),
    (r'\bthe Providence Performing Arts Center', 'PPAC'),
    (r'Providence Performing Arts Center', 'PPAC'),
    (r'Waterfire & Waterfire Arts Center', 'WaterFire Providence'),
    (r'\bthe WaterFire Arts Center', "WaterFire Providence's building"),
    (r'WaterFire Arts Center', 'WaterFire Providence'),
    (r'(?:the )?URI Fine Arts Center', 'URI Fine Arts'),
    (r'(?:the )?Lindemann Performing Arts Center', "Brown's Lindemann Center"),
    (r'(?:the )?Four Corners Arts Center', 'Tiverton Four Corners'),
    (r'(?:the )?Fremont Abbey Arts Center', 'Fremont Abbey'),
    (r'(?:the )?Cannonball Arts Center', 'Cannonball Arts'),
]
# Site-only extras: tools/banned_extra.json {"renames": [[regex, replacement], ...], "ban": [regex, ...]}
# (e.g. names the owner may not use on one site). Renames run first; banned items/sentences are removed.
EXTRA = {}
_xp = os.path.join(ROOT, 'tools', 'banned_extra.json')
if os.path.exists(_xp): EXTRA = json.load(open(_xp, encoding='utf-8'))
RENAMES = [tuple(x) for x in EXTRA.get('renames', [])] + RENAMES
RENAMES = [(re.compile(p, re.I), r) for p, r in RENAMES]
URI_CTX = re.compile(r'\bURI\b|University of Rhode Island|Kingston', re.I)
URI_FAC = re.compile(r'(?:the )?Fine Arts Center', re.I)

BAN = re.compile('|'.join([r'\barts?[\s\-]+cent(?:er|re)s?\b', r'jamestownarts\.com', r'jamestown fine arts\b'] + EXTRA.get('ban', [])), re.I)
BAN_CASE = re.compile(r'\bJAC\b')  # Jamestown Arts Center's abbreviation (case-sensitive)
def banned(s): return bool(BAN.search(s) or BAN_CASE.search(s))
# link addresses are not seen by readers: only the two Jamestown arts-center sites count there
URL_BAN = re.compile(r'jamestownarts\.com|jamestownartcenter\.org', re.I)
URL_KEYS = {'url', 'source_url', 'source', 'src', 'w', 'link', 'href', 'apply_url', 'application_url'}
def is_url(s): return bool(re.match(r'\s*https?://\S+\s*$', s))
def vis_banned(s): return bool(URL_BAN.search(s)) if is_url(s) else banned(s)

stats = {'renamed': 0, 'removed': 0, 'sentences': 0, 'pages': 0}
removed_titles = []

def rename(s):
    n = s
    for p, r in RENAMES: n = p.sub(r, n)
    if URI_CTX.search(n): n = URI_FAC.sub('URI Fine Arts', n)
    if n != s: stats['renamed'] += 1
    return n

ABBR = re.compile(r'(?:\b[ap]\.m|\b(?:St|Ave|Rd|Dr|Mr|Mrs|Ms|No|Jan|Feb|Mar|Apr|Aug|Sept?|Oct|Nov|Dec|Jr|Sr|Inc|vs|Mt|Ft|U\.S)|\b[A-Z])\.$')
def split_sentences(s):
    """split on . ! ? but not after a.m./p.m., St., Nov., initials and similar"""
    out = []
    for piece in re.split(r'(?<=[.!?])\s+', s):
        if out and ABBR.search(out[-1]): out[-1] += ' ' + piece
        else: out.append(piece)
    return out

def drop_sentences(s):
    if is_url(s) or not banned(s): return s
    parts = split_sentences(s)
    keep = [p for p in parts if not banned(p)]
    stats['sentences'] += len(parts) - len(keep)
    return ' '.join(keep)

def text(x): return json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x

# fields that say what an item IS: if one of these is banned, the whole item goes (not just a sentence)
KEY = ('title', 'name', 'n', 'artists', 'dek', 'slug', 'venue', 'v', 'org', 'employer', 'where', 'location',
       'place', 'host', 'url', 'source_url', 'source', 'src', 'w', 'link', 'href', 'apply_url', 'application_url', 'a')
def key_banned(d):
    for k in KEY:
        v = d.get(k)
        if isinstance(v, str) and vis_banned(rename(v)): return True
        if isinstance(v, list) and any(isinstance(s, str) and vis_banned(rename(s)) for s in v): return True
    return False

def visible(x):
    """the text of an item a reader can see (link addresses checked only for the Jamestown arts sites)"""
    if isinstance(x, str): return x if not is_url(x) else ('jamestownarts.com' if URL_BAN.search(x) else '')
    if isinstance(x, list): return ' | '.join(visible(v) for v in x)
    if isinstance(x, dict): return ' | '.join(visible(v) for v in x.values())
    return ''

def clean_table(s):
    """'#T {json}' table strings in story bodies: drop only the rows that mention the words"""
    try: T = json.loads(s[3:])
    except Exception: return drop_sentences(s)
    if isinstance(T, dict) and isinstance(T.get('rows'), list):
        T['title'] = rename(T.get('title', '')) if isinstance(T.get('title'), str) else T.get('title')
        rows = [[rename(c) if isinstance(c, str) else c for c in r] if isinstance(r, list) else r for r in T['rows']]
        keep = [r for r in rows if not banned(visible(r))]
        stats['removed'] += len(rows) - len(keep)
        if not keep or banned(visible(T.get('title', ''))): return ''
        T['rows'] = keep
        return '#T ' + json.dumps(T, ensure_ascii=False)
    return drop_sentences(s)

def clean(x, in_list=False):
    if isinstance(x, str):
        x = rename(x)
        if is_url(x): return x
        return clean_table(x) if x.startswith('#T ') else drop_sentences(x)
    if isinstance(x, list):
        out = []
        for v in x:
            if isinstance(v, dict) and key_banned(v):
                stats['removed'] += 1
                removed_titles.append(str(v.get('title') or v.get('name') or v.get('n') or v.get('artists') or '')[:80])
                continue
            if isinstance(v, str):
                v = rename(v)
                if is_url(v):
                    if URL_BAN.search(v): stats['removed'] += 1; continue
                    out.append(v); continue
                v = clean_table(v) if v.startswith('#T ') else drop_sentences(v)
                if v.strip(): out.append(v)
                continue
            v = clean(v, True)
            if banned(visible(v)):
                stats['removed'] += 1
                if isinstance(v, dict): removed_titles.append(str(v.get('title') or v.get('name') or v.get('n') or v.get('artists') or '')[:80])
                else: removed_titles.append(text(v)[:80])
                continue
            out.append(v)
        return out
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    return x

def write(p, s):
    if not DRY: open(p, 'w', encoding='utf-8').write(s)

def main():
    changed = []
    # 1. index.html (and any preview copies): the STORIES array, then any other one-line
    #    array entries (e.g. the newspaper ISSUES list) that mention the words
    slugs = None
    pages = [os.path.join(ROOT, 'index.html')] + [os.path.join(ROOT, x, 'index.html') for x in ('preview', 'preview-light')]
    for n, p in enumerate(pages):
        if not os.path.exists(p): continue
        t = open(p, encoding='utf-8').read(); t0 = t; i = t.find('const STORIES=')
        if i >= 0:
            a = i + len('const STORIES=')
            L, end = json.JSONDecoder().raw_decode(t[a:])
            C = clean(L)
            if n == 0: slugs = {s.get('slug') for s in C if isinstance(s, dict)}
            if C != L: t = t[:a] + json.dumps(C, ensure_ascii=False, separators=(',', ':')) + t[a + end:]
        lines = t.split('\n'); keep = []
        for ln in lines:
            if re.match(r'\s*\[\s*["\'].*\]\s*,?\s*$', ln) and len(ln) < 2000 and (banned(rename(ln)) or URL_BAN.search(ln)):
                stats['removed'] += 1; removed_titles.append(ln.strip()[:80]); continue
            keep.append(ln)
        t = '\n'.join(keep)
        if t != t0: write(p, t); changed.append(os.path.relpath(p, ROOT))
    # 2. data/*.json
    d = os.path.join(ROOT, 'data')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not f.endswith('.json'): continue
        fp = os.path.join(d, f); raw = open(fp, encoding='utf-8').read()
        if not banned(raw) and not any(pp.search(raw) for pp, _ in RENAMES): continue
        D = json.loads(raw); C = clean(D)
        if C != D:
            ind = 1 if raw.startswith('{\n') or raw.startswith('[\n') else None
            sep = None if ind else (',', ':')
            write(fp, json.dumps(C, ensure_ascii=False, indent=ind, separators=sep) + ('\n' if raw.endswith('\n') else '')); changed.append('data/' + f)
    # 2b. headline cards that point at a story which is no longer in STORIES
    hp = os.path.join(ROOT, 'data', 'headlines.json')
    if slugs is not None and os.path.exists(hp):
        H = json.load(open(hp, encoding='utf-8')); items = H.get('items') if isinstance(H, dict) else H
        if isinstance(items, list):
            keep = [x for x in items if not (isinstance(x, dict) and x.get('story') and x['story'] not in slugs)]
            if len(keep) != len(items):
                stats['removed'] += len(items) - len(keep)
                if isinstance(H, dict): H['items'] = keep
                else: H = keep
                raw = open(hp, encoding='utf-8').read(); ind = 1 if raw.startswith(('{\n', '[\n')) else None
                write(hp, json.dumps(H, ensure_ascii=False, indent=ind, separators=None if ind else (',', ':')) + '\n')
                if 'data/headlines.json' not in changed: changed.append('data/headlines.json')
    # 3. share pages of stories no longer in STORIES (pages of current stories are rebuilt by share_pages.py):
    #    rename venues in place; if the page still has banned words, replace it with a plain redirect
    #    to the home page so old shared links still land somewhere.
    sd = os.path.join(ROOT, 's')
    if slugs is not None and os.path.isdir(sd):
        for slug in sorted(os.listdir(sd)):
            pp = os.path.join(sd, slug, 'index.html')
            if slug in slugs or not os.path.exists(pp): continue
            old = open(pp, encoding='utf-8').read()
            if not banned(old) and not URL_BAN.search(old) and not any(p.search(old) for p, _ in RENAMES): continue
            new = rename(old)
            if banned(new) or URL_BAN.search(new):
                new = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
                       '<meta http-equiv="refresh" content="0;url=/"><link rel="canonical" href="/"><title>Moved</title>'
                       '<script>location.replace("/")</script></head><body><a href="/">Go to the home page</a></body></html>\n')
                stats['pages'] += 1
                sh = os.path.join(ROOT, 'img', 'share')
                for f in (os.listdir(sh) if os.path.isdir(sh) else []):
                    if f.rsplit('-', 1)[0] == slug and not DRY: os.remove(os.path.join(sh, f))
            if new != old:
                write(pp, new); changed.append('s/' + slug)
    # 4. report anything left in the pages readers see (other embedded text the rules above don't reach)
    for p in pages:
        if os.path.exists(p):
            for m in BAN.finditer(open(p, encoding='utf-8').read() if DRY or True else ''):
                print('  WARNING still in', os.path.relpath(p, ROOT), ':', m.group(0)); break
    print(('DRY RUN ' if DRY else '') + 'banned words:', stats, '| changed:', ', '.join(changed) or 'nothing')
    for t in removed_titles[:400]: print('  removed:', t)

if __name__ == '__main__':
    main()
