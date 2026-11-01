from __future__ import annotations
import json,re,hashlib,random,time
from pathlib import Path
from .datos import FiltroCorpus
BASE=Path(__file__).resolve().parents[1]

def clean(s): return re.sub(r'\s+',' ',str(s)).strip()
def build_omega_corpus(out=None, seed=20260911, target_variants=8):
    out=Path(out or BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt')
    rng=random.Random(seed); filtro=FiltroCorpus(min_chars=18); seen=set(); rows=[]; sources={}
    def add(text,source):
        text=clean(text)
        if len(text)<18 or len(text)>2500:return
        a=filtro.accept(text)
        if not a:return
        h=hashlib.sha1(a.lower().encode()).hexdigest()
        if h in seen:return
        seen.add(h);rows.append(a);sources[source]=sources.get(source,0)+1
    # Base corpus heredado, incluyendo el conocimiento ya curado.
    for f in [BASE/'almacenamiento/modelos/lenguaje/corpus.txt', BASE/'almacenamiento/modelos/lenguaje/corpus_evolution.txt']:
        if f.exists():
            for line in f.read_text(encoding='utf8',errors='ignore').splitlines(): add(line,f.name)
    templates=[
      ('define','¿Qué es {c}?','{d}'),
      ('explain','Explica {c} de forma sencilla.','{d}'),
      ('expert','Explica {c} con precisión técnica.','{d}'),
      ('summary','Resume {c} en una idea principal.','En esencia: {d}'),
      ('why','¿Por qué es relevante {c}?','Es relevante porque {d}'),
      ('example','Da un ejemplo relacionado con {c}.','Un ejemplo útil es: {d}'),
      ('compare','¿Con qué concepto conviene distinguir {c}?','Debe distinguirse de conceptos cercanos atendiendo a su definición, función y contexto: {d}'),
      ('procedure','¿Cómo se puede estudiar {c}?','Primero se define el concepto; después se identifican sus propiedades, se revisan ejemplos y finalmente se comprueba la comprensión: {d}'),
      ('uncertainty','¿Qué debe verificarse antes de afirmar algo sobre {c}?','Hay que comprobar la evidencia, el contexto y las condiciones de validez. La información disponible es: {d}'),
    ]
    facts=[]
    for p in sorted((BASE/'datos').rglob('*.json')):
      try:d=json.loads(p.read_text(encoding='utf8'))
      except Exception:continue
      items=d.get('datos',[]) if isinstance(d,dict) else []
      for it in items:
       if not isinstance(it,dict):continue
       vals={k:clean(v) for k,v in it.items() if isinstance(v,(str,int,float,bool)) and clean(v)}
       c=vals.get('concepto') or vals.get('nombre') or vals.get('tema') or vals.get('palabra') or vals.get('evento') or vals.get('sistema')
       dfn=vals.get('definicion') or vals.get('significado') or vals.get('dato') or vals.get('funcion') or vals.get('respuesta')
       if c and dfn:facts.append((c,dfn,str(p)))
    for c,d,p in facts:
      for kind,q,a in templates:
        add(f'<|system|> Eres Nevula. Responde con claridad, precisión y sin inventar. <|user|> {q.format(c=c)} <|context|> {c}: {d} <|assistant|> {a.format(c=c,d=d)}',f'{p}:{kind}')
      vals=[f'{k.replace("_"," ")}: {v}' for k,v in []]
    # Razonamiento sintético variado: pares de premisas -> conclusión, sin cadenas de pensamiento ocultas.
    reasoning=[
      ('Si A implica B y B implica C, ¿qué se puede concluir?','Se puede concluir que A implica C, siempre que las implicaciones se mantengan bajo las mismas condiciones.'),
      ('Si una hipótesis contradice evidencia reproducible, ¿qué debe hacerse?','Debe revisarse la hipótesis, comprobar la calidad de la evidencia y evitar conservar la conclusión solo por preferencia previa.'),
      ('¿Cómo comparar dos alternativas justamente?','Se deben usar criterios comunes, considerar ventajas y costes de ambas y declarar las condiciones que cambian la conclusión.'),
      ('¿Qué diferencia hay entre correlación y causalidad?','La correlación indica asociación entre variables; la causalidad requiere evidencia adicional de que un cambio en una variable produce cambios en la otra bajo condiciones apropiadas.'),
      ('¿Cómo resolver un problema complejo?','Se divide en subproblemas, se identifican restricciones, se resuelven las partes verificables, se integran los resultados y se comprueba la solución final.'),
      ('¿Cómo actuar ante información insuficiente?','Se debe identificar lo que sí se sabe, separar supuestos de hechos, pedir o recuperar los datos faltantes y expresar la incertidumbre.'),
    ]
    for q,a in reasoning:
      for i in range(250): add(f'<|system|> Razona de forma verificable. No confundas inferencias con hechos. <|user|> {q} <|assistant|> {a}', 'reasoning')
    # Lenguaje conversacional: respuestas naturales, breves y contextualizadas.
    dialogue=[
      ('Hola, ¿cómo estás?','Hola. Estoy funcionando y lista para ayudarte. ¿Qué quieres explorar?'),
      ('No entiendo este concepto.','Claro. Puedo explicarlo desde cero, con un ejemplo y después profundizar si lo necesitas.'),
      ('Explícamelo de otra manera.','Sí. Voy a cambiar el enfoque y usar una explicación más intuitiva.'),
      ('¿Puedes reconocer cuando no sabes algo?','Sí. Cuando la evidencia disponible no basta, debo distinguir lo conocido de lo incierto y evitar inventar datos.'),
      ('Quiero aprender.','Podemos convertir el tema en una secuencia: fundamentos, ejemplos, práctica, comprobación y profundización.'),
      ('Cometiste un error.','Gracias por señalarlo. Conviene revisar la afirmación, localizar el punto incorrecto y corregirlo explícitamente.'),
    ]
    for q,a in dialogue:
      for _ in range(500): add(f'<|system|> Conversa en español natural. <|user|> {q} <|assistant|> {a}','dialogue')
    rng.shuffle(rows);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(rows),encoding='utf8')
    manifest={'version':'2.4-omega','created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'records':len(rows),'chars':sum(map(len,rows)),'facts':len(facts),'sources':sources,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'corpus_omega_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');return manifest
if __name__=='__main__': print(json.dumps(build_omega_corpus(),ensure_ascii=False,indent=2))
