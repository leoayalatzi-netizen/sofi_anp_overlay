# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Prioridades (El Corazón del Orden Cósmico)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de prioridades que
# trasciende los simples números. Incluye políticas adaptativas,
# boosting dinámico, degradación temporal, herencia de prioridades
# y un algoritmo de envejecimiento anti-inanición.
# =====================================================================

import sys
import os
import time
import threading
import math
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict
from functools import total_ordering, lru_cache, wraps
import heapq

# =====================================================================
# ENUMERACIÓN BASE DE PRIORIDADES
# =====================================================================

class PrioridadBase(IntEnum):
    """
    Enumeración base de prioridades del sistema ANP.
    Menor valor = Mayor prioridad (estilo UNIX).
    """
    COSMICA = -10      # Prioridad suprema (solo sistema)
    CRITICA = 0        # Crítico - fallo inminente
    ALTA = 1           # Alta - operación esencial
    MEDIA_ALTA = 2     # Media-Alta - importante
    MEDIA = 3          # Media - normal
    MEDIA_BAJA = 4     # Media-Baja - postergable
    BAJA = 5           # Baja - background
    MINIMA = 6         # Mínima - solo en idle
    DIFERIDA = 7       # Diferida - puede esperar
    INERTE = 10        # Inerte - casi nunca se ejecuta

class PrioridadEvento(IntEnum):
    """
    Prioridades específicas para eventos del bus.
    Hereda los valores de PrioridadBase para mantener consistencia.
    """
    CRITICA = PrioridadBase.CRITICA
    ALTA = PrioridadBase.ALTA
    MEDIA = PrioridadBase.MEDIA
    BAJA = PrioridadBase.BAJA
    DIFERIDA = PrioridadBase.DIFERIDA

class PrioridadTarea(IntEnum):
    """
    Prioridades específicas para tareas del planificador.
    """
    COSMICA = PrioridadBase.COSMICA
    CRITICA = PrioridadBase.CRITICA
    ALTA = PrioridadBase.ALTA
    MEDIA = PrioridadBase.MEDIA
    BAJA = PrioridadBase.BAJA
    DIFERIDA = PrioridadBase.DIFERIDA
    
    # =====================================================================
# POLÍTICAS DE PRIORIDAD
# =====================================================================

class PoliticaPrioridad(Enum):
    """Políticas de asignación y modificación de prioridades."""
    FIJA = "fija"                       # La prioridad nunca cambia
    ADAPTATIVA = "adaptativa"           # Cambia según contexto
    DECREMENTAL = "decremental"         # Disminuye con el tiempo
    INCREMENTAL = "incremental"         # Aumenta con el tiempo (anti-inanición)
    HEREDADA = "heredada"               # Hereda del padre
    CONTEXTUAL = "contextual"           # Depende del contexto
    PREDICTIVA = "predictiva"           # Basada en predicción
    CUANTICA = "cuantica"              # Combinación de múltiples factores
    
    # =====================================================================
# METADATOS DE PRIORIDAD
# =====================================================================

@dataclass(frozen=True)
class MetadatosPrioridad:
    """Metadatos que describen un nivel de prioridad."""
    nivel: int
    nombre: str
    descripcion: str
    color: str
    emoji: str
    timeout_default: float      # Timeout por defecto en segundos
    reintentos_max: int          # Número máximo de reintentos
    requiere_confirmacion: bool  # Si requiere confirmación para degradar
    es_preemptivo: bool          # Si puede interrumpir tareas de menor prioridad
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'nivel': self.nivel,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'color': self.color,
            'emoji': self.emoji,
            'timeout_default': self.timeout_default,
            'reintentos_max': self.reintentos_max,
            'requiere_confirmacion': self.requiere_confirmacion,
            'es_preemptivo': self.es_preemptivo,
        }
        
        # =====================================================================
# REGISTRO DE METADATOS DE PRIORIDAD
# =====================================================================

class RegistroPrioridades:
    """Registro central de metadatos para cada nivel de prioridad."""
    
    _metadatos: Dict[int, MetadatosPrioridad] = {
        PrioridadBase.COSMICA: MetadatosPrioridad(
            nivel=PrioridadBase.COSMICA,
            nombre="CÓSMICA",
            descripcion="Prioridad suprema del sistema. Solo para operaciones vitales.",
            color="#FF0000",
            emoji="🌌",
            timeout_default=0.5,
            reintentos_max=0,
            requiere_confirmacion=True,
            es_preemptivo=True,
        ),
        PrioridadBase.CRITICA: MetadatosPrioridad(
            nivel=PrioridadBase.CRITICA,
            nombre="CRÍTICA",
            descripcion="Operación crítica. Fallo inminente si no se ejecuta.",
            color="#FF4500",
            emoji="🚨",
            timeout_default=1.0,
            reintentos_max=1,
            requiere_confirmacion=True,
            es_preemptivo=True,
        ),
        PrioridadBase.ALTA: MetadatosPrioridad(
            nivel=PrioridadBase.ALTA,
            nombre="ALTA",
            descripcion="Operación esencial. Debe ejecutarse lo antes posible.",
            color="#FF8C00",
            emoji="🔥",
            timeout_default=3.0,
            reintentos_max=2,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.MEDIA_ALTA: MetadatosPrioridad(
            nivel=PrioridadBase.MEDIA_ALTA,
            nombre="MEDIA-ALTA",
            descripcion="Operación importante. Prioridad sobre tareas normales.",
            color="#FFD700",
            emoji="⭐",
            timeout_default=5.0,
            reintentos_max=3,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.MEDIA: MetadatosPrioridad(
            nivel=PrioridadBase.MEDIA,
            nombre="MEDIA",
            descripcion="Operación normal. Prioridad estándar.",
            color="#00BFFF",
            emoji="📋",
            timeout_default=10.0,
            reintentos_max=3,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.MEDIA_BAJA: MetadatosPrioridad(
            nivel=PrioridadBase.MEDIA_BAJA,
            nombre="MEDIA-BAJA",
            descripcion="Operación postergable. Puede esperar si hay carga.",
            color="#32CD32",
            emoji="🍃",
            timeout_default=15.0,
            reintentos_max=2,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.BAJA: MetadatosPrioridad(
            nivel=PrioridadBase.BAJA,
            nombre="BAJA",
            descripcion="Operación de background. Baja prioridad.",
            color="#808080",
            emoji="💤",
            timeout_default=30.0,
            reintentos_max=1,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.MINIMA: MetadatosPrioridad(
            nivel=PrioridadBase.MINIMA,
            nombre="MÍNIMA",
            descripcion="Operación solo en idle. Casi sin prioridad.",
            color="#A9A9A9",
            emoji="🌙",
            timeout_default=60.0,
            reintentos_max=0,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.DIFERIDA: MetadatosPrioridad(
            nivel=PrioridadBase.DIFERIDA,
            nombre="DIFERIDA",
            descripcion="Operación que puede esperar indefinidamente.",
            color="#D3D3D3",
            emoji="⏳",
            timeout_default=120.0,
            reintentos_max=0,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
        PrioridadBase.INERTE: MetadatosPrioridad(
            nivel=PrioridadBase.INERTE,
            nombre="INERTE",
            descripcion="Operación casi muerta. Solo se ejecuta si no hay nada más.",
            color="#F5F5F5",
            emoji="💀",
            timeout_default=300.0,
            reintentos_max=0,
            requiere_confirmacion=False,
            es_preemptivo=False,
        ),
    }
    
    @classmethod
    def obtener(cls, nivel: Union[int, PrioridadBase]) -> MetadatosPrioridad:
        """Obtiene los metadatos para un nivel de prioridad."""
        if isinstance(nivel, PrioridadBase):
            nivel = nivel.value
        return cls._metadatos.get(nivel, cls._metadatos[PrioridadBase.MEDIA])
    
    @classmethod
    def todos(cls) -> Dict[int, MetadatosPrioridad]:
        """Obtiene todos los metadatos."""
        return cls._metadatos.copy()
    
    @classmethod
    def niveles(cls) -> List[int]:
        """Obtiene todos los niveles disponibles ordenados por prioridad."""
        return sorted(cls._metadatos.keys())
    
    @classmethod
    def nombres(cls) -> List[str]:
        """Obtiene los nombres de todos los niveles."""
        return [m.nombre for m in cls._metadatos.values()]
    
    @classmethod
    def desde_nombre(cls, nombre: str) -> Optional[int]:
        """Obtiene el nivel desde su nombre."""
        for nivel, meta in cls._metadatos.items():
            if meta.nombre.upper() == nombre.upper():
                return nivel
        return None

# =====================================================================
# GESTOR DE PRIORIDADES (Núcleo del sistema)
# =====================================================================

class GestorPrioridades:
    """
    Gestor central de prioridades con políticas adaptativas.
    Implementa patrón Singleton thread-safe.
    """
    
    _instancia: Optional['GestorPrioridades'] = None
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
            
            # Políticas por tipo de entidad
            self._politicas: Dict[str, PoliticaPrioridad] = {}
            
            # Factores de ajuste dinámico
            self._factores: Dict[str, float] = {}
            
            # Historial de cambios
            self._historial: deque = deque(maxlen=500)
            
            # Colas por nivel de prioridad
            self._colas: Dict[int, deque] = defaultdict(deque)
            
            # Contadores de inanición
            self._inanicion: Dict[str, int] = defaultdict(int)
            
            # Factores de boosting
            self._boost_por_tiempo: float = 0.1      # Boost por segundo de espera
            self._boost_por_intentos: float = 0.5    # Boost por reintento
            self._boost_max: float = 3.0             # Boost máximo (3 niveles)
            
            self._inicializado = True
    
    # ===== MÉTODOS DE CONFIGURACIÓN =====
    
    def configurar_politica(self, entidad: str, politica: PoliticaPrioridad):
        """Configura la política de prioridad para un tipo de entidad."""
        self._politicas[entidad] = politica
    
    def configurar_factor(self, nombre: str, valor: float):
        """Configura un factor de ajuste dinámico."""
        self._factores[nombre] = valor
    
    # ===== MÉTODOS DE CONSULTA =====
    
    def obtener_metadatos(self, prioridad: Union[int, PrioridadBase]) -> MetadatosPrioridad:
        """Obtiene los metadatos de una prioridad."""
        return RegistroPrioridades.obtener(prioridad)
    
    def es_mayor(self, p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> bool:
        """Verifica si p1 tiene mayor prioridad que p2 (menor valor numérico)."""
        v1 = p1.value if isinstance(p1, PrioridadBase) else p1
        v2 = p2.value if isinstance(p2, PrioridadBase) else p2
        return v1 < v2
    
    def es_mayor_o_igual(self, p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> bool:
        """Verifica si p1 tiene mayor o igual prioridad que p2."""
        v1 = p1.value if isinstance(p1, PrioridadBase) else p1
        v2 = p2.value if isinstance(p2, PrioridadBase) else p2
        return v1 <= v2
    
    def comparar(self, p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> int:
        """
        Compara dos prioridades.
        Retorna: -1 si p1 > p2, 0 si iguales, 1 si p1 < p2
        """
        v1 = p1.value if isinstance(p1, PrioridadBase) else p1
        v2 = p2.value if isinstance(p2, PrioridadBase) else p2
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        return 0
    
    # ===== MÉTODOS DE TRANSFORMACIÓN =====
    
    def degradar(self, prioridad: Union[int, PrioridadBase], 
                 pasos: int = 1) -> PrioridadBase:
        """
        Degrada una prioridad (aumenta el valor numérico).
        """
        v = prioridad.value if isinstance(prioridad, PrioridadBase) else prioridad
        niveles = RegistroPrioridades.niveles()
        idx = niveles.index(v)
        nuevo_idx = min(len(niveles) - 1, idx + pasos)
        return PrioridadBase(niveles[nuevo_idx])
    
    def elevar(self, prioridad: Union[int, PrioridadBase], 
               pasos: int = 1) -> PrioridadBase:
        """
        Eleva una prioridad (disminuye el valor numérico).
        """
        v = prioridad.value if isinstance(prioridad, PrioridadBase) else prioridad
        niveles = RegistroPrioridades.niveles()
        idx = niveles.index(v)
        nuevo_idx = max(0, idx - pasos)
        return PrioridadBase(niveles[nuevo_idx])
    
    def clamp(self, prioridad: Union[int, PrioridadBase]) -> PrioridadBase:
        """
        Asegura que la prioridad esté dentro de los límites válidos.
        """
        v = prioridad.value if isinstance(prioridad, PrioridadBase) else prioridad
        niveles = RegistroPrioridades.niveles()
        if v < niveles[0]:
            return PrioridadBase(niveles[0])
        if v > niveles[-1]:
            return PrioridadBase(niveles[-1])
        return PrioridadBase(v)
    
    # ===== MÉTODOS DE BOOSTING (Anti-inanición) =====
    
    def calcular_boost_tiempo(self, tiempo_espera: float) -> int:
        """
        Calcula cuántos niveles subir basado en el tiempo de espera.
        """
        boost = tiempo_espera * self._boost_por_tiempo
        return min(int(boost), int(self._boost_max))
    
    def calcular_boost_intentos(self, intentos: int) -> int:
        """
        Calcula cuántos niveles subir basado en reintentos.
        """
        boost = intentos * self._boost_por_intentos
        return min(int(boost), int(self._boost_max))
    
    def aplicar_anti_inanicion(self, entidad_id: str, 
                               prioridad_actual: PrioridadBase,
                               tiempo_espera: float = 0,
                               intentos: int = 0) -> PrioridadBase:
        """
        Aplica boosting anti-inanición a una entidad.
        """
        # Incrementar contador de inanición
        self._inanicion[entidad_id] += 1
        
        # Calcular boost total
        boost_tiempo = self.calcular_boost_tiempo(tiempo_espera)
        boost_intentos = self.calcular_boost_intentos(intentos)
        boost_inanicion = min(self._inanicion[entidad_id] // 10, 2)
        
        boost_total = boost_tiempo + boost_intentos + boost_inanicion
        
        if boost_total > 0:
            nueva = self.elevar(prioridad_actual, boost_total)
            self._registrar_cambio(entidad_id, prioridad_actual, nueva, 
                                  f"anti_inanicion (boost={boost_total})")
            return nueva
        
        return prioridad_actual
    
    def reset_inanicion(self, entidad_id: str):
        """Resetea el contador de inanición de una entidad."""
        if entidad_id in self._inanicion:
            del self._inanicion[entidad_id]
    
    # ===== MÉTODOS DE COLA DE PRIORIDAD =====
    
    def encolar(self, entidad: Any, prioridad: PrioridadBase, entidad_id: str = None):
        """Encola una entidad según su prioridad."""
        self._colas[prioridad.value].append((time.time(), entidad_id, entidad))
    
    def desencolar(self) -> Optional[Tuple[Any, PrioridadBase]]:
        """
        Desencola la entidad de mayor prioridad disponible.
        Aplica envejecimiento a las entidades en espera.
        """
        niveles = RegistroPrioridades.niveles()
        
        for nivel in niveles:
            if self._colas[nivel]:
                timestamp, entidad_id, entidad = self._colas[nivel].popleft()
                
                # Aplicar envejecimiento a las demás
                self._envejecer_cola(nivel)
                
                if entidad_id:
                    self.reset_inanicion(entidad_id)
                
                return entidad, PrioridadBase(nivel)
        
        return None
    
    def _envejecer_cola(self, nivel: int):
        """
        Aplica envejecimiento a las entidades en la cola.
        Las entidades más antiguas pueden ser promovidas.
        """
        ahora = time.time()
        nuevas_entidades = []
        
        while self._colas[nivel]:
            timestamp, entidad_id, entidad = self._colas[nivel].popleft()
            tiempo_espera = ahora - timestamp
            
            # Si ha esperado mucho, promover a mayor prioridad
            if tiempo_espera > 30.0:  # 30 segundos
                nueva_prioridad = self.elevar(PrioridadBase(nivel), 1)
                self._colas[nueva_prioridad.value].append((timestamp, entidad_id, entidad))
                self._registrar_cambio(entidad_id or "anon", PrioridadBase(nivel),
                                      nueva_prioridad, "envejecimiento")
            else:
                nuevas_entidades.append((timestamp, entidad_id, entidad))
        
        self._colas[nivel] = deque(nuevas_entidades)
    
    # ===== MÉTODOS DE REGISTRO =====
    
    def _registrar_cambio(self, entidad_id: str, anterior: PrioridadBase,
                          nueva: PrioridadBase, motivo: str):
        """Registra un cambio de prioridad en el historial."""
        self._historial.append({
            'timestamp': time.time(),
            'entidad_id': entidad_id,
            'anterior': anterior.value,
            'anterior_nombre': anterior.name,
            'nueva': nueva.value,
            'nueva_nombre': nueva.name,
            'motivo': motivo,
        })
    
    # ===== MÉTODOS DE ESTADÍSTICAS =====
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de prioridades."""
        return {
            'politicas': {k: v.value for k, v in self._politicas.items()},
            'factores': self._factores,
            'colas': {PrioridadBase(k).name: len(v) for k, v in self._colas.items()},
            'total_encolados': sum(len(v) for v in self._colas.values()),
            'cambios_historial': len(self._historial),
            'entidades_inanicion': len(self._inanicion),
        }
    
    def __len__(self) -> int:
        return sum(len(v) for v in self._colas.values())

# =====================================================================
# CLASE PRINCIPAL DE PRIORIDAD
# =====================================================================

class Prioridad:
    """
    Clase principal para gestión de prioridades.
    Proporciona acceso unificado a todas las funcionalidades.
    """
    
    _gestor: ClassVar[GestorPrioridades] = None
    
    def __init__(self):
        raise TypeError("Prioridad es una clase estática, no debe instanciarse")
    
    @classmethod
    def _get_gestor(cls) -> GestorPrioridades:
        if cls._gestor is None:
            cls._gestor = GestorPrioridades()
        return cls._gestor
    
    # ===== VALORES CONSTANTES =====
    
    @classmethod
    def COSMICA(cls) -> int: return PrioridadBase.COSMICA.value
    @classmethod
    def CRITICA(cls) -> int: return PrioridadBase.CRITICA.value
    @classmethod
    def ALTA(cls) -> int: return PrioridadBase.ALTA.value
    @classmethod
    def MEDIA_ALTA(cls) -> int: return PrioridadBase.MEDIA_ALTA.value
    @classmethod
    def MEDIA(cls) -> int: return PrioridadBase.MEDIA.value
    @classmethod
    def MEDIA_BAJA(cls) -> int: return PrioridadBase.MEDIA_BAJA.value
    @classmethod
    def BAJA(cls) -> int: return PrioridadBase.BAJA.value
    @classmethod
    def MINIMA(cls) -> int: return PrioridadBase.MINIMA.value
    @classmethod
    def DIFERIDA(cls) -> int: return PrioridadBase.DIFERIDA.value
    @classmethod
    def INERTE(cls) -> int: return PrioridadBase.INERTE.value
    
    # ===== MÉTODOS DE CONSULTA =====
    
    @classmethod
    def metadatos(cls, nivel: Union[int, PrioridadBase]) -> MetadatosPrioridad:
        return cls._get_gestor().obtener_metadatos(nivel)
    
    @classmethod
    def nombre(cls, nivel: Union[int, PrioridadBase]) -> str:
        return cls.metadatos(nivel).nombre
    
    @classmethod
    def emoji(cls, nivel: Union[int, PrioridadBase]) -> str:
        return cls.metadatos(nivel).emoji
    
    @classmethod
    def color(cls, nivel: Union[int, PrioridadBase]) -> str:
        return cls.metadatos(nivel).color
    
    @classmethod
    def timeout(cls, nivel: Union[int, PrioridadBase]) -> float:
        return cls.metadatos(nivel).timeout_default
    
    @classmethod
    def reintentos(cls, nivel: Union[int, PrioridadBase]) -> int:
        return cls.metadatos(nivel).reintentos_max
    
    @classmethod
    def es_preemptivo(cls, nivel: Union[int, PrioridadBase]) -> bool:
        return cls.metadatos(nivel).es_preemptivo
    
    # ===== MÉTODOS DE COMPARACIÓN =====
    
    @classmethod
    def es_mayor(cls, p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> bool:
        return cls._get_gestor().es_mayor(p1, p2)
    
    @classmethod
    def comparar(cls, p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> int:
        return cls._get_gestor().comparar(p1, p2)
    
    # ===== MÉTODOS DE TRANSFORMACIÓN =====
    
    @classmethod
    def degradar(cls, prioridad: Union[int, PrioridadBase], pasos: int = 1) -> PrioridadBase:
        return cls._get_gestor().degradar(prioridad, pasos)
    
    @classmethod
    def elevar(cls, prioridad: Union[int, PrioridadBase], pasos: int = 1) -> PrioridadBase:
        return cls._get_gestor().elevar(prioridad, pasos)
    
    # ===== MÉTODOS DE ANTI-INANICIÓN =====
    
    @classmethod
    def aplicar_boost(cls, entidad_id: str, prioridad_actual: PrioridadBase,
                      tiempo_espera: float = 0, intentos: int = 0) -> PrioridadBase:
        return cls._get_gestor().aplicar_anti_inanicion(
            entidad_id, prioridad_actual, tiempo_espera, intentos
        )
    
    # ===== MÉTODOS DE CONFIGURACIÓN =====
    
    @classmethod
    def configurar_politica(cls, entidad: str, politica: PoliticaPrioridad):
        cls._get_gestor().configurar_politica(entidad, politica)
    
    # ===== MÉTODOS DE INFORMACIÓN =====
    
    @classmethod
    def niveles(cls) -> List[int]:
        return RegistroPrioridades.niveles()
    
    @classmethod
    def nombres(cls) -> List[str]:
        return RegistroPrioridades.nombres()
    
    @classmethod
    def desde_nombre(cls, nombre: str) -> Optional[int]:
        return RegistroPrioridades.desde_nombre(nombre)
    
    @classmethod
    def estadisticas(cls) -> Dict[str, Any]:
        return cls._get_gestor().obtener_estadisticas()
    
    @classmethod
    def resumen(cls) -> str:
        stats = cls.estadisticas()
        return f"Prioridad: {stats['total_encolados']} encolados, {len(stats['colas'])} niveles"
        
        # =====================================================================
# DECORADORES DE PRIORIDAD
# =====================================================================

def con_prioridad(prioridad: Union[int, PrioridadBase]):
    """
    Decorador para asignar una prioridad por defecto a una función.
    
    Uso:
        @con_prioridad(Prioridad.ALTA())
        def funcion_critica():
            pass
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._prioridad_default = prioridad
        return wrapper
    return decorador

def prioridad_adaptativa(politica: PoliticaPrioridad = PoliticaPrioridad.INCREMENTAL):
    """
    Decorador para funciones con prioridad adaptativa.
    
    Uso:
        @prioridad_adaptativa(PoliticaPrioridad.INCREMENTAL)
        def tarea_larga():
            pass
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._politica_prioridad = politica
        return wrapper
    return decorador

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def obtener_prioridad(valor: Union[int, str, PrioridadBase]) -> PrioridadBase:
    """
    Convierte cualquier representación a PrioridadBase.
    """
    if isinstance(valor, PrioridadBase):
        return valor
    if isinstance(valor, int):
        return Prioridad(valor)
    if isinstance(valor, str):
        nivel = Prioridad.desde_nombre(valor)
        if nivel is not None:
            return PrioridadBase(nivel)
    return PrioridadBase(Prioridad.MEDIA())

def prioridad_mas_alta(p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> PrioridadBase:
    """Retorna la prioridad más alta de dos."""
    return p1 if Prioridad.es_mayor(p1, p2) else p2

def prioridad_mas_baja(p1: Union[int, PrioridadBase], p2: Union[int, PrioridadBase]) -> PrioridadBase:
    """Retorna la prioridad más baja de dos."""
    return p2 if Prioridad.es_mayor(p1, p2) else p1

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE PRIORIDADES")
    print("=" * 70)
    
    try:
        # 1. Niveles disponibles
        print("\n[1/7] Niveles de prioridad:")
        for nivel in Prioridad.niveles():
            meta = Prioridad.metadatos(nivel)
            print(f"  {meta.emoji} {meta.nombre:12} (nivel {nivel:3}): {meta.descripcion[:40]}...")
        
        # 2. Comparaciones
        print("\n[2/7] Probando comparaciones...")
        print(f"  CRITICA > ALTA: {Prioridad.es_mayor(Prioridad.CRITICA(), Prioridad.ALTA())}")
        print(f"  MEDIA > BAJA: {Prioridad.es_mayor(Prioridad.MEDIA(), Prioridad.BAJA())}")
        print(f"  Comparar(ALTA, MEDIA): {Prioridad.comparar(Prioridad.ALTA(), Prioridad.MEDIA())}")
        
        # 3. Transformaciones
        print("\n[3/7] Probando transformaciones...")
        original = PrioridadBase.MEDIA
        degradada = Prioridad.degradar(original, 2)
        elevada = Prioridad.elevar(original, 1)
        print(f"  Original: {original.name}")
        print(f"  Degradada 2 pasos: {degradada.name}")
        print(f"  Elevada 1 paso: {elevada.name}")
        
        # 4. Metadatos
        print("\n[4/7] Metadatos de prioridad ALTA:")
        meta = Prioridad.metadatos(Prioridad.ALTA())
        print(f"  Timeout default: {meta.timeout_default}s")
        print(f"  Reintentos max: {meta.reintentos_max}")
        print(f"  Es preemptivo: {meta.es_preemptivo}")
        print(f"  Color: {meta.color}")
        
        # 5. Conversión desde nombre
        print("\n[5/7] Conversión desde nombre...")
        nombres = ["CRÍTICA", "ALTA", "MEDIA", "BAJA", "INEXISTENTE"]
        for nombre in nombres:
            nivel = Prioridad.desde_nombre(nombre)
            if nivel:
                print(f"  ✅ '{nombre}' -> nivel {nivel}")
            else:
                print(f"  ❌ '{nombre}' no encontrado")
        
        # 6. Anti-inanición
        print("\n[6/7] Probando anti-inanición...")
        gestor = Prioridad._get_gestor()
        entidad_id = "test_entidad"
        prioridad_inicial = PrioridadBase.BAJA
        
        for i in range(5):
            nueva = gestor.aplicar_anti_inanicion(entidad_id, prioridad_inicial, tiempo_espera=i*10)
            print(f"  Espera {i*10}s, intentos {i}: {prioridad_inicial.name} -> {nueva.name}")
        
        # 7. Colas de prioridad
        print("\n[7/7] Probando colas de prioridad...")
        gestor.encolar("Tarea crítica", PrioridadBase.CRITICA, "t1")
        gestor.encolar("Tarea media", PrioridadBase.MEDIA, "t2")
        gestor.encolar("Tarea alta", PrioridadBase.ALTA, "t3")
        gestor.encolar("Tarea baja", PrioridadBase.BAJA, "t4")
        
        print("  Orden de desencolado:")
        for _ in range(4):
            resultado = gestor.desencolar()
            if resultado:
                entidad, prioridad = resultado
                print(f"    - {entidad} ({prioridad.name})")
        
        # Estadísticas
        print("\n" + "=" * 70)
        stats = Prioridad.estadisticas()
        print(f"   📊 ESTADÍSTICAS FINALES")
        print(f"   Total encolados: {stats['total_encolados']}")
        print(f"   Cambios registrados: {stats['cambios_historial']}")
        print(f"   Entidades con inanición: {stats['entidades_inanicion']}")
        print("=" * 70)
        
        print("\n📈 Distribución por colas:")
        for nombre, cantidad in stats['colas'].items():
            if cantidad > 0:
                barra = "█" * cantidad
                print(f"   {nombre:12} {barra} {cantidad}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Prioridades está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")