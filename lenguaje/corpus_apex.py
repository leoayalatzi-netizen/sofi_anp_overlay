from __future__ import annotations
import hashlib, json, random, re, time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

def clean(s): return re.sub(r'\s+',' ',str(s)).strip()

def build_apex_corpus(out=None, seed=20260917):
    out=Path(out or BASE/'almacenamiento/modelos/lenguaje/corpus_apex.txt')
    rng=random.Random(seed); rows=[]; seen=set(); sources={}
    def add(x, src):
        x=clean(x)
        if len(x)<25 or len(x)>3000:return
        h=hashlib.sha1(x.lower().encode()).hexdigest()
        if h in seen:return
        seen.add(h); rows.append(x); sources[src]=sources.get(src,0)+1
    base=BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt'
    for line in base.read_text(encoding='utf8',errors='ignore').splitlines(): add(line,'omega')
    planning=[
      ('¿Qué debe hacer un sistema antes de responder una pregunta factual?','Interpretar la intención, recuperar evidencia relevante, distinguir memoria de conocimiento externo, sintetizar una respuesta y verificarla antes de entregarla.'),
      ('¿Qué herramienta conviene usar para 37 por 24?','Una calculadora simbólica o aritmética verificable; el modelo de lenguaje no debe sustituir una operación exacta cuando puede comprobarla.'),
      ('¿Qué hacer si dos fuentes discrepan?','Registrar la discrepancia, conservar ambas fuentes, revisar sus condiciones y declarar la incertidumbre si no puede resolverse.'),
      ('¿Cuándo debe usarse la memoria persistente?','Para información explícita que sea útil entre sesiones, como preferencias o hechos proporcionados por el usuario; no para conjeturas del sistema.'),
      ('¿Cómo se repara una respuesta rechazada por el verificador?','Primero se identifica la causa del rechazo; después se recupera evidencia adicional o una fuente más directa; finalmente se vuelve a sintetizar y verificar.'),
      ('¿Qué diferencia hay entre memoria de trabajo y episódica?','La memoria de trabajo mantiene activas las variables de la tarea actual; la episódica conserva eventos o interacciones concretas para recuperarlos posteriormente.'),
      ('¿Qué diferencia hay entre memoria semántica y procedural?','La semántica conserva conceptos y hechos; la procedural conserva procedimientos, reglas operativas o secuencias de acción.'),
      ('¿Por qué un modelo pequeño puede combinarse con herramientas?','Porque el modelo puede encargarse de interpretar y redactar mientras herramientas deterministas resuelven tareas donde la exactitud o la trazabilidad son más importantes.'),
      ('¿Cómo evitar una alucinación factual?','No completar huecos con una suposición presentada como hecho; buscar evidencia, citar su procedencia internamente y expresar incertidumbre cuando falten datos.'),
      ('¿Cómo resolver una tarea de varios pasos?','Convertirla en subtareas, ejecutar primero las dependencias, guardar resultados intermedios, comprobar cada resultado y solo entonces integrar una respuesta final.'),
    ]
    for q,a in planning:
        for _ in range(180):
            add(f'<|system|> Eres Nevula APEX. Planifica sin mostrar razonamientos privados. <|user|> {q} <|assistant|> {a}','planning')
    tool_use=[
      ('[herramienta=calculista] entrada: 19*23','resultado: 437'),
      ('[herramienta=memoria] clave: preferencia','resultado: recuperar solo recuerdos explícitos y relevantes'),
      ('[herramienta=conocimiento] consulta: ¿qué es una célula?','resultado: unidad estructural y funcional básica de los seres vivos'),
      ('[herramienta=verificador] respuesta sin evidencia','acción: rechazar o marcar como incierta y pedir/recuperar evidencia adicional'),
      ('[herramienta=rag] consulta: diferencia entre correlación y causalidad','acción: recuperar pasajes relevantes y comparar definiciones'),
    ]
    for q,a in tool_use:
        for _ in range(350): add(f'<|system|> Selecciona herramientas de forma trazable. <|user|> {q} <|assistant|> {a}','tools')
    reasoning=[
      ('Premisa 1: si A implica B. Premisa 2: si B implica C.','Conclusión: bajo las mismas condiciones, A implica C.'),
      ('Una muestra tiene correlación alta entre X e Y.','Conclusión: todavía no basta para afirmar que X cause Y.'),
      ('Una respuesta comparte muchas palabras con la pregunta pero contradice la evidencia.','Conclusión: la similitud léxica no basta; debe prevalecer la comprobación de evidencia.'),
      ('Una respuesta es correcta pero proviene de una fuente vieja y una fuente reciente la contradice.','Conclusión: se debe revisar el contexto temporal antes de tratarla como vigente.'),
      ('Hay dos respuestas con confianza similar y fuentes independientes.','Conclusión: existe conflicto y la respuesta final debe reducir su certeza o investigar más.'),
    ]
    for q,a in reasoning:
        for _ in range(220): add(f'<|system|> Resuelve con reglas explícitas y verifica la conclusión. <|user|> {q} <|assistant|> {a}','reasoning_apex')
    selfcheck=[
      ('¿Qué debes comprobar en una respuesta antes de entregarla?','Relevancia respecto de la pregunta, soporte en evidencia disponible, coherencia interna, ausencia de contradicción y, cuando aplique, verificación numérica.'),
      ('¿Qué hacer si la respuesta neuronal es incoherente?','Rechazarla y activar una ruta grounded: conocimiento estructurado, recuperación local, herramienta determinista o declaración de incertidumbre.'),
      ('¿Por qué guardar respuestas fallidas en memoria puede ser peligroso?','Porque contaminaría futuras recuperaciones con información que el propio verificador ya consideró poco fiable.'),
    ]
    for q,a in selfcheck:
        for _ in range(250): add(f'<|system|> Eres un sistema que audita sus propias salidas. <|user|> {q} <|assistant|> {a}','selfcheck')
    rng.shuffle(rows)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(rows),encoding='utf8')
    manifest={'version':'2.5-APEX','created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'records':len(rows),'chars':sum(map(len,rows)),'sources':sources,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'corpus_apex_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return manifest
if __name__=='__main__':print(json.dumps(build_apex_corpus(),ensure_ascii=False,indent=2))
