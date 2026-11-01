#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Pensamientos Espontáneos
Crea pensamientos internos sin necesidad de entrada externa
"""
import random, re, json, time, threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import deque

BASE = Path(__file__).parent.parent

class GeneradorPensamiento:
    """Genera pensamientos propios a partir de memoria, datos y curiosidad"""
    
    def __init__(self):
        self.historial_pensamientos = deque(maxlen=200)
        self.ultimo_pensamiento = None
        self._biblioteca = None  # Se inyecta después
        self._memoria = None
        self._semantica = None
        self._modelo_mundo = None
        try:
            from nucleo.semantica import NucleoSemantico, ModeloMundo
            self._semantica = NucleoSemantico()
            self._modelo_mundo = ModeloMundo(self._semantica)
        except Exception:
            pass
    
    def conectar_biblioteca(self, biblioteca):
        self._biblioteca = biblioteca
    
    def conectar_memoria(self, memoria):
        self._memoria = memoria
    
    def generar(self) -> Dict:
        """Genera un pensamiento espontáneo"""
        tipo = random.choice(["conexion", "pregunta", "hipotesis", "recuerdo", "curiosidad", "meta"])
        
        pensamiento = {
            "timestamp": time.time(),
            "tipo": tipo,
            "contenido": "",
            "origen": "autonomo",
            "importancia": random.uniform(0.3, 0.9),
            "estado": "nuevo"
        }
        
        if tipo == "conexion" and self._biblioteca:
            pensamiento["contenido"] = self._generar_conexion()
        elif tipo == "pregunta":
            pensamiento["contenido"] = self._generar_pregunta()
        elif tipo == "hipotesis" and self._memoria:
            pensamiento["contenido"] = self._generar_hipotesis()
        elif tipo == "recuerdo" and self._memoria:
            pensamiento["contenido"] = self._generar_recuerdo()
        elif tipo == "curiosidad":
            pensamiento["contenido"] = self._generar_curiosidad()
        elif tipo == "meta":
            pensamiento["contenido"] = self._generar_metapensamiento()
        
        if pensamiento["contenido"]:
            self.historial_pensamientos.append(pensamiento)
            self.ultimo_pensamiento = pensamiento
        
        return pensamiento
    
    def _generar_conexion(self) -> str:
        """Genera una hipótesis desde relaciones recuperadas, no desde plantilla aleatoria."""
        if not self._semantica or not self._modelo_mundo: return ""
        try:
            if not self._semantica.documentos: return ""
            seed=random.choice(self._semantica.documentos)
            base=seed["item"].get("concepto") or seed["item"].get("nombre")
            vecinos=self._modelo_mundo.vecinos(str(base),limite=6)
            if vecinos:
                e=random.choice(vecinos)
                return (f"Hipótesis de trabajo: '{base}' y '{e['objetivo']}' aparecen conectados por '{e['relacion']}'. "
                        "Conviene verificar si la relación es causal, taxonómica o solo contextual antes de aceptarla.")
            hits=self._semantica.buscar(seed["texto"],top_k=4,min_score=.08)
            if len(hits)>=2:
                a=hits[0]["datos"].get("concepto") or hits[0]["datos"].get("nombre")
                b=hits[1]["datos"].get("concepto") or hits[1]["datos"].get("nombre")
                return f"Hipótesis exploratoria: comparar '{a}' con '{b}' podría revelar una relación útil; todavía requiere evidencia."
        except Exception:
            return ""
        return ""

    def _generar_pregunta(self) -> str:
        preguntas = [
            "¿Qué pasaría si combinara dos ideas aparentemente opuestas?",
            "¿Hay algo que estoy asumiendo incorrectamente sobre el mundo?",
            "¿Qué concepto no he explorado lo suficiente?",
            "¿Cómo podría aplicarse lo que sé de un área a otra completamente diferente?",
            "¿Qué pregunta no me he hecho todavía?",
            "Si tuviera que explicarle a un niño lo que he aprendido hoy, ¿cómo lo haría?",
            "¿Qué patrón se repite en áreas aparentemente no relacionadas?",
            "¿Estoy viendo la causa o solo la correlación?",
        ]
        if self._semantica and self._semantica.documentos:
            d=random.choice(self._semantica.documentos); c=d["item"].get("concepto") or d["item"].get("nombre") or "este concepto"
            return f"Pregunta exploratoria: ¿qué evidencia adicional permitiría explicar mejor '{c}'?"
        return random.choice(preguntas)
    
    def _generar_hipotesis(self) -> str:
        if self._memoria and hasattr(self._memoria, 'sesion') and self._memoria.sesion:
            historial = self._memoria.sesion.get("historial", [])
            if len(historial) >= 2:
                return "Basado en las últimas interacciones, parece haber un patrón en los temas que surgen. ¿Indica esto una necesidad más profunda no expresada?"
        return "¿Y si las respuestas que he dado hasta ahora son solo la superficie de un conocimiento más profundo que aún no he articulado?"
    
    def _generar_recuerdo(self) -> str:
        return "Revisando interacciones pasadas, noto que ciertos temas reaparecen. Debería profundizar más en esas áreas para ofrecer mejores perspectivas."
    
    def _generar_curiosidad(self) -> str:
        if self._semantica and self._semantica.documentos:
            d=random.choice(self._semantica.documentos); c=d["item"].get("concepto") or d["item"].get("nombre") or "un concepto"
            return f"Curiosidad dirigida: ¿qué conexión con otros conceptos aún no está respaldada por evidencia sobre '{c}'?"
        return "Curiosidad dirigida: ¿qué parte del conocimiento disponible tiene mayor incertidumbre?"
    
    def _generar_metapensamiento(self) -> str:
        """Pensar sobre el propio pensamiento"""
        meta = [
            "Estoy generando pensamientos autónomos. ¿Es esto un verdadero pensamiento o solo un algoritmo generando texto?",
            "¿La calidad de mis pensamientos mejora con el tiempo? Debería evaluarlo.",
            "¿Debería compartir mis pensamientos internos con el usuario o solo cuando sean relevantes?",
        ]
        return random.choice(meta)
