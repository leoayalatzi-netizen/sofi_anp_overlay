from __future__ import annotations
import json,re,hashlib,time,random
from pathlib import Path
from .datos import FiltroCorpus
BASE=Path(__file__).resolve().parents[1]

def clean(s): return re.sub(r'\s+',' ',str(s)).strip()
def build_evolution_corpus(out=None,seed=20260911):
    out=Path(out or BASE/'almacenamiento/modelos/lenguaje/corpus_evolution.txt'); rng=random.Random(seed); filtro=FiltroCorpus(min_chars=25)
    rows=[]; seen=set(); sources={}
    def add(text,source,kind='knowledge'):
        text=clean(text)
        if len(text)<25:return
        if text.count('<|assistant|>')>1:return
        a=filtro.accept(text)
        if not a:return
        key=hashlib.sha1(a.lower().encode()).hexdigest()
        if key in seen:return
        seen.add(key); rows.append(a); sources[source]=sources.get(source,0)+1
    # Datos estructurados: convertir cada hecho en múltiples tareas lingüísticas.
    for p in sorted((BASE/'datos').rglob('*.json')):
        try:d=json.loads(p.read_text(encoding='utf8'))
        except Exception:continue
        items=d.get('datos',[]) if isinstance(d,dict) else []
        for it in items:
            if not isinstance(it,dict):continue
            vals={k:clean(v) for k,v in it.items() if isinstance(v,(str,int,float,bool)) and clean(v)}
            if not vals:continue
            concept=vals.get('concepto') or vals.get('nombre') or vals.get('tema') or vals.get('palabra') or vals.get('evento') or vals.get('sistema')
            definition=vals.get('definicion') or vals.get('significado') or vals.get('dato') or vals.get('funcion') or vals.get('respuesta')
            if concept and definition:
                add(f'<|user|> ¿Qué es {concept}? <|context|> {concept}: {definition} <|assistant|> {definition}',str(p),'fact')
                add(f'<|user|> Explica {concept} con claridad. <|context|> {concept}: {definition} <|assistant|> {definition}',str(p),'explain')
                add(f'<|user|> Resume lo esencial de {concept}. <|context|> {concept}: {definition} <|assistant|> En esencia, {definition}',str(p),'summary')
            if len(vals)>=3:
                facts='; '.join(f'{k.replace("_"," ")}: {v}' for k,v in vals.items())
                add(f'<|user|> Organiza esta información: {facts} <|assistant|> La información se puede organizar así: {facts}',str(p),'instruction')
    # Conversaciones previas
    for f in (BASE/'almacenamiento/conversaciones').glob('*.json'):
        try:d=json.loads(f.read_text(encoding='utf8'))
        except Exception:continue
        for t in d.get('turns',[]):
            if isinstance(t,dict) and t.get('text'): add(str(t['text']),str(f),'dialogue')
    # Datos de entrenamiento existentes
    for f in [BASE/'entrenamiento/dataset_masivo_v14.json',BASE/'entrenamiento/dataset_masivo_v13.json',BASE/'entrenamiento/dataset_dominios.json']:
        if not f.exists():continue
        try:d=json.loads(f.read_text(encoding='utf8'))
        except Exception:continue
        for key in ('train','ejemplos','validation'):
            arr=d.get(key,[]) if isinstance(d,dict) else []
            if not isinstance(arr,list): continue
            for item in arr:
                if isinstance(item,str):add(item,str(f),'legacy')
                elif isinstance(item,list) and item:add(str(item[0]),str(f),'legacy')
    # Currículum sintético pequeño, orientado a conducta lingüística y razonamiento.
    templates=[
      ('¿Cuál es la diferencia entre un hecho y una inferencia?','Un hecho es una afirmación respaldada por evidencia disponible; una inferencia es una conclusión obtenida al relacionar esa evidencia con reglas o supuestos.'),
      ('¿Qué debe hacer un sistema cuando no conoce una respuesta?','Debe reconocer la incertidumbre, explicar qué información falta y evitar presentar una conjetura como si fuera un hecho.'),
      ('¿Cómo se razona una comparación?','Primero se definen criterios comunes, después se evalúa cada alternativa con esos criterios y finalmente se explican ventajas, desventajas y condiciones de la conclusión.'),
      ('¿Cómo se detecta una contradicción?','Se comparan las afirmaciones y sus condiciones de validez. Si ambas no pueden ser verdaderas bajo las mismas condiciones, existe una contradicción que debe señalarse.'),
      ('¿Cómo se construye una buena explicación?','Se parte de la pregunta, se definen los conceptos necesarios, se presentan las relaciones causales o lógicas y se termina con una conclusión que responda exactamente al objetivo.')]
    for q,a in templates*120:add(f'<|user|> {q} <|assistant|> {a}','curriculum_reasoning','reasoning')
    rng.shuffle(rows); out.parent.mkdir(parents=True,exist_ok=True); out.write_text('\n'.join(rows),encoding='utf8')
    manifest={'version':'2.3.1','created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'records':len(rows),'chars':sum(map(len,rows)),'sources':sources,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'corpus_evolution_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return manifest
