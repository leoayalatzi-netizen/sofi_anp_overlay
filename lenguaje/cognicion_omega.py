from __future__ import annotations
import re
from collections import OrderedDict
class SintesisCognitiva:
 VERSION='2.4-OMEGA-cognition'
 def __init__(self): self.cache=OrderedDict()
 def _records(self,evidence):
  rows=[]
  for line in evidence.splitlines():
   line=re.sub(r'<\|(?:user|assistant|context|system)\|>',' ',line);line=re.sub(r'\s+',' ',line).strip()
   m=re.search(r'concepto:\s*([^;]+)',line,re.I); d=re.search(r'definicion:\s*(.*?)(?:;\s*\w+\s*:|$)',line,re.I)
   if m and d: rows.append((m.group(1).strip(),d.group(1).strip(),line))
  return rows
 def responder(self,q,evidence):
  l=q.lower(); rows=self._records(evidence)
  if not rows:return None
  # Exact fact retrieval: concise, grounded answer.
  if any(x in l for x in ('qué es','que es','define','definición','definicion')):
   for c,d,_ in rows:
    if c.lower() in l or any(tok in l.split() for tok in c.lower().split() if len(tok)>4): return f'{c}: {d}'
  if any(x in l for x in ('compara','diferencia','vs','versus')):
   uniq=[]
   for r in rows:
    if r[0].lower() not in [x[0].lower() for x in uniq]:uniq.append(r)
   relevant=[r for r in uniq if any(tok in l for tok in r[0].lower().split() if len(tok)>4)]
   if len(relevant)>=2:return 'La comparación debe hacerse con el mismo criterio para ambos conceptos.\n\n• '+relevant[0][0]+': '+relevant[0][1]+'\n• '+relevant[1][0]+': '+relevant[1][1]
  if any(x in l for x in ('resume','resumen')): return 'En resumen: '+rows[0][1]
  if any(x in l for x in ('ejemplo','ejemplifica')):
   m=re.search(r'ejemplo:\s*(.*?)(?:;\s*\w+\s*:|$)',rows[0][2],re.I)
   if m:return 'Ejemplo: '+m.group(1).strip()
  if any(x in l for x in ('por qué','porque','relevante')): return 'La relevancia depende del contexto. La evidencia disponible indica: '+rows[0][1]
  return None
