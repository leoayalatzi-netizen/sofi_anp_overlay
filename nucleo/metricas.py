#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Métricas (El Ojo Cuántico de la Observabilidad)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de recolección,
# agregación y análisis de métricas que trasciende los simples
# contadores. Incluye histograms, resúmenes, percentiles, series
# temporales, y exportación a múltiples destinos.
# =====================================================================

import sys
import os
import time
import uuid
import threading
import asyncio
import json
import math
import hashlib
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict, Counter
from functools import wraps, lru_cache, total_ordering
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import traceback

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from ..bus_eventos import Evento, TipoEvento, PrioridadEvento, publicar
except ImportError:
    @dataclass
    class Evento:
        tipo: str = ""
        datos: Any = None
        origen: str = ""
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: float = field(default_factory=time.time)
        prioridad: int = 3
    
    class TipoEvento:
        METRICA_REGISTRADA = "metrica.registrada"
        METRICA_ALERTA = "metrica.alerta"
        METRICA_UMBRAL_SUPERADO = "metrica.umbral_superado"
    
    class PrioridadEvento(IntEnum):
        ALTA = 1
        MEDIA = 2
        BAJA = 3
    
    def publicar(tipo, datos=None, origen="", prioridad=2, **kwargs):
        pass

try:
    from servicios.base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

# =====================================================================
# ENUMERACIONES FUNDAMENTALES
# =====================================================================

class TipoMetrica(Enum):
    """Tipos de métricas soportadas."""
    CONTADOR = "contador"           # Solo incrementa
    MEDIDOR = "medidor"             # Valor instantáneo (sube/baja)
    HISTOGRAMA = "histograma"       # Distribución de valores
    RESUMEN = "resumen"             # Resumen estadístico
    SERIE_TEMPORAL = "serie_temporal"  # Valores en el tiempo
    INDICADOR = "indicador"         # Valor booleano (0/1)
    GAUGE = "gauge"                 # Valor que puede subir/bajar

class UnidadMetrica(Enum):
    """Unidades de medida para métricas."""
    NINGUNA = ""
    SEGUNDOS = "s"
    MILISEGUNDOS = "ms"
    MICROSEGUNDOS = "µs"
    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    PORCENTAJE = "%"
    CONTADOR = "count"
    TASA = "rate"
    OPERACIONES_POR_SEGUNDO = "ops/s"
    PETICIONES_POR_SEGUNDO = "req/s"

class EstadoMetrica(Enum):
    """Estados de una métrica."""
    ACTIVA = "activa"
    PAUSADA = "pausada"
    ARCHIVADA = "archivada"
    CORRUPTA = "corrupta"

class NivelAlerta(IntEnum):
    """Niveles de alerta para umbrales."""
    INFO = 0
    ADVERTENCIA = 1
    PRECAUCION = 2
    PELIGRO = 3
    CRITICO = 4

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class UmbralMetrica:
    """Define umbrales para generar alertas."""
    nombre: str = ""
    valor_min: Optional[float] = None
    valor_max: Optional[float] = None
    nivel: NivelAlerta = NivelAlerta.ADVERTENCIA
    mensaje: str = ""
    accion: Optional[Callable] = None
    cooldown: float = 60.0  # Segundos entre alertas
    _ultima_alerta: float = field(default=0.0, repr=False)
    
    def evaluar(self, valor: float) -> bool:
        """Evalúa si el valor cruza el umbral."""
        if self.valor_min is not None and valor < self.valor_min:
            return True
        if self.valor_max is not None and valor > self.valor_max:
            return True
        return False
    
    def puede_alertar(self) -> bool:
        """Verifica si ha pasado el cooldown."""
        ahora = time.time()
        if ahora - self._ultima_alerta >= self.cooldown:
            self._ultima_alerta = ahora
            return True
        return False

@dataclass
class PuntoMetrica:
    """Un punto individual en una serie temporal."""
    valor: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metadatos: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EstadisticasMetrica:
    """Estadísticas acumuladas de una métrica."""
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    mean: float = 0.0
    variance: float = 0.0
    stddev: float = 0.0
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    last: float = 0.0
    first_timestamp: float = 0.0
    last_timestamp: float = 0.0

# =====================================================================
# MÉTRICA BASE (ABSTRACTA)
# =====================================================================

class Metrica(ABC):
    """Clase base abstracta para todas las métricas."""
    
    def __init__(self, nombre: str, descripcion: str = "", 
                 unidad: UnidadMetrica = UnidadMetrica.NINGUNA,
                 tags: Dict[str, str] = None,
                 umbrales: List[UmbralMetrica] = None):
        self.id = str(uuid.uuid4())
        self.nombre = nombre
        self.descripcion = descripcion
        self.unidad = unidad
        self.tags = tags or {}
        self.umbrales = umbrales or []
        self.estado = EstadoMetrica.ACTIVA
        self.created_at = time.time()
        self._lock = threading.RLock()
        self._observadores: List[Callable] = []
    
    @abstractmethod
    def tipo(self) -> TipoMetrica:
        """Retorna el tipo de métrica."""
        pass
    
    @abstractmethod
    def obtener_valor(self) -> Any:
        """Obtiene el valor actual de la métrica."""
        pass
    
    @abstractmethod
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        """Obtiene estadísticas acumuladas."""
        pass
    
    def _verificar_umbrales(self, valor: float):
        """Verifica y dispara alertas por umbrales."""
        for umbral in self.umbrales:
            if umbral.evaluar(valor) and umbral.puede_alertar():
                self._disparar_alerta(umbral, valor)
    
    def _disparar_alerta(self, umbral: UmbralMetrica, valor: float):
        """Dispara una alerta por umbral superado."""
        alerta = {
            'metrica_id': self.id,
            'metrica_nombre': self.nombre,
            'umbral': umbral.nombre,
            'nivel': umbral.nivel.name,
            'valor': valor,
            'mensaje': umbral.mensaje or f"{self.nombre} = {valor}",
            'timestamp': time.time(),
        }
        
        try:
            publicar(TipoEvento.METRICA_ALERTA, alerta, origen="metricas", 
                    prioridad=PrioridadEvento.ALTA if umbral.nivel >= NivelAlerta.PELIGRO else PrioridadEvento.MEDIA)
        except Exception:
            pass
        
        if umbral.accion:
            try:
                umbral.accion(alerta)
            except Exception:
                pass
    
    def suscribir(self, callback: Callable):
        """Suscribe un callback a cambios de la métrica."""
        self._observadores.append(callback)
    
    def _notificar(self, valor: Any):
        """Notifica a los observadores."""
        for callback in self._observadores:
            try:
                callback(self, valor)
            except Exception:
                pass
    
    def pausar(self):
        self.estado = EstadoMetrica.PAUSADA
    
    def reanudar(self):
        self.estado = EstadoMetrica.ACTIVA
    
    def archivar(self):
        self.estado = EstadoMetrica.ARCHIVADA
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'tipo': self.tipo().value,
            'unidad': self.unidad.value,
            'tags': self.tags,
            'estado': self.estado.value,
            'created_at': self.created_at,
        }

# =====================================================================
# CONTADOR (Counter)
# =====================================================================

class Contador(Metrica):
    """Métrica que solo puede incrementarse."""
    
    def __init__(self, nombre: str, **kwargs):
        super().__init__(nombre, **kwargs)
        self._valor: float = 0.0
        self._historico: deque = deque(maxlen=1000)
    
    def tipo(self) -> TipoMetrica:
        return TipoMetrica.CONTADOR
    
    def inc(self, delta: float = 1.0, tags: Dict[str, str] = None) -> float:
        """Incrementa el contador."""
        with self._lock:
            if self.estado != EstadoMetrica.ACTIVA:
                return self._valor
            
            self._valor += delta
            punto = PuntoMetrica(valor=self._valor, tags=tags)
            self._historico.append(punto)
            self._verificar_umbrales(self._valor)
            self._notificar(self._valor)
            return self._valor
    
    def obtener_valor(self) -> float:
        return self._valor
    
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        with self._lock:
            stats = EstadisticasMetrica()
            stats.count = len(self._historico)
            stats.last = self._valor
            if self._historico:
                stats.first_timestamp = self._historico[0].timestamp
                stats.last_timestamp = self._historico[-1].timestamp
            return stats
    
    def reset(self):
        """Resetea el contador a cero."""
        with self._lock:
            self._valor = 0.0
            self._historico.clear()

# =====================================================================
# MEDIDOR (Gauge)
# =====================================================================

class Medidor(Metrica):
    """Métrica que puede subir y bajar."""
    
    def __init__(self, nombre: str, valor_inicial: float = 0.0, **kwargs):
        super().__init__(nombre, **kwargs)
        self._valor: float = valor_inicial
        self._historico: deque = deque(maxlen=1000)
    
    def tipo(self) -> TipoMetrica:
        return TipoMetrica.MEDIDOR
    
    def set(self, valor: float, tags: Dict[str, str] = None) -> float:
        """Establece un nuevo valor."""
        with self._lock:
            if self.estado != EstadoMetrica.ACTIVA:
                return self._valor
            
            self._valor = valor
            punto = PuntoMetrica(valor=valor, tags=tags)
            self._historico.append(punto)
            self._verificar_umbrales(valor)
            self._notificar(valor)
            return self._valor
    
    def inc(self, delta: float = 1.0) -> float:
        """Incrementa el valor."""
        return self.set(self._valor + delta)
    
    def dec(self, delta: float = 1.0) -> float:
        """Decrementa el valor."""
        return self.set(self._valor - delta)
    
    def obtener_valor(self) -> float:
        return self._valor
    
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        with self._lock:
            stats = EstadisticasMetrica()
            valores = [p.valor for p in self._historico]
            if valores:
                stats.count = len(valores)
                stats.sum = sum(valores)
                stats.min = min(valores)
                stats.max = max(valores)
                stats.mean = stats.sum / stats.count
                stats.last = valores[-1]
                stats.first_timestamp = self._historico[0].timestamp
                stats.last_timestamp = self._historico[-1].timestamp
                
                if stats.count > 1:
                    variance = sum((v - stats.mean) ** 2 for v in valores) / stats.count
                    stats.variance = variance
                    stats.stddev = math.sqrt(variance)
            return stats

# =====================================================================
# HISTOGRAMA
# =====================================================================

class Histograma(Metrica):
    """Métrica que registra distribución de valores."""
    
    def __init__(self, nombre: str, buckets: List[float] = None, **kwargs):
        super().__init__(nombre, **kwargs)
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.buckets.sort()
        self._bucket_counts: Dict[float, int] = defaultdict(int)
        self._sum: float = 0.0
        self._count: int = 0
        self._min: float = float('inf')
        self._max: float = float('-inf')
        self._valores: deque = deque(maxlen=1000)
    
    def tipo(self) -> TipoMetrica:
        return TipoMetrica.HISTOGRAMA
    
    def observar(self, valor: float, tags: Dict[str, str] = None) -> None:
        """Registra una observación."""
        with self._lock:
            if self.estado != EstadoMetrica.ACTIVA:
                return
            
            self._count += 1
            self._sum += valor
            self._min = min(self._min, valor)
            self._max = max(self._max, valor)
            
            for bucket in self.buckets:
                if valor <= bucket:
                    self._bucket_counts[bucket] += 1
            
            self._valores.append(valor)
            self._verificar_umbrales(valor)
            self._notificar(valor)
    
    def obtener_valor(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'count': self._count,
                'sum': self._sum,
                'min': self._min if self._min != float('inf') else 0,
                'max': self._max if self._max != float('-inf') else 0,
                'avg': self._sum / self._count if self._count > 0 else 0,
                'buckets': dict(self._bucket_counts),
            }
    
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        with self._lock:
            stats = EstadisticasMetrica()
            stats.count = self._count
            stats.sum = self._sum
            stats.min = self._min if self._min != float('inf') else 0
            stats.max = self._max if self._max != float('-inf') else 0
            stats.mean = self._sum / self._count if self._count > 0 else 0
            stats.last = self._valores[-1] if self._valores else 0
            
            if len(self._valores) >= 100:
                valores_ordenados = sorted(self._valores)
                stats.p50 = valores_ordenados[int(len(valores_ordenados) * 0.5)]
                stats.p90 = valores_ordenados[int(len(valores_ordenados) * 0.9)]
                stats.p95 = valores_ordenados[int(len(valores_ordenados) * 0.95)]
                stats.p99 = valores_ordenados[int(len(valores_ordenados) * 0.99)]
            
            return stats

# =====================================================================
# RESUMEN (Summary)
# =====================================================================

class Resumen(Metrica):
    """Métrica que mantiene un resumen estadístico completo."""
    
    def __init__(self, nombre: str, ventana_tiempo: float = 3600.0, **kwargs):
        super().__init__(nombre, **kwargs)
        self.ventana_tiempo = ventana_tiempo
        self._valores: deque = deque()
        self._sum: float = 0.0
        self._count: int = 0
    
    def tipo(self) -> TipoMetrica:
        return TipoMetrica.RESUMEN
    
    def observar(self, valor: float, tags: Dict[str, str] = None) -> None:
        """Registra una observación."""
        with self._lock:
            if self.estado != EstadoMetrica.ACTIVA:
                return
            
            ahora = time.time()
            self._valores.append((ahora, valor))
            self._sum += valor
            self._count += 1
            
            while self._valores and ahora - self._valores[0][0] > self.ventana_tiempo:
                _, viejo = self._valores.popleft()
                self._sum -= viejo
                self._count -= 1
            
            self._verificar_umbrales(valor)
            self._notificar(valor)
    
    def obtener_valor(self) -> Dict[str, Any]:
        with self._lock:
            if self._count == 0:
                return {'count': 0, 'sum': 0, 'avg': 0, 'min': 0, 'max': 0}
            
            valores = [v for _, v in self._valores]
            valores_ordenados = sorted(valores)
            
            return {
                'count': self._count,
                'sum': self._sum,
                'avg': self._sum / self._count,
                'min': valores_ordenados[0],
                'max': valores_ordenados[-1],
                'p50': valores_ordenados[int(len(valores_ordenados) * 0.5)],
                'p90': valores_ordenados[int(len(valores_ordenados) * 0.9)],
                'p95': valores_ordenados[int(len(valores_ordenados) * 0.95)],
                'p99': valores_ordenados[int(len(valores_ordenados) * 0.99)],
            }
    
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        valor = self.obtener_valor()
        stats = EstadisticasMetrica()
        stats.count = valor['count']
        stats.sum = valor['sum']
        stats.min = valor['min']
        stats.max = valor['max']
        stats.mean = valor['avg']
        stats.p50 = valor['p50']
        stats.p90 = valor['p90']
        stats.p95 = valor['p95']
        stats.p99 = valor['p99']
        return stats

# =====================================================================
# INDICADOR (Boolean)
# =====================================================================

class Indicador(Metrica):
    """Métrica booleana (0/1) para estados."""
    
    def __init__(self, nombre: str, valor_inicial: bool = False, **kwargs):
        super().__init__(nombre, **kwargs)
        self._valor: bool = valor_inicial
        self._historico: deque = deque(maxlen=100)
    
    def tipo(self) -> TipoMetrica:
        return TipoMetrica.INDICADOR
    
    def set(self, valor: bool, tags: Dict[str, str] = None) -> bool:
        with self._lock:
            if self.estado != EstadoMetrica.ACTIVA:
                return self._valor
            
            anterior = self._valor
            self._valor = valor
            self._historico.append((time.time(), valor))
            self._notificar(valor)
            
            if anterior != valor:
                self._verificar_umbrales(1.0 if valor else 0.0)
            
            return self._valor
    
    def activar(self) -> bool:
        return self.set(True)
    
    def desactivar(self) -> bool:
        return self.set(False)
    
    def toggle(self) -> bool:
        return self.set(not self._valor)
    
    def obtener_valor(self) -> bool:
        return self._valor
    
    def obtener_estadisticas(self) -> EstadisticasMetrica:
        with self._lock:
            stats = EstadisticasMetrica()
            stats.count = len(self._historico)
            stats.last = 1.0 if self._valor else 0.0
            if self._historico:
                stats.first_timestamp = self._historico[0][0]
                stats.last_timestamp = self._historico[-1][0]
            return stats

# =====================================================================
# RECOLECTOR DE MÉTRICAS (SINGLETON)
# =====================================================================

class RecolectorMetricas:
    """
    Recolector central de métricas de ANP.
    Implementa patrón Singleton thread-safe.
    """
    
    _instancia: Optional['RecolectorMetricas'] = None
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
            
            self._metricas: Dict[str, Metrica] = {}
            self._metricas_por_tipo: Dict[TipoMetrica, List[str]] = defaultdict(list)
            self._metricas_por_tag: Dict[str, List[str]] = defaultdict(list)
            
            self._flush_interval = 60.0
            self._persistir_habilitado = True
            self._eventos_habilitados = True
            self._flush_activo = False
            self._hilo_flush: Optional[threading.Thread] = None
            
            self._inicializar_metricas_sistema()
            self._iniciar_flush()
            
            self._inicializado = True
    
    def _inicializar_metricas_sistema(self):
        """Inicializa métricas predefinidas del sistema."""
        self.contador("sistema.eventos_procesados", "Total de eventos procesados")
        self.contador("sistema.errores", "Total de errores del sistema")
        self.medidor("sistema.memoria_usada", "Memoria en uso", unidad=UnidadMetrica.MEGABYTES)
        self.medidor("sistema.cpu_uso", "CPU en uso", unidad=UnidadMetrica.PORCENTAJE)
        self.histograma("sistema.latencia", "Latencia de operaciones", unidad=UnidadMetrica.MILISEGUNDOS)
        self.indicador("sistema.saludable", "Estado de salud del sistema")
    
    def _iniciar_flush(self):
        """Inicia el hilo de flush periódico."""
        self._flush_activo = True
        self._hilo_flush = threading.Thread(target=self._bucle_flush, daemon=True)
        self._hilo_flush.start()
    
    def _bucle_flush(self):
        """Bucle de persistencia periódica."""
        while self._flush_activo:
            time.sleep(self._flush_interval)
            self._flush_a_bd()
    
    def _flush_a_bd(self):
        """Persiste métricas en la base de datos."""
        if not self._persistir_habilitado:
            return
        
        try:
            bd = obtener_bd()
            if bd:
                for nombre, metrica in self._metricas.items():
                    if metrica.estado == EstadoMetrica.ACTIVA:
                        valor = metrica.obtener_valor()
                        bd.guardar_metrica(
                            nombre, 
                            valor if isinstance(valor, (int, float)) else json.dumps(valor),
                            metrica.unidad.value,
                            metrica.tags
                        )
        except Exception:
            pass
    
    # ===== FACTORY METHODS =====
    
    def contador(self, nombre: str, descripcion: str = "", 
                 unidad: UnidadMetrica = UnidadMetrica.CONTADOR,
                 tags: Dict[str, str] = None) -> Contador:
        """Crea o obtiene un contador."""
        if nombre in self._metricas:
            metrica = self._metricas[nombre]
            if isinstance(metrica, Contador):
                return metrica
            raise TypeError(f"Métrica '{nombre}' ya existe con tipo {metrica.tipo().value}")
        
        metrica = Contador(nombre, descripcion=descripcion, unidad=unidad, tags=tags)
        self._registrar(nombre, metrica)
        return metrica
    
    def medidor(self, nombre: str, descripcion: str = "",
                valor_inicial: float = 0.0,
                unidad: UnidadMetrica = UnidadMetrica.NINGUNA,
                tags: Dict[str, str] = None) -> Medidor:
        """Crea o obtiene un medidor."""
        if nombre in self._metricas:
            metrica = self._metricas[nombre]
            if isinstance(metrica, Medidor):
                return metrica
            raise TypeError(f"Métrica '{nombre}' ya existe con tipo {metrica.tipo().value}")
        
        metrica = Medidor(nombre, descripcion=descripcion, valor_inicial=valor_inicial,
                         unidad=unidad, tags=tags)
        self._registrar(nombre, metrica)
        return metrica
    
    def histograma(self, nombre: str, descripcion: str = "",
                   buckets: List[float] = None,
                   unidad: UnidadMetrica = UnidadMetrica.NINGUNA,
                   tags: Dict[str, str] = None) -> Histograma:
        """Crea o obtiene un histograma."""
        if nombre in self._metricas:
            metrica = self._metricas[nombre]
            if isinstance(metrica, Histograma):
                return metrica
            raise TypeError(f"Métrica '{nombre}' ya existe con tipo {metrica.tipo().value}")
        
        metrica = Histograma(nombre, descripcion=descripcion, buckets=buckets,
                            unidad=unidad, tags=tags)
        self._registrar(nombre, metrica)
        return metrica
    
    def resumen(self, nombre: str, descripcion: str = "",
                ventana_tiempo: float = 3600.0,
                unidad: UnidadMetrica = UnidadMetrica.NINGUNA,
                tags: Dict[str, str] = None) -> Resumen:
        """Crea o obtiene un resumen."""
        if nombre in self._metricas:
            metrica = self._metricas[nombre]
            if isinstance(metrica, Resumen):
                return metrica
            raise TypeError(f"Métrica '{nombre}' ya existe con tipo {metrica.tipo().value}")
        
        metrica = Resumen(nombre, descripcion=descripcion, ventana_tiempo=ventana_tiempo,
                         unidad=unidad, tags=tags)
        self._registrar(nombre, metrica)
        return metrica
    
    def indicador(self, nombre: str, descripcion: str = "",
                  valor_inicial: bool = False,
                  tags: Dict[str, str] = None) -> Indicador:
        """Crea o obtiene un indicador."""
        if nombre in self._metricas:
            metrica = self._metricas[nombre]
            if isinstance(metrica, Indicador):
                return metrica
            raise TypeError(f"Métrica '{nombre}' ya existe con tipo {metrica.tipo().value}")
        
        metrica = Indicador(nombre, descripcion=descripcion, valor_inicial=valor_inicial, tags=tags)
        self._registrar(nombre, metrica)
        return metrica
    
    def _registrar(self, nombre: str, metrica: Metrica):
        """Registra una métrica en el recolector."""
        self._metricas[nombre] = metrica
        self._metricas_por_tipo[metrica.tipo()].append(nombre)
        for tag in metrica.tags:
            self._metricas_por_tag[tag].append(nombre)
    
    # ===== MÉTODOS DE CONSULTA =====
    
    def obtener(self, nombre: str) -> Optional[Metrica]:
        """Obtiene una métrica por nombre."""
        return self._metricas.get(nombre)
    
    def listar(self, tipo: Optional[TipoMetrica] = None, tag: Optional[str] = None) -> List[str]:
        """Lista métricas filtradas por tipo o tag."""
        if tipo:
            return self._metricas_por_tipo.get(tipo, [])
        if tag:
            return self._metricas_por_tag.get(tag, [])
        return list(self._metricas.keys())
    
    def obtener_todas(self) -> Dict[str, Metrica]:
        """Obtiene todas las métricas."""
        return self._metricas.copy()
    
    def obtener_valores(self) -> Dict[str, Any]:
        """Obtiene valores actuales de todas las métricas."""
        return {nombre: metrica.obtener_valor() for nombre, metrica in self._metricas.items()
                if metrica.estado == EstadoMetrica.ACTIVA}
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de todas las métricas."""
        return {
            'total_metricas': len(self._metricas),
            'por_tipo': {t.value: len(v) for t, v in self._metricas_por_tipo.items()},
            'metricas': {
                nombre: {
                    'tipo': m.tipo().value,
                    'unidad': m.unidad.value,
                    'estado': m.estado.value,
                    'valor': m.obtener_valor(),
                }
                for nombre, m in self._metricas.items()
            }
        }
    
    # ===== CONTROL =====
    
    def pausar_todas(self):
        """Pausa todas las métricas."""
        for metrica in self._metricas.values():
            metrica.pausar()
    
    def reanudar_todas(self):
        """Reanuda todas las métricas."""
        for metrica in self._metricas.values():
            metrica.reanudar()
    
    def detener(self):
        """Detiene el recolector."""
        self._flush_activo = False
        if self._hilo_flush:
            self._hilo_flush.join(timeout=5.0)
        self._flush_a_bd()
    
    def __getitem__(self, nombre: str) -> Metrica:
        metrica = self.obtener(nombre)
        if metrica is None:
            raise KeyError(f"Métrica no encontrada: {nombre}")
        return metrica
    
    def __contains__(self, nombre: str) -> bool:
        return nombre in self._metricas
    
    def __len__(self) -> int:
        return len(self._metricas)

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_recolector_global: Optional[RecolectorMetricas] = None

def obtener_recolector() -> RecolectorMetricas:
    """Obtiene la instancia global del recolector."""
    global _recolector_global
    if _recolector_global is None:
        _recolector_global = RecolectorMetricas()
    return _recolector_global

def contador(nombre: str, **kwargs) -> Contador:
    """Función rápida para crear/obtener un contador."""
    return obtener_recolector().contador(nombre, **kwargs)

def medidor(nombre: str, **kwargs) -> Medidor:
    """Función rápida para crear/obtener un medidor."""
    return obtener_recolector().medidor(nombre, **kwargs)

def histograma(nombre: str, **kwargs) -> Histograma:
    """Función rápida para crear/obtener un histograma."""
    return obtener_recolector().histograma(nombre, **kwargs)

def resumen(nombre: str, **kwargs) -> Resumen:
    """Función rápida para crear/obtener un resumen."""
    return obtener_recolector().resumen(nombre, **kwargs)

def indicador(nombre: str, **kwargs) -> Indicador:
    """Función rápida para crear/obtener un indicador."""
    return obtener_recolector().indicador(nombre, **kwargs)

# =====================================================================
# DECORADORES DE MÉTRICAS
# =====================================================================

def contar(nombre: str, delta: float = 1.0):
    """Decorador para contar invocaciones."""
    def decorador(func: Callable) -> Callable:
        metrica = contador(nombre)
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrica.inc(delta)
            return func(*args, **kwargs)
        return wrapper
    return decorador

def medir_tiempo(nombre: str):
    """Decorador para medir tiempo de ejecución."""
    def decorador(func: Callable) -> Callable:
        metrica = histograma(nombre, unidad=UnidadMetrica.MILISEGUNDOS)
        @wraps(func)
        def wrapper(*args, **kwargs):
            inicio = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                tiempo_ms = (time.time() - inicio) * 1000
                metrica.observar(tiempo_ms)
        return wrapper
    return decorador

def medir_estado(nombre: str):
    """Decorador para indicador de estado."""
    def decorador(func: Callable) -> Callable:
        metrica = indicador(nombre)
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrica.activar()
            try:
                return func(*args, **kwargs)
            except Exception:
                metrica.desactivar()
                raise
            finally:
                metrica.desactivar()
        return wrapper
    return decorador

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE MÉTRICAS")
    print("=" * 70)
    
    recolector = None
    
    try:
        print("\n[1/8] Inicializando recolector...")
        recolector = RecolectorMetricas()
        print(f"  ✅ Recolector inicializado con {len(recolector)} métricas de sistema")
        
        print("\n[2/8] Creando métricas personalizadas...")
        c = recolector.contador("test.contador", "Contador de prueba")
        m = recolector.medidor("test.medidor", "Medidor de prueba", valor_inicial=50)
        h = recolector.histograma("test.histograma", "Histograma de prueba", 
                                  buckets=[1, 5, 10, 25, 50, 100])
        r = recolector.resumen("test.resumen", "Resumen de prueba", ventana_tiempo=60)
        i = recolector.indicador("test.indicador", "Indicador de prueba")
        print(f"  ✅ 5 métricas creadas")
        
        print("\n[3/8] Registrando valores...")
        for _ in range(10):
            c.inc()
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            m.set(v)
        for v in [5, 12, 8, 45, 23, 67, 34, 89, 15, 42]:
            h.observar(v)
            r.observar(v)
        i.activar()
        print(f"  ✅ Valores registrados")
        
        print("\n[4/8] Leyendo valores...")
        print(f"  📊 Contador: {c.obtener_valor()}")
        print(f"  📊 Medidor: {m.obtener_valor()}")
        print(f"  📊 Histograma: count={h.obtener_valor()['count']}, avg={h.obtener_valor()['avg']:.2f}")
        print(f"  📊 Resumen: count={r.obtener_valor()['count']}, avg={r.obtener_valor()['avg']:.2f}")
        print(f"  📊 Indicador: {i.obtener_valor()}")
        
        print("\n[5/8] Probando decoradores...")
        
        @contar("test.decorador.contador")
        @medir_tiempo("test.decorador.tiempo")
        def funcion_de_prueba(n):
            time.sleep(0.01 * n)
            return n * 2
        
        for i in range(5):
            funcion_de_prueba(i)
        
        print(f"  ✅ Decoradores ejecutados")
        
        print("\n[6/8] Estadísticas del histograma...")
        stats_h = h.obtener_estadisticas()
        print(f"  📊 p50: {stats_h.p50:.2f}")
        print(f"  📊 p90: {stats_h.p90:.2f}")
        print(f"  📊 p95: {stats_h.p95:.2f}")
        print(f"  📊 p99: {stats_h.p99:.2f}")
        
        print("\n[7/8] Umbrales y alertas...")
        umbral = UmbralMetrica(
            nombre="test_umbral",
            valor_max=80,
            nivel=NivelAlerta.ADVERTENCIA,
            mensaje="Valor superó 80"
        )
        m.umbrales.append(umbral)
        m.set(85)
        m.set(90)
        print(f"  ✅ Umbral configurado y superado")
        
        print("\n[8/8] Resumen del recolector...")
        stats = recolector.obtener_estadisticas()
        print(f"  📊 Total métricas: {stats['total_metricas']}")
        print(f"  📊 Por tipo: {stats['por_tipo']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Métricas está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if recolector:
            print("\n🛑 Deteniendo recolector...")
            recolector.detener()
            print("   ✓ Recolector detenido")
    
    print("\n" + "=" * 70 + "\n")