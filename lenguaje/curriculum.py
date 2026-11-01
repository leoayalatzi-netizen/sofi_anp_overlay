from __future__ import annotations
from pathlib import Path
import json

def construir_curriculum(corpus: Path, salida: Path):
    """Separa material por dificultad para permitir entrenamiento por curriculum."""
    text=corpus.read_text(encoding='utf8',errors='ignore') if corpus.exists() else ''
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    buckets={'dialogo':[],'conocimiento':[],'razonamiento':[],'largo':[]}
    for x in lines:
        low=x.lower()
        if '<|user|>' in low and '<|assistant|>' in low: buckets['dialogo'].append(x)
        elif any(k in low for k in ('porque','por qué','demuestra','calcula','compara','explica')): buckets['razonamiento'].append(x)
        elif len(x)>600: buckets['largo'].append(x)
        else: buckets['conocimiento'].append(x)
    salida.mkdir(parents=True,exist_ok=True)
    for k,v in buckets.items(): (salida/f'{k}.txt').write_text('\n'.join(v),encoding='utf8')
    report={k:len(v) for k,v in buckets.items()}; (salida/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8'); return report
