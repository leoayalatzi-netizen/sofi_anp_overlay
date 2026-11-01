from __future__ import annotations
import json,random,re,time,hashlib
from pathlib import Path
from .datos import FiltroCorpus
BASE=Path(__file__).resolve().parents[1]

def _clean(x): return re.sub(r'\s+',' ',str(x)).strip()

def build_corpus(out:Path, seed=20260911):
    rng=random.Random(seed); rows=[]; meta=[]; filtro=FiltroCorpus(min_chars=25)
    def add(text,source):
        text=_clean(text); accepted=filtro.accept(text)
        if accepted: rows.append(accepted); meta.append({'source':source,'chars':len(accepted)})
    for p in sorted((BASE/'datos').rglob('*.json')):
        try: d=json.loads(p.read_text(encoding='utf8'))
        except Exception: continue
        items=d.get('datos',[]) if isinstance(d,dict) else []
        for it in items:
            if not isinstance(it,dict): continue
            concept=_clean(it.get('concepto') or it.get('nombre') or it.get('tema') or it.get('palabra') or it.get('evento') or it.get('obra') or it.get('genero') or it.get('sistema') or '')
            definition=_clean(it.get('definicion') or it.get('significado') or it.get('dato') or it.get('funcion') or it.get('respuesta') or '')
            example=_clean(it.get('ejemplo') or it.get('ejemplos') or '')
            if concept and definition:
                add(f'<|user|> ¿Qué es {concept}? <|context|> {concept}: {definition} <|assistant|> {definition}',str(p))
                add(f'<|user|> Explícame {concept}. <|context|> {concept}: {definition} <|assistant|> {definition}',str(p))
                add(f'<|user|> ¿Qué sabes sobre {concept}? <|context|> {concept}: {definition} <|assistant|> {definition}',str(p))
                if example: add(f'<|user|> Dame un ejemplo de {concept}. <|context|> {concept}: {definition}. Ejemplo: {example} <|assistant|> Un ejemplo de {concept} es {example}',str(p))
            parts=[]
            for k,v in it.items():
                if isinstance(v,(str,int,float,bool)): parts.append(f'{k.replace("_"," ")}: {_clean(v)}')
                elif isinstance(v,list) and v: parts.append(f'{k.replace("_"," ")}: '+', '.join(map(str,v[:8])))
            if parts: add(' '.join(parts),str(p))
    for f in [BASE/'entrenamiento/dataset_masivo_v14.json',BASE/'entrenamiento/dataset_masivo_v13.json',BASE/'entrenamiento/dataset_dominios.json']:
        if not f.exists(): continue
        try: d=json.loads(f.read_text(encoding='utf8'))
        except Exception: continue
        for key in ('train','ejemplos'):
            arr=d.get(key,[]) if isinstance(d,dict) else []
            if not isinstance(arr,list): continue
            for item in arr:
                if isinstance(item,list) and item: add(item[0],str(f))
    for f in (BASE/'almacenamiento/conversaciones').glob('*.json'):
        try: d=json.loads(f.read_text(encoding='utf8'))
        except Exception: continue
        for t in d.get('turns',[]):
            if isinstance(t,dict) and t.get('text'): add(t['text'],str(f))
    seeds=['Hola, ¿cómo estás?','Estoy aquí para ayudarte.','Claro, puedo explicártelo paso a paso.','Entiendo lo que quieres decir.','¿Podrías darme un poco más de contexto?','La respuesta depende del contexto y de la evidencia disponible.','No estoy completamente seguro; prefiero comprobarlo antes de afirmarlo.','Hay una diferencia importante entre saber un dato y comprender cómo se relaciona con otros datos.','Si quieres, podemos analizarlo desde otra perspectiva.','Primero identificamos el problema y después buscamos la explicación más sólida.','Una buena respuesta debe ser clara, precisa y relevante para la pregunta.']
    for s in seeds*30: add(s,'seed_dialogo')
    web_root=BASE/'almacenamiento/web_corpus/raw'
    if web_root.exists():
        for f in sorted(web_root.glob('*.json')):
            try:
                rec=json.loads(f.read_text(encoding='utf8')); add(rec.get('text',''),f'web:{rec.get("url",f.name)}')
            except Exception: pass
    rng.shuffle(rows); out.parent.mkdir(parents=True,exist_ok=True); out.write_text('\n'.join(rows),encoding='utf8')
    manifest={'version':'2.1','created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'records':len(rows),'chars':sum(map(len,rows)),'sources':len(set(m['source'] for m in meta)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'corpus_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return len(rows)
