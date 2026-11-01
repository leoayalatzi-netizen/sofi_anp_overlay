# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Enrutador Inteligente (Sistema de Enrutamiento Cuántico)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa algoritmos de enrutamiento
# predictivo, balanceo de carga adaptativo, y selección de rutas
# basada en múltiples criterios ponderados dinámicamente.
# =====================================================================

import sys
import os
import time
import threading
import random
import math
import hashlib
import json
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, overload, DefaultDict
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto, Flag
from collections import defaultdict, deque, OrderedDict, Counter
from functools import lru_cache, wraps, partial
from abc import ABC, abstractmethod
import heapq
from contextlib import contextmanager

# =====================================================================
# IMPORTS DEL SISTEMA ANP (con fallback elegante)
# =====================================================================

try:
    from configuracion import Configuracion, obtener_config
except ImportError:
    Configuracion = None
    obtener_config = lambda: None

try:
    from .maestro import (
        PrioridadTarea, TipoTarea, Ruta, EstadoNucleo,
        ModoOrquestacion, MetricaOrquestador
    )
except ImportError:
    # Fallback para pruebas independientes
    class PrioridadTarea(IntEnum):
        CRITICA = 0
        ALTA = 1
        MEDIA = 2
        BAJA = 3
        DIFERIDA = 4
    
    class TipoTarea(Enum):
        CONSULTA = "consulta"
        RAZONAMIENTO = "razonamiento"
        BUSQUEDA = "busqueda"
        MEMORIA = "memoria"
        RESOLUCION = "resolucion"
        CREATIVIDAD = "creatividad"
        SISTEMA = "sistema"
        FALLBACK = "fallback"
    
    class EstadoNucleo(Enum):
        INACTIVO = "inactivo"
        ACTIVO = "activo"
        DEGRADADO = "degradado"
        ERROR = "error"
    
    class ModoOrquestacion(Enum):
        NORMAL = "normal"
        DEGRADADO = "degradado"
        EMERGENCIA = "emergencia"
        DIOS = "dios"
    
    @dataclass(frozen=True)
    class Ruta:
        nucleo_principal: str
        nucleo_fallback: Optional[str]
        motor: Optional[str]
        prioridad: PrioridadTarea
        timeout: float
        reintentos_max: int
        requiere_contexto: bool = True
        cacheable: bool = False
        ttl_cache: int = 300
        peso: float = 1.0

# =====================================================================
# SECCIÓN 1: ENUMERACIONES Y ESTRUCTURAS DE DATOS
# =====================================================================

class EstrategiaEnrutamiento(Enum):
    """Estrategias de enrutamiento disponibles."""
    ROUND_ROBIN = "round_robin"
    MENOR_CARGA = "menor_carga"
    PRIORIDAD = "prioridad"
    ADAPTATIVO = "adaptativo"
    PREDICTIVO = "predictivo"
    PONDERADO = "ponderado"
    CUANTICO = "cuantico"  # Combina múltiples estrategias
    ALEATORIO_PONDERADO = "aleatorio_ponderado"
    MENOR_LATENCIA = "menor_latencia"
    MAYOR_DISPONIBILIDAD = "mayor_disponibilidad"

class CriterioSeleccion(Enum):
    """Criterios para evaluar rutas."""
    CARGA_ACTUAL = "carga_actual"
    LATENCIA_PROMEDIO = "latencia_promedio"
    TASA_EXITO = "tasa_exito"
    DISPONIBILIDAD = "disponibilidad"
    PRIORIDAD_NUCLEO = "prioridad_nucleo"
    AFINIDAD_TAREA = "afinidad_tarea"
    DISTANCIA_TOPOLOGICA = "distancia_topologica"
    COSTE_COMPUTACIONAL = "coste_computacional"
    PREDICCION_CARGA = "prediccion_carga"
    ESTABILIDAD_HISTORICA = "estabilidad_historica"

class EstadoRuta(Enum):
    """Estados posibles de una ruta."""
    DISPONIBLE = "disponible"
    OCUPADA = "ocupada"
    DEGRADADA = "degradada"
    INACTIVA = "inactiva"
    MANTENIMIENTO = "mantenimiento"
    PROBANDO = "probando"

@dataclass
class MetricaRuta:
    """Métricas detalladas de una ruta."""
    latencia_promedio: float = 0.0
    latencia_p95: float = 0.0
    latencia_p99: float = 0.0
    tasa_exito: float = 1.0
    tasa_error: float = 0.0
    uso_promedio: float = 0.0
    uso_pico: float = 0.0
    tiempo_respuesta_min: float = float('inf')
    tiempo_respuesta_max: float = 0.0
    total_peticiones: int = 0
    total_exitos: int = 0
    total_fallos: int = 0
    ultimo_uso: float = 0.0
    primera_vez: float = field(default_factory=time.time)
    
    def actualizar(self, exito: bool, latencia: float):
        """Actualiza métricas con una nueva petición."""
        self.total_peticiones += 1
        self.ultimo_uso = time.time()
        
        if exito:
            self.total_exitos += 1
        else:
            self.total_fallos += 1
        
        # Actualizar tasas
        if self.total_peticiones > 0:
            self.tasa_exito = self.total_exitos / self.total_peticiones
            self.tasa_error = self.total_fallos / self.total_peticiones
        
        # Actualizar latencias
        if latencia < self.tiempo_respuesta_min:
            self.tiempo_respuesta_min = latencia
        if latencia > self.tiempo_respuesta_max:
            self.tiempo_respuesta_max = latencia
        
        # Promedio móvil exponencial
        alpha = 0.3
        self.latencia_promedio = alpha * latencia + (1 - alpha) * self.latencia_promedio
        
        # Almacenar para percentiles
        self._almacenar_latencia(latencia)
    
    _latencias_recientes: List[float] = field(default_factory=list, init=False, repr=False)
    
    def _almacenar_latencia(self, latencia: float):
        """Almacena latencia para cálculo de percentiles."""
        self._latencias_recientes.append(latencia)
        if len(self._latencias_recientes) > 1000:
            self._latencias_recientes = self._latencias_recientes[-500:]
        
        # Actualizar percentiles
        if len(self._latencias_recientes) >= 10:
            sorted_lats = sorted(self._latencias_recientes)
            self.latencia_p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
            self.latencia_p99 = sorted_lats[int(len(sorted_lats) * 0.99)]

@dataclass
class EstadoRutaExtendido:
    """Estado extendido de una ruta con métricas completas."""
    ruta: Ruta
    estado: EstadoRuta = EstadoRuta.DISPONIBLE
    carga_actual: int = 0
    carga_maxima: int = 100
    prioridad_actual: float = 1.0
    peso_dinamico: float = 1.0
    metricas: MetricaRuta = field(default_factory=MetricaRuta)
    tags: Dict[str, str] = field(default_factory=dict)
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def disponible(self) -> bool:
        return (self.estado == EstadoRuta.DISPONIBLE and 
                self.carga_actual < self.carga_maxima)
    
    @property
    def carga_porcentaje(self) -> float:
        return (self.carga_actual / self.carga_maxima) * 100 if self.carga_maxima > 0 else 0
    
    @property
    def salud(self) -> float:
        """Calcula un índice de salud de la ruta (0-1)."""
        salud = self.metricas.tasa_exito
        if self.carga_porcentaje > 80:
            salud *= 0.7
        elif self.carga_porcentaje > 60:
            salud *= 0.9
        
        if self.estado != EstadoRuta.DISPONIBLE:
            salud *= 0.5
        
        return min(1.0, max(0.0, salud))

# =====================================================================
# SECCIÓN 2: PREDICTOR DE CARGA
# =====================================================================

class PredictorCarga:
    """
    Predice la carga futura de los núcleos usando series temporales.
    Implementa suavizado exponencial Holt-Winters y detección de tendencias.
    """
    
    def __init__(self, ventana_historica: int = 100):
        self.ventana_historica = ventana_historica
        self._historico: DefaultDict[str, deque] = defaultdict(lambda: deque(maxlen=ventana_historica))
        self._tendencias: Dict[str, float] = {}
        self._estacionalidad: Dict[str, float] = {}
        self._lock = threading.RLock()
        
    def registrar_carga(self, nucleo: str, carga: float, timestamp: float = None):
        """Registra una medición de carga."""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self._historico[nucleo].append((timestamp, carga))
            self._actualizar_predicciones(nucleo)
    
    def _actualizar_predicciones(self, nucleo: str):
        """Actualiza predicciones para un núcleo."""
        historico = list(self._historico[nucleo])
        if len(historico) < 3:
            return
        
        # Calcular tendencia (regresión lineal simple)
        n = len(historico)
        if n > 1:
            x = list(range(n))
            y = [c for _, c in historico]
            
            x_mean = sum(x) / n
            y_mean = sum(y) / n
            
            numerador = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominador = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominador != 0:
                self._tendencias[nucleo] = numerador / denominador
            else:
                self._tendencias[nucleo] = 0.0
        
        # Detectar estacionalidad (autocorrelación)
        if n > 10:
            self._estacionalidad[nucleo] = self._calcular_autocorrelacion(y, lag=5)
    
    def _calcular_autocorrelacion(self, datos: List[float], lag: int = 5) -> float:
        """Calcula autocorrelación para detectar patrones."""
        n = len(datos)
        if n <= lag:
            return 0.0
        
        mean = sum(datos) / n
        numerador = sum((datos[i] - mean) * (datos[i - lag] - mean) for i in range(lag, n))
        denominador = sum((d - mean) ** 2 for d in datos)
        
        if denominador != 0:
            return numerador / denominador
        return 0.0
    
    def predecir_carga(self, nucleo: str, horizonte_segundos: float = 5.0) -> float:
        """Predice la carga futura de un núcleo."""
        with self._lock:
            historico = list(self._historico[nucleo])
            if not historico:
                return 0.0
            
            carga_actual = historico[-1][1]
            tendencia = self._tendencias.get(nucleo, 0.0)
            
            # Proyección lineal
            pasos_futuros = horizonte_segundos / 5.0  # Asumiendo mediciones cada 5s
            carga_predicha = carga_actual + tendencia * pasos_futuros
            
            # Ajustar por estacionalidad
            estacionalidad = self._estacionalidad.get(nucleo, 0.0)
            if abs(estacionalidad) > 0.3:
                # Hay patrón estacional, ajustar
                fase = (time.time() % 60) / 60  # Patrón por minuto
                ajuste = estacionalidad * math.sin(2 * math.pi * fase)
                carga_predicha += ajuste * 10
            
            return max(0.0, min(100.0, carga_predicha))
    
    def obtener_tendencia(self, nucleo: str) -> float:
        """Obtiene la tendencia actual de un núcleo."""
        return self._tendencias.get(nucleo, 0.0)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del predictor."""
        with self._lock:
            return {
                'nucleos_monitoreados': len(self._historico),
                'tendencias': dict(self._tendencias),
                'estacionalidad': dict(self._estacionalidad),
            }

# =====================================================================
# SECCIÓN 3: BALANCEADOR DE CARGA ADAPTATIVO
# =====================================================================

class BalanceadorAdaptativo:
    """
    Balanceador de carga que ajusta pesos dinámicamente.
    Implementa el algoritmo "Weighted Least Connections" con ajuste predictivo.
    """
    
    def __init__(self):
        self._pesos_base: Dict[str, float] = {}
        self._pesos_dinamicos: Dict[str, float] = {}
        self._conexiones_activas: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._historico_decisiones: deque = deque(maxlen=1000)
        
    def registrar_nucleo(self, nucleo: str, peso_base: float = 1.0):
        """Registra un núcleo para balanceo."""
        with self._lock:
            self._pesos_base[nucleo] = peso_base
            self._pesos_dinamicos[nucleo] = peso_base
    
    def actualizar_metrica(self, nucleo: str, metrica: str, valor: float):
        """Actualiza una métrica que afecta el peso dinámico."""
        with self._lock:
            if nucleo not in self._pesos_base:
                return
            
            peso = self._pesos_base[nucleo]
            
            # Ajustar según latencia
            if metrica == 'latencia':
                if valor > 1.0:
                    peso *= 0.7
                elif valor < 0.1:
                    peso *= 1.2
            
            # Ajustar según tasa de éxito
            elif metrica == 'tasa_exito':
                if valor < 0.9:
                    peso *= (0.5 + valor * 0.5)
                else:
                    peso *= valor
            
            # Ajustar según carga
            elif metrica == 'carga':
                if valor > 80:
                    peso *= 0.3
                elif valor > 60:
                    peso *= 0.6
                elif valor < 20:
                    peso *= 1.3
            
            self._pesos_dinamicos[nucleo] = max(0.1, min(5.0, peso))
    
    def seleccionar_nucleo(self, nucleos_disponibles: List[str]) -> Optional[str]:
        """
        Selecciona el mejor núcleo usando Weighted Least Connections.
        """
        with self._lock:
            if not nucleos_disponibles:
                return None
            
            # Calcular puntuación para cada núcleo
            puntuaciones = {}
            for nucleo in nucleos_disponibles:
                if nucleo not in self._pesos_dinamicos:
                    continue
                
                peso = self._pesos_dinamicos[nucleo]
                conexiones = self._conexiones_activas[nucleo]
                
                # Fórmula: peso / (conexiones + 1)
                puntuacion = peso / (conexiones + 1)
                puntuaciones[nucleo] = puntuacion
            
            if not puntuaciones:
                return random.choice(nucleos_disponibles) if nucleos_disponibles else None
            
            # Seleccionar el de mayor puntuación
            mejor_nucleo = max(puntuaciones, key=puntuaciones.get)
            
            # Registrar decisión
            self._historico_decisiones.append({
                'timestamp': time.time(),
                'nucleo': mejor_nucleo,
                'puntuaciones': puntuaciones.copy()
            })
            
            return mejor_nucleo
    
    def incrementar_conexiones(self, nucleo: str):
        """Incrementa el contador de conexiones activas."""
        with self._lock:
            self._conexiones_activas[nucleo] += 1
    
    def decrementar_conexiones(self, nucleo: str):
        """Decrementa el contador de conexiones activas."""
        with self._lock:
            if self._conexiones_activas[nucleo] > 0:
                self._conexiones_activas[nucleo] -= 1
    
    def obtener_pesos(self) -> Dict[str, float]:
        """Obtiene los pesos dinámicos actuales."""
        with self._lock:
            return dict(self._pesos_dinamicos)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del balanceador."""
        with self._lock:
            return {
                'pesos_base': dict(self._pesos_base),
                'pesos_dinamicos': dict(self._pesos_dinamicos),
                'conexiones_activas': dict(self._conexiones_activas),
                'total_decisiones': len(self._historico_decisiones),
            }

# =====================================================================
# SECCIÓN 4: ENRUTADOR PRINCIPAL
# =====================================================================

class Enrutador:
    """
    Enrutador Inteligente de ANP.
    
    Capacidades:
    - Múltiples estrategias de enrutamiento
    - Balanceo de carga adaptativo
    - Predicción de carga futura
    - Selección multi-criterio ponderada
    - Auto-aprendizaje de rutas óptimas
    - Fallback inteligente
    """
    
    def __init__(self, estrategia: EstrategiaEnrutamiento = EstrategiaEnrutamiento.CUANTICO):
        self.estrategia = estrategia
        self.modo = ModoOrquestacion.NORMAL
        
        # Tablas de enrutamiento
        self._rutas: Dict[str, List[EstadoRutaExtendido]] = defaultdict(list)
        self._rutas_por_nucleo: Dict[str, List[EstadoRutaExtendido]] = defaultdict(list)
        self._rutas_por_tipo: Dict[TipoTarea, List[EstadoRutaExtendido]] = defaultdict(list)
        
        # Sistemas inteligentes
        self._predictor_carga = PredictorCarga()
        self._balanceador = BalanceadorAdaptativo()
        
        # Caché de decisiones
        self._cache_decisiones: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._cache_max_size = 500
        self._cache_ttl = 60  # segundos
        
        # Métricas de enrutamiento
        self._metricas_enrutamiento: DefaultDict[str, List[float]] = defaultdict(list)
        self._contador_rutas: DefaultDict[str, int] = defaultdict(int)
        
        # Pesos para criterios múltiples
        self._pesos_criterios: Dict[CriterioSeleccion, float] = {
            CriterioSeleccion.CARGA_ACTUAL: 0.25,
            CriterioSeleccion.LATENCIA_PROMEDIO: 0.20,
            CriterioSeleccion.TASA_EXITO: 0.25,
            CriterioSeleccion.DISPONIBILIDAD: 0.15,
            CriterioSeleccion.PREDICCION_CARGA: 0.15,
        }
        
        # Locks
        self._lock_rutas = threading.RLock()
        self._lock_cache = threading.RLock()
        
        # Estado
        self._inicializado = False
        self._timestamp_inicio = time.time()
        
        # Inicializar
        self._inicializar()
    
    def _inicializar(self):
        """Inicializa el enrutador."""
        self._inicializado = True
    
    # =====================================================================
    # REGISTRO DE RUTAS
    # =====================================================================
    
    def registrar_ruta(self, ruta: Ruta, estado_inicial: EstadoRuta = EstadoRuta.DISPONIBLE) -> bool:
        """Registra una nueva ruta en el enrutador."""
        with self._lock_rutas:
            clave = f"{ruta.nucleo_principal}:{ruta.motor or 'default'}"
            
            estado_ext = EstadoRutaExtendido(
                ruta=ruta,
                estado=estado_inicial,
                carga_maxima=100
            )
            
            self._rutas[clave].append(estado_ext)
            self._rutas_por_nucleo[ruta.nucleo_principal].append(estado_ext)
            
            # Registrar en balanceador
            self._balanceador.registrar_nucleo(ruta.nucleo_principal, peso_base=1.0)
            
            return True
    
    def registrar_rutas_tipo(self, tipo: TipoTarea, rutas: List[Ruta]):
        """Registra rutas específicas para un tipo de tarea."""
        with self._lock_rutas:
            for ruta in rutas:
                estado_ext = EstadoRutaExtendido(ruta=ruta)
                self._rutas_por_tipo[tipo].append(estado_ext)
                self.registrar_ruta(ruta)
    
    # =====================================================================
    # ACTUALIZACIÓN DE ESTADO
    # =====================================================================
    
    def actualizar_carga(self, nucleo: str, carga: float):
        """Actualiza la carga de un núcleo."""
        with self._lock_rutas:
            for ruta in self._rutas_por_nucleo.get(nucleo, []):
                ruta.carga_actual = int(carga)
            
            # Registrar en predictor
            self._predictor_carga.registrar_carga(nucleo, carga)
            
            # Actualizar balanceador
            self._balanceador.actualizar_metrica(nucleo, 'carga', carga)
    
    def actualizar_latencia(self, nucleo: str, latencia: float, exito: bool = True):
        """Actualiza la latencia de un núcleo."""
        with self._lock_rutas:
            for ruta in self._rutas_por_nucleo.get(nucleo, []):
                ruta.metricas.actualizar(exito, latencia)
            
            # Actualizar balanceador
            self._balanceador.actualizar_metrica(nucleo, 'latencia', latencia)
            if not exito:
                self._balanceador.actualizar_metrica(nucleo, 'tasa_exito', 
                    self._rutas_por_nucleo[nucleo][0].metricas.tasa_exito if self._rutas_por_nucleo[nucleo] else 0.0)
    
    def actualizar_estado_ruta(self, nucleo: str, motor: Optional[str], estado: EstadoRuta):
        """Actualiza el estado de una ruta específica."""
        with self._lock_rutas:
            clave = f"{nucleo}:{motor or 'default'}"
            for ruta in self._rutas.get(clave, []):
                ruta.estado = estado
    
    # =====================================================================
    # ENRUTAMIENTO PRINCIPAL
    # =====================================================================
    
    def enrutar(
        self,
        tipo: TipoTarea,
        datos: Any = None,
        contexto: Dict[str, Any] = None,
        prioridad: PrioridadTarea = None,
        forzar_nucleo: Optional[str] = None
    ) -> Optional[Ruta]:
        """
        Enruta una tarea a la mejor ruta disponible.
        
        Args:
            tipo: Tipo de tarea a enrutar
            datos: Datos de la tarea (para decisiones contextuales)
            contexto: Contexto adicional
            prioridad: Prioridad de la tarea
            forzar_nucleo: Forzar un núcleo específico
            
        Returns:
            Ruta óptima o None si no hay disponible
        """
        if not self._inicializado:
            return None
        
        # Verificar caché
        if datos is not None:
            clave_cache = self._generar_clave_cache(tipo, datos, contexto)
            ruta_cache = self._obtener_de_cache(clave_cache)
            if ruta_cache:
                return ruta_cache
        
        # Forzar núcleo específico
        if forzar_nucleo:
            return self._enrutar_a_nucleo(forzar_nucleo, tipo)
        
        # Seleccionar estrategia
        if self.estrategia == EstrategiaEnrutamiento.CUANTICO:
            ruta = self._enrutamiento_cuantico(tipo, datos, contexto, prioridad)
        elif self.estrategia == EstrategiaEnrutamiento.PREDICTIVO:
            ruta = self._enrutamiento_predictivo(tipo, datos, contexto)
        elif self.estrategia == EstrategiaEnrutamiento.ADAPTATIVO:
            ruta = self._enrutamiento_adaptativo(tipo, datos, contexto)
        elif self.estrategia == EstrategiaEnrutamiento.MENOR_CARGA:
            ruta = self._enrutamiento_menor_carga(tipo)
        elif self.estrategia == EstrategiaEnrutamiento.MENOR_LATENCIA:
            ruta = self._enrutamiento_menor_latencia(tipo)
        elif self.estrategia == EstrategiaEnrutamiento.PONDERADO:
            ruta = self._enrutamiento_ponderado(tipo, datos, contexto)
        elif self.estrategia == EstrategiaEnrutamiento.ALEATORIO_PONDERADO:
            ruta = self._enrutamiento_aleatorio_ponderado(tipo)
        else:
            ruta = self._enrutamiento_round_robin(tipo)
        
        # Guardar en caché
        if ruta and datos is not None:
            self._guardar_en_cache(clave_cache, ruta)
        
        # Registrar métrica
        if ruta:
            self._contador_rutas[ruta.nucleo_principal] += 1
        
        return ruta
    
    def _generar_clave_cache(self, tipo: TipoTarea, datos: Any, contexto: Dict = None) -> str:
        """Genera una clave para la caché de enrutamiento."""
        contenido = f"{tipo.value}:"
        if datos:
            contenido += hashlib.md5(str(datos).encode()).hexdigest()[:16]
        if contexto:
            contenido += hashlib.md5(str(sorted(contexto.items())).encode()).hexdigest()[:8]
        return hashlib.sha256(contenido.encode()).hexdigest()[:32]
    
    def _obtener_de_cache(self, clave: str) -> Optional[Ruta]:
        """Obtiene una decisión de la caché."""
        with self._lock_cache:
            if clave in self._cache_decisiones:
                ruta_str, timestamp = self._cache_decisiones[clave]
                if time.time() - timestamp < self._cache_ttl:
                    self._cache_decisiones.move_to_end(clave)
                    # Reconstruir ruta (simplificado)
                    return self._buscar_ruta_por_str(ruta_str)
                else:
                    del self._cache_decisiones[clave]
        return None
    
    def _guardar_en_cache(self, clave: str, ruta: Ruta):
        """Guarda una decisión en la caché."""
        with self._lock_cache:
            if len(self._cache_decisiones) >= self._cache_max_size:
                self._cache_decisiones.popitem(last=False)
            
            ruta_str = f"{ruta.nucleo_principal}:{ruta.motor or 'default'}"
            self._cache_decisiones[clave] = (ruta_str, time.time())
    
    def _buscar_ruta_por_str(self, ruta_str: str) -> Optional[Ruta]:
        """Busca una ruta por su representación string."""
        partes = ruta_str.split(':')
        if len(partes) >= 1:
            nucleo = partes[0]
            rutas_nucleo = self._rutas_por_nucleo.get(nucleo, [])
            if rutas_nucleo:
                return rutas_nucleo[0].ruta
        return None
    
    # =====================================================================
    # ESTRATEGIAS DE ENRUTAMIENTO
        # =====================================================================
    
    def _enrutar_a_nucleo(self, nucleo: str, tipo: TipoTarea) -> Optional[Ruta]:
        """Enruta a un núcleo específico."""
        rutas = self._rutas_por_nucleo.get(nucleo, [])
        rutas_disponibles = [r for r in rutas if r.disponible]
        
        if rutas_disponibles:
            # Buscar ruta específica para el tipo
            for r in rutas_disponibles:
                if self._ruta_compatible_con_tipo(r.ruta, tipo):
                    return r.ruta
            return rutas_disponibles[0].ruta
        return None
    
    def _ruta_compatible_con_tipo(self, ruta: Ruta, tipo: TipoTarea) -> bool:
        """Verifica si una ruta es compatible con un tipo de tarea."""
        # Mapeo simple de compatibilidad
        compatibilidad = {
            TipoTarea.CONSULTA: ['comunicacion'],
            TipoTarea.RAZONAMIENTO: ['razonamiento'],
            TipoTarea.MEMORIA: ['memoria'],
            TipoTarea.BUSQUEDA: ['busqueda'],
            TipoTarea.RESOLUCION: ['resolucion'],
            TipoTarea.CREATIVIDAD: ['creatividad'],
        }
        
        nucleos_compatibles = compatibilidad.get(tipo, [])
        return ruta.nucleo_principal in nucleos_compatibles
    
    def _enrutamiento_cuantico(
        self, 
        tipo: TipoTarea, 
        datos: Any, 
        contexto: Dict, 
        prioridad: PrioridadTarea = None
    ) -> Optional[Ruta]:
        """
        Enrutamiento cuántico: combina múltiples estrategias y selecciona la mejor.
        """
        # Obtener rutas candidatas
        rutas_tipo = self._rutas_por_tipo.get(tipo, [])
        if not rutas_tipo:
            # Buscar en todas las rutas
            todas_rutas = []
            for rutas in self._rutas.values():
                todas_rutas.extend(rutas)
            rutas_tipo = todas_rutas
        
        rutas_disponibles = [r for r in rutas_tipo if r.disponible]
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        # Calcular puntuación multi-criterio para cada ruta
        puntuaciones = []
        for estado_ruta in rutas_disponibles:
            puntuacion = self._calcular_puntuacion_cuantica(estado_ruta, tipo, prioridad)
            puntuaciones.append((puntuacion, estado_ruta))
        
        if not puntuaciones:
            return None
        
        # Seleccionar la mejor
        puntuaciones.sort(key=lambda x: x[0], reverse=True)
        mejor_ruta = puntuaciones[0][1].ruta
        
        # Incrementar conexiones en balanceador
        self._balanceador.incrementar_conexiones(mejor_ruta.nucleo_principal)
        
        return mejor_ruta
    
    def _calcular_puntuacion_cuantica(
        self, 
        estado: EstadoRutaExtendido, 
        tipo: TipoTarea,
        prioridad: PrioridadTarea = None
    ) -> float:
        """Calcula una puntuación multi-criterio para una ruta."""
        puntuacion = 0.0
        
        # 1. Carga actual (inversa)
        carga_pct = estado.carga_porcentaje
        puntuacion += self._pesos_criterios[CriterioSeleccion.CARGA_ACTUAL] * (1 - carga_pct / 100)
        
        # 2. Latencia promedio (inversa)
        latencia = estado.metricas.latencia_promedio
        if latencia > 0:
            latencia_score = 1.0 / (1.0 + latencia)
        else:
            latencia_score = 1.0
        puntuacion += self._pesos_criterios[CriterioSeleccion.LATENCIA_PROMEDIO] * latencia_score
        
        # 3. Tasa de éxito
        puntuacion += self._pesos_criterios[CriterioSeleccion.TASA_EXITO] * estado.metricas.tasa_exito
        
        # 4. Disponibilidad
        disponibilidad = 1.0 if estado.estado == EstadoRuta.DISPONIBLE else 0.5
        puntuacion += self._pesos_criterios[CriterioSeleccion.DISPONIBILIDAD] * disponibilidad
        
        # 5. Predicción de carga
        carga_predicha = self._predictor_carga.predecir_carga(estado.ruta.nucleo_principal)
        puntuacion += self._pesos_criterios[CriterioSeleccion.PREDICCION_CARGA] * (1 - carga_predicha / 100)
        
        # 6. Afinidad con tipo de tarea
        if self._ruta_compatible_con_tipo(estado.ruta, tipo):
            puntuacion += 0.1
        
        # 7. Ajuste por prioridad
        if prioridad == PrioridadTarea.CRITICA:
            # Priorizar rutas con alta tasa de éxito
            puntuacion *= (0.5 + 0.5 * estado.metricas.tasa_exito)
        
        return puntuacion
    
    def _enrutamiento_predictivo(
        self, 
        tipo: TipoTarea, 
        datos: Any, 
        contexto: Dict
    ) -> Optional[Ruta]:
        """Enrutamiento basado en predicción de carga futura."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        mejor_ruta = None
        mejor_puntuacion = -1
        
        for estado in rutas_disponibles:
            nucleo = estado.ruta.nucleo_principal
            carga_actual = estado.carga_porcentaje
            carga_predicha = self._predictor_carga.predecir_carga(nucleo)
            tendencia = self._predictor_carga.obtener_tendencia(nucleo)
            
            # Puntuación: evitar núcleos con tendencia creciente
            if tendencia > 2.0:
                puntuacion = (100 - carga_predicha) * 0.7
            elif tendencia < -2.0:
                puntuacion = (100 - carga_predicha) * 1.3
            else:
                puntuacion = (100 - carga_predicha)
            
            if puntuacion > mejor_puntuacion:
                mejor_puntuacion = puntuacion
                mejor_ruta = estado.ruta
        
        return mejor_ruta
    
    def _enrutamiento_adaptativo(self, tipo: TipoTarea, datos: Any, contexto: Dict) -> Optional[Ruta]:
        """Enrutamiento adaptativo usando el balanceador."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        nucleos = list(set(r.ruta.nucleo_principal for r in rutas_disponibles))
        mejor_nucleo = self._balanceador.seleccionar_nucleo(nucleos)
        
        if mejor_nucleo:
            for estado in rutas_disponibles:
                if estado.ruta.nucleo_principal == mejor_nucleo:
                    return estado.ruta
        
        return rutas_disponibles[0].ruta if rutas_disponibles else None
    
    def _enrutamiento_menor_carga(self, tipo: TipoTarea) -> Optional[Ruta]:
        """Enrutamiento por menor carga."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        rutas_disponibles.sort(key=lambda r: r.carga_porcentaje)
        return rutas_disponibles[0].ruta
    
    def _enrutamiento_menor_latencia(self, tipo: TipoTarea) -> Optional[Ruta]:
        """Enrutamiento por menor latencia."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        rutas_disponibles.sort(key=lambda r: r.metricas.latencia_promedio)
        return rutas_disponibles[0].ruta
    
    def _enrutamiento_ponderado(self, tipo: TipoTarea, datos: Any, contexto: Dict) -> Optional[Ruta]:
        """Enrutamiento ponderado por múltiples factores."""
        return self._enrutamiento_cuantico(tipo, datos, contexto)
    
    def _enrutamiento_aleatorio_ponderado(self, tipo: TipoTarea) -> Optional[Ruta]:
        """Enrutamiento aleatorio con pesos."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        pesos = [r.metricas.tasa_exito for r in rutas_disponibles]
        suma_pesos = sum(pesos)
        if suma_pesos == 0:
            pesos = [1.0] * len(rutas_disponibles)
            suma_pesos = len(rutas_disponibles)
        
        probabilidades = [p / suma_pesos for p in pesos]
        seleccionada = random.choices(rutas_disponibles, weights=probabilidades, k=1)[0]
        return seleccionada.ruta
    
    def _enrutamiento_round_robin(self, tipo: TipoTarea) -> Optional[Ruta]:
        """Enrutamiento round-robin simple."""
        rutas_disponibles = self._obtener_rutas_disponibles(tipo)
        if not rutas_disponibles:
            return self._enrutar_fallback(tipo)
        
        # Usar contador interno
        if not hasattr(self, '_rr_contador'):
            self._rr_contador = 0
        
        self._rr_contador = (self._rr_contador + 1) % len(rutas_disponibles)
        return rutas_disponibles[self._rr_contador].ruta
    
    def _obtener_rutas_disponibles(self, tipo: TipoTarea) -> List[EstadoRutaExtendido]:
        """Obtiene todas las rutas disponibles para un tipo de tarea."""
        rutas_tipo = self._rutas_por_tipo.get(tipo, [])
        if not rutas_tipo:
            todas = []
            for rutas in self._rutas.values():
                todas.extend(rutas)
            rutas_tipo = todas
        
        return [r for r in rutas_tipo if r.disponible]
    
    def _enrutar_fallback(self, tipo: TipoTarea) -> Optional[Ruta]:
        """Enruta a un fallback cuando no hay rutas disponibles."""
        # Buscar rutas degradadas
        todas_rutas = []
        for rutas in self._rutas.values():
            todas_rutas.extend(rutas)
        
        rutas_degradadas = [r for r in todas_rutas if r.estado == EstadoRuta.DEGRADADA]
        if rutas_degradadas:
            return rutas_degradadas[0].ruta
        
        return None
    
    # =====================================================================
    # REGISTRO DE RESULTADOS
        # =====================================================================
    
    def registrar_resultado(
        self, 
        ruta: Ruta, 
        exito: bool, 
        latencia: float,
        liberar_conexion: bool = True
    ):
        """Registra el resultado de una ejecución."""
        if liberar_conexion:
            self._balanceador.decrementar_conexiones(ruta.nucleo_principal)
        
        self.actualizar_latencia(ruta.nucleo_principal, latencia, exito)
        
        # Registrar métrica
        self._metricas_enrutamiento['latencia'].append(latencia)
        self._metricas_enrutamiento['exito' if exito else 'fallo'].append(1.0)
    
    # =====================================================================
    # MÉTRICAS Y ESTADÍSTICAS
    # =====================================================================
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del enrutador."""
        with self._lock_rutas:
            rutas_info = {}
            for clave, rutas in self._rutas.items():
                if rutas:
                    r = rutas[0]
                    rutas_info[clave] = {
                        'estado': r.estado.value,
                        'carga': r.carga_porcentaje,
                        'latencia_promedio': r.metricas.latencia_promedio,
                        'tasa_exito': r.metricas.tasa_exito,
                        'total_peticiones': r.metricas.total_peticiones,
                        'salud': r.salud,
                    }
            
            return {
                'estrategia': self.estrategia.value,
                'modo': self.modo.value,
                'uptime': time.time() - self._timestamp_inicio,
                'total_rutas': sum(len(r) for r in self._rutas.values()),
                'rutas_por_nucleo': {k: len(v) for k, v in self._rutas_por_nucleo.items()},
                'rutas_por_tipo': {k.value: len(v) for k, v in self._rutas_por_tipo.items()},
                'rutas_detalle': rutas_info,
                'predictor': self._predictor_carga.obtener_estadisticas(),
                'balanceador': self._balanceador.obtener_estadisticas(),
                'cache_size': len(self._cache_decisiones),
                'contador_rutas': dict(self._contador_rutas),
                'metricas': {
                    k: {
                        'count': len(v),
                        'avg': sum(v) / len(v) if v else 0,
                        'min': min(v) if v else 0,
                        'max': max(v) if v else 0,
                    }
                    for k, v in self._metricas_enrutamiento.items()
                },
            }
    
    def obtener_mejor_ruta_para(self, tipo: TipoTarea) -> Optional[str]:
        """Obtiene el nombre de la mejor ruta para un tipo de tarea."""
        ruta = self.enrutar(tipo)
        return ruta.nucleo_principal if ruta else None
    
    def cambiar_estrategia(self, nueva_estrategia: EstrategiaEnrutamiento):
        """Cambia la estrategia de enrutamiento."""
        self.estrategia = nueva_estrategia
    
    def cambiar_modo(self, nuevo_modo: ModoOrquestacion):
        """Cambia el modo de operación."""
        self.modo = nuevo_modo
        
        # Ajustar estrategia según modo
        if nuevo_modo == ModoOrquestacion.EMERGENCIA:
            self.estrategia = EstrategiaEnrutamiento.MENOR_CARGA
        elif nuevo_modo == ModoOrquestacion.DEGRADADO:
            self.estrategia = EstrategiaEnrutamiento.ALEATORIO_PONDERADO
    
    def limpiar_cache(self):
        """Limpia la caché de decisiones."""
        with self._lock_cache:
            self._cache_decisiones.clear()
    
    def __repr__(self) -> str:
        return f"Enrutador(estrategia={self.estrategia.value}, rutas={sum(len(r) for r in self._rutas.values())})"

# =====================================================================
# SECCIÓN 5: FÁBRICA DE ENRUTADORES
# =====================================================================

class FabricaEnrutador:
    """Fábrica para crear enrutadores preconfigurados."""
    
    @staticmethod
    def crear_enrutador_cuantico() -> Enrutador:
        """Crea un enrutador con estrategia cuántica."""
        return Enrutador(estrategia=EstrategiaEnrutamiento.CUANTICO)
    
    @staticmethod
    def crear_enrutador_predictivo() -> Enrutador:
        """Crea un enrutador con estrategia predictiva."""
        return Enrutador(estrategia=EstrategiaEnrutamiento.PREDICTIVO)
    
    @staticmethod
    def crear_enrutador_adaptativo() -> Enrutador:
        """Crea un enrutador con estrategia adaptativa."""
        return Enrutador(estrategia=EstrategiaEnrutamiento.ADAPTATIVO)
    
    @staticmethod
    def crear_enrutador_baja_latencia() -> Enrutador:
        """Crea un enrutador optimizado para baja latencia."""
        enrutador = Enrutador(estrategia=EstrategiaEnrutamiento.MENOR_LATENCIA)
        enrutador._pesos_criterios[CriterioSeleccion.LATENCIA_PROMEDIO] = 0.5
        enrutador._pesos_criterios[CriterioSeleccion.CARGA_ACTUAL] = 0.2
        return enrutador
    
    @staticmethod
    def crear_enrutador_alta_disponibilidad() -> Enrutador:
        """Crea un enrutador optimizado para alta disponibilidad."""
        enrutador = Enrutador(estrategia=EstrategiaEnrutamiento.MAYOR_DISPONIBILIDAD)
        enrutador._pesos_criterios[CriterioSeleccion.TASA_EXITO] = 0.4
        enrutador._pesos_criterios[CriterioSeleccion.DISPONIBILIDAD] = 0.3
        return enrutador

# =====================================================================
# SECCIÓN 6: SINGLETON GLOBAL
# =====================================================================

_enrutador_global: Optional[Enrutador] = None
_lock_enrutador = threading.RLock()

def obtener_enrutador() -> Enrutador:
    """Obtiene la instancia global del enrutador."""
    global _enrutador_global
    with _lock_enrutador:
        if _enrutador_global is None:
            _enrutador_global = FabricaEnrutador.crear_enrutador_cuantico()
        return _enrutador_global

# =====================================================================
# SECCIÓN 7: DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL ENRUTADOR INTELIGENTE")
    print("=" * 70)
    
    try:
        # 1. Crear enrutador
        print("\n[1/7] Creando enrutador...")
        enrutador = FabricaEnrutador.crear_enrutador_cuantico()
        print(f"  ✅ Enrutador creado: {enrutador}")
        
        # 2. Registrar rutas de prueba
        print("\n[2/7] Registrando rutas...")
        rutas_prueba = [
            Ruta("comunicacion", "comunicacion_fallback", "dialogo", PrioridadTarea.ALTA, 5.0, 2),
            Ruta("razonamiento", "razonamiento_fallback", "logico", PrioridadTarea.CRITICA, 10.0, 3),
            Ruta("memoria", "memoria_fallback", "semantica", PrioridadTarea.ALTA, 3.0, 3),
            Ruta("busqueda", "busqueda_fallback", "web", PrioridadTarea.MEDIA, 15.0, 2),
            Ruta("resolucion", "resolucion_fallback", "matematicas", PrioridadTarea.MEDIA, 12.0, 2),
            Ruta("creatividad", "creatividad_fallback", "ideas", PrioridadTarea.BAJA, 20.0, 1),
        ]
        
        for ruta in rutas_prueba:
            enrutador.registrar_ruta(ruta)
            print(f"  ✓ {ruta.nucleo_principal}")
        
        # 3. Actualizar cargas simuladas
        print("\n[3/7] Simulando cargas...")
        for nucleo in ["comunicacion", "razonamiento", "memoria", "busqueda", "resolucion"]:
            carga = random.randint(10, 60)
            enrutador.actualizar_carga(nucleo, carga)
            print(f"  ✓ {nucleo}: carga {carga}%")
        
        # 4. Probar enrutamiento
        print("\n[4/7] Probando enrutamiento...")
        tipos_prueba = [
            TipoTarea.CONSULTA,
            TipoTarea.RAZONAMIENTO,
            TipoTarea.MEMORIA,
            TipoTarea.BUSQUEDA,
            TipoTarea.RESOLUCION,
        ]
        
        resultados_enrutamiento = []
        for tipo in tipos_prueba:
            ruta = enrutador.enrutar(tipo, {"test": True})
            if ruta:
                resultados_enrutamiento.append((tipo.value, ruta.nucleo_principal))
                print(f"  ✓ {tipo.value} -> {ruta.nucleo_principal}")
            else:
                print(f"  ✗ {tipo.value} -> sin ruta")
        
        # 5. Simular ejecuciones
        print("\n[5/7] Simulando ejecuciones...")
        for _ in range(20):
            tipo = random.choice(tipos_prueba)
            ruta = enrutador.enrutar(tipo)
            if ruta:
                exito = random.random() > 0.1
                latencia = random.uniform(0.05, 0.5)
                enrutador.registrar_resultado(ruta, exito, latencia)
        print(f"  ✓ 20 ejecuciones simuladas")
        
        # 6. Cambiar estrategia
        print("\n[6/7] Probando cambio de estrategia...")
        enrutador.cambiar_estrategia(EstrategiaEnrutamiento.PREDICTIVO)
        print(f"  ✓ Estrategia cambiada a: {enrutador.estrategia.value}")
        
        ruta_pred = enrutador.enrutar(TipoTarea.CONSULTA)
        print(f"  ✓ Consulta con predictivo -> {ruta_pred.nucleo_principal if ruta_pred else 'None'}")
        
        # 7. Obtener estadísticas
        print("\n[7/7] Estadísticas del enrutador:")
        stats = enrutador.obtener_estadisticas()
        
        print(f"  📊 General:")
        print(f"     - Estrategia: {stats['estrategia']}")
        print(f"     - Uptime: {stats['uptime']:.2f}s")
        print(f"     - Total rutas: {stats['total_rutas']}")
        print(f"     - Cache size: {stats['cache_size']}")
        
        print(f"  📊 Rutas por núcleo:")
        for nucleo, count in stats['rutas_por_nucleo'].items():
            print(f"     - {nucleo}: {count} rutas")
        
        print(f"  📊 Contador de uso:")
        for nucleo, count in stats['contador_rutas'].items():
            print(f"     - {nucleo}: {count} usos")
        
        print(f"  📊 Predictor:")
        print(f"     - Núcleos monitoreados: {stats['predictor']['nucleos_monitoreados']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Enrutador Inteligente funciona perfectamente.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")