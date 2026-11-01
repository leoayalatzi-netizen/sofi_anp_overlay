#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Núcleo de Razonamiento — Coordinador de Motores Lógicos
# =====================================================================
# Versión: 0.0.2-NEBULA
# =====================================================================

import sys, time, traceback, threading, re
from pathlib import Path
from typing import Any, Dict
from enum import Enum

try:
    from ....nucleo.nucleo_base import NucleoBase
except ImportError:
    try:
        from nucleo.nucleo_base import NucleoBase
    except ImportError:
        from abc import ABC
        class EstadoMotor(Enum):
            NO_INICIALIZADO = "no_inicializado"
            ACTIVO = "activo"
            ERROR = "error"
        class NucleoBase:
            def __init__(self, nombre="NucleoBase"):
                self.nombre = nombre
                self._motores = {}
                self._estado = EstadoMotor.NO_INICIALIZADO
                self._lock = threading.RLock()
            def registrar_motor(self, nombre: str, motor):
                self._motores[nombre] = motor
            def inicializar(self):
                self._estado = EstadoMotor.ACTIVO
                for nombre, motor in self._motores.items():
                    try: motor.inicializar()
                    except: pass
                return True
            def detener(self):
                for nombre, motor in self._motores.items():
                    try: motor.detener()
                    except: pass
                self._estado = EstadoMotor.ERROR
                return True

class NucleoRazonamiento(NucleoBase):
    """Núcleo de Razonamiento — 6 motores lógicos."""
    
    def __init__(self):
        super().__init__("Razonamiento")
        self._motores_cargados = False
        self._dir = Path(__file__).parent / "motores"
    
    def _cargar_motores(self):
        if self._motores_cargados:
            return
        
        motores_esperados = {
            'motor_logico.py': 'MotorLogico',
            'motor_probabilistico.py': 'MotorProbabilistico',
            'motor_critico.py': 'MotorCritico',
            'motor_etico.py': 'MotorEtico',
            'motor_reflexivo.py': 'MotorReflexivo',
            'motor_causal.py': 'MotorCausal',
        }
        
        for archivo, clase_esperada in motores_esperados.items():
            ruta = self._dir / archivo
            if not ruta.exists():
                continue
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                clases = re.findall(r'class\s+(\w+)\s*\(\s*MotorBase\s*\)', contenido)
                if not clases:
                    continue
                clase_real = clases[0]
                nombre_modulo = archivo.replace('.py', '')
                modulo = __import__(f'nucleos.razonamiento.motores.{nombre_modulo}', fromlist=[clase_real])
                Clase = getattr(modulo, clase_real)
                instancia = Clase()
                self.registrar_motor(nombre_modulo, instancia)
            except Exception:
                pass
        
        self._motores_cargados = True
    
    def procesar(self, entrada: Dict, contexto=None) -> Dict:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        operacion = entrada.get('operacion', 'info')
        if operacion == 'info':
            return {'exito': True, 'nombre': self.nombre, 'motores': list(self._motores.keys()), 'total': len(self._motores)}
        motor_nombre = entrada.get('motor', 'motor_logico')
        if motor_nombre in self._motores:
            return self._motores[motor_nombre].procesar(entrada, contexto)
        return {'error': f'Motor no encontrado: {motor_nombre}', 'exito': False}


if __name__ == "__main__":
    n = NucleoRazonamiento()
    n._cargar_motores()
    print(f"Razonamiento: {len(n._motores)} motores")