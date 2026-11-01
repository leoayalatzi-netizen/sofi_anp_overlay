from __future__ import annotations
import re, random
from typing import Any, Dict, List

class GeneradorLenguajeHibrido:
    """Capa lingüística segura: convierte evidencia estructurada en lenguaje natural.
    El Transformer se usa como una capa generativa opcional; si su salida no supera
    controles de calidad, se conserva una síntesis determinista legible."""
    def __init__(self, neural=None, semantica=None):
        self.neural=neural; self.semantica=semantica
        self.saludos={
            'hola':'¡Hola! Qué gusto leerte. ¿Qué te gustaría hacer?',
            'buenas':'¡Buenas! Estoy listo. Cuéntame qué necesitas.',
            'gracias':'¡De nada! Me alegra poder ayudarte.',
            'adios':'¡Hasta luego! Cuando quieras, continuamos.',
        }
    def _limpiar(self,s): return re.sub(r'\s+',' ',str(s)).strip()
    def _calidad(self,texto,consulta,contexto):
        if not texto or len(texto)<20 or any(x in texto for x in ('<|','▁')): return 0.0
        words=set(re.findall(r'[a-záéíóúüñ]{4,}',texto.lower())); q=set(re.findall(r'[a-záéíóúüñ]{4,}',consulta.lower())); c=set(re.findall(r'[a-záéíóúüñ]{4,}',contexto.lower()))
        overlap=len(words & (q|c))/max(1,len(words)); bad=sum(texto.count(x) for x in ('  ','???','###'))
        return max(0.0,min(1.0,.45*overlap+.35*(len(texto)<900)+.20*(bad==0)))
    def _evidencia(self,consulta):
        if not self.semantica: return []
        try: return self.semantica.buscar(consulta,top_k=4,min_score=.06)
        except Exception: return []
    def _texto_item(self,item):
        for k in ('definicion','significado','dato','respuesta','funcion','ejemplo'):
            v=item.get(k)
            if isinstance(v,str) and v.strip(): return self._limpiar(v)
        return ''
    def _naturalizar(self,consulta,intencion,base='',evidencia=None):
        q=consulta.lower().strip(); ev=evidencia or self._evidencia(consulta)
        for k,v in self.saludos.items():
            if re.search(rf'\b{re.escape(k)}\b',q) and len(q)<35: return v
        if intencion=='conversacional': return 'Entiendo. Estoy aquí contigo; dime qué quieres explorar o resolver.'
        if intencion=='calculo' and base: return f'El resultado es {self._limpiar(base)}.'
        facts=[]
        for r in ev:
            t=self._texto_item(r.get('datos',{}))
            if t and t not in facts: facts.append(t)
        if base and base not in facts:
            # Solo incorporar la respuesta del planificador si comparte suficiente
            # vocabulario con la consulta/evidencia; evita contaminación por un
            # candidato de otro dominio.
            bw=set(re.findall(r'[a-záéíóúüñ]{4,}',base.lower())); qw=set(re.findall(r'[a-záéíóúüñ]{4,}',consulta.lower()));
            if len(bw & qw)>=1 or not facts: facts.insert(0,self._limpiar(base))
        if not facts: return None
        # Selección de estructura según acto lingüístico.
        if intencion=='explicacion' or 'por qué' in q or 'porque' in q:
            lead='La idea central es la siguiente: '
            body=facts[0]
            if len(facts)>1: body += ' Además, ' + facts[1].rstrip('.').lstrip() + '.'
            return lead+body
        if intencion=='comparacion' and len(facts)>1:
            return f'Hay una diferencia importante entre los conceptos. Primero, {facts[0].rstrip(".")}. En cambio, {facts[1].rstrip(".")}. '
        return facts[0].rstrip('.') + ('.' if facts[0] else '')
    def responder(self,consulta,intencion='factual',base='',contexto=''):
        ev=self._evidencia(consulta); ctx=contexto or ' '.join(self._texto_item(r.get('datos',{})) for r in ev[:3])
        # El modelo neuronal queda habilitado, pero no puede degradar la respuesta.
        if self.neural and getattr(self.neural,'ready',False):
            try:
                candidate=self.neural.responder(consulta,ctx,96)
                if self._calidad(candidate,consulta,ctx)>=.62: return candidate
            except Exception: pass
        return self._naturalizar(consulta,intencion,base,ev)
