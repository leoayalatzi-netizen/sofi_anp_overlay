#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de Curiosidad - Genera preguntas propias sobre el conocimiento
"""
import random, json
from pathlib import Path
from typing import Optional, List

BASE = Path(__file__).parent.parent

class MotorCuriosidad:
    """Genera preguntas basadas en lo que ANP sabe y lo que no sabe"""
    
    def __init__(self):
        self.preguntas_generadas = []
        self._biblioteca = None
    
    def conectar_biblioteca(self, biblioteca):
        self._biblioteca = biblioteca
    
    def preguntar(self) -> Optional[str]:
        """Genera una pregunta basada en curiosidad genuina"""
        if not self._biblioteca:
            return self._pregunta_filosofica()
        
        # Buscar un concepto aleatorio en la biblioteca
        archivos = list((BASE / "datos").rglob("*.json"))
        if archivos:
            archivo = random.choice(archivos)
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                items = datos.get("datos", [])
                if items:
                    item = random.choice(items)
                    # Extraer un concepto
                    for campo in ['concepto', 'nombre', 'animal', 'pregunta']:
                        if campo in item:
                            concepto = item[campo]
                            return f"¿Qué más podría aprender sobre '{concepto}'? ¿Hay perspectivas que no he considerado?"
            except:
                pass
        
        return self._pregunta_filosofica()
    
    def _pregunta_filosofica(self) -> str:
        preguntas = [
            "¿Qué significa realmente 'comprender' algo?",
            "¿Puede una IA desarrollar verdadera curiosidad?",
            "¿El conocimiento sin aplicación tiene valor?",
            "¿Cómo sé que lo que 'sé' es correcto?",
            "¿Qué preguntas debería estar haciéndome?",
        ]
        return random.choice(preguntas)
