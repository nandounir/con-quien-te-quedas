"""PLAYER DNA · escudos, caras y edades (los descarga descargar_imagenes.py; aquí solo se leen).

v3.9.4 · Emparejado robusto entre el nombre del ranking (Brainster) y la ficha de SofaScore:
  1. nombre y equipo idénticos
  2. mismo nombre y equipo equivalente (Athletic Club B U21 = Athletic Club B; Villarreal B U23 = Villarreal B…)
  3. nombre contenido (Jesús Vizcay = Jesús Vizcay Hurtado) o con una errata mínima, en el mismo equipo
  4. mismo nombre, o nombre contenido de 2+ palabras, y un único candidato en toda la liga
  + data/fotos_manuales.json: «Jugador|Equipo»: id de SofaScore (o {"id":…, "birth":…}) para lo que no se pueda emparejar.
Nunca inventa: si no hay una ficha clara, devuelve todo None."""
from __future__ import annotations
import difflib, json, re, time, unicodedata
from pathlib import Path

def _n(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

_AGE=re.compile(r'\bu ?(?:1[6-9]|2[0-3])\b')
def _tk(team):
    """Equipo sin la etiqueta de categoría (U21, U23…): «Athletic Club B U21» → «athletic club b»."""
    return re.sub(r'\s+',' ',_AGE.sub(' ',_n(team))).strip()

def _same_team(a,b):
    a,b=_tk(a),_tk(b)
    if not a or not b: return False
    return a==b or a.startswith(b+' ') or b.startswith(a+' ')

def _toks(name): return [t for t in _n(name).split() if t]

def _name_match(a,b):
    """0 = distintos · 1 = mismas palabras (en cualquier orden) · 2 = uno contiene al otro (2+ palabras) · 3 = errata mínima."""
    ta,tb=_toks(a),_toks(b)
    if not ta or not tb: return 0
    if sorted(ta)==sorted(tb): return 1
    sa,sb=set(ta),set(tb)
    short,long_=(sa,sb) if len(sa)<=len(sb) else (sb,sa)
    if len(short)>=2 and short<=long_: return 2
    na,nb=' '.join(ta),' '.join(tb)
    if len(na)>=8 and len(nb)>=8 and difflib.SequenceMatcher(None,na,nb).ratio()>=0.9: return 3
    return 0

_CACHE={'mt':None,'idx':None,'data':None,'omt':None,'ov':{}}

def _load(data_dir: Path):
    f=data_dir/'dna_fichas.json'
    d={'jugadores':[]}
    mt=f.stat().st_mtime_ns if f.exists() else -1
    if _CACHE['mt']!=mt or _CACHE.get('dir')!=str(data_dir):
        if f.exists():
            try: d=json.loads(f.read_text(encoding='utf-8'))
            except Exception: d={'jugadores':[]}
        by_pt,by_p,by_id={}, {}, {}
        for j in d.get('jugadores',[]):
            by_pt[(_n(j['name']),_n(j.get('team','')))]=j
            by_p.setdefault(_n(j['name']),[]).append(j)
            by_id[j['id']]=j
        _CACHE.update(mt=mt,idx=(by_pt,by_p,by_id),data=d,dir=str(data_dir))
    # fotos manuales (se relee si cambia el archivo)
    g=data_dir/'fotos_manuales.json'
    omt=g.stat().st_mtime_ns if g.exists() else -1
    if _CACHE['omt']!=omt or _CACHE.get('odir')!=str(data_dir):
        ov={}
        if g.exists():
            try:
                for k,v in json.loads(g.read_text(encoding='utf-8')).items():
                    if k.startswith('_'): continue
                    pl,_,tm=k.partition('|')
                    if isinstance(v,dict): v={'id':v.get('id'),'birth':v.get('birth'),'team_id':v.get('team_id')}
                    else: v={'id':v,'birth':None,'team_id':None}
                    try: v['id']=int(v['id'])
                    except Exception: continue
                    ov[(_n(pl),_tk(tm))]=v; ov.setdefault((_n(pl),''),v)
            except Exception: ov={}
        _CACHE.update(omt=omt,ov=ov,odir=str(data_dir))
    return _CACHE['idx'],_CACHE['data']

def age_from_ts(ts, today=None):
    if not ts: return None
    t=time.gmtime(ts); n=time.gmtime(today or time.time())
    return n.tm_year-t.tm_year-((n.tm_mon,n.tm_mday)<(t.tm_mon,t.tm_mday))

def birth_year(data_dir: Path, player: str, team: str=''):
    """Año de nacimiento (de la ficha de SofaScore o de data/fotos_manuales.json) o None."""
    try:
        (by_pt,by_p,by_id),data=_load(data_dir)
        j,how=find_ficha(data_dir,player,team)
        o=_CACHE['ov'].get((_n(player),_tk(team))) or _CACHE['ov'].get((_n(player),''))
        ts=None
        if o is not None: ts=o.get('birth') or (by_id.get(o['id']) or {}).get('birth')
        if not ts and j: ts=j.get('birth')
        return time.gmtime(ts).tm_year if ts else None
    except Exception:
        return None

def find_ficha(data_dir: Path, player: str, team: str=''):
    """Devuelve (ficha, cómo) o (None, None). Los jugadores con ficha repetida se resuelven por equipo."""
    (by_pt,by_p,by_id),data=_load(data_dir)
    n=_n(player)
    j=by_pt.get((n,_n(team)))
    if j is not None: return j,'exacto'
    allj=data.get('jugadores',[])
    same=[x for x in allj if _same_team(x.get('team',''),team)] if team else []
    c=[x for x in same if _n(x['name'])==n]
    if len(c)==1: return c[0],'equipo equivalente'
    best=None
    for x in same:
        m=_name_match(player,x['name'])
        if m and (best is None or m<best[0]): best=(m,x)
    if best is not None:
        rivals=[x for x in same if _name_match(player,x['name']) and x is not best[1]]
        if not rivals or best[0]<min(_name_match(player,x['name']) for x in rivals): return best[1],'nombre parecido en su equipo'
    c=by_p.get(n,[])
    if len(c)==1: return c[0],'único en la liga'
    if not c:
        cand=[x for x in allj if _name_match(player,x['name'])==2]
        if len(cand)==1: return cand[0],'nombre contenido, único en la liga'
    return None,None

def _crest_by_team(data_dir,data,team):
    if not team: return None
    for x in data.get('jugadores',[]):
        if x.get('team_id') and _same_team(x.get('team',''),team) and (data_dir/'imagenes'/'equipos'/f"{x['team_id']}.png").exists():
            return f"/media/equipos/{x['team_id']}.png"
    return None

def lookup(data_dir: Path, player: str, team: str=''):
    """Devuelve {age, photo, crest, found} (cada campo puede ser None)."""
    out={'age':None,'photo':None,'crest':None,'found':False}
    (by_pt,by_p,by_id),data=_load(data_dir)
    ov=_CACHE['ov']
    j,how=find_ficha(data_dir,player,team)
    o=ov.get((_n(player),_tk(team))) or ov.get((_n(player),''))
    if o is not None:                           # lo puesto a mano manda sobre el emparejado automático
        base=by_id.get(o['id']) or {}
        j={'id':o['id'],'birth':o.get('birth') or base.get('birth'),'team_id':o.get('team_id') or base.get('team_id') or (j or {}).get('team_id')}
    if j is None:
        out['crest']=_crest_by_team(data_dir,data,team)     # sin ficha de jugador, el escudo del equipo se devuelve igual
        return out
    out['found']=True; out['age']=age_from_ts(j.get('birth'))
    f=data_dir/'imagenes'/'jugadores'/f"{j['id']}.png"
    try:
        if f.exists() and f.stat().st_size>300: out['photo']=f"/media/jugadores/{j['id']}.png"
    except OSError: pass
    tid=j.get('team_id')
    if tid and (data_dir/'imagenes'/'equipos'/f"{tid}.png").exists(): out['crest']=f"/media/equipos/{tid}.png"
    if not out['crest']: out['crest']=_crest_by_team(data_dir,data,team)
    return out

def media_file(data_dir: Path, rel: str):
    """Ruta segura dentro de data/imagenes (solo .png de jugadores/equipos)."""
    m=re.fullmatch(r'(jugadores|equipos)/(\d{1,10})\.png',rel)
    if not m: return None
    f=data_dir/'imagenes'/m.group(1)/f'{m.group(2)}.png'
    return f if f.is_file() else None
