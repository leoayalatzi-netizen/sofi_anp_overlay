#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reflexión - Analiza pensamientos y evalúa su valor
"""
import time, re
from typing import Dict, Any, List
from collections import deque

class Reflexion:
    """Analiza pensamientos generados y evalúa su calidad"""
    
    def __init__(self):
        self.historial_reflexiones = deque(maxlen=100)
        self.criterios = ["novedad", "coherencia", "utilidad", "profundidad", "aplicabilidad"]
    
    def analizar(self, pensamiento: Dict) -> Dict:
        """Analiza un pensamiento y devuelve una evaluación"""
        contenido = pensamiento.get("contenido", "")
        
        if not contenido:
            return {"valoracion": "sin_contenido", "puntuacion": 0, "deberia_guardar": False}
        
        puntuaciones = {}
        
        # Novedad: ¿es similar a pensamientos anteriores?
        puntuaciones["novedad"] = self._evaluar_novedad(contenido)
        
        # Coherencia: ¿tiene sentido interno?
        puntuaciones["coherencia"] = self._evaluar_coherencia(contenido)
        
        # Utilidad: ¿podría ser útil para respuestas futuras?
        puntuaciones["utilidad"] = self._evaluar_utilidad(contenido)
        
        # Profundidad: ¿va más allá de lo superficial?
        puntuaciones["profundidad"] = self._evaluar_profundidad(contenido)
        
        puntuacion_total = sum(puntuaciones.values()) / len(puntuaciones)
        
        reflexion = {
            "timestamp": time.time(),
            "pensamiento_original": pensamiento,
            "puntuaciones": puntuaciones,
            "puntuacion_total": round(puntuacion_total, 2),
            "conclusion": self._generar_conclusion(puntuacion_total),
            "deberia_guardar": puntuacion_total > 0.4,
            "deberia_compartir": puntuacion_total > 0.7,
        }
        
        self.historial_reflexiones.append(reflexion)
        return reflexion
    
    def _evaluar_novedad(self, contenido: str) -> float:
        if len(self.historial_reflexiones) == 0:
            return 0.8
        contenidos_previos = " ".join([
            str(r.get("pensamiento_original", {}).get("contenido", ""))
            for r in list(self.historial_reflexiones)[-10:]
        ])
        if contenido[:50] in contenidos_previos:
            return 0.1
        return 0.6
    
    def _evaluar_coherencia(self, contenido: str) -> float:
        score = 0.5
        if len(contenido) > 20: score += 0.1
        if len(contenido) > 50: score += 0.1
        if '?' in contenido and len(contenido) > 30: score += 0.1
        if any(p in contenido.lower() for p in ['porque', 'conexión', 'relación', 'patrón']): score += 0.1
        return min(1.0, score)
    
    def _evaluar_utilidad(self, contenido: str) -> float:
        score = 0.3
        if any(p in contenido.lower() for p in ['podría', 'quizás', 'tal vez', '¿y si']): score += 0.2
        if any(p in contenido.lower() for p in ['conocimiento', 'aprender', 'mejorar', 'respuesta']): score += 0.2
        if len(contenido) > 40: score += 0.1
        return min(1.0, score)
    
    def _evaluar_profundidad(self, contenido: str) -> float:
        score = 0.3
        indicadores_profundidad = ['consciencia', 'significado', 'esencia', 'filosofía', 'patrón', 'conexión profunda', 'no sé', 'duda', 'cuestionar']
        for ind in indicadores_profundidad:
            if ind in contenido.lower():
                score += 0.1
        return min(1.0, score)
    
    def _generar_conclusion(self, puntuacion: float) -> str:
        if puntuacion > 0.8: return "Excelente pensamiento. Vale la pena desarrollarlo."
        if puntuacion > 0.6: return "Buen pensamiento. Puede llevar a ideas útiles."
        if puntuacion > 0.4: return "Pensamiento aceptable. Registrar para revisión."
        return "Pensamiento débil. Descartar o reformular."
