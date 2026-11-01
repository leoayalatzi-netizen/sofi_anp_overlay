from __future__ import annotations
import json,re,unicodedata
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def norm(s):
 s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9 ]+',' ',s)
class IndiceConocimiento:
 VERSION='2.4-OMEGA-knowledge'
 def __init__(self,root=None):
  self.root=Path(root or BASE/'datos');self.by_name={}
  for p in self.root.rglob('*.json'):
   try:d=json.loads(p.read_text(encoding='utf8'))
   except Exception:continue
   for it in (d.get('datos',[]) if isinstance(d,dict) else []):
    if not isinstance(it,dict):continue
    name=it.get('concepto') or it.get('nombre') or it.get('tema')
    definition=it.get('definicion') or it.get('significado') or it.get('dato') or it.get('funcion') or it.get('respuesta')
    if name and definition:self.by_name[norm(name)]={'nombre':str(name),'definicion':str(definition),'ejemplo':str(it.get('ejemplo','')),'fuente':str(p.relative_to(self.root))}
 def buscar(self,q):
  nq=norm(q); tokens=set(nq.split()); candidates=[]
  # Match por tokens/concepto, no por subcadenas: evita que 'ide' haga match
  # dentro de 'tiene' o que 'relacion' gane dentro de 'correlacion'.
  for k,v in self.by_name.items():
   kt=[x for x in k.split() if x]
   if not kt: continue
   exact_all=all(x in tokens for x in kt)
   if exact_all:
    candidates.append((100+len(k),v))
  if not candidates:
   # Para frases con verbo + concepto, acepta una coincidencia única de
   # concepto largo (>4 caracteres) en los tokens de la pregunta.
   for k,v in self.by_name.items():
    kt=[x for x in k.split() if len(x)>=5]
    if kt and any(x in tokens for x in kt): candidates.append((20+max(map(len,kt)),v))
  candidates.sort(reverse=True,key=lambda x:x[0]);return candidates[0][1] if candidates else None
 def responder(self,q):
  r=self.buscar(q)
  if not r:return None
  l=norm(q)
  if 'ejemplo' in l and r['ejemplo']:return f"Ejemplo: {r['ejemplo']}"
  return f"{r['nombre']}: {r['definicion']}"
