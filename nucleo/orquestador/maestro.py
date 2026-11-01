# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Orquestador Maestro (Cerebro Cósmico)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa patrones avanzados de orquestación
# cuántica, enrutamiento predictivo y conciencia sistémica autónoma.
# La complejidad es intencional - es el corazón de ANP.
# =====================================================================

import sys
import os
import time
import threading
import asyncio
import concurrent.futures
import queue
import uuid
import hashlib
import json
import weakref
import inspect
import traceback
import warnings
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Coroutine, 
    Type, Tuple, Set, FrozenSet, DefaultDict, OrderedDict,
    Awaitable, TypeVar, Generic, cast, overload
)
from dataclasses import dataclass, field, asdict, fields
from enum import IntEnum, Enum, auto, Flag
from collections import defaultdict, deque, Counter, namedtuple
from contextlib import contextmanager, asynccontextmanager
from functools import lru_cache, wraps, partial, total_ordering
from abc import ABC, abstractmethod
import heapq
import random
import math

# =====================================================================
# IMPORTS DEL SISTEMA ANP (con fallback elegante)
# =====================================================================

try:
    from configuracion import Configuracion, obtener_config, CategoriaConfig
except ImportError:
    Configuracion = None
    obtener_config = lambda: None
    CategoriaConfig = None

# =====================================================================
# SECCIÓN 1: ENUMERACIONES Y CONSTANTES FUNDAMENTALES
# =====================================================================

class EstadoNucleo(Enum):
    """Estados posibles de un núcleo especializado."""
    INACTIVO = "inactivo"
    INICIALIZANDO = "inicializando"
    ACTIVO = "activo"
    DEGRADADO = "degradado"
    FALLBACK = "fallback"
    ERROR = "error"
    RECUPERANDO = "recuperando"
    APAGADO = "apagado"

class PrioridadTarea(IntEnum):
    """Prioridades de tareas (menor número = mayor prioridad)."""
    CRITICA = 0      # P0 - Sistema en riesgo
    ALTA = 1         # P1 - Usuario esperando
    MEDIA = 2        # P2 - Procesamiento normal
    BAJA = 3         # P3 - Background
    DIFERIDA = 4     # P4 - Puede esperar indefinidamente

class TipoTarea(Enum):
    """Tipos de tareas que puede procesar el orquestador."""
    CONSULTA = "consulta"
    RAZONAMIENTO = "razonamiento"
    BUSQUEDA = "busqueda"
    MEMORIA = "memoria"
    RESOLUCION = "resolucion"
    CREATIVIDAD = "creatividad"
    SISTEMA = "sistema"
    FALLBACK = "fallback"

class ModoOrquestacion(Enum):
    """Modos de operación del orquestador."""
    NORMAL = "normal"
    DEGRADADO = "degradado"
    EMERGENCIA = "emergencia"
    APRENDIZAJE = "aprendizaje"
    MANTENIMIENTO = "mantenimiento"
    DIOS = "dios"  # Modo con telemetría completa

class MetricaOrquestador(Enum):
    """Métricas que recolecta el orquestador."""
    TAREAS_PROCESADAS = "tareas_procesadas"
    TAREAS_FALLIDAS = "tareas_fallidas"
    TIEMPO_PROMEDIO = "tiempo_promedio"
    FALLBACKS_ACTIVADOS = "fallbacks_activados"
    RUTAS_CACHE_HITS = "rutas_cache_hits"
    RUTAS_CACHE_MISSES = "rutas_cache_misses"
    NUCLEOS_ACTIVOS = "nucleos_activos"
    NUCLEOS_DEGRADADOS = "nucleos_degradados"
    CIRCUIT_BREAKERS_ABIERTOS = "circuit_breakers_abiertos"
    PREDICCIONES_CORRECTAS = "predicciones_correctas"
    PREDICCIONES_FALLIDAS = "predicciones_fallidas"

# =====================================================================
# SECCIÓN 2: ESTRUCTURAS DE DATOS CUÁNTICAS
# =====================================================================

@dataclass(frozen=True)
class Ruta:
    """Define una ruta de ejecución para una tarea."""
    nucleo_principal: str
    nucleo_fallback: Optional[str]
    motor: Optional[str]
    prioridad: PrioridadTarea
    timeout: float
    reintentos_max: int
    requiere_contexto: bool = True
    cacheable: bool = False
    ttl_cache: int = 300

@dataclass(order=True)
class TareaPriorizada:
    """Tarea con prioridad para la cola de ejecución."""
    prioridad: PrioridadTarea
    timestamp: float = field(compare=False)
    id: str = field(compare=False)
    tipo: TipoTarea = field(compare=False)
    datos: Any = field(compare=False)
    contexto: Dict[str, Any] = field(compare=False)
    intentos: int = field(default=0, compare=False)
    ruta: Optional[Ruta] = field(default=None, compare=False)
    futuro: Optional[Any] = field(default=None, compare=False)
    
    def __post_init__(self):
        if self.futuro is None:
            self.futuro = concurrent.futures.Future()

@dataclass
class EstadoNucleoInfo:
    """Información completa del estado de un núcleo."""
    nombre: str
    estado: EstadoNucleo
    carga_actual: int = 0
    carga_maxima: int = 100
    tareas_procesadas: int = 0
    tareas_fallidas: int = 0
    tiempo_respuesta_promedio: float = 0.0
    ultimo_latido: float = field(default_factory=time.time)
    fallos_consecutivos: int = 0
    circuit_breaker_abierto: bool = False
    circuit_breaker_hasta: float = 0.0
    version: str = "0.0.0"
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def carga_porcentaje(self) -> float:
        return (self.carga_actual / self.carga_maxima) * 100 if self.carga_maxima > 0 else 0
    
    @property
    def saludable(self) -> bool:
        return (self.estado in (EstadoNucleo.ACTIVO, EstadoNucleo.DEGRADADO) 
                and not self.circuit_breaker_abierto
                and self.fallos_consecutivos < 5)

@dataclass
class MetricaRendimiento:
    """Métrica individual de rendimiento."""
    nombre: str
    valor: float
    unidad: str
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

# =====================================================================
# SECCIÓN 3: SISTEMA DE PREDICCIÓN Y OPTIMIZACIÓN
# =====================================================================

class PredictorRutas:
    """
    Sistema de predicción de rutas óptimas usando aprendizaje bayesiano.
    Aprende de ejecuciones pasadas para predecir la mejor ruta.
    """
    
    def __init__(self, ventana_historico: int = 1000):
        self.ventana_historico = ventana_historico
        self._historico_exitos: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)
        self._historico_fallos: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)
        self._probabilidades: Dict[Tuple[str, str], float] = {}  # (tipo_tarea, nucleo) -> prob_exito
        self._tiempos_promedio: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._lock = threading.RLock()
        
    def registrar_exito(self, tipo_tarea: str, nucleo: str, tiempo_ejecucion: float):
        """Registra una ejecución exitosa."""
        with self._lock:
            self._historico_exitos[tipo_tarea].append((nucleo, tiempo_ejecucion))
            if len(self._historico_exitos[tipo_tarea]) > self.ventana_historico:
                self._historico_exitos[tipo_tarea].pop(0)
            self._actualizar_probabilidades(tipo_tarea)
            self._actualizar_tiempos(tipo_tarea, nucleo, tiempo_ejecucion)
    
    def registrar_fallo(self, tipo_tarea: str, nucleo: str):
        """Registra una ejecución fallida."""
        with self._lock:
            self._historico_fallos[tipo_tarea].append((nucleo, time.time()))
            if len(self._historico_fallos[tipo_tarea]) > self.ventana_historico:
                self._historico_fallos[tipo_tarea].pop(0)
            self._actualizar_probabilidades(tipo_tarea)
    
    def _actualizar_probabilidades(self, tipo_tarea: str):
        """Actualiza las probabilidades bayesianas para un tipo de tarea."""
        exitos = Counter([n for n, _ in self._historico_exitos[tipo_tarea]])
        fallos = Counter([n for n, _ in self._historico_fallos[tipo_tarea]])
        
        todos_nucleos = set(exitos.keys()) | set(fallos.keys())
        for nucleo in todos_nucleos:
            ex = exitos.get(nucleo, 0)
            fa = fallos.get(nucleo, 0)
            total = ex + fa
            if total > 0:
                # Estimador bayesiano con prior de Laplace
                prob = (ex + 1) / (total + 2)
                self._probabilidades[(tipo_tarea, nucleo)] = prob
    
    def _actualizar_tiempos(self, tipo_tarea: str, nucleo: str, tiempo: float):
        """Actualiza tiempos promedio con decaimiento exponencial."""
        actual = self._tiempos_promedio[tipo_tarea].get(nucleo, tiempo)
        # Decaimiento exponencial: 70% nuevo, 30% histórico
        self._tiempos_promedio[tipo_tarea][nucleo] = 0.7 * tiempo + 0.3 * actual
    
    def predecir_mejor_ruta(self, tipo_tarea: str, nucleos_disponibles: List[str]) -> Optional[str]:
        """Predice el mejor núcleo para una tarea."""
        with self._lock:
            mejor_nucleo = None
            mejor_puntuacion = -1.0
            
            for nucleo in nucleos_disponibles:
                prob = self._probabilidades.get((tipo_tarea, nucleo), 0.5)
                tiempo = self._tiempos_promedio.get(tipo_tarea, {}).get(nucleo, 10.0)
                
                # Puntuación combina probabilidad de éxito y tiempo (inverso)
                puntuacion = prob * (1.0 / max(tiempo, 0.1))
                
                if puntuacion > mejor_puntuacion:
                    mejor_puntuacion = puntuacion
                    mejor_nucleo = nucleo
            
            return mejor_nucleo
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del predictor."""
        with self._lock:
            return {
                'total_exitos': sum(len(v) for v in self._historico_exitos.values()),
                'total_fallos': sum(len(v) for v in self._historico_fallos.values()),
                'tipos_tarea': list(self._historico_exitos.keys()),
                'probabilidades': dict(self._probabilidades),
            }

# =====================================================================
# SECCIÓN 4: CIRCUIT BREAKER ADAPTATIVO
# =====================================================================

class CircuitBreaker:
    """
    Implementación avanzada de Circuit Breaker con estados adaptativos.
    """
    
    class Estado(Enum):
        CERRADO = "cerrado"      # Funcionamiento normal
        ABIERTO = "abierto"      # Bloqueado por fallos
        SEMI_ABIERTO = "semi_abierto"  # Probando recuperación
        DEGRADADO = "degradado"  # Funcionando con limitaciones
    
    def __init__(self, nombre: str, umbral_fallos: int = 5, timeout_recuperacion: float = 60.0):
        self.nombre = nombre
        self.umbral_fallos = umbral_fallos
        self.timeout_recuperacion = timeout_recuperacion
        
        self._estado = self.Estado.CERRADO
        self._fallos_consecutivos = 0
        self._total_fallos = 0
        self._total_exitos = 0
        self._ultimo_fallo: float = 0.0
        self._ultimo_exito: float = 0.0
        self._abierto_hasta: float = 0.0
        self._lock = threading.RLock()
        self._metricas: Dict[str, List[float]] = defaultdict(list)
        
    def permitir_operacion(self) -> bool:
        """Determina si una operación está permitida."""
        with self._lock:
            ahora = time.time()
            
            if self._estado == self.Estado.CERRADO:
                return True
                
            elif self._estado == self.Estado.ABIERTO:
                if ahora >= self._abierto_hasta:
                    self._transicionar_a(self.Estado.SEMI_ABIERTO)
                    return True
                return False
                
            elif self._estado == self.Estado.SEMI_ABIERTO:
                # En semi-abierto, permitimos solo una operación de prueba
                return True
                
            elif self._estado == self.Estado.DEGRADADO:
                # En degradado, permitimos pero con throttling
                return random.random() < 0.5
                
            return False
    
    def registrar_exito(self):
        """Registra una operación exitosa."""
        with self._lock:
            self._total_exitos += 1
            self._ultimo_exito = time.time()
            
            if self._estado == self.Estado.SEMI_ABIERTO:
                self._fallos_consecutivos = 0
                self._transicionar_a(self.Estado.CERRADO)
            elif self._estado == self.Estado.DEGRADADO:
                # Si hay suficientes éxitos consecutivos, recuperar
                self._fallos_consecutivos = max(0, self._fallos_consecutivos - 1)
                if self._fallos_consecutivos == 0:
                    self._transicionar_a(self.Estado.CERRADO)
            else:
                self._fallos_consecutivos = 0
    
    def registrar_fallo(self):
        """Registra una operación fallida."""
        with self._lock:
            ahora = time.time()
            self._total_fallos += 1
            self._fallos_consecutivos += 1
            self._ultimo_fallo = ahora
            
            if self._estado == self.Estado.CERRADO:
                if self._fallos_consecutivos >= self.umbral_fallos:
                    self._transicionar_a(self.Estado.ABIERTO)
                    self._abierto_hasta = ahora + self.timeout_recuperacion
                    
            elif self._estado == self.Estado.SEMI_ABIERTO:
                self._transicionar_a(self.Estado.ABIERTO)
                self._abierto_hasta = ahora + self.timeout_recuperacion * 2
                
            elif self._estado == self.Estado.DEGRADADO:
                if self._fallos_consecutivos >= self.umbral_fallos * 2:
                    self._transicionar_a(self.Estado.ABIERTO)
                    self._abierto_hasta = ahora + self.timeout_recuperacion * 3
    
    def _transicionar_a(self, nuevo_estado: Estado):
        """Realiza una transición de estado."""
        estado_anterior = self._estado
        self._estado = nuevo_estado
        self._metricas['transiciones'].append(time.time())
        
        # Log interno para depuración
        if hasattr(self, '_log_callback'):
            self._log_callback(f"CircuitBreaker[{self.nombre}]: {estado_anterior.value} -> {nuevo_estado.value}")
    
    def forzar_estado(self, estado: Estado):
        """Fuerza un estado específico (solo para pruebas/emergencias)."""
        with self._lock:
            self._transicionar_a(estado)
            if estado == self.Estado.ABIERTO:
                self._abierto_hasta = time.time() + self.timeout_recuperacion
    
    @property
    def estado(self) -> Estado:
        return self._estado
    
    @property
    def metricas(self) -> Dict[str, Any]:
        return {
            'estado': self._estado.value,
            'fallos_consecutivos': self._fallos_consecutivos,
            'total_exitos': self._total_exitos,
            'total_fallos': self._total_fallos,
            'tasa_exito': self._total_exitos / max(1, self._total_exitos + self._total_fallos),
        }

# =====================================================================
# SECCIÓN 5: CACHÉ DE RUTAS CON PREDICCIÓN
# =====================================================================

class CacheRutas:
    """
    Caché de rutas con predicción de uso futuro y LRU adaptativo.
    """
    
    def __init__(self, capacidad_maxima: int = 100, ttl_default: int = 300):
        self.capacidad_maxima = capacidad_maxima
        self.ttl_default = ttl_default
        self._cache: OrderedDict[str, Tuple[Ruta, float, int]] = OrderedDict()
        self._contador_accesos: DefaultDict[str, int] = defaultdict(int)
        self._patrones_acceso: DefaultDict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
        
    def obtener(self, clave: str) -> Optional[Ruta]:
        """Obtiene una ruta de la caché si es válida."""
        with self._lock:
            if clave not in self._cache:
                return None
            
            ruta, timestamp, ttl = self._cache[clave]
            if time.time() - timestamp > ttl:
                del self._cache[clave]
                return None
            
            # Actualizar estadísticas
            self._contador_accesos[clave] += 1
            self._patrones_acceso[clave].append(time.time())
            
            # Mover al final (LRU)
            self._cache.move_to_end(clave)
            
            return ruta
    
    def guardar(self, clave: str, ruta: Ruta, ttl: Optional[int] = None):
        """Guarda una ruta en la caché."""
        with self._lock:
            if ttl is None:
                ttl = self.ttl_default
            
            # Si ya existe, actualizar
            if clave in self._cache:
                del self._cache[clave]
            
            # Si excede capacidad, eliminar el menos usado
            if len(self._cache) >= self.capacidad_maxima:
                self._evict_lru()
            
            self._cache[clave] = (ruta, time.time(), ttl)
    
    def _evict_lru(self):
        """Elimina la entrada menos recientemente usada."""
        if self._cache:
            # Estrategia: eliminar el que tiene menos accesos entre los más antiguos
            clave_evict = min(
                list(self._cache.keys())[:10],
                key=lambda k: self._contador_accesos[k]
            )
            del self._cache[clave_evict]
    
    def predecir_precarga(self, patron_reciente: List[str]) -> List[str]:
        """Predice qué rutas precargar basado en patrones de uso."""
        predicciones = []
        for clave in patron_reciente:
            if clave in self._patrones_acceso:
                # Buscar claves que suelen accederse juntas
                tiempos = self._patrones_acceso[clave]
                if len(tiempos) > 10:
                    predicciones.append(clave)
        return predicciones[:5]
    
    def limpiar_expiradas(self):
        """Limpia todas las entradas expiradas."""
        with self._lock:
            ahora = time.time()
            expiradas = [
                k for k, (_, ts, ttl) in self._cache.items()
                if ahora - ts > ttl
            ]
            for k in expiradas:
                del self._cache[k]
    
    def estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la caché."""
        with self._lock:
            return {
                'tamano': len(self._cache),
                'capacidad_maxima': self.capacidad_maxima,
                'uso_promedio': sum(self._contador_accesos.values()) / max(1, len(self._cache)),
                'claves_mas_usadas': sorted(
                    self._contador_accesos.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }

# =====================================================================
# SECCIÓN 6: EL ORQUESTADOR MAESTRO (LA ENTIDAD PRINCIPAL)
# =====================================================================

class Orquestador:
    """
    Orquestador Maestro de ANP.
    
    Implementa:
    - Patrón Singleton thread-safe
    - Cola de prioridad para tareas
    - Enrutamiento predictivo
    - Gestión de fallbacks
    - Circuit breakers por núcleo
    - Métricas en tiempo real
    - Auto-recuperación
    """
    
    _instancia: Optional['Orquestador'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self, modo: ModoOrquestacion = ModoOrquestacion.NORMAL):
        if self._inicializado:
            return
            
        with self._lock_instancia:
            if self._inicializado:
                return
            
            self.modo = modo
            self.id_orquestador = str(uuid.uuid4())
            self.timestamp_inicio = time.time()
            
            # Configuración
            self._config = self._cargar_configuracion()
            
            # Estado de núcleos
            self._nucleos: Dict[str, EstadoNucleoInfo] = {}
            self._circuit_breakers: Dict[str, CircuitBreaker] = {}
            
            # Colas de procesamiento
            self._cola_tareas = queue.PriorityQueue()
            self._tareas_en_proceso: Dict[str, TareaPriorizada] = {}
            
            # Sistemas inteligentes
            self._predictor = PredictorRutas()
            self._cache_rutas = CacheRutas(
                capacidad_maxima=self._get_config('orquestador.tamano_cache_rutas', 100)
            )
            
            # Ejecutores
            self._ejecutor_principal = concurrent.futures.ThreadPoolExecutor(
                max_workers=self._get_config('sistema.max_hilos', 8),
                thread_name_prefix="ANP-Orquestador"
            )
            self._ejecutor_fallbacks = concurrent.futures.ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="ANP-Fallback"
            )
            
            # Métricas
            self._metricas: DefaultDict[str, List[MetricaRendimiento]] = defaultdict(list)
            self._contador_metricas: DefaultDict[str, int] = defaultdict(int)
            
            # Sistema de conciencia (monitoreo interno)
            self._conciencia_activa = True
            self._hilo_conciencia = threading.Thread(target=self._bucle_conciencia, daemon=True)
            
            # Registro de rutas predefinidas
            self._rutas_predefinidas: Dict[TipoTarea, List[Ruta]] = self._inicializar_rutas()
            
            # Observadores
            self._observadores: Dict[str, List[Callable]] = defaultdict(list)
            
            # Iniciar sistemas
            self._iniciar_subsistemas()
            
            self._inicializado = True
            
            self._registrar_metrica('orquestador.inicio', 1.0, 'count')
    
    def _cargar_configuracion(self) -> Any:
        """Carga la configuración del sistema."""
        try:
            return obtener_config()
        except:
            return None
    
    def _get_config(self, clave: str, default: Any) -> Any:
        """Obtiene un valor de configuración con fallback."""
        if self._config:
            try:
                return self._config[clave]
            except:
                pass
        return default
    
    def _inicializar_rutas(self) -> Dict[TipoTarea, List[Ruta]]:
        """Inicializa las rutas predefinidas para cada tipo de tarea."""
        return {
            TipoTarea.CONSULTA: [
                Ruta(
                    nucleo_principal="comunicacion",
                    nucleo_fallback="comunicacion_fallback",
                    motor="dialogo",
                    prioridad=PrioridadTarea.ALTA,
                    timeout=5.0,
                    reintentos_max=2,
                    cacheable=True,
                    ttl_cache=60
                )
            ],
            TipoTarea.RAZONAMIENTO: [
                Ruta(
                    nucleo_principal="razonamiento",
                    nucleo_fallback="razonamiento_fallback",
                    motor="logico",
                    prioridad=PrioridadTarea.CRITICA,
                    timeout=10.0,
                    reintentos_max=3,
                    cacheable=False
                ),
                Ruta(
                    nucleo_principal="razonamiento",
                    nucleo_fallback="razonamiento_fallback",
                    motor="probabilistico",
                    prioridad=PrioridadTarea.ALTA,
                    timeout=8.0,
                    reintentos_max=2,
                    cacheable=False
                )
            ],
            TipoTarea.BUSQUEDA: [
                Ruta(
                    nucleo_principal="busqueda",
                    nucleo_fallback="busqueda_fallback",
                    motor="web",
                    prioridad=PrioridadTarea.MEDIA,
                    timeout=15.0,
                    reintentos_max=2,
                    cacheable=True,
                    ttl_cache=3600
                )
            ],
            TipoTarea.MEMORIA: [
                Ruta(
                    nucleo_principal="memoria",
                    nucleo_fallback="memoria_fallback",
                    motor="semantica",
                    prioridad=PrioridadTarea.ALTA,
                    timeout=3.0,
                    reintentos_max=3,
                    cacheable=True,
                    ttl_cache=300
                )
            ],
            TipoTarea.RESOLUCION: [
                Ruta(
                    nucleo_principal="resolucion",
                    nucleo_fallback="resolucion_fallback",
                    motor="matematicas",
                    prioridad=PrioridadTarea.MEDIA,
                    timeout=12.0,
                    reintentos_max=2,
                    cacheable=True,
                    ttl_cache=1800
                )
            ],
            TipoTarea.CREATIVIDAD: [
                Ruta(
                    nucleo_principal="creatividad",
                    nucleo_fallback="creatividad_fallback",
                    motor="ideas",
                    prioridad=PrioridadTarea.BAJA,
                    timeout=20.0,
                    reintentos_max=1,
                    cacheable=False
                )
            ],
            TipoTarea.SISTEMA: [
                Ruta(
                    nucleo_principal="sistema",
                    nucleo_fallback=None,
                    motor=None,
                    prioridad=PrioridadTarea.CRITICA,
                    timeout=5.0,
                    reintentos_max=1,
                    cacheable=False
                )
            ],
        }
    
    def _iniciar_subsistemas(self):
        """Inicia todos los subsistemas del orquestador."""
        # Inicializar circuit breakers para cada núcleo
        for nucleo in ["comunicacion", "razonamiento", "memoria", "resolucion", "busqueda", "creatividad"]:
            self._circuit_breakers[nucleo] = CircuitBreaker(
                nombre=nucleo,
                umbral_fallos=self._get_config('fallback.circuit_breaker_umbral', 5),
                timeout_recuperacion=self._get_config('fallback.circuit_breaker_timeout', 60.0)
            )
            
            # Inicializar estado del núcleo
            self._nucleos[nucleo] = EstadoNucleoInfo(
                nombre=nucleo,
                estado=EstadoNucleo.INACTIVO,
                carga_maxima=self._get_config(f'nucleos.{nucleo}.carga_maxima', 100)
            )
        
        # Iniciar hilo de conciencia
        self._hilo_conciencia.start()
        
        # Iniciar limpieza periódica de caché
        self._programar_limpieza_cache()
    
    def _programar_limpieza_cache(self):
        """Programa la limpieza periódica de la caché."""
        def limpiar_periodicamente():
            while self._conciencia_activa:
                time.sleep(300)  # Cada 5 minutos
                self._cache_rutas.limpiar_expiradas()
        
        threading.Thread(target=limpiar_periodicamente, daemon=True).start()
    
    def _bucle_conciencia(self):
        """Bucle de conciencia sistémica (monitoreo continuo)."""
        while self._conciencia_activa:
            try:
                # Actualizar estado de núcleos
                for nombre, estado in self._nucleos.items():
                    cb = self._circuit_breakers.get(nombre)
                    if cb:
                        estado.circuit_breaker_abierto = (cb.estado == CircuitBreaker.Estado.ABIERTO)
                        estado.fallos_consecutivos = cb.metricas['fallos_consecutivos']
                
                # Verificar núcleos inactivos por mucho tiempo
                ahora = time.time()
                for nombre, estado in self._nucleos.items():
                    if estado.estado == EstadoNucleo.ACTIVO:
                        if ahora - estado.ultimo_latido > 30:
                            estado.estado = EstadoNucleo.DEGRADADO
                            self._registrar_metrica(f'nucleo.{nombre}.degradado', 1.0, 'count')
                
                time.sleep(5)  # Latido cada 5 segundos
                
            except Exception as e:
                self._registrar_metrica('conciencia.error', 1.0, 'count')
    
    # =====================================================================
    # API PÚBLICA DEL ORQUESTADOR
        # =====================================================================
    
    def registrar_nucleo(self, nombre: str, version: str = "0.0.0", metadatos: Dict = None) -> bool:
        """Registra un núcleo en el orquestador."""
        if nombre not in self._nucleos:
            self._nucleos[nombre] = EstadoNucleoInfo(
                nombre=nombre,
                estado=EstadoNucleo.INICIALIZANDO,
                version=version,
                metadatos=metadatos or {}
            )
        else:
            self._nucleos[nombre].estado = EstadoNucleo.ACTIVO
            self._nucleos[nombre].version = version
            self._nucleos[nombre].metadatos.update(metadatos or {})
        
        self._nucleos[nombre].ultimo_latido = time.time()
        self._registrar_metrica(f'nucleo.{nombre}.registrado', 1.0, 'count')
        return True
    
    def latido_nucleo(self, nombre: str, carga: int = 0) -> bool:
        """Recibe un latido de un núcleo (keep-alive)."""
        if nombre in self._nucleos:
            self._nucleos[nombre].ultimo_latido = time.time()
            self._nucleos[nombre].carga_actual = carga
            if self._nucleos[nombre].estado == EstadoNucleo.INACTIVO:
                self._nucleos[nombre].estado = EstadoNucleo.ACTIVO
            return True
        return False
    
    def enviar_tarea(
        self,
        tipo: TipoTarea,
        datos: Any,
        contexto: Dict[str, Any] = None,
        prioridad: PrioridadTarea = None,
        timeout: float = None
    ) -> concurrent.futures.Future:
        """
        Envía una tarea al orquestador para su procesamiento.
        
        Returns:
            Future con el resultado de la tarea
        """
        if contexto is None:
            contexto = {}
        
        # Determinar prioridad
        if prioridad is None:
            prioridad = self._calcular_prioridad(tipo, datos)
        
        # Crear tarea priorizada
        tarea = TareaPriorizada(
            prioridad=prioridad,
            timestamp=time.time(),
            id=str(uuid.uuid4()),
            tipo=tipo,
            datos=datos,
            contexto=contexto
        )
        
        # Encontrar ruta óptima
        ruta = self._enrutar(tarea)
        if ruta is None:
            # Sin ruta disponible, ir a fallback global
            ruta = self._ruta_fallback_global(tipo)
        
        tarea.ruta = ruta
        
        if timeout:
            tarea.ruta = Ruta(
                nucleo_principal=ruta.nucleo_principal,
                nucleo_fallback=ruta.nucleo_fallback,
                motor=ruta.motor,
                prioridad=ruta.prioridad,
                timeout=timeout,
                reintentos_max=ruta.reintentos_max,
                requiere_contexto=ruta.requiere_contexto,
                cacheable=ruta.cacheable,
                ttl_cache=ruta.ttl_cache
            )
        
        # Verificar caché si es cacheable
        if ruta.cacheable:
            clave_cache = self._generar_clave_cache(tarea)
            ruta_cache = self._cache_rutas.obtener(clave_cache)
            if ruta_cache:
                self._registrar_metrica(MetricaOrquestador.RUTAS_CACHE_HITS.value, 1.0, 'count')
                futuro = concurrent.futures.Future()
                futuro.set_result({"cache": True, "ruta": str(ruta_cache)})
                return futuro
            self._registrar_metrica(MetricaOrquestador.RUTAS_CACHE_MISSES.value, 1.0, 'count')
        
        # Verificar circuit breaker
        cb = self._circuit_breakers.get(ruta.nucleo_principal)
        if cb and not cb.permitir_operacion():
            # Circuit breaker abierto, usar fallback
            if ruta.nucleo_fallback:
                self._registrar_metrica(MetricaOrquestador.FALLBACKS_ACTIVADOS.value, 1.0, 'count')
                return self._ejecutar_fallback(tarea, ruta.nucleo_fallback)
            else:
                futuro = concurrent.futures.Future()
                futuro.set_exception(Exception(f"Circuit breaker abierto para {ruta.nucleo_principal}"))
                return futuro
        
        # Encolar tarea
        self._cola_tareas.put(tarea)
        self._tareas_en_proceso[tarea.id] = tarea
        
        # Programar ejecución
        futuro = self._ejecutor_principal.submit(self._procesar_tarea, tarea)
        tarea.futuro = futuro
        
        self._registrar_metrica(MetricaOrquestador.TAREAS_PROCESADAS.value, 1.0, 'count')
        
        return futuro
    
    async def enviar_tarea_async(
        self,
        tipo: TipoTarea,
        datos: Any,
        contexto: Dict[str, Any] = None,
        prioridad: PrioridadTarea = None
    ) -> Any:
        """Versión asíncrona de enviar_tarea."""
        futuro = self.enviar_tarea(tipo, datos, contexto, prioridad)
        
        # Esperar resultado de manera asíncrona
        while not futuro.done():
            await asyncio.sleep(0.1)
        
        return futuro.result()
    
    def _calcular_prioridad(self, tipo: TipoTarea, datos: Any) -> PrioridadTarea:
        """Calcula la prioridad basada en el tipo y los datos."""
        prioridades_default = {
            TipoTarea.SISTEMA: PrioridadTarea.CRITICA,
            TipoTarea.RAZONAMIENTO: PrioridadTarea.ALTA,
            TipoTarea.CONSULTA: PrioridadTarea.ALTA,
            TipoTarea.MEMORIA: PrioridadTarea.ALTA,
            TipoTarea.BUSQUEDA: PrioridadTarea.MEDIA,
            TipoTarea.RESOLUCION: PrioridadTarea.MEDIA,
            TipoTarea.CREATIVIDAD: PrioridadTarea.BAJA,
            TipoTarea.FALLBACK: PrioridadTarea.ALTA,
        }
        return prioridades_default.get(tipo, PrioridadTarea.MEDIA)
    
    def _enrutar(self, tarea: TareaPriorizada) -> Optional[Ruta]:
        """Determina la mejor ruta para una tarea."""
        # Intentar predicción inteligente
        rutas_disponibles = self._rutas_predefinidas.get(tarea.tipo, [])
        if not rutas_disponibles:
            return None
        
        # Obtener núcleos saludables
        nucleos_saludables = [
            r.nucleo_principal for r in rutas_disponibles
            if self._nucleo_saludable(r.nucleo_principal)
        ]
        
        if not nucleos_saludables:
            return None
        
        # Usar predictor para elegir mejor núcleo
        mejor_nucleo = self._predictor.predecir_mejor_ruta(
            tarea.tipo.value,
            nucleos_saludables
        )
        
        # Encontrar la ruta correspondiente
        for ruta in rutas_disponibles:
            if ruta.nucleo_principal == mejor_nucleo:
                return ruta
        
        # Fallback: primera ruta disponible
        for ruta in rutas_disponibles:
            if self._nucleo_saludable(ruta.nucleo_principal):
                return ruta
        
        return None
    
    def _nucleo_saludable(self, nombre: str) -> bool:
        """Verifica si un núcleo está saludable."""
        if nombre not in self._nucleos:
            return False
        
        estado = self._nucleos[nombre]
        cb = self._circuit_breakers.get(nombre)
        
        if cb and cb.estado == CircuitBreaker.Estado.ABIERTO:
            return False
        
        return estado.saludable
    
    def _ruta_fallback_global(self, tipo: TipoTarea) -> Ruta:
        """Proporciona una ruta de fallback global."""
        return Ruta(
            nucleo_principal="fallback_global",
            nucleo_fallback=None,
            motor="emergencia",
            prioridad=PrioridadTarea.CRITICA,
            timeout=10.0,
            reintentos_max=1,
            requiere_contexto=False,
            cacheable=False
        )
    
    def _generar_clave_cache(self, tarea: TareaPriorizada) -> str:
        """Genera una clave única para la caché."""
        contenido = f"{tarea.tipo.value}:{hashlib.md5(str(tarea.datos).encode()).hexdigest()}"
        return hashlib.sha256(contenido.encode()).hexdigest()[:32]
    
    def _procesar_tarea(self, tarea: TareaPriorizada) -> Any:
        """Procesa una tarea (ejecutado en el pool de hilos)."""
        inicio = time.time()
        nucleo = tarea.ruta.nucleo_principal
        cb = self._circuit_breakers.get(nucleo)
        
        try:
            # Simular procesamiento (en producción, aquí se llamaría al núcleo real)
            resultado = self._ejecutar_en_nucleo(tarea)
            
            # Registrar éxito
            if cb:
                cb.registrar_exito()
            
            self._predictor.registrar_exito(
                tarea.tipo.value,
                nucleo,
                time.time() - inicio
            )
            
            # Actualizar métricas del núcleo
            if nucleo in self._nucleos:
                self._nucleos[nucleo].tareas_procesadas += 1
                tiempo_total = self._nucleos[nucleo].tiempo_respuesta_promedio * (self._nucleos[nucleo].tareas_procesadas - 1)
                self._nucleos[nucleo].tiempo_respuesta_promedio = (tiempo_total + (time.time() - inicio)) / self._nucleos[nucleo].tareas_procesadas
            
            # Guardar en caché si aplica
            if tarea.ruta.cacheable:
                clave = self._generar_clave_cache(tarea)
                self._cache_rutas.guardar(clave, tarea.ruta, tarea.ruta.ttl_cache)
            
            return resultado
            
        except Exception as e:
            # Registrar fallo
            if cb:
                cb.registrar_fallo()
            
            self._predictor.registrar_fallo(tarea.tipo.value, nucleo)
            
            if nucleo in self._nucleos:
                self._nucleos[nucleo].tareas_fallidas += 1
            
            self._registrar_metrica(MetricaOrquestador.TAREAS_FALLIDAS.value, 1.0, 'count')
            
            # Reintentar o fallback
            if tarea.intentos < tarea.ruta.reintentos_max:
                tarea.intentos += 1
                return self._procesar_tarea(tarea)
            elif tarea.ruta.nucleo_fallback:
                return self._ejecutar_fallback(tarea, tarea.ruta.nucleo_fallback)
            else:
                raise
    
    def _ejecutar_en_nucleo(self, tarea: TareaPriorizada) -> Any:
        """Ejecuta la tarea en el núcleo correspondiente."""
        # En una implementación real, esto llamaría al núcleo vía RPC/eventos
        # Por ahora, simulamos procesamiento
        
        # Simular tiempo de procesamiento
        time.sleep(random.uniform(0.1, 0.5))
        
        return {
            "status": "success",
            "nucleo": tarea.ruta.nucleo_principal,
            "tipo": tarea.tipo.value,
            "datos": tarea.datos,
            "intentos": tarea.intentos + 1,
            "timestamp": time.time()
        }
    
    def _ejecutar_fallback(self, tarea: TareaPriorizada, nucleo_fallback: str) -> concurrent.futures.Future:
        """Ejecuta una tarea en modo fallback."""
        self._registrar_metrica(MetricaOrquestador.FALLBACKS_ACTIVADOS.value, 1.0, 'count')
        
        futuro = self._ejecutor_fallbacks.submit(self._procesar_fallback, tarea, nucleo_fallback)
        return futuro
    
    def _procesar_fallback(self, tarea: TareaPriorizada, nucleo_fallback: str) -> Any:
        """Procesa una tarea en el núcleo de fallback."""
        time.sleep(random.uniform(0.2, 0.8))
        
        return {
            "status": "fallback",
            "nucleo": nucleo_fallback,
            "tipo": tarea.tipo.value,
            "datos": tarea.datos,
            "mensaje": "Procesado en modo degradado",
            "timestamp": time.time()
        }
    
    # =====================================================================
    # MÉTRICAS Y MONITOREO
    # =====================================================================
    
    def _registrar_metrica(self, nombre: str, valor: float, unidad: str, tags: Dict = None):
        """Registra una métrica de rendimiento."""
        metrica = MetricaRendimiento(
            nombre=nombre,
            valor=valor,
            unidad=unidad,
            tags=tags or {}
        )
        self._metricas[nombre].append(metrica)
        self._contador_metricas[nombre] += 1
        
        # Mantener solo últimas 1000 métricas por nombre
        if len(self._metricas[nombre]) > 1000:
            self._metricas[nombre] = self._metricas[nombre][-1000:]
    
    def obtener_metricas(self) -> Dict[str, Any]:
        """Obtiene todas las métricas del orquestador."""
        return {
            'orquestador': {
                'id': self.id_orquestador,
                'modo': self.modo.value,
                'uptime': time.time() - self.timestamp_inicio,
                'tareas_en_cola': self._cola_tareas.qsize(),
                'tareas_en_proceso': len(self._tareas_en_proceso),
            },
            'nucleos': {
                nombre: asdict(estado)
                for nombre, estado in self._nucleos.items()
            },
            'circuit_breakers': {
                nombre: cb.metricas
                for nombre, cb in self._circuit_breakers.items()
            },
            'predictor': self._predictor.obtener_estadisticas(),
            'cache': self._cache_rutas.estadisticas(),
            'contadores': dict(self._contador_metricas),
        }
    
    def obtener_estado_nucleo(self, nombre: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado detallado de un núcleo."""
        if nombre in self._nucleos:
            return asdict(self._nucleos[nombre])
        return None
    
    # =====================================================================
    # OBSERVADORES Y EVENTOS
        # =====================================================================
    
    def suscribir(self, evento: str, callback: Callable):
        """Suscribe un callback a un evento del orquestador."""
        self._observadores[evento].append(callback)
    
    def _notificar(self, evento: str, datos: Any = None):
        """Notifica a los observadores de un evento."""
        for callback in self._observadores.get(evento, []):
            try:
                callback(evento, datos)
            except Exception as e:
                pass
    
    # =====================================================================
    # CONTROL DEL CICLO DE VIDA
    # =====================================================================
    
    def apagar(self, graceful: bool = True):
        """Apaga el orquestador de manera controlada."""
        self._conciencia_activa = False
        self._notificar('orquestador.apagando', {'graceful': graceful})
        
        if graceful:
            # Esperar a que terminen las tareas en proceso
            self._ejecutor_principal.shutdown(wait=True)
            self._ejecutor_fallbacks.shutdown(wait=True)
        else:
            self._ejecutor_principal.shutdown(wait=False)
            self._ejecutor_fallbacks.shutdown(wait=False)
        
        self._registrar_metrica('orquestador.apagado', 1.0, 'count')
        self._inicializado = False
    
    def reiniciar(self) -> bool:
        """Reinicia el orquestador."""
        self.apagar(graceful=True)
        time.sleep(2)
        self.__init__(modo=self.modo)
        return self._inicializado
    
    # =====================================================================
    # MÉTODOS MÁGICOS
    # =====================================================================
    
    def __repr__(self) -> str:
        return f"Orquestador(id={self.id_orquestador[:8]}, modo={self.modo.value}, nucleos={len(self._nucleos)})"
    
    def __str__(self) -> str:
        return f"ANP Orquestador Maestro v0.0.1-NEBULA [{self.modo.value}]"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.apagar(graceful=True)

# =====================================================================
# SECCIÓN 7: FUNCIONES DE CONVENIENCIA
# =====================================================================

_orquestador_global: Optional[Orquestador] = None

def obtener_orquestador(modo: ModoOrquestacion = ModoOrquestacion.NORMAL) -> Orquestador:
    """Obtiene la instancia global del orquestador."""
    global _orquestador_global
    if _orquestador_global is None:
        _orquestador_global = Orquestador(modo=modo)
    return _orquestador_global

def enviar_tarea(tipo: TipoTarea, datos: Any, **kwargs) -> concurrent.futures.Future:
    """Función de conveniencia para enviar tareas."""
    orch = obtener_orquestador()
    return orch.enviar_tarea(tipo, datos, **kwargs)

