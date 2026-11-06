"""Convierte el proyecto (index.html + data.js + assets/) en versión alojable:
- escudos embebidos en data.js (PNG optimizado, data URI)
- fotos de cada equipo en fotos/<id>.js (JPEG en data URI), cargadas solo al abrir el equipo
- fuentes embebidas en fonts.css como data URI  -> sin dependencias externas
Uso: python3 -I bundle_web.py <proyecto_origen> <salida>
"""
import base64, io, json, os, sys
from pathlib import Path
from PIL import Image

src, out = Path(sys.argv[1]), Path(sys.argv[2])
(out / 'fotos').mkdir(parents=True, exist_ok=True)
raw = (src / 'data.js').read_text(encoding='utf-8')
data = json.loads(raw[raw.index('{'):raw.rstrip().rindex(';')])

def uri(b, mime): return f'data:{mime};base64,' + base64.b64encode(b).decode()

for t in data['teams']:
    im = Image.open(src / 'assets/teams' / f"{t['id']}.png").convert('RGBA')
    im.thumbnail((200, 200), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'WEBP', quality=90, method=6)
    t['crest'] = uri(buf.getvalue(), 'image/webp')

total = 0
for tid, players in data['players'].items():
    photos = {}
    for p in players:
        if not p['photo']: continue
        im = Image.open(src / 'assets/players' / f"{p['photo']}.png").convert('RGB')
        buf = io.BytesIO(); im.save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
        photos[p['photo']] = uri(buf.getvalue(), 'image/jpeg')
    js = ('window.ADNP_PHOTOS=window.ADNP_PHOTOS||{};window.ADNP_PHOTOS[' + json.dumps(tid) + ']=' +
          json.dumps(photos, separators=(',', ':')) + ';\n')
    (out / 'fotos' / f'{tid}.js').write_text(js, encoding='utf-8')
    total += len(js)

(out / 'data.js').write_text('/* ADN PLAYER — ¿Con quién te quedas? · THE EYE INTELLIGENCE UNIT */\nwindow.APP_DATA = ' +
                             json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')

F = Path('/home/claude/fonts')
faces = [  # familia, carpeta, peso, estilo, subsets
    ('Barlow Condensed', 'fontsource-barlow-condensed-5.3.0', 'barlow-condensed', 700, 'normal', ['latin', 'latin-ext']),
    ('Barlow Condensed', 'fontsource-barlow-condensed-5.3.0', 'barlow-condensed', 800, 'normal', ['latin', 'latin-ext']),
    ('Barlow Condensed', 'fontsource-barlow-condensed-5.3.0', 'barlow-condensed', 800, 'italic', ['latin', 'latin-ext']),
    ('Barlow', 'fontsource-barlow-5.3.0', 'barlow', 500, 'normal', ['latin']),
    ('Barlow', 'fontsource-barlow-5.3.0', 'barlow', 600, 'normal', ['latin']),
    ('Barlow', 'fontsource-barlow-5.3.0', 'barlow', 700, 'normal', ['latin']),
    ('Anton', 'fontsource-anton-5.3.0', 'anton', 400, 'normal', ['latin']),
    ('JetBrains Mono', 'fontsource-jetbrains-mono-5.3.0', 'jetbrains-mono', 700, 'normal', ['latin']),
]
RANGES = {'latin': 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD',
          'latin-ext': 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+1EF2-1EFF,U+2C60-2C7F,U+A720-A7FF'}
css = '/* Barlow, Barlow Condensed, Anton, JetBrains Mono — SIL Open Font License */\n'
for fam, pkg, stem, w, st, subs in faces:
    for s in subs:
        b = (F / pkg / 'files' / f'{stem}-{s}-{w}-{st}.woff2').read_bytes()
        css += (f'@font-face{{font-family:"{fam}";font-style:{st};font-weight:{w};font-display:swap;'
                f'src:url({uri(b, "font/woff2")}) format("woff2");unicode-range:{RANGES[s]}}}\n')
(out / 'fonts.css').write_text(css, encoding='utf-8')
print('fotos', total // 1024, 'KB en', len(data['players']), 'archivos; data.js', os.path.getsize(out / 'data.js') // 1024, 'KB; fonts.css', len(css) // 1024, 'KB')
