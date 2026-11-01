# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Módulo de Fallback (Sistema de Resiliencia)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

# ===== CORRECCIÓN CRÍTICA: Agregar directorio actual al path =====
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

__version__ = "0.0.1-NEBULA"
__author__ = "ANP Team"
__all__ = [
    'GestorFallback',
    'CircuitBreaker',
    'EstadoCircuitBreaker',
    'DetectorAnomalias',
    'Degradador',
    'NivelDegradacion',
    'RedundanciaNucleos',
    'RecuperadorEstado',
    'TipoFallo',
    'GestorRespuestasEmergencia',
    'NivelEmergencia',
    'CategoriaFallo',
    'TonoRespuesta',
    'obtener_gestor_fallback',
    'obtener_gestor_respuestas',
    'respuesta_emergencia',
    'inicializar_sistema_fallback',
]

# =====================================================================
# IMPORTACIONES DESDE WRAPPERS
# =====================================================================

_wrappers_disponible = False
try:
    from wrappers import (
        CircuitBreaker,
        EstadoCircuitBreaker,
        DetectorAnomalias,
        Degradador,
        NivelDegradacion,
        RedundanciaNucleos,
        RecuperadorEstado,
        GestorFallback,
        TipoFallo,
        obtener_gestor_fallback,
        inicializar_sistema_fallback,
    )
    _wrappers_disponible = True
except ImportError as e:
    print(f"⚠️ Error importando wrappers: {e}")
    
    # Placeholders
    class CircuitBreaker:
        def __init__(self, *a, **k): pass
    class DetectorAnomalias:
        def __init__(self, *a, **k): pass
    class Degradador:
        def __init__(self, *a, **k): pass
    class RedundanciaNucleos:
        def __init__(self, *a, **k): pass
    class RecuperadorEstado:
        def __init__(self, *a, **k): pass
    class GestorFallback:
        def __init__(self, *a, **k): pass
        def obtener_estado(self): return {}
    EstadoCircuitBreaker = None
    NivelDegradacion = None
    TipoFallo = None
    obtener_gestor_fallback = lambda: None
    inicializar_sistema_fallback = lambda: None

# =====================================================================
# IMPORTACIONES DESDE RESPUESTAS_EMERGENCIA
# =====================================================================

_respuestas_disponible = False
try:
    from respuestas_emergencia import (
        GestorRespuestasEmergencia,
        NivelEmergencia,
        CategoriaFallo,
        TonoRespuesta,
        obtener_gestor_respuestas,
        respuesta_emergencia,
    )
    _respuestas_disponible = True
except ImportError as e:
    print(f"⚠️ Error importando respuestas_emergencia: {e}")
    
    # Placeholders
    class NivelEmergencia:
        LEVE, MODERADA, GRAVE, CRITICA, CATASTROFICA = range(5)
    class CategoriaFallo:
        DESCONOCIDO = "desconocido"
        TIMEOUT = "timeout"
        MEMORIA_INSUFICIENTE = "memoria_insuficiente"
        NUCLEO_NO_DISPONIBLE = "nucleo_no_disponible"
        ERROR_INTERNO = "error_interno"
        RED_NO_DISPONIBLE = "red_no_disponible"
        SOBRECARGA = "sobrecarga"
    class TonoRespuesta:
        NEUTRAL = "neutral"
    GestorRespuestasEmergencia = None
    obtener_gestor_respuestas = lambda: None
    respuesta_emergencia = lambda *a, **k: "Error: Respuestas no disponibles"

# =====================================================================
# METADATOS
# =====================================================================

def version() -> str:
    return __version__

def componentes_disponibles() -> Dict[str, bool]:
    return {
        'wrappers': _wrappers_disponible,
        'respuestas_emergencia': _respuestas_disponible,
        'gestor_fallback': _wrappers_disponible,
        'circuit_breaker': _wrappers_disponible,
        'detector_anomalias': _wrappers_disponible,
        'degradador': _wrappers_disponible,
        'redundancia_nucleos': _wrappers_disponible,
        'recuperador_estado': _wrappers_disponible,
    }

def inicializar_fallback():
    if _wrappers_disponible:
        return inicializar_sistema_fallback()
    return None

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MÓDULO DE FALLBACK")
    print("=" * 70)
    
    print(f"\n📁 Directorio actual: {_current_dir}")
    print(f"📌 Versión: {version()}")
    
    print("\n[1/3] Verificando componentes...")
    disponibles = componentes_disponibles()
    for nombre, disponible in disponibles.items():
        icono = "✅" if disponible else "❌"
        print(f"  {icono} {nombre}")
    
    print("\n[2/3] Inicializando gestor de fallback...")
    gestor = inicializar_fallback()
    if gestor:
        print(f"  ✅ Gestor inicializado")
        estado = gestor.obtener_estado()
        print(f"  📊 fallback_activo={estado.get('fallback_activo', False)}")
    else:
        print(f"  ⚠️ Gestor no disponible")
    
    print("\n[3/3] Probando respuestas de emergencia...")
    if _respuestas_disponible:
        resp = respuesta_emergencia(CategoriaFallo.TIMEOUT, NivelEmergencia.MODERADA)
        print(f"  📍 {resp[:60]}...")
    else:
        print(f"  ⚠️ No disponible")
    
    print("\n" + "=" * 70)
    if _wrappers_disponible and _respuestas_disponible:
        print("   ✅ SISTEMA DE FALLBACK COMPLETO")
    else:
        print("   ⚠️ SISTEMA PARCIAL")
    print("=" * 70 + "\n")