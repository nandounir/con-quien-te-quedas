import colorsys
from collections import Counter
from PIL import Image

COLOR_FIX = {'Real Madrid Castilla U21': ('#1b2b5e', '#d4a92a'), 'Pontevedra CF': ('#8a1c2e', '#e2b443'),
             'Real Unión Club': ('#161616', '#ffffff'), 'SD Ponferradina': ('#1f4e9b', '#ffffff'),
             'Deportivo Fabril': ('#1f55a5', '#ffffff'), 'CDA Águilas FC': ('#1e5aa8', '#ffffff'),
             'Juventud Torremolinos CF': ('#1d8446', '#ffffff'), 'Real Avilés': ('#1c3d8f', '#c8102e'),
             'CE Europa': ('#1f5b9c', '#ffffff'), 'Unionistas de Salamanca CF': ('#161616', '#ffffff'),
             'UD Ibiza': ('#1f86b8', '#ffffff'), 'Racing de Ferrol': ('#0f6b52', '#ffffff'),
             'FC Cartagena': ('#161616', '#d1253a'), 'Athletic Club B': ('#c8102e', '#ffffff'),
             'CD Extremadura': ('#2a2e4f', '#8a2340'), 'Mérida AD': ('#161616', '#d12a2a'),
             'Real Jaén': ('#4a1468', '#f2a51c')}

def crest_colors(path):
    im = Image.open(path).convert('RGBA').resize((80, 80))
    cnt = Counter()
    for r, g, b, a in im.convert("RGBA").getdata():
        if a < 200:
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > 0.9 or (s < 0.12 and l > 0.75):   # blancos
            continue
        cnt[(r // 24 * 24 + 12, g // 24 * 24 + 12, b // 24 * 24 + 12)] += 1
    if not cnt:
        return '#1d2a44', '#c8a24a'
    def score(c):
        h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in c))
        return cnt[c] * (0.35 + s) * (1 if 0.12 < l < 0.75 else 0.5)
    ranked = sorted(cnt, key=score, reverse=True)
    prim = ranked[0]
    hp = colorsys.rgb_to_hls(*(x / 255 for x in prim))
    sec = None
    for c in ranked[1:]:
        h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in c))
        dh = min(abs(h - hp[0]), 1 - abs(h - hp[0]))
        if cnt[c] > cnt[prim] * 0.06 and (dh > 0.08 or abs(l - hp[1]) > 0.3):
            sec = c
            break
    hx = lambda c: '#%02x%02x%02x' % c
    # color principal ligeramente profundizado para fondos
    h, l, s = hp
    l = min(max(l, 0.2), 0.42) if s > 0.15 else min(l, 0.3)
    prim2 = tuple(int(x * 255) for x in colorsys.hls_to_rgb(h, l, s))
    return hx(prim2), hx(sec) if sec else '#ffffff'

