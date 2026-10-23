import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'research/celebrities/jay-leno-blackbird.json'
a = json.loads(path.read_text())
a['body'][3]['text'] = 'The proposed 6.2-liter V8, developed with Ilmor, has no turbochargers. Hennessey is targeting 800–850 horsepower and more than 9,000 rpm. Those are development targets for a car still several years from customer production.'
titles = [
    'Jay Leno on buying a Newport mansion and buying things he likes',
    'All new Hennessey Blackbird hypercar revealed',
    'Jay Leno’s Garage announces the Blackbird walkaround with Nathan Malinick'
]
for s, title in zip(a['source_notes'], titles):
    s['title'] = title
a['bodyparagraphs'] = [p['text'] for p in a['body']]
a['word_count'] = sum(len(p['text'].split()) for p in a['body'])
path.write_text(json.dumps(a, ensure_ascii=False, indent=2))

path = root / 'research/celebrities/vinny-paz-ten-years.json'
a = json.loads(path.read_text())
a['body'][0]['text'] = 'Vinny Paz had survived a broken neck and fought his way back into the ring. Seeing his parents on a movie screen made him cry.'
titles = [
    'Boxer Vinny Paz says Hollywood biopic made him cry',
    'Vinny Paz biography',
    'Vinny Paz professional fight record',
    'International Boxing Hall of Fame class of 2025',
    'Vinny Paz Hall of Fame profile',
    'International Boxing Hall of Fame official 2025 induction program',
    '2025 International Boxing Hall of Fame inductees announced',
    'Bleed for This official film and streaming listing'
]
for s, title in zip(a['source_notes'], titles):
    s['title'] = title
a['bodyparagraphs'] = [p['text'] for p in a['body']]
a['word_count'] = sum(len(p['text'].split()) for p in a['body'])
path.write_text(json.dumps(a, ensure_ascii=False, indent=2))

path = root / 'research/food/food-stories.json'
articles = json.loads(path.read_text())
for a in articles:
    if a['slug'].startswith('matunuck'):
        a['body'][4]['text'] = a['body'][4]['text'].replace('before the restaurant became the best-known part of Raso’s work.', 'before there was a restaurant.')
        a['bodyparagraphs'] = [p['text'] for p in a['body']]
        a['word_count'] = sum(len(p['text'].split()) for p in a['body'])
path.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
