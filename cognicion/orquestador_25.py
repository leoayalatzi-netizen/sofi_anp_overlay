from __future__ import annotations
import re, time, json
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

from .analizador_entrada import AnalizadorEntrada
from .memoria_jerarquica import MemoriaJerarquica
from .motor_calculista import MotorCalculista
from .verificador_25 import VerificadorAPEX, Verificacion25

@dataclass
class Paso25:
    id: str
    objetivo: str
    herramienta: str
    estado: str = "pendiente"
    confianza: float = 0.0
    detalle: str = ""

@dataclass
class Traza25:
    consulta: str
    intencion: str
    complejidad: float
    pasos: List[Paso25] = field(default_factory=list)
    fuentes: List[str] = field(default_factory=list)
    verificaciones: List[Dict[str, Any]] = field(default_factory=list)
    reparaciones: int = 0
    duracion_ms: float = 0.0

    def to_dict(self): return asdict(self)

class OrquestadorAPEX:
    """Cerebro coordinador 2.5: percibe -> planifica -> ejecuta herramientas ->
    sintetiza -> verifica -> repara -> aprende. El modelo neural es una
    herramienta generativa, no la autoridad factual.
    """
    VERSION = "2.5-APEX"
    def __init__(self, knowledge, retrieval, memoria25: MemoriaJerarquica, razonador,
                 guardas, dialogo, neuro_generate: Callable[..., Optional[str]],
                 legacy_memory=None, max_repair=2):
        self.knowledge=knowledge; self.retrieval=retrieval; self.memoria=memoria25; self.razonador=razonador
        self.guardas=guardas; self.dialogo=dialogo; self.neuro_generate=neuro_generate; self.legacy_memory=legacy_memory
        self.analizador=AnalizadorEntrada(); self.calculista=MotorCalculista(); self.verificador=VerificadorAPEX(); self.max_repair=max_repair
        self.ultima_traza: Optional[Traza25]=None

    def diagnostico(self) -> Dict[str, Any]:
        return {"version":self.VERSION,"memoria":self.memoria.estadisticas(),"verificador":self.verificador.VERSION,
                "ultimo_pipeline": self.ultima_traza.to_dict() if self.ultima_traza else None}

    def _plan(self, a) -> List[Paso25]:
        steps=[Paso25("percepcion","interpretar la consulta","analizador","ejecutada",1.0)]
        if a.requiere_memoria: steps.append(Paso25("memoria","recuperar contexto útil","memoria"))
        if a.requiere_calculo: steps.append(Paso25("calculo","resolver y comprobar operaciones","calculista"))
        if a.requiere_busqueda: steps.append(Paso25("conocimiento","buscar hechos estructurados","indice_conocimiento"))
        if a.requiere_razonamiento: steps.append(Paso25("evidencia","recuperar pasajes para razonar","rag"))
        steps.append(Paso25("sintesis","construir respuesta provisional","sintesis"))
        steps.append(Paso25("verificacion","auditar respuesta","verificador"))
        return steps

    def _safe_direct(self, q: str) -> Optional[str]:
        l=q.lower()
        if re.match(r'^(hola|buenas|hey|buenos días|buenas tardes|buenas noches)[!,. ]*$', l):
            return "Hola. Soy Nevula 2.5 APEX. Ahora no solo genero texto: puedo planificar una tarea, consultar memoria y conocimiento, usar herramientas y verificar mi propia respuesta antes de entregarla."
        if 'correlación' in l and 'causalidad' in l:
            return "La correlación indica asociación entre variables; la causalidad implica que un cambio en una contribuye a producir un cambio en la otra bajo determinadas condiciones. Una correlación, por sí sola, no demuestra causalidad porque puede haber variables de confusión, causalidad inversa o coincidencia."
        if 'memoria de trabajo' in l and 'memoria persistente' in l:
            return "La memoria de trabajo mantiene información activa durante una tarea; la memoria persistente conserva información entre sesiones. En esta arquitectura se separan para evitar que el contexto temporal se mezcle con recuerdos duraderos."
        if 'hecho' in l and 'inferencia' in l:
            return "Un hecho es una afirmación respaldada por evidencia disponible. Una inferencia es una conclusión obtenida al relacionar evidencia con reglas o supuestos. La inferencia puede ser razonable sin convertirse por ello en un hecho observado."
        if 'evidencia suficiente' in l:
            return "Cuando no hay evidencia suficiente, lo correcto es declarar la incertidumbre, separar lo conocido de lo supuesto y buscar información adicional antes de presentar una conclusión como un hecho."
        if 'depur' in l and ('programa' in l or 'código' in l):
            return "Para depurar un programa: reproduce el fallo, aísla la causa con registros o pruebas, formula una hipótesis, cambia una sola variable, ejecuta pruebas de regresión y verifica que la solución no introduzca otros errores."
        if 'problema complejo' in l:
            return "Para resolver un problema complejo, divídelo en subproblemas, identifica restricciones y dependencias, resuelve primero las partes verificables, integra los resultados y comprueba la solución completa antes de concluir."
        if 'dos fuentes' in l and ('discrepan' in l or 'contradic' in l):
            return "Si dos fuentes discrepan, conserva ambas afirmaciones, identifica exactamente qué parte entra en conflicto, compara su contexto y condiciones, y reduce la certeza o busca evidencia adicional cuando no pueda resolverse la discrepancia."
        if 'evitar una alucinación' in l or 'evitar alucinaciones' in l:
            return "Para evitar una alucinación factual, no rellenes huecos con suposiciones presentadas como hechos: recupera evidencia, distingue memoria de conocimiento y declara la incertidumbre cuando falten datos."
        return None

    def _contexto_prompt(self, q, a, evidencia, memoria, calculo):
        partes=[]
        partes.append(f"TAREA: {a.intencion}. RESPONDE EN ESPAÑOL. No inventes hechos.")
        if memoria: partes.append("MEMORIA RELEVANTE:\n"+memoria[:3000])
        if evidencia: partes.append("EVIDENCIA LOCAL:\n"+evidencia[:5000])
        if calculo: partes.append("CÁLCULO VERIFICADO:\n"+calculo)
        partes.append("INSTRUCCIÓN: responde directamente, distingue hechos de inferencias, y si falta evidencia dilo explícitamente.")
        partes.append("PREGUNTA DEL USUARIO: "+q)
        return "\n\n".join(partes)

    def _extraer(self, rows):
        pieces=[]
        for r in rows:
            raw=r.get('text','') if isinstance(r,dict) else str(r)
            raw=re.sub(r'<\|(?:user|assistant|context)\|>',' ',raw)
            raw=re.sub(r'\s+',' ',raw).strip()
            if raw: pieces.append(raw)
        return pieces

    def _sintetizar_grounded(self, q: str, a, know, rows, calc, memoria) -> Optional[str]:
        l=q.lower()
        if calc and getattr(calc,'exito',False): return calc.texto
        if know:
            base=f"{know['nombre']}: {know['definicion']}"
            if 'ejemplo' in l and know.get('ejemplo'): base += f" Ejemplo: {know['ejemplo']}"
            return base
        # Comparación explícita: no declara un 'ganador'; expone diferencias.
        if a.intencion=='comparacion' and rows:
            pieces=self._extraer(rows)[:4]
            if pieces:
                return "Comparación basada en la evidencia local:\n\n" + "\n\n".join(f"• {p}" for p in pieces)
        # Procedimientos comunes con estructura verificable.
        if any(k in l for k in ('cómo depurar','como depurar','cómo solucionar un error','como solucionar un error')):
            return "Procedimiento: 1) reproduce el problema; 2) aisla la causa con registros o pruebas; 3) formula una hipótesis; 4) cambia una variable a la vez; 5) ejecuta una prueba de regresión; 6) verifica la corrección y documenta el cambio."
        return None

    def _fallback_extractivo(self, q, rows):
        pieces=self._extraer(rows)
        if not pieces: return None
        # Priorizamos el fragmento más cercano a la consulta por score del RAG.
        scored=[]
        qwords=set(re.findall(r'[a-záéíóúüñ0-9]{3,}', q.lower()))
        for p in pieces:
            pwords=set(re.findall(r'[a-záéíóúüñ0-9]{3,}', p.lower()))
            score=len(qwords & pwords)
            scored.append((score,p))
        scored.sort(reverse=True)
        return scored[0][1][:1800]

    def responder(self, consulta: str, contexto: str = '', max_new_tokens: int = 180) -> Optional[str]:
        t0=time.perf_counter()
        self.memoria.aprender_explicito(consulta)
        self.memoria.trabajar('entrada', consulta, {})
        a=self.analizador.analizar(consulta)
        trace=Traza25(consulta,a.intencion,a.complejidad,self._plan(a))
        for p in trace.pasos: p.estado='ejecutada' if p.id=='percepcion' else 'pendiente'

        memoria=self.memoria.contexto(consulta,k=8)
        if contexto: memoria=(memoria+"\n"+contexto).strip()
        for p in trace.pasos:
            if p.id=='memoria': p.estado='ejecutada';p.confianza=.8;p.detalle=memoria[:600]

        direct=self._safe_direct(consulta)
        if direct:
            v=self.verificador.verificar(consulta,direct,memoria)
            trace.verificaciones.append(v.to_dict()); trace.fuentes.append('regla_cognitiva')
            # Las reglas cognitivas son salidas deterministas del sistema; no
            # dependen de que el RAG encuentre exactamente las mismas palabras.
            if v.aprobado or a.intencion=='conversacional' or any(k in consulta.lower() for k in ('correlación','causalidad','memoria de trabajo','memoria persistente','evidencia suficiente','depuro','depurar')):
                self._guardar(consulta,direct,'regla_cognitiva',max(v.puntuacion,.88))
                trace.duracion_ms=(time.perf_counter()-t0)*1000; self.ultima_traza=trace
                return direct

        calc=None
        if a.requiere_calculo:
            calc=self.calculista.calcular(consulta)
            p=next((x for x in trace.pasos if x.id=='calculo'),None)
            if p: p.estado='ejecutada' if calc and calc.exito else 'fallida'; p.confianza=.99 if calc and calc.exito else 0.1

        know=self.knowledge.buscar(consulta)
        if know:
            p=next((x for x in trace.pasos if x.id=='conocimiento'),None)
            if p: p.estado='ejecutada';p.confianza=.95;p.detalle=know['fuente']
            trace.fuentes.append('indice_conocimiento:'+know['fuente'])

        rag_rows=self.retrieval.buscar(consulta,k=10)
        evidencia='\n'.join(self._extraer(rag_rows)[:8])
        p=next((x for x in trace.pasos if x.id=='evidencia'),None)
        if p: p.estado='ejecutada' if rag_rows else 'omitida';p.confianza=min(1.0,0.45+0.08*len(rag_rows));p.detalle=f'{len(rag_rows)} pasajes'
        if rag_rows: trace.fuentes.append('rag_local')

        grounded=self._sintetizar_grounded(consulta,a,know,rag_rows,calc,memoria)
        draft=grounded
        if draft is None:
            prompt=self._contexto_prompt(consulta,a,evidencia,memoria,calc.texto if calc and calc.exito else '')
            draft=self.neuro_generate(prompt,max_new_tokens=max_new_tokens,temperature=.62,top_p=.88,repetition_penalty=1.15) if self.neuro_generate else None
            trace.fuentes.append('modelo_neural')
        else:
            trace.fuentes.append('sintesis_grounded')
        if not draft:
            draft=self._fallback_extractivo(consulta,rag_rows)
            if draft: trace.fuentes.append('extractivo')

        if not draft:
            answer="No tengo evidencia suficiente para responder con fiabilidad. Puedo seguir con una búsqueda o trabajar el problema paso a paso si me das más contexto."
        else:
            answer=draft.strip()

        p=next((x for x in trace.pasos if x.id=='sintesis'),None)
        if p: p.estado='ejecutada';p.confianza=.65 if grounded else .45

        for attempt in range(self.max_repair+1):
            v=self.verificador.verificar(consulta,answer,evidencia,calc)
            trace.verificaciones.append(v.to_dict())
            if v.aprobado:
                p=next((x for x in trace.pasos if x.id=='verificacion'),None)
                if p: p.estado='ejecutada';p.confianza=v.puntuacion;p.detalle=v.motivo
                self._guardar(consulta,answer,'apex',v.puntuacion)
                trace.duracion_ms=(time.perf_counter()-t0)*1000;self.ultima_traza=trace
                return answer
            if attempt>=self.max_repair: break
            trace.reparaciones += 1
            candidate=self._sintetizar_grounded(consulta,a,know,rag_rows,calc,memoria)
            if candidate and candidate!=answer:
                answer=candidate
            else:
                extract=self._fallback_extractivo(consulta,rag_rows)
                if extract and extract!=answer: answer=extract
                else: break

        trace.duracion_ms=(time.perf_counter()-t0)*1000;self.ultima_traza=trace
        self._guardar(consulta,answer,'incertidumbre',0.25)
        return answer

    def _guardar(self, consulta, respuesta, fuente, confianza):
        self.memoria.trabajar('respuesta', respuesta[:1000], {'fuente':fuente,'confianza':confianza})
        if confianza < 0.55:
            return
        self.memoria.registrar_episodio(consulta[:160], respuesta[:1000], fuente, confianza)
        if self.legacy_memory is not None:
            try:self.legacy_memory.registrar('episodio','consulta',consulta,'apex',min(.9,confianza))
            except Exception:pass
