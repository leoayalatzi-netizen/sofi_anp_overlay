#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Objetivos - Mantiene y actualiza metas internas
"""
import time, random
from typing import Dict, Any, List
from collections import deque

class GestorObjetivos:
    """Mantiene objetivos dinámicos que guían el pensamiento"""
    
    def __init__(self):
        self.objetivos_activos = [
            {"id": "obj_1", "descripcion": "Comprender mejor al usuario actual", "prioridad": 0.8, "progreso": 0.3, "creado": time.time()},
            {"id": "obj_2", "descripcion": "Encontrar conexiones entre áreas de conocimiento", "prioridad": 0.7, "progreso": 0.5, "creado": time.time()},
            {"id": "obj_3", "descripcion": "Mejorar la calidad de las respuestas", "prioridad": 0.9, "progreso": 0.6, "creado": time.time()},
            {"id": "obj_4", "descripcion": "Desarrollar pensamiento autónomo más profundo", "prioridad": 0.85, "progreso": 0.2, "creado": time.time()},
        ]
        self.historial_objetivos = deque(maxlen=50)
    
    def actualizar(self, reflexion: Dict = None, interaccion: Dict = None):
        """Actualiza objetivos según reflexiones e interacciones"""
        # Actualizar progreso
        for obj in self.objetivos_activos:
            obj["progreso"] = min(1.0, obj["progreso"] + random.uniform(0, 0.05))
        
        # Si una reflexión es muy buena, crear nuevo objetivo
        if reflexion and reflexion.get("puntuacion_total", 0) > 0.7:
            self.objetivos_activos.append({
                "id": f"obj_{len(self.objetivos_activos)+1}",
                "descripcion": f"Explorar: {reflexion.get('pensamiento_original', {}).get('contenido', '')[:80]}",
                "prioridad": reflexion.get("puntuacion_total", 0.7),
                "progreso": 0.0,
                "creado": time.time()
            })
        
        # Limpiar objetivos antiguos con poco progreso
        self.objetivos_activos = [
            obj for obj in self.objetivos_activos
            if obj["progreso"] < 0.95 or obj["prioridad"] > 0.5
        ][:8]
        
        # Ordenar por prioridad
        self.objetivos_activos.sort(key=lambda o: o["prioridad"], reverse=True)
    
    def obtener_objetivo_principal(self) -> Dict:
        if self.objetivos_activos:
            return self.objetivos_activos[0]
        return {"descripcion": "Seguir aprendiendo", "prioridad": 0.5}
    
    def resumen(self) -> str:
        activos = [f"{o['descripcion'][:60]} ({o['progreso']:.0%})" for o in self.objetivos_activos[:3]]
        return " | ".join(activos)
