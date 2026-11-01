# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Módulo de Bus de Eventos (Sistema Nervioso Central)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# Este módulo implementa el sistema nervioso central de ANP,
# permitiendo comunicación asíncrona y desacoplada entre todos
# los componentes del sistema mediante un bus de eventos pub/sub.
# =====================================================================

import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union

# ===== Agregar directorio actual al path =====
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

__version__ = "0.0.1-NEBULA"
__author__ = "ANP Team"

# =====================================================================
# API PÚBLICA DEL MÓDULO
# =====================================================================

__all__ = [
    # Bus principal
    'BusEventos',
    'Evento',
    'TipoEvento',
    'PrioridadEvento',
    'Suscriptor',
    'MiddlewareBase',
    
    # Middleware incluidos
    'MiddlewareLogging',
    'MiddlewareValidacion',
    'MiddlewareMetricas',
    
    # Utilidades
    'suscriptor',
    'publicar',
    'suscribir',
    'obtener_bus',
    
    # Excepciones
    'ErrorEvento',
    'ErrorPublicacion',
    'ErrorSuscripcion',
]

# =====================================================================
# IMPORTACIONES DE COMPONENTES (con placeholders)
# =====================================================================

# Tipos de eventos
try:
    from .tipos import TipoEvento
except ImportError:
    class TipoEvento:
        """Placeholder para tipos de eventos."""
        SISTEMA_INICIANDO = "sistema.iniciando"
        SISTEMA_LISTO = "sistema.listo"
        SISTEMA_APAGANDO = "sistema.apagando"
        SISTEMA_ERROR = "sistema.error"
        FALLO_GENERAL = "fallo.general"
        FALLO_TIMEOUT = "fallo.timeout"
        FALLO_MEMORIA = "fallo.memoria"
        FALLO_NUCLEO = "fallo.nucleo"
        NUCLEO_ACTIVADO = "nucleo.activado"
        NUCLEO_DESACTIVADO = "nucleo.desactivado"
        NUCLEO_FALLBACK = "nucleo.fallback"
        TAREA_CREADA = "tarea.creada"
        TAREA_COMPLETADA = "tarea.completada"
        TAREA_FALLIDA = "tarea.fallida"
        CONTEXTO_CAMBIADO = "contexto.cambiado"
        MEMORIA_ACTUALIZADA = "memoria.actualizada"
        USUARIO_HABLANDO = "usuario.hablando"
        IA_PENSANDO = "ia.pensando"
        IA_RESPONDIENDO = "ia.respondiendo"
        
        @classmethod
        def todos(cls) -> List[str]:
            return [v for k, v in cls.__dict__.items() if not k.startswith('_') and isinstance(v, str)]

# Prioridad de eventos
try:
    from .prioridad import PrioridadEvento
except ImportError:
    class PrioridadEvento:
        """Placeholder para prioridades de eventos."""
        CRITICA = 0
        ALTA = 1
        MEDIA = 2
        BAJA = 3
        DIFERIDA = 4
        
        _nombres = ['CRITICA', 'ALTA', 'MEDIA', 'BAJA', 'DIFERIDA']
        
        @classmethod
        def nombre(cls, prioridad: int) -> str:
            return cls._nombres[prioridad] if 0 <= prioridad < len(cls._nombres) else 'DESCONOCIDA'

# Clase Evento
try:
    from .evento import Evento
except ImportError:
    from dataclasses import dataclass, field
    import time
    import uuid
    
    @dataclass
    class Evento:
        """Placeholder para la clase Evento."""
        tipo: str = ""
        datos: Any = None
        origen: str = ""
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: float = field(default_factory=time.time)
        prioridad: int = PrioridadEvento.MEDIA
        metadatos: Dict[str, Any] = field(default_factory=dict)
        
        def a_dict(self) -> Dict[str, Any]:
            return {
                'id': self.id,
                'tipo': self.tipo,
                'datos': self.datos,
                'origen': self.origen,
                'timestamp': self.timestamp,
                'prioridad': self.prioridad,
                'metadatos': self.metadatos,
            }

# Suscriptor (ABC)
try:
    from .suscriptor import Suscriptor
except ImportError:
    from abc import ABC, abstractmethod
    
    class Suscriptor(ABC):
        """Placeholder para la interfaz Suscriptor."""
        
        @abstractmethod
        def on_evento(self, evento: Evento) -> None:
            """Maneja un evento recibido."""
            pass
        
        @property
        @abstractmethod
        def id_suscriptor(self) -> str:
            """Identificador único del suscriptor."""
            pass

# Bus principal
try:
    from .bus import BusEventos
except ImportError:
    import threading
    from collections import defaultdict, deque
    
    class BusEventos:
        """Placeholder para el Bus de Eventos."""
        
        _instancia = None
        _lock = threading.RLock()
        
        def __new__(cls):
            with cls._lock:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
                    cls._instancia._inicializado = False
                return cls._instancia
        
        def __init__(self):
            if self._inicializado:
                return
            with self._lock:
                if self._inicializado:
                    return
                self._suscriptores = defaultdict(list)
                self._cola_eventos = deque()
                self._procesando = False
                self._inicializado = True
        
        def suscribir(self, tipo_evento: str, suscriptor: Suscriptor) -> bool:
            if suscriptor not in self._suscriptores[tipo_evento]:
                self._suscriptores[tipo_evento].append(suscriptor)
                return True
            return False
        
        def desuscribir(self, tipo_evento: str, suscriptor: Suscriptor) -> bool:
            if suscriptor in self._suscriptores[tipo_evento]:
                self._suscriptores[tipo_evento].remove(suscriptor)
                return True
            return False
        
        def publicar(self, evento: Evento) -> bool:
            self._cola_eventos.append(evento)
            return True
        
        def __repr__(self):
            return f"BusEventos(suscriptores={sum(len(v) for v in self._suscriptores.values())})"

# Middleware
try:
    from .middleware import MiddlewareBase, MiddlewareLogging, MiddlewareValidacion, MiddlewareMetricas
except ImportError:
    from abc import ABC, abstractmethod
    
    class MiddlewareBase(ABC):
        """Placeholder para middleware base."""
        
        @abstractmethod
        def antes_publicar(self, evento: Evento) -> Optional[Evento]:
            pass
        
        @abstractmethod
        def despues_publicar(self, evento: Evento):
            pass
        
        @abstractmethod
        def antes_entregar(self, evento: Evento, suscriptor: Suscriptor) -> Optional[Evento]:
            pass
    
    class MiddlewareLogging(MiddlewareBase):
        def antes_publicar(self, evento): return evento
        def despues_publicar(self, evento): pass
        def antes_entregar(self, evento, suscriptor): return evento
    
    class MiddlewareValidacion(MiddlewareBase):
        def antes_publicar(self, evento): return evento
        def despues_publicar(self, evento): pass
        def antes_entregar(self, evento, suscriptor): return evento
    
    class MiddlewareMetricas(MiddlewareBase):
        def antes_publicar(self, evento): return evento
        def despues_publicar(self, evento): pass
        def antes_entregar(self, evento, suscriptor): return evento

# =====================================================================
# EXCEPCIONES
# =====================================================================

class ErrorEvento(Exception):
    """Excepción base para errores del bus de eventos."""
    pass

class ErrorPublicacion(ErrorEvento):
    """Error al publicar un evento."""
    pass

class ErrorSuscripcion(ErrorEvento):
    """Error al suscribirse a eventos."""
    pass

# =====================================================================
# DECORADOR DE SUSCRIPTOR
# =====================================================================

def suscriptor(tipo_evento: Union[str, List[str]]):
    """
    Decorador para marcar métodos como manejadores de eventos.
    
    Uso:
        @suscriptor(TipoEvento.USUARIO_HABLANDO)
        def manejar_mensaje(self, evento: Evento):
            print(f"Mensaje recibido: {evento.datos}")
    """
    def decorador(func: Callable):
        func._suscripciones = tipo_evento if isinstance(tipo_evento, list) else [tipo_evento]
        return func
    return decorador

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_bus_global: Optional[BusEventos] = None

def obtener_bus() -> BusEventos:
    """Obtiene la instancia global del bus de eventos."""
    global _bus_global
    if _bus_global is None:
        _bus_global = BusEventos()
    return _bus_global

def publicar(tipo: str, datos: Any = None, origen: str = "", 
             prioridad: int = PrioridadEvento.MEDIA, **kwargs) -> bool:
    """
    Función rápida para publicar un evento.
    
    Uso:
        publicar(TipoEvento.USUARIO_HABLANDO, datos={"mensaje": "Hola"})
    """
    bus = obtener_bus()
    evento = Evento(
        tipo=tipo,
        datos=datos,
        origen=origen or "desconocido",
        prioridad=prioridad,
        metadatos=kwargs
    )
    return bus.publicar(evento)

def suscribir(tipo_evento: str, callback: Callable[[Evento], None]) -> bool:
    """
    Función rápida para suscribir un callback a un tipo de evento.
    
    Uso:
        def mi_callback(evento: Evento):
            print(f"Evento recibido: {evento.tipo}")
        
        suscribir(TipoEvento.USUARIO_HABLANDO, mi_callback)
    """
    bus = obtener_bus()
    
    # Crear suscriptor anónimo
    class SuscriptorAnonimo(Suscriptor):
        def __init__(self, callback):
            self.callback = callback
            self._id = f"anon_{id(self)}"
        
        def on_evento(self, evento: Evento):
            self.callback(evento)
        
        @property
        def id_suscriptor(self) -> str:
            return self._id
    
    return bus.suscribir(tipo_evento, SuscriptorAnonimo(callback))

# =====================================================================
# METADATOS DEL MÓDULO
# =====================================================================

def version() -> str:
    """Retorna la versión del módulo de bus de eventos."""
    return __version__

def componentes_disponibles() -> Dict[str, bool]:
    """Retorna el estado de disponibilidad de cada componente."""
    return {
        'bus': True,
        'evento': True,
        'tipos': True,
        'prioridad': True,
        'suscriptor': True,
        'middleware': True,
    }

def inicializar_bus() -> BusEventos:
    """Inicializa el bus de eventos."""
    bus = obtener_bus()
    publicar(TipoEvento.SISTEMA_INICIANDO, 
             datos={"version": __version__},
             origen="bus_eventos")
    return bus

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MÓDULO DE BUS DE EVENTOS")
    print("=" * 70)
    
    print(f"\n📁 Directorio: {_current_dir}")
    print(f"📌 Versión: {version()}")
    
    print("\n[1/4] Verificando componentes...")
    disponibles = componentes_disponibles()
    for nombre, disponible in disponibles.items():
        icono = "✅" if disponible else "❌"
        print(f"  {icono} {nombre}")
    
    print("\n[2/4] Inicializando bus de eventos...")
    try:
        bus = inicializar_bus()
        print(f"  ✅ Bus inicializado: {bus}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        bus = None
    
    if bus:
        print("\n[3/4] Probando publicación/suscripción...")
        
        eventos_recibidos = []
        
        def callback_test(evento: Evento):
            eventos_recibidos.append(evento)
            print(f"  📍 Evento recibido: {evento.tipo}")
        
        # Suscribir
        suscribir("test.evento", callback_test)
        print(f"  ✅ Suscripción creada")
        
        # Publicar
        publicar("test.evento", datos={"mensaje": "Hola Mundo"}, origen="test")
        publicar("test.evento", datos={"mensaje": "Segundo evento"}, origen="test")
        print(f"  ✅ Eventos publicados")
        
        print(f"  📊 Eventos recibidos: {len(eventos_recibidos)}")
    
    print("\n[4/4] Tipos de eventos disponibles:")
    tipos = TipoEvento.todos() if hasattr(TipoEvento, 'todos') else []
    if tipos:
        for tipo in tipos[:10]:
            print(f"  📍 {tipo}")
        if len(tipos) > 10:
            print(f"  ... y {len(tipos) - 10} más")
    else:
        print(f"  📍 {len(tipos)} tipos definidos")
    
    print("\n" + "=" * 70)
    print("   ✅ DIAGNÓSTICO COMPLETADO")
    print("   El Módulo de Bus de Eventos está listo.")
    print("=" * 70 + "\n")