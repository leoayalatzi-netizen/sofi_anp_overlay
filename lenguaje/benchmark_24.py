from __future__ import annotations
import time,json
from pathlib import Path
from .core import LanguageCore
CASES=[
 ('definicion','¿Qué es la célula?'),
 ('definicion','¿Qué es Python?'),
 ('razonamiento','¿Cuál es la diferencia entre un hecho y una inferencia?'),
 ('causalidad','¿Qué diferencia hay entre correlación y causalidad?'),
 ('comparacion','Compara memoria de trabajo y memoria persistente.'),
 ('procedimiento','Describe un procedimiento seguro para depurar un programa.'),
 ('incertidumbre','¿Qué debe hacer un sistema cuando no dispone de evidencia suficiente?'),
 ('dialogo','Hola, ¿cómo estás?')]
def run():
 c=LanguageCore();out=[]
 for cat,q in CASES:
  t=time.perf_counter();r=c.responder(q,max_new_tokens=80);dt=time.perf_counter()-t;out.append({'categoria':cat,'pregunta':q,'respuesta':r,'latencia_s':round(dt,4),'calidad':round(c.guardas.evaluar(r or '',q,''),4)})
 report={'version':'2.4-OMEGA','diagnostico':c.diagnostico(),'casos':out,'calidad_media':round(sum(x['calidad'] for x in out)/len(out),4)};p=Path(__file__).resolve().parents[1]/'almacenamiento/modelos/lenguaje/benchmark_2_4.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return report
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
