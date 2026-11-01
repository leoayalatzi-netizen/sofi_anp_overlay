from __future__ import annotations
import time,json
from pathlib import Path
from .core import LanguageCore
CASES=[
 ('lenguaje','Explica con claridad qué es una metáfora.'),
 ('razonamiento','¿Cuál es la diferencia entre un hecho y una inferencia?'),
 ('comparacion','Compara memoria de trabajo y memoria persistente.'),
 ('procedimiento','Describe un procedimiento seguro para depurar un programa.'),
 ('incertidumbre','¿Qué debe hacer un sistema cuando no dispone de evidencia suficiente?')]
def run():
 c=LanguageCore();out=[]
 for cat,q in CASES:
  t=time.perf_counter();r=c.responder(q,max_new_tokens=120);dt=time.perf_counter()-t;out.append({'categoria':cat,'pregunta':q,'respuesta':r,'latencia_s':round(dt,4),'calidad':round(c.guardas.evaluar(r or '',q,''),4)})
 report={'version':'2.3.1','diagnostico':c.diagnostico(),'casos':out};p=Path(__file__).resolve().parents[1]/'almacenamiento/modelos/lenguaje/benchmark_2_3_1.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return report
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
