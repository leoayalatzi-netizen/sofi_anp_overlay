#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Suscriptores (Los Receptores del Sistema Nervioso)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
import time
import uuid
import threading
import asyncio
import inspect
import traceback
import weakref
import queue
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator, Awaitable,
    Pattern
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto, Flag
from collections import defaultdict, deque, OrderedDict, Counter
from functools import wraps, partial, lru_cache
from abc import ABC, abstractmethod
import re
import json
import hashlib
import heapq
from datetime import datetime, timedelta

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .evento import Evento, EstadoEvento
except ImportError:
    class Evento:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    class EstadoEvento:
        CREADO = "creado"
        PROCESADO = "procesado"

try:
    from .tipos import TipoEvento
except ImportError:
    class TipoEvento:
        @classmethod
        def SISTEMA_INICIANDO(cls): return "sistema.iniciando"
        @classmethod
        def SISTEMA_LISTO(cls): return "sistema.listo"

try:
    from .prioridad import Prioridad, PrioridadBase
except ImportError:
    class PrioridadBase:
        COSMICA = -10
        CRITICA = 0
        ALTA = 1
        MEDIA = 3
        BAJA = 5
        DIFERIDA = 7
    
    class Prioridad:
        COSMICA = -10
        CRITICA = 0
        ALTA = 1
        MEDIA = 3
        BAJA = 5
        DIFERIDA = 7
        
        @classmethod
        def get_cosmica(cls): return cls.COSMICA
        @classmethod
        def get_critica(cls): return cls.CRITICA
        @classmethod
        def get_alta(cls): return cls.ALTA
        @classmethod
        def get_media(cls): return cls.MEDIA
        @classmethod
        def get_baja(cls): return cls.BAJA
        @classmethod
        def get_diferida(cls): return cls.DIFERIDA
        
        @classmethod
        def metadatos(cls, nivel):
            nombres = {
                -10: "CÓSMICA", 0: "CRÍTICA", 1: "ALTA", 
                3: "MEDIA", 5: "BAJA", 7: "DIFERIDA"
            }
            return type('Meta', (), {'nombre': nombres.get(nivel, f'NIVEL_{nivel}')})

# =====================================================================
# ENUMERACIONES AVANZADAS
# =====================================================================

class EstadoSuscriptor(Enum):
    """Estados posibles de un suscriptor."""
    INACTIVO = "inactivo"
    ACTIVO = "activo"
    DEGRADADO = "degradado"
    ESTRANGULADO = "estrangulado"
    PAUSADO = "pausado"
    RECUPERANDO = "recuperando"
    MUERTO = "muerto"

class ModoEjecucion(Enum):
    """Modos de ejecución del suscriptor."""
    SINCRONO = "sincrono"
    ASINCRONO = "asincrono"
    HILO_DEDICADO = "hilo_dedicado"
    COLA_PROPIA = "cola_propia"
    ADAPTATIVO = "adaptativo"

class PoliticaFallo(Enum):
    """Políticas cuando un suscriptor falla."""
    IGNORAR = "ignorar"
    REINTENTAR = "reintentar"
    DEGRADAR = "degradar"
    DESUSCRIBIR = "desuscribir"
    DEAD_LETTER = "dead_letter"

class TipoFiltro(Enum):
    """Tipos de filtros disponibles."""
    EXACTO = "exacto"
    PREFIJO = "prefijo"
    REGEX = "regex"
    FUNCION = "funcion"
    CONTEXTUAL = "contextual"
    JERARQUICO = "jerarquico"
    WILDCARD = "wildcard"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EstadisticasSuscriptor:
    """Estadísticas de rendimiento de un suscriptor."""
    eventos_recibidos: int = 0
    eventos_procesados: int = 0
    eventos_fallidos: int = 0
    tiempo_total_procesamiento: float = 0.0
    tiempo_promedio_ms: float = 0.0
    tiempo_max_ms: float = 0.0
    tiempo_min_ms: float = float('inf')
    ultimo_procesamiento: float = 0.0
    fallos_consecutivos: int = 0
    throttling_aplicado: int = 0
    dead_letters: int = 0
    
    def registrar_exito(self, tiempo_ms: float):
        self.eventos_recibidos += 1
        self.eventos_procesados += 1
        self.tiempo_total_procesamiento += tiempo_ms
        self.tiempo_promedio_ms = self.tiempo_total_procesamiento / self.eventos_procesados
        self.tiempo_max_ms = max(self.tiempo_max_ms, tiempo_ms)
        self.tiempo_min_ms = min(self.tiempo_min_ms, tiempo_ms)
        self.ultimo_procesamiento = time.time()
        self.fallos_consecutivos = 0
    
    def registrar_fallo(self):
        self.eventos_recibidos += 1
        self.eventos_fallidos += 1
        self.fallos_consecutivos += 1
        self.ultimo_procesamiento = time.time()
    
    def tasa_exito(self) -> float:
        if self.eventos_recibidos == 0:
            return 1.0
        return self.eventos_procesados / self.eventos_recibidos

@dataclass
class FiltroSuscripcion:
    """Filtro avanzado para suscripciones."""
    tipo: TipoFiltro
    patron: Union[str, Pattern, Callable]
    prioridad: int = 50
    condiciones: Optional[Dict[str, Any]] = None
    
    def coincide(self, tipo_evento: str, evento: Optional['Evento'] = None) -> bool:
        if self.tipo == TipoFiltro.EXACTO:
            return self.patron == tipo_evento
        elif self.tipo == TipoFiltro.PREFIJO:
            return tipo_evento.startswith(self.patron)
        elif self.tipo == TipoFiltro.REGEX:
            return bool(re.match(self.patron, tipo_evento))
        elif self.tipo == TipoFiltro.WILDCARD:
            patron_regex = self.patron.replace('.', r'\.').replace('*', '.*')
            return bool(re.match(f"^{patron_regex}$", tipo_evento))
        elif self.tipo == TipoFiltro.FUNCION:
            return self.patron(tipo_evento, evento)
        elif self.tipo == TipoFiltro.JERARQUICO:
            return tipo_evento.startswith(self.patron) or tipo_evento == self.patron
        elif self.tipo == TipoFiltro.CONTEXTUAL:
            if not evento or not self.condiciones:
                return False
            for clave, valor in self.condiciones.items():
                if hasattr(evento, clave):
                    if getattr(evento, clave) != valor:
                        return False
                elif hasattr(evento, 'metadatos') and evento.metadatos.get(clave) != valor:
                    return False
            return True
        return False

@dataclass
class ConfiguracionThrottling:
    """Configuración de throttling para suscriptores."""
    max_eventos_por_segundo: float = 100.0
    max_eventos_por_minuto: int = 1000
    max_eventos_por_hora: int = 10000
    bucket_tokens: int = 100
    tasa_recarga: float = 10.0
    politica_exceso: str = "rechazar"
    
    def __post_init__(self):
        self._tokens = self.bucket_tokens
        self._ultima_recarga = time.time()
        self._eventos_ventana: deque = deque()
    
    def permitir(self) -> bool:
        ahora = time.time()
        tiempo_transcurrido = ahora - self._ultima_recarga
        tokens_nuevos = tiempo_transcurrido * self.tasa_recarga
        self._tokens = min(self.bucket_tokens, self._tokens + tokens_nuevos)
        self._ultima_recarga = ahora
        
        while self._eventos_ventana and self._eventos_ventana[0] < ahora - 3600:
            self._eventos_ventana.popleft()
        
        eventos_hora = len(self._eventos_ventana)
        if eventos_hora >= self.max_eventos_por_hora:
            return False
        
        if self._tokens >= 1:
            self._tokens -= 1
            self._eventos_ventana.append(ahora)
            return True
        
        return False

# =====================================================================
# DEAD LETTER QUEUE
# =====================================================================

class DeadLetterQueue:
    """Cola para eventos que no pudieron ser procesados."""
    
    def __init__(self, capacidad: int = 1000):
        self._cola: deque = deque(maxlen=capacidad)
        self._lock = threading.RLock()
        self._total_encolados: int = 0
        self._total_procesados: int = 0
    
    def encolar(self, evento: 'Evento', suscriptor_id: str, error: str):
        with self._lock:
            entrada = {
                'id': str(uuid.uuid4()),
                'timestamp': time.time(),
                'evento': evento,
                'suscriptor_id': suscriptor_id,
                'error': error,
                'reintentos': 0,
                'estado': 'pendiente'
            }
            self._cola.append(entrada)
            self._total_encolados += 1
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            pendientes = sum(1 for e in self._cola if e['estado'] == 'pendiente')
            return {
                'total_encolados': self._total_encolados,
                'total_procesados': self._total_procesados,
                'pendientes': pendientes,
                'capacidad': self._cola.maxlen,
            }

# =====================================================================
# SUSCRIPTOR BASE (ABC)
# =====================================================================

class Suscriptor(ABC):
    """Clase abstracta base para todos los suscriptores del sistema."""
    
    _contador_global: ClassVar[int] = 0
    
    def __init__(self, 
                 suscriptor_id: Optional[str] = None,
                 nombre: str = "",
                 filtros: List[FiltroSuscripcion] = None,
                 prioridad: int = 3,
                 modo: ModoEjecucion = ModoEjecucion.ADAPTATIVO,
                 politica_fallo: PoliticaFallo = PoliticaFallo.DEGRADAR,
                 max_reintentos: int = 3,
                 throttling: Optional[ConfiguracionThrottling] = None):
        
        Suscriptor._contador_global += 1
        self._id = suscriptor_id or f"suscriptor_{Suscriptor._contador_global}"
        self.nombre = nombre or self._id
        self.filtros = filtros or [FiltroSuscripcion(TipoFiltro.WILDCARD, "*")]
        self.prioridad = prioridad
        self.modo = modo
        self.politica_fallo = politica_fallo
        self.max_reintentos = max_reintentos
        self.throttling = throttling or ConfiguracionThrottling()
        
        self.estado = EstadoSuscriptor.INACTIVO
        self.estadisticas = EstadisticasSuscriptor()
        self._reintentos_actuales: Dict[str, int] = defaultdict(int)
        self._ultimo_error: Optional[str] = None
        self._fecha_activacion: Optional[float] = None
        self._lock = threading.RLock()
        self._cola_personal: Optional[queue.Queue] = None
        self._hilo_procesamiento: Optional[threading.Thread] = None
        self._activo = False
        
        self._inicializar()
    
    def _inicializar(self):
        if self.modo == ModoEjecucion.COLA_PROPIA:
            self._cola_personal = queue.Queue(maxsize=1000)
            self._hilo_procesamiento = threading.Thread(
                target=self._bucle_procesamiento_cola,
                daemon=True,
                name=f"{self._id}_worker"
            )
    
    @property
    def id_suscriptor(self) -> str:
        return self._id
    
    @abstractmethod
    def on_evento(self, evento: Evento) -> Optional[Any]:
        pass
    
    def puede_procesar(self, tipo_evento: str, evento: Optional[Evento] = None) -> bool:
        for filtro in self.filtros:
            if filtro.coincide(tipo_evento, evento):
                return True
        return False
    
    def recibir_evento(self, evento: Evento) -> bool:
        if self.estado not in (EstadoSuscriptor.ACTIVO, EstadoSuscriptor.DEGRADADO):
            return False
        
        if not self.throttling.permitir():
            self.estadisticas.throttling_aplicado += 1
            return False
        
        if self.modo == ModoEjecucion.SINCRONO:
            return self._procesar_sincrono(evento)
        elif self.modo == ModoEjecucion.ASINCRONO:
            threading.Thread(target=self._procesar_sincrono, args=(evento,), daemon=True).start()
            return True
        elif self.modo == ModoEjecucion.COLA_PROPIA and self._cola_personal:
            try:
                self._cola_personal.put_nowait(evento)
                return True
            except queue.Full:
                return False
        elif self.modo == ModoEjecucion.ADAPTATIVO:
            prioridad_evento = evento.prioridad if hasattr(evento, 'prioridad') else 3
            if hasattr(prioridad_evento, 'value'):
                prioridad_evento = prioridad_evento.value
            
            prioridad_alta = Prioridad.ALTA
            
            if prioridad_evento <= prioridad_alta:
                return self._procesar_sincrono(evento)
            else:
                threading.Thread(target=self._procesar_sincrono, args=(evento,), daemon=True).start()
                return True
        return False
    
    def _procesar_sincrono(self, evento: Evento) -> bool:
        inicio = time.time()
        
        try:
            if hasattr(evento, 'comenzar_entrega'):
                evento.comenzar_entrega(self.id_suscriptor)
            
            resultado = self.on_evento(evento)
            
            tiempo_ms = (time.time() - inicio) * 1000
            self.estadisticas.registrar_exito(tiempo_ms)
            
            if hasattr(evento, 'entregado'):
                evento.entregado(self.id_suscriptor, tiempo_ms)
            if hasattr(evento, 'procesado') and resultado is not None:
                evento.procesado(resultado)
            
            if self._id in self._reintentos_actuales:
                del self._reintentos_actuales[self._id]
            
            return True
            
        except Exception as e:
            self.estadisticas.registrar_fallo()
            self._ultimo_error = str(e)
            
            if hasattr(evento, 'fallido'):
                evento.fallido(str(e))
            
            return self._manejar_fallo(evento, e)
    
    def _manejar_fallo(self, evento: Evento, error: Exception) -> bool:
        if self.politica_fallo == PoliticaFallo.IGNORAR:
            return False
        elif self.politica_fallo == PoliticaFallo.REINTENTAR:
            key = f"{evento.id}_{self.id_suscriptor}"
            self._reintentos_actuales[key] += 1
            if self._reintentos_actuales[key] <= self.max_reintentos:
                time.sleep(0.1 * self._reintentos_actuales[key])
                return self._procesar_sincrono(evento)
            return False
        elif self.politica_fallo == PoliticaFallo.DEGRADAR:
            if self.estadisticas.fallos_consecutivos >= 5:
                self.estado = EstadoSuscriptor.DEGRADADO
            return False
        elif self.politica_fallo == PoliticaFallo.DESUSCRIBIR:
            self.estado = EstadoSuscriptor.MUERTO
            return False
        elif self.politica_fallo == PoliticaFallo.DEAD_LETTER:
            return False
        return False
    
    def _bucle_procesamiento_cola(self):
        while self._activo:
            try:
                if self._cola_personal:
                    evento = self._cola_personal.get(timeout=1.0)
                    self._procesar_sincrono(evento)
            except queue.Empty:
                continue
            except Exception:
                pass
    
    def activar(self):
        with self._lock:
            self.estado = EstadoSuscriptor.ACTIVO
            self._fecha_activacion = time.time()
            self._activo = True
            
            if self._hilo_procesamiento and not self._hilo_procesamiento.is_alive():
                self._hilo_procesamiento.start()
    
    def pausar(self):
        with self._lock:
            self.estado = EstadoSuscriptor.PAUSADO
    
    def reanudar(self):
        with self._lock:
            if self.estado == EstadoSuscriptor.PAUSADO:
                self.estado = EstadoSuscriptor.ACTIVO
    
    def desactivar(self):
        with self._lock:
            self.estado = EstadoSuscriptor.INACTIVO
            self._activo = False
    
    def obtener_info(self) -> Dict[str, Any]:
        return {
            'id': self._id,
            'nombre': self.nombre,
            'estado': self.estado.value,
            'prioridad': self.prioridad,
            'modo': self.modo.value,
            'politica_fallo': self.politica_fallo.value,
            'filtros': [(f.tipo.value, str(f.patron)) for f in self.filtros],
            'estadisticas': asdict(self.estadisticas),
            'tasa_exito': self.estadisticas.tasa_exito(),
            'ultimo_error': self._ultimo_error,
            'tiempo_activo': (time.time() - self._fecha_activacion) if self._fecha_activacion else 0,
        }
    
    def __repr__(self) -> str:
        return f"Suscriptor(id={self._id}, nombre={self.nombre}, estado={self.estado.value})"
    
    def __lt__(self, other: 'Suscriptor') -> bool:
        return self.prioridad < other.prioridad

# =====================================================================
# SUSCRIPTOR FUNCIONAL (Wrapper para callbacks)
# =====================================================================

class SuscriptorFuncional(Suscriptor):
    """Suscriptor que envuelve una función callback."""
    
    def __init__(self, 
                 callback: Callable[[Evento], Optional[Any]],
                 suscriptor_id: Optional[str] = None,
                 nombre: str = "",
                 filtros: List[FiltroSuscripcion] = None,
                 **kwargs):
        
        super().__init__(suscriptor_id, nombre, filtros, **kwargs)
        self.callback = callback
        self._es_corutina = inspect.iscoroutinefunction(callback)
    
    def on_evento(self, evento: Evento) -> Optional[Any]:
        if self._es_corutina:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.callback(evento), loop)
                return future.result(timeout=30)
            else:
                return loop.run_until_complete(self.callback(evento))
        return self.callback(evento)

# =====================================================================
# SUSCRIPTOR CON THROTTLING AVANZADO
# =====================================================================

class SuscriptorThrottled(Suscriptor):
    """Suscriptor con throttling avanzado basado en token bucket."""
    
    def __init__(self, callback: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback
        self._tokens = self.throttling.bucket_tokens
        self._ultima_recarga = time.time()
    
    def on_evento(self, evento: Evento) -> Optional[Any]:
        return self.callback(evento)
    
    def recibir_evento(self, evento: Evento) -> bool:
        if self.estado not in (EstadoSuscriptor.ACTIVO, EstadoSuscriptor.DEGRADADO):
            return False
        
        ahora = time.time()
        tiempo_transcurrido = ahora - self._ultima_recarga
        tokens_nuevos = tiempo_transcurrido * self.throttling.tasa_recarga
        self._tokens = min(self.throttling.bucket_tokens, self._tokens + tokens_nuevos)
        self._ultima_recarga = ahora
        
        if self._tokens >= 1:
            self._tokens -= 1
            return super().recibir_evento(evento)
        else:
            self.estadisticas.throttling_aplicado += 1
            return False

# =====================================================================
# SUSCRIPTOR PRIORITARIO (Con cola de prioridad)
# =====================================================================

class SuscriptorPrioritario(Suscriptor):
    """Suscriptor con cola de prioridad interna."""
    
    def __init__(self, callback: Callable, capacidad_cola: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.capacidad_cola = capacidad_cola
        self._cola_prioridad: List[Tuple[int, float, str, Evento]] = []
        self._lock_cola = threading.RLock()
        self._hilo_prioridad: Optional[threading.Thread] = None
    
    def on_evento(self, evento: Evento) -> Optional[Any]:
        return self.callback(evento)
    
    def activar(self):
        super().activar()
        self._hilo_prioridad = threading.Thread(
            target=self._bucle_prioridad,
            daemon=True,
            name=f"{self._id}_priority_worker"
        )
        self._hilo_prioridad.start()
    
    def recibir_evento(self, evento: Evento) -> bool:
        if self.estado not in (EstadoSuscriptor.ACTIVO, EstadoSuscriptor.DEGRADADO):
            return False
        
        with self._lock_cola:
            if len(self._cola_prioridad) >= self.capacidad_cola:
                return False
            
            prioridad_val = evento.prioridad if hasattr(evento, 'prioridad') else 3
            if hasattr(prioridad_val, 'value'):
                prioridad_val = prioridad_val.value
            
            entrada = (prioridad_val, time.time(), str(uuid.uuid4()), evento)
            heapq.heappush(self._cola_prioridad, entrada)
            return True
    
    def _bucle_prioridad(self):
        while self._activo:
            with self._lock_cola:
                if not self._cola_prioridad:
                    time.sleep(0.05)
                    continue
                entrada = heapq.heappop(self._cola_prioridad)
            
            _, _, _, evento = entrada
            self._procesar_sincrono(evento)
    
    def desactivar(self):
        super().desactivar()
        if self._hilo_prioridad and self._hilo_prioridad.is_alive():
            self._hilo_prioridad.join(timeout=2.0)

# =====================================================================
# SUSCRIPTOR RESILIENTE (Con circuit breaker interno)
# =====================================================================

class SuscriptorResiliente(Suscriptor):
    """Suscriptor con circuit breaker interno y auto-recuperación."""
    
    def __init__(self, callback: Callable, umbral_fallos: int = 5,
                 timeout_recuperacion: float = 30.0, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.umbral_fallos = umbral_fallos
        self.timeout_recuperacion = timeout_recuperacion
        self._circuit_breaker_abierto = False
        self._circuit_breaker_hasta: float = 0.0
        self._fallos_consecutivos = 0
    
    def on_evento(self, evento: Evento) -> Optional[Any]:
        return self.callback(evento)
    
    def recibir_evento(self, evento: Evento) -> bool:
        if self._circuit_breaker_abierto:
            if time.time() < self._circuit_breaker_hasta:
                return False
            else:
                self._circuit_breaker_abierto = False
                self.estado = EstadoSuscriptor.RECUPERANDO
        
        return super().recibir_evento(evento)
    
    def _procesar_sincrono(self, evento: Evento) -> bool:
        exito = super()._procesar_sincrono(evento)
        
        if exito:
            self._fallos_consecutivos = 0
            if self.estado == EstadoSuscriptor.RECUPERANDO:
                self.estado = EstadoSuscriptor.ACTIVO
        else:
            self._fallos_consecutivos += 1
            if self._fallos_consecutivos >= self.umbral_fallos:
                self._circuit_breaker_abierto = True
                self._circuit_breaker_hasta = time.time() + self.timeout_recuperacion
                self.estado = EstadoSuscriptor.DEGRADADO
        
        return exito

# =====================================================================
# GESTOR DE SUSCRIPTORES (Singleton)
# =====================================================================

class GestorSuscriptores:
    """Gestor central de suscriptores. Singleton thread-safe."""
    
    _instancia: Optional['GestorSuscriptores'] = None
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
            
            self._suscriptores: Dict[str, Suscriptor] = {}
            self._suscripciones: Dict[str, List[str]] = defaultdict(list)
            self._dead_letter_queue = DeadLetterQueue()
            self._estadisticas_globales: Dict[str, Any] = defaultdict(int)
            
            self._inicializado = True
    
    def registrar(self, suscriptor: Suscriptor) -> bool:
        with self._lock:
            if suscriptor.id_suscriptor in self._suscriptores:
                return False
            
            self._suscriptores[suscriptor.id_suscriptor] = suscriptor
            if suscriptor.estado == EstadoSuscriptor.INACTIVO:
                suscriptor.activar()
            return True
    
    def suscribir(self, suscriptor: Suscriptor, patron: str, 
                  tipo_filtro: TipoFiltro = TipoFiltro.WILDCARD) -> bool:
        with self._lock:
            if suscriptor.id_suscriptor not in self._suscriptores:
                self.registrar(suscriptor)
            
            filtro = FiltroSuscripcion(tipo_filtro, patron)
            suscriptor.filtros.append(filtro)
            self._suscripciones[patron].append(suscriptor.id_suscriptor)
            return True
    
    def desuscribir(self, suscriptor_id: str, patron: Optional[str] = None):
        with self._lock:
            if patron:
                if patron in self._suscripciones:
                    self._suscripciones[patron] = [
                        sid for sid in self._suscripciones[patron] 
                        if sid != suscriptor_id
                    ]
            else:
                for p in self._suscripciones:
                    self._suscripciones[p] = [
                        sid for sid in self._suscripciones[p] 
                        if sid != suscriptor_id
                    ]
    
    def obtener_suscriptores_para(self, tipo_evento: str, 
                                   evento: Optional[Evento] = None) -> List[Suscriptor]:
        with self._lock:
            interesados = []
            for suscriptor in self._suscriptores.values():
                if suscriptor.estado in (EstadoSuscriptor.ACTIVO, 
                                         EstadoSuscriptor.DEGRADADO,
                                         EstadoSuscriptor.RECUPERANDO):
                    if suscriptor.puede_procesar(tipo_evento, evento):
                        interesados.append(suscriptor)
            interesados.sort(key=lambda s: s.prioridad)
            return interesados
    
    def notificar(self, evento: Evento) -> int:
        tipo = evento.tipo if hasattr(evento, 'tipo') else 'desconocido'
        suscriptores = self.obtener_suscriptores_para(tipo, evento)
        
        notificados = 0
        for suscriptor in suscriptores:
            if suscriptor.recibir_evento(evento):
                notificados += 1
            else:
                self._dead_letter_queue.encolar(
                    evento, 
                    suscriptor.id_suscriptor,
                    suscriptor._ultimo_error or "Error desconocido"
                )
        
        self._estadisticas_globales['eventos_notificados'] += 1
        self._estadisticas_globales['total_notificaciones'] += notificados
        
        return notificados
    
    def obtener_suscriptor(self, suscriptor_id: str) -> Optional[Suscriptor]:
        return self._suscriptores.get(suscriptor_id)
    
    def listar_suscriptores(self) -> List[Dict[str, Any]]:
        return [s.obtener_info() for s in self._suscriptores.values()]
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_suscriptores': len(self._suscriptores),
                'suscriptores_activos': sum(1 for s in self._suscriptores.values() 
                                           if s.estado == EstadoSuscriptor.ACTIVO),
                'suscriptores_degradados': sum(1 for s in self._suscriptores.values() 
                                              if s.estado == EstadoSuscriptor.DEGRADADO),
                'total_suscripciones': sum(len(v) for v in self._suscripciones.values()),
                'dead_letter_queue': self._dead_letter_queue.obtener_estadisticas(),
                'estadisticas_globales': dict(self._estadisticas_globales),
            }

# =====================================================================
# DECORADORES DE SUSCRIPCIÓN
# =====================================================================

def suscriptor(patron: str = "*", 
               prioridad: int = 3,
               modo: ModoEjecucion = ModoEjecucion.ADAPTATIVO,
               politica_fallo: PoliticaFallo = PoliticaFallo.DEGRADAR,
               nombre: str = ""):
    """Decorador para marcar una función como suscriptor."""
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._suscripcion_config = {
            'patron': patron,
            'prioridad': prioridad,
            'modo': modo,
            'politica_fallo': politica_fallo,
            'nombre': nombre or func.__name__,
            'callback': func,
        }
        return wrapper
    return decorador
    
# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_gestor_global: Optional[GestorSuscriptores] = None

def obtener_gestor() -> GestorSuscriptores:
    global _gestor_global
    if _gestor_global is None:
        _gestor_global = GestorSuscriptores()
    return _gestor_global

def suscribir(patron: str, callback: Callable[[Evento], Any], 
              prioridad: int = 3, nombre: str = "") -> Suscriptor:
    gestor = obtener_gestor()
    filtros = [FiltroSuscripcion(TipoFiltro.WILDCARD, patron)]
    suscriptor_obj = SuscriptorFuncional(
        callback=callback,
        nombre=nombre or callback.__name__,
        filtros=filtros,
        prioridad=prioridad
    )
    gestor.registrar(suscriptor_obj)
    return suscriptor_obj
    
 # =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE SUSCRIPTORES")
    print("=" * 70)
    
    try:
        print("\n[1/8] Inicializando gestor de suscriptores...")
        gestor = GestorSuscriptores()
        print(f"  ✅ Gestor inicializado")
        
        print("\n[2/8] Creando suscriptor funcional...")
        eventos_recibidos = []
        
        def mi_callback(evento):
            eventos_recibidos.append(evento)
            return f"Procesado: {evento.tipo}"
        
        sub1 = SuscriptorFuncional(
            callback=mi_callback,
            nombre="TestSuscriptor",
            filtros=[FiltroSuscripcion(TipoFiltro.WILDCARD, "test.*")],
            prioridad=Prioridad.ALTA
        )
        
        gestor.registrar(sub1)
        print(f"  ✅ Suscriptor registrado: {sub1.id_suscriptor}")
        
        print("\n[3/8] Probando filtros...")
        
        @dataclass
        class EventoTest:
            tipo: str
            id: str = field(default_factory=lambda: str(uuid.uuid4()))
            prioridad: int = Prioridad.MEDIA
            metadatos: Dict = field(default_factory=dict)
        
        eventos_test = [
            EventoTest(tipo="test.evento1", prioridad=Prioridad.ALTA),
            EventoTest(tipo="test.evento2", prioridad=Prioridad.MEDIA),
            EventoTest(tipo="otro.evento", prioridad=Prioridad.BAJA),
        ]
        
        for evt in eventos_test:
            puede = sub1.puede_procesar(evt.tipo, evt)
            print(f"  📍 {evt.tipo}: {'✅' if puede else '❌'}")
        
        print("\n[4/8] Procesando eventos...")
        for evt in eventos_test:
            if sub1.puede_procesar(evt.tipo, evt):
                sub1.recibir_evento(evt)
        
        time.sleep(0.5)
        print(f"  ✅ Eventos procesados: {len(eventos_recibidos)}")
        
        print("\n[5/8] Probando suscriptor con throttling...")
        sub2 = SuscriptorThrottled(
            callback=lambda e: None,
            nombre="ThrottledSuscriptor",
            filtros=[FiltroSuscripcion(TipoFiltro.WILDCARD, "*")],
            throttling=ConfiguracionThrottling(bucket_tokens=5, tasa_recarga=2.0)
        )
        
        gestor.registrar(sub2)
        permitidos = sum(1 for i in range(20) if sub2.recibir_evento(EventoTest(tipo=f"test.{i}")))
        print(f"  ✅ Eventos permitidos: {permitidos}/20")
        
        print("\n[6/8] Probando suscriptor prioritario...")
        orden_procesado = []
        
        def callback_prioridad(evento):
            orden_procesado.append(evento.tipo)
            time.sleep(0.01)
        
        sub3 = SuscriptorPrioritario(
            callback=callback_prioridad,
            nombre="PrioridadSuscriptor",
            capacidad_cola=10
        )
        
        gestor.registrar(sub3)
        sub3.activar()
        
        for i, prio in enumerate([Prioridad.BAJA, Prioridad.ALTA, Prioridad.CRITICA, Prioridad.MEDIA]):
            sub3.recibir_evento(EventoTest(tipo=f"test.prio.{i}", prioridad=prio))
        
        time.sleep(1.0)
        sub3.desactivar()
        print(f"  ✅ Orden procesado: {orden_procesado}")
        
        print("\n[7/8] Probando decorador @suscriptor...")
        
        @suscriptor("decorador.*", prioridad=Prioridad.ALTA, nombre="DecoradorTest")
        def funcion_decorada(evento):
            return f"Decorador: {evento.tipo}"
        
        config = funcion_decorada._suscripcion_config
        print(f"  ✅ Configuración: patrón='{config['patron']}', nombre='{config['nombre']}'")
        
        print("\n[8/8] Estadísticas del gestor...")
        stats = gestor.obtener_estadisticas()
        print(f"  📊 Total suscriptores: {stats['total_suscriptores']}")
        print(f"  📊 Suscriptores activos: {stats['suscriptores_activos']}")
        
        for sub in gestor._suscriptores.values():
            info = sub.obtener_info()
            print(f"  📍 {info['nombre']}: tasa éxito={info['tasa_exito']:.1%}, estado={info['estado']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Suscriptores está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")                                                         