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
MASTHEAD = os.path.join(ROOT, 'img', 'rambler-masthead.png')
DEFLABEL = 'Boston Stories'
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


def _art(x, coast):
    s = ' '.join(str(x.get(k) or '') for k in ('title', 'dek', 'topic')).lower()
    ti = (x.get('title') or '').lower()
    def has(*w): return any(k in s for k in w)
    if any(k in ti for k in ('mass', 'worship', 'vespers', 'hymn', 'prayer')) and not has('parade', 'halloween', 'concert', 'fair', 'party'): k = 'church'
    elif has('symphon', 'orchestra', 'philharmon', 'opera', 'ballet', 'nutcracker', 'choral', 'chorus', 'messiah', 'quartet', 'chamber', 'recital', 'baroque', 'classical'): k = 'gala'
    elif has('jazz', 'blues', 'swing'): k = 'jazz'
    elif x.get('topic') == 'stage' or has('theat', 'broadway', 'musical', 'comed', 'christmas carol', 'cabaret', 'much ado'): k = 'marquee'
    elif has(' dj ', 'dance party', 'nightclub', 'nightlife'): k = 'club'
    elif has('museum', 'gallery', 'exhibit', 'arts center', 'painting', 'photograph', 'sculpt', 'film', 'screening'): k = 'gallery'
    elif has('parade', 'fair', 'festival', 'holiday', 'halloween', 'pumpkin', 'lantern', 'family', 'kids', 'library', 'thanksgiving', 'tree', 'market', 'comic con'): k = 'fair'
    elif has('music', 'band', 'rock', 'concert', 'tour', 'live', 'cafe', 'café') or x.get('topic') == 'music': k = 'gig'
    else: k = 'wharf' if coast else 'gala'
    for name in ([k + '2', k] if coast else [k, k + '2']):
        p = os.path.join(ROOT, 'img', 'posters', name + '.jpg')
        if os.path.exists(p): return p
    return None


def card(x, out):
    from PIL import ImageFilter, ImageEnhance
    W, H = 1200, 630
    coast = os.path.exists(os.path.join(ROOT, 'img', 'posters', 'wharf.jpg')) and ('jamestown' in SITE or 'hurricane' in SITE)
    ap = _art(x, coast)
    if ap:
        bg = Image.open(ap).convert('RGB')
        r = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1), Image.LANCZOS)
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(2))).enhance(0.55)
    else:
        bg = Image.new('RGB', (W, H), NAVY)
    sh = Image.new('L', (W, H), 0); sd = ImageDraw.Draw(sh)
    for yy in range(H):
        a = int(70 + 150 * abs(yy - H * 0.55) / H)
        sd.line([(0, yy), (W, yy)], fill=min(200, a))
    im = Image.composite(Image.new('RGB', (W, H), (8, 6, 14)), bg, sh)
    glow = Image.new('RGB', (W, H), (0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.ellipse((W * 0.15, H * 0.2, W * 0.85, H * 1.1), fill=(90, 50, 10)); glow = glow.filter(ImageFilter.GaussianBlur(120))
    im = Image.fromarray(__import__('numpy').minimum(255, __import__('numpy').asarray(im, dtype='int16') + __import__('numpy').asarray(glow, dtype='int16')).astype('uint8'))
    d = ImageDraw.Draw(im)
    mh = Image.open(MASTHEAD).convert('RGBA')
    mw = 420; mh = mh.resize((mw, int(mh.height * mw / mh.width)), Image.LANCZOS)
    im.paste(mh, ((W - mw) // 2, 30), mh)
    top = 30 + mh.height + 22
    lab = font(['DejaVuSans-Bold.ttf'], 22)
    t = LABEL.get(x.get('topic'), DEFLABEL).upper()
    tw = d.textlength(t, font=lab)
    d.rounded_rectangle(((W - tw) / 2 - 16, top - 6, (W + tw) / 2 + 16, top + 30), 6, fill=GOLD)
    d.text(((W - tw) / 2, top - 1), t, font=lab, fill=(30, 18, 0))
    top += 54
    hf = os.path.join(ROOT, 'fonts', 'ep-abril.woff')
    for size in range(84, 34, -2):
        try: f = ImageFont.truetype(hf, size)
        except Exception: f = font(['DejaVuSerif-Bold.ttf'], size)
        lines = wrap(d, x['title'], f, W - 120)
        lh = int(size * 1.12)
        if len(lines) <= 4 and top + lh * len(lines) <= H - 50:
            break
    y = top + (H - 50 - top - lh * len(lines)) // 2
    halo = Image.new('RGBA', (W, H), (0, 0, 0, 0)); hd = ImageDraw.Draw(halo); yy = y
    for ln in lines:
        lw = d.textlength(ln, font=f); hd.text(((W - lw) / 2, yy), ln, font=f, fill=(255, 170, 60, 200)); yy += lh
    halo = halo.filter(ImageFilter.GaussianBlur(14)); im.paste(halo, (0, 0), halo); d = ImageDraw.Draw(im)
    for ln in lines:
        lw = d.textlength(ln, font=f)
        d.text(((W - lw) / 2 + 2, y + 3), ln, font=f, fill=(10, 6, 0))
        d.text(((W - lw) / 2, y), ln, font=f, fill=(255, 246, 220))
        y += lh
    d.rectangle((0, H - 10, W, H), fill=GOLD)
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
        h = hashlib.sha1((x['title'] + '|' + str(x.get('topic')) + '|v2').encode()).hexdigest()[:8]
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
