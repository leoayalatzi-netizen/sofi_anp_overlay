# =====================================================================
# ANP - NÚCLEO CENTRAL
# Punto de entrada del sistema de orquestación
# =====================================================================
"""
Módulo central de ANP que contiene el orquestador maestro,
el bus de eventos y el sistema de contexto.
"""

__version__ = "0.0.1-NEBULA"
__author__ = "ANP Team"

# =====================================================================
# EXPORTACIONES PÚBLICAS DEL MÓDULO NUCLEO
# =====================================================================

# Estas importaciones permitirán usar:
# from nucleo import Orquestador, BusEventos, Contexto

try:
    from .orquestador.maestro import Orquestador
except ImportError:
    Orquestador = None

try:
    from .bus_eventos.bus import BusEventos
except ImportError:
    BusEventos = None

try:
    from .contexto.contexto import Contexto
except ImportError:
    Contexto = None

# =====================================================================
# METADATOS DEL NÚCLEO
# =====================================================================

def version():
    """Retorna la versión del núcleo."""
    return __version__

def nucleos_disponibles():
    """Verifica qué componentes del núcleo están disponibles."""
    return {
        'orquestador': Orquestador is not None,
        'bus_eventos': BusEventos is not None,
        'contexto': Contexto is not None,
    }

# =====================================================================
# INICIALIZACIÓN DEL NÚCLEO
# =====================================================================

def inicializar():
    """Inicializa el núcleo central y sus componentes."""
    from ..configuracion import obtener_config
    
    config = obtener_config()
    print(f"[NÚCLEO] Inicializando ANP Core v{__version__}")
    print(f"[NÚCLEO] Entorno: {config.entorno.name}")
    
    return nucleos_disponibles()

# =====================================================================
# AUTO-EJECUCIÓN PARA DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   DIAGNÓSTICO DEL NÚCLEO ANP")
    print("="*50)
    print(f"   Versión: {version()}")
    print(f"   Componentes: {nucleos_disponibles()}")
    print("="*50 + "\n")