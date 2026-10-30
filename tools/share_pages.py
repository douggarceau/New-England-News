#!/usr/bin/env python3
"""Build one small share page per story so Facebook, X and texts show the story itself.

For every story in index.html this writes:
  s/<slug>/index.html   share page with the story's headline, summary and card image
                        (people who open it are sent straight to the story on the site)
  img/share/<slug>-<hash>.jpg   1200x630 headline card used as the preview picture
Run from the repo root. Safe to run repeatedly; only changed stories are rewritten.
"""
import hashlib, html, json, os, re, shutil, sys
from PIL import Image, ImageDraw, ImageFont

SITE = 'https://thebostonrambler.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'tools', 'fonts')
LABEL = {'crime': 'Crime Watch', 'streets': 'Boston News', 'politics': 'City Hall', 'housing': 'Homes',
         'culture': 'Arts & Culture', 'music': 'Music', 'food': 'Food & Drink', 'people': 'People',
         'cover': 'Boston Stories', 'sports': 'Sports', 'stage': 'On Stage', 'business': 'Business',
         'news': 'Boston News', 'transit': 'Getting Around'}
NAVY, GOLD, CREAM = (10, 26, 51), (232, 184, 24), (248, 244, 234)


def stories():
    s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i = s.index('const STORIES=') + len('const STORIES=')
    arr, _ = json.JSONDecoder().raw_decode(s[i:])
    return [x for x in arr if x.get('slug') and x.get('title') and re.fullmatch(r'[a-z0-9-]+', x['slug'])]


def font(names, size):
    for n in names:
        for d in (FONTS, '/usr/share/fonts/truetype/dejavu'):
            p = os.path.join(d, n)
            if os.path.exists(p):
                f = ImageFont.truetype(p, size)
                try:
                    f.set_variation_by_name('Bold')
                except Exception:
                    pass
                return f
    return ImageFont.load_default()


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def card(x, out):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), NAVY)
    d = ImageDraw.Draw(im)
    mh = Image.open(os.path.join(ROOT, 'img', 'rambler-masthead.png')).convert('RGBA')
    mw = 520; mh = mh.resize((mw, int(mh.height * mw / mh.width)), Image.LANCZOS)
    im.paste(mh, ((W - mw) // 2, 34), mh)
    top = 34 + mh.height + 26
    lab = font(['LibreFranklin-Bold.ttf', 'DejaVuSans-Bold.ttf'], 26)
    t = LABEL.get(x.get('topic'), 'Boston Stories').upper()
    tw = d.textlength(t, font=lab)
    d.text(((W - tw) / 2, top), t, font=lab, fill=GOLD)
    top += 50
    # headline: biggest size that fits in 4 lines
    for size in range(76, 34, -2):
        f = font(['PlayfairDisplay-Bold.ttf', 'DejaVuSerif-Bold.ttf'], size)
        lines = wrap(d, x['title'], f, W - 140)
        lh = int(size * 1.14)
        if len(lines) <= 4 and top + lh * len(lines) <= H - 60:
            break
    y = top + (H - 60 - top - lh * len(lines)) // 2
    for ln in lines:
        lw = d.textlength(ln, font=f)
        d.text(((W - lw) / 2, y), ln, font=f, fill=CREAM)
        y += lh
    d.rectangle((0, H - 12, W, H), fill=GOLD)
    im.save(out, quality=88, optimize=True)


def page(x, img):
    e = lambda v: html.escape(v or '', quote=True)
    url = f'{SITE}/s/{x["slug"]}/'
    dest = f'/?story={x["slug"]}'
    desc = x.get('dek') or 'The Boston Rambler'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(x["title"])} | The Boston Rambler</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="The Boston Rambler">
<meta property="og:title" content="{e(x["title"])}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/{img}">
<meta property="og:image:secure_url" content="{SITE}/{img}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(x["title"])}">
<meta property="article:published_time" content="{e(x.get("date"))}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(x["title"])}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/{img}">
<script>location.replace({json.dumps(dest)})</script>
<style>body{{margin:0;background:#0a1a33;color:#f8f4ea;font:18px/1.5 Georgia,serif;display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center;padding:24px;box-sizing:border-box}}a{{color:#e8b818}}</style>
</head><body><p><a href="{dest}">{e(x["title"])}</a><br>The Boston Rambler</p></body></html>
'''


def main():
    L = stories()
    os.makedirs(os.path.join(ROOT, 'img', 'share'), exist_ok=True)
    keep_s, keep_i = set(), set()
    for x in L:
        h = hashlib.sha1((x['title'] + '|' + str(x.get('topic')) + '|v1').encode()).hexdigest()[:8]
        img = f'img/share/{x["slug"]}-{h}.jpg'
        keep_i.add(os.path.basename(img)); keep_s.add(x['slug'])
        if not os.path.exists(os.path.join(ROOT, img)):
            card(x, os.path.join(ROOT, img))
        d = os.path.join(ROOT, 's', x['slug']); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, 'index.html'); new = page(x, img)
        if not os.path.exists(p) or open(p, encoding='utf-8').read() != new:
            open(p, 'w', encoding='utf-8').write(new)
    # remove cards for old headlines; keep pages for removed stories so old links still land on the site
    for f in os.listdir(os.path.join(ROOT, 'img', 'share')):
        if f.endswith('.jpg') and f not in keep_i and f.rsplit('-', 1)[0] in keep_s:
            os.remove(os.path.join(ROOT, 'img', 'share', f))
    print(f'{len(L)} stories')


if __name__ == '__main__':
    main()
