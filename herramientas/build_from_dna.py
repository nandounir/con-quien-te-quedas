"""Genera data.js + assets desde ADN PLAYER (PLAYER_DNA).
Plantilla = jugadores de data/dna_demarcaciones.json (los mismos que salen en ADN PLAYER).
Foto = emparejado oficial de ADN PLAYER (dna_media.lookup).
Uso: python3 -I build_from_dna.py <PLAYER_DNA> <proyecto_salida> <data.json_original>
"""
import json, os, shutil, sys, importlib.util
from pathlib import Path

dna, out, orig = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dna_media', here / 'dna_media.py')
dm = importlib.util.module_from_spec(spec); spec.loader.exec_module(dm)
sys.path.insert(0, str(here))
from build_data_colors import crest_colors, COLOR_FIX  # noqa

data_dir = dna / 'data'
demar = json.loads((data_dir / 'dna_demarcaciones.json').read_text(encoding='utf-8'))
fichas = json.loads((data_dir / 'dna_fichas.json').read_text(encoding='utf-8'))
groups = {t['id']: (1 if t['group'].endswith('1') else 2) for t in json.load(open(orig, encoding='utf-8'))['teams']}

# alias: nombre que sobra -> nombre oficial
alias = {}
for line in (dna / 'app' / 'alias_base.csv').read_text(encoding='utf-8').splitlines():
    if line.startswith('#') or not line.strip():
        continue
    eq, sobra, oficial, *_ = line.split(';')
    alias[(dm._tk(eq), dm._n(sobra))] = oficial

DEM = {'POR': 'Portero', 'DFC': 'Defensa central', 'LAT': 'Lateral', 'MCD': 'Mediocentro',
       'MCO': 'Mediapunta', 'EXT': 'Extremo', 'DC': 'Delantero centro',
       'G_POR': 'Portero', 'G_DEF': 'Defensa', 'G_MED': 'Centrocampista', 'G_DEL': 'Delantero'}
LINE = {'POR': 0, 'G_POR': 0, 'DFC': 1, 'LAT': 2, 'G_DEF': 2.5, 'MCD': 3, 'MCO': 4, 'G_MED': 4.5, 'EXT': 5, 'DC': 6, 'G_DEL': 6.5}
GEN = {'Portero': 'G_POR', 'Defensa': 'G_DEF', 'Centrocampista': 'G_MED', 'Delantero': 'G_DEL'}
# Lista completa de ADN PLAYER = jugadores con minutos (dna_estado.json). Los que aún no tienen demarcación fina
# entran con su línea (Portero / Defensa / Centrocampista / Delantero).
estado = json.loads((data_dir / 'dna_estado.json').read_text(encoding='utf-8')).get('minutes', {})
entries = [(k, v) for k, v in demar.items()]
_seen_keys = {' '.join(k.split()) for k in demar}
for k in estado:
    kk = ' '.join(k.split())
    if kk not in _seen_keys:
        entries.append((kk, GEN[kk.split('|')[2]]))
        _seen_keys.add(kk)

team_by_tk = {}
for tid, name in fichas['equipos'].items():
    team_by_tk[dm._tk(name)] = (tid, name)

def team_of(name):
    tk = dm._tk(name)
    if tk in team_by_tk:
        return team_by_tk[tk]
    for k, v in team_by_tk.items():
        if dm._same_team(k, tk):
            return v
    raise KeyError(name)

import re, unicodedata
def toks(s):
    s = unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z ]', ' ', s).split()
def same_person(a, b):
    A, B = toks(a), toks(b)
    if not A or not B: return False
    if A == B: return True
    short, long_ = (A, B) if len(A) <= len(B) else (B, A)
    if long_[:len(short)] == short: return True
    return len(A) > 1 and A[0][:4] == B[0][:4] and len(A[0]) >= 4 and A[1:2] == B[1:2]
IMG_DIRS = [data_dir / 'imagenes' / 'jugadores', orig.parent / 'assets' / 'players']
def img_path(pid):
    for d in IMG_DIRS:
        f = d / f'{pid}.png'
        if f.exists() and f.stat().st_size > 300: return f
    return None
orig_players = json.load(open(orig, encoding='utf-8'))['players']
pool = [(str(j['id']), j['name'], str(j['team_id'])) for j in fichas['jugadores']] + \
       [(p['id'], p['name'], p['teamId']) for p in orig_players]
def fallback_photo(name, tid):
    c = {pid for pid, n, t in pool if t == tid and (same_person(n, name) or dm._name_match(n, name)) and img_path(pid)}
    return c.pop() if len(c) == 1 else None

players, seen = {}, set()
MERGED = []
(out / 'assets' / 'players').mkdir(parents=True, exist_ok=True)
(out / 'assets' / 'teams').mkdir(parents=True, exist_ok=True)
nophoto = []
for key, code in entries:
    name, team, _line = key.split('|')
    name = ' '.join(name.split())
    name = alias.get((dm._tk(team), dm._n(name)), name)
    tid, _ = team_of(team)
    k = (tid, dm._n(name))
    if k in seen:
        continue
    seen.add(k)
    info = dm.lookup(data_dir, name, team)
    pid = info['photo'].rsplit('/', 1)[1][:-4] if info['photo'] else fallback_photo(name, tid)
    lst = players.setdefault(tid, [])
    generic = code.startswith('G_')
    dup = next((p for p in lst if (p['pos'] == DEM[code] or generic) and (same_person(p['name'], name) or dm._name_match(p['name'], name)
                or dm._toks(p['name'])[-1:] == dm._toks(name)[-1:] and dm._toks(p['name'])[0][:4] == dm._toks(name)[0][:4]
                or ''.join(dm._toks(p['name'])).startswith(''.join(dm._toks(name))[:8]) and len(''.join(dm._toks(name))) >= 8)), None)
    if dup:   # mismo jugador partido en dos nombres: una sola tarjeta, nombre corto
        MERGED.append(f"{name} -> {dup['name']} ({team})")
        if len(name) < len(dup['name']) and not generic: dup['name'] = name
        if not dup['photo'] and pid: dup['photo'] = pid
        continue
    lst.append({'name': name, 'pos': DEM[code], 'photo': pid, '_o': LINE[code], '_t': team})

for tid, lst in players.items():
    for p in lst:
        if p['photo']:
            shutil.copyfile(img_path(p['photo']), out / 'assets' / 'players' / f"{p['photo']}.png")
        else:
            nophoto.append(f"{p['name']} ({p['_t']})")
        del p['_t']

teams = []
for tid, name in fichas['equipos'].items():
    shutil.copyfile(data_dir / 'imagenes' / 'equipos' / f'{tid}.png', out / 'assets' / 'teams' / f'{tid}.png')
    c1, c2 = COLOR_FIX.get(name) or crest_colors(out / 'assets' / 'teams' / f'{tid}.png')
    teams.append({'id': tid, 'name': name, 'group': groups[tid], 'c1': c1, 'c2': c2})
    players[tid].sort(key=lambda p: (p['_o'], p['name']))
    for i, p in enumerate(players[tid]):
        p['id'] = f'{tid}-{i}'
        del p['_o']
teams.sort(key=lambda t: t['name'])

(out / 'data.js').write_text(
    '/* ADN PLAYER — ¿Con quién te quedas? · escudos, nombres, posiciones y grupo */\n'
    'window.APP_DATA = ' + json.dumps({'teams': teams, 'players': players}, ensure_ascii=False, separators=(',', ':')) + ';\n',
    encoding='utf-8')
print('equipos', len(teams), 'jugadores', sum(map(len, players.values())), 'sin foto', len(nophoto))
print(sorted(len(v) for v in players.values()))
print('fusionados', len(MERGED)); print('\n'.join(MERGED))
print('sin foto', len(nophoto))
