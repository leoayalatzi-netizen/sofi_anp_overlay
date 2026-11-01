from __future__ import annotations
import re, math
from dataclasses import dataclass, asdict
@dataclass
class Plan:
    intencion:str; objetivo:str; pasos:list; necesita_evidencia:bool; confianza:float
class PlanificadorRazonamiento:
    VERSION='2.4-OMEGA-reasoning'
    def analizar(self,q):
        q=q.strip(); l=q.lower()
        if any(x in l for x in ('por qué','porque','cómo funciona','demuestra','razona','explica por qué')): intent='explicacion_causal'
        elif any(x in l for x in ('compara','diferencia','vs','versus','mejor que')): intent='comparacion'
        elif any(x in l for x in ('cuánto','cuanto','calcula','resuelve','resultado')): intent='calculo'
        elif any(x in l for x in ('paso a paso','cómo hacer','como hacer','implementa','código','codigo')): intent='procedimiento'
        elif '?' in q: intent='pregunta_factica'
        else: intent='conversacion'
        steps={
            'explicacion_causal':['identificar conceptos','recuperar evidencia','separar causas de consecuencias','comprobar coherencia','redactar explicación'],
            'comparacion':['extraer criterios','recuperar datos de ambos lados','comparar simétricamente','señalar trade-offs','concluir'],
            'calculo':['normalizar variables','resolver simbólicamente si procede','comprobar unidades','verificar resultado','explicar'],
            'procedimiento':['definir objetivo','listar restricciones','proponer pasos','verificar riesgos','entregar procedimiento'],
            'pregunta_factica':['identificar entidades','recuperar evidencia','detectar incertidumbre','responder con alcance'],
            'conversacion':['interpretar intención','usar memoria pertinente','responder directamente']
        }[intent]
        return Plan(intent,q,steps,intent not in ('conversacion',),.72 if intent!='conversacion' else .55)
    def prompt(self,plan,evidence,memory):
        lines=[f"INTENCION: {plan.intencion}",f"OBJETIVO: {plan.objetivo}","PLAN: "+' -> '.join(plan.pasos)]
        if evidence: lines.append('EVIDENCIA LOCAL:\n'+evidence)
        if memory: lines.append('MEMORIA PERTINENTE:\n'+memory)
        lines.append('REGLAS: no inventes hechos ausentes; distingue evidencia de inferencia; responde en español claro; si falta información dilo explícitamente.')
        return '\n'.join(lines)
