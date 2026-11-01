from __future__ import annotations
import json, time, unicodedata
from pathlib import Path
from .core import LanguageCore

CASES = [
    ("¿Qué es la célula?", "célula"),
    ("¿Qué es Python?", "python"),
    ("Explica la diferencia entre correlación y causalidad.", "correlación"),
    ("¿Qué diferencia hay entre memoria de trabajo y memoria persistente?", "memoria"),
    ("¿Cuánto es 27 * 14?", "378"),
    ("¿Qué es un robot?", "robot"),
    ("¿Cómo depuro un programa que falla?", "depur"),
    ("¿Qué haces cuando no tienes evidencia suficiente?", "evidencia"),
    ("Hola", "hola"),
    ("¿Cómo resolver un problema complejo?", "subproblemas"),
]

def run():
    c=LanguageCore()
    rows=[]
    for q,needle in CASES:
        t=time.perf_counter(); r=c.responder(q) or ''; ms=(time.perf_counter()-t)*1000
        nr=unicodedata.normalize('NFKD',r).encode('ascii','ignore').decode().lower(); nn=unicodedata.normalize('NFKD',needle).encode('ascii','ignore').decode().lower(); score=1.0 if nn in nr else 0.0
        score += 0.5 if len(r.split())>=8 else 0.0
        score=min(1.0,score)
        rows.append({'q':q,'answer':r,'needle':needle,'score':score,'ms':round(ms,2)})
    result={'version':'2.5-APEX','backend':c.diagnostico(),'cases':rows,'mean_score':round(sum(x['score'] for x in rows)/len(rows),4)}
    p=Path(__file__).resolve().parents[1]/'almacenamiento/modelos/lenguaje/benchmark_2_5.json'
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2));return result

if __name__=='__main__':run()
