#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ciclo Autónomo de Pensamiento
Hilo permanente que genera pensamientos sin entrada externa
"""
import time, threading, random
from typing import Optional, Dict, Any
from collections import deque

class CicloAutonomo:
    """Hilo de pensamiento que corre en segundo plano"""
    
    def __init__(self, generador, reflexion, objetivos, curiosidad):
        self.generador = generador
        self.reflexion = reflexion
        self.objetivos = objetivos
        self.curiosidad = curiosidad
        self.pensamientos_procesados = deque(maxlen=500)
        self.activo = False
        self.hilo = None
        self.intervalo_base = 5  # segundos entre pensamientos
    
    def iniciar(self):
        """Inicia el ciclo autónomo en un hilo separado"""
        if self.activo:
            return
        self.activo = True
        self.hilo = threading.Thread(target=self._ciclo, daemon=True)
        self.hilo.start()
    
    def detener(self):
        self.activo = False
    
    def _ciclo(self):
        """El ciclo principal de pensamiento"""
        while self.activo:
            try:
                # 1. Generar pensamiento
                pensamiento = self.generador.generar()
                
                if pensamiento and pensamiento.get("contenido"):
                    # 2. Reflexionar sobre él
                    reflexion = self.reflexion.analizar(pensamiento)
                    
                    # 3. Actualizar objetivos según reflexión
                    self.objetivos.actualizar(reflexion=reflexion)
                    
                    # 4. Guardar
                    self.pensamientos_procesados.append({
                        "pensamiento": pensamiento,
                        "reflexion": reflexion,
                        "timestamp": time.time()
                    })
                
                # 5. Generar curiosidad ocasionalmente
                if random.random() < 0.2:
                    pregunta = self.curiosidad.preguntar()
                    if pregunta:
                        self.pensamientos_procesados.append({
                            "pensamiento": {"tipo": "curiosidad", "contenido": pregunta},
                            "timestamp": time.time()
                        })
                
                # Intervalo variable (más rápido si hay mucha actividad)
                intervalo = self.intervalo_base + random.uniform(0, 10)
                time.sleep(intervalo)
                
            except Exception as e:
                time.sleep(5)
    
    def obtener_ultimos_pensamientos(self, n: int = 5) -> list:
        return list(self.pensamientos_procesados)[-n:]
    
    def estadisticas(self) -> Dict:
        total = len(self.pensamientos_procesados)
        return {
            "total_pensamientos": total,
            "activo": self.activo,
            "ultimos_5": [
                p.get("pensamiento", {}).get("contenido", "")[:100]
                for p in list(self.pensamientos_procesados)[-5:]
            ]
        }
