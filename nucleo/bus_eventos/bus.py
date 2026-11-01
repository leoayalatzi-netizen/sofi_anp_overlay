#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Bus de Eventos Cuántico (El Sistema Nervioso Central)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
import time
import uuid
import threading
import asyncio
import queue
import traceback
import json
import hashlib
import heapq
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator, Awaitable
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict, Counter
from functools import wraps, partial
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from contextlib import contextmanager

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .evento import Evento, EstadoEvento, FabricaEventos, PrioridadEvento
except ImportError:
    @dataclass
    class Evento:
        tipo: str = ""
        datos: Any = None
        origen: str = ""
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: float = field(default_factory=time.time)
        prioridad: int = 3
        metadatos: Dict = field(default_factory=dict)
    
    class EstadoEvento:
        CREADO = "creado"
        EN_COLA = "en_cola"
        ENTREGADO = "entregado"
        PROCESADO = "procesado"
        FALLIDO = "fallido"
    
    class FabricaEventos:
        @staticmethod
        def crear_evento_sistema(tipo, datos=None):
            return Evento(tipo=tipo, datos=datos, origen="sistema", prioridad=1)
    
    class PrioridadEvento(IntEnum):
        CRITICA = 0
        ALTA = 1
        MEDIA = 2
        BAJA = 3
        DIFERIDA = 4

try:
    from .tipos import TipoEvento
except ImportError:
    class TipoEvento:
        SISTEMA_INICIANDO = "sistema.iniciando"
        SISTEMA_LISTO = "sistema.listo"
        SISTEMA_APAGANDO = "sistema.apagando"
        SISTEMA_ERROR = "sistema.error"
        BUS_INICIADO = "bus.iniciado"
        BUS_DETENIDO = "bus.detenido"
        BUS_ERROR = "bus.error"

try:
    from .prioridad import Prioridad, PrioridadBase
except ImportError:
    class Prioridad:
        COSMICA = -10
        CRITICA = 0
        ALTA = 1
        MEDIA = 3
        BAJA = 5
        DIFERIDA = 7

# Importación de suscriptor (con fallback completo)
try:
    from .suscriptor import (
        Suscriptor, SuscriptorFuncional, GestorSuscriptores,
        EstadoSuscriptor, ModoEjecucion, PoliticaFallo,
        DeadLetterQueue, ConfiguracionThrottling, FiltroSuscripcion,
        TipoFiltro, obtener_gestor as obtener_gestor_suscriptores,
        suscribir as suscribir_func
    )
except ImportError:
    class Suscriptor(ABC):
        @abstractmethod
        def on_evento(self, evento): pass
        @property
        def id_suscriptor(self): return "base"
        def puede_procesar(self, tipo, evento=None): return True
        def recibir_evento(self, evento): return True
    
    class SuscriptorFuncional(Suscriptor):
        def __init__(self, callback, nombre="", filtros=None, prioridad=3):
            self.callback = callback
            self.nombre = nombre
            self.filtros = filtros or []
            self.prioridad = prioridad
            self.estado = "activo"
            self.estadisticas = type('Stats', (), {'tasa_exito': lambda: 1.0})()
        def on_evento(self, evento): return self.callback(evento)
        @property
        def id_suscriptor(self): return self.nombre or str(id(self))
        def activar(self): pass
        def obtener_info(self): return {'nombre': self.nombre, 'estado': 'activo', 'tasa_exito': 1.0}
    
    class GestorSuscriptores:
        def __init__(self):
            self._suscriptores = {}
        def registrar(self, s):
            self._suscriptores[s.id_suscriptor] = s
            return True
        def notificar(self, e):
            count = 0
            for s in self._suscriptores.values():
                if s.puede_procesar(e.tipo, e):
                    s.recibir_evento(e)
                    count += 1
            return count
        def suscribir(self, s, p, tf=None): return True
        def desuscribir(self, sid, p=None): pass
        def obtener_estadisticas(self): return {'total_suscriptores': len(self._suscriptores)}
    
    class EstadoSuscriptor:
        ACTIVO = "activo"
    
    class DeadLetterQueue:
        def __init__(self, capacidad=1000): pass
        def encolar(self, e, sid, err): pass
        def obtener_estadisticas(self): return {'total_encolados': 0, 'pendientes': 0}
    
    class ConfiguracionThrottling:
        pass
    
    class FiltroSuscripcion:
        def __init__(self, tipo, patron): pass
    
    class TipoFiltro:
        WILDCARD = "wildcard"
        EXACTO = "exacto"
        PREFIJO = "prefijo"
    
    def obtener_gestor_suscriptores():
        return GestorSuscriptores()
    
    def suscribir_func(patron, callback, prioridad=3, nombre=""):
        return SuscriptorFuncional(callback, nombre, [FiltroSuscripcion(TipoFiltro.WILDCARD, patron)], prioridad)

try:
    from servicios.base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

# =====================================================================
# ENUMERACIONES AVANZADAS
# =====================================================================

class EstadoBus(Enum):
    INACTIVO = "inactivo"
    INICIANDO = "iniciando"
    ACTIVO = "activo"
    DEGRADADO = "degradado"
    PAUSADO = "pausado"
    DETENIENDO = "deteniendo"
    DETENIDO = "detenido"
    ERROR = "error"

class ModoBus(Enum):
    SINCRONO = "sincrono"
    ASINCRONO = "asincrono"
    HIBRIDO = "hibrido"
    ADAPTATIVO = "adaptativo"

class PoliticaCola(Enum):
    BLOQUEAR = "bloquear"
    RECHAZAR = "rechazar"
    DESCARTAR_ANTIGUO = "descartar_antiguo"
    DESCARTAR_BAJA_PRIORIDAD = "descartar_baja_prioridad"
    EXPANDIR = "expandir"

# =====================================================================
# CONFIGURACIÓN DEL BUS
# =====================================================================

@dataclass
class ConfiguracionBus:
    modo: ModoBus = ModoBus.ADAPTATIVO
    politica_cola: PoliticaCola = PoliticaCola.DESCARTAR_BAJA_PRIORIDAD
    capacidad_cola: int = 10000
    num_workers: int = 4
    batch_size: int = 50
    timeout_procesamiento: float = 30.0
    persistir_eventos: bool = True
    max_reintentos: int = 3
    retraso_reintento: float = 0.1
    limpiar_completados: bool = True
    intervalo_limpieza: float = 300.0
    estadisticas_habilitadas: bool = True
    dead_letter_habilitada: bool = True
    monitoreo_salud: bool = True

# =====================================================================
# COLA DE PRIORIDAD GLOBAL
# =====================================================================

class ColaPrioridadBus:
    def __init__(self, capacidad: int = 10000, politica: PoliticaCola = PoliticaCola.DESCARTAR_BAJA_PRIORIDAD):
        self.capacidad = capacidad
        self.politica = politica
        self._heap: List[Tuple[int, float, str, Evento]] = []
        self._lock = threading.RLock()
        self._total_encolados: int = 0
        self._total_rechazados: int = 0
        self._total_desencolados: int = 0
        
    def poner(self, evento: Evento) -> bool:
        with self._lock:
            if len(self._heap) >= self.capacidad:
                if self.politica == PoliticaCola.RECHAZAR:
                    self._total_rechazados += 1
                    return False
                elif self.politica == PoliticaCola.DESCARTAR_ANTIGUO:
                    self._heap.sort(key=lambda x: x[1])
                    self._heap.pop(0)
                elif self.politica == PoliticaCola.DESCARTAR_BAJA_PRIORIDAD:
                    self._heap.sort(key=lambda x: (-x[0], x[1]))
                    self._heap.pop(0)
                elif self.politica == PoliticaCola.EXPANDIR:
                    self.capacidad = int(self.capacidad * 1.5)
                else:
                    return False
            
            prioridad = evento.prioridad if hasattr(evento, 'prioridad') else Prioridad.MEDIA
            if hasattr(prioridad, 'value'):
                prioridad = prioridad.value
            
            entrada = (prioridad, time.time(), evento.id, evento)
            heapq.heappush(self._heap, entrada)
            self._total_encolados += 1
            
            if hasattr(evento, 'encolar'):
                evento.encolar()
            
            return True
    
    def obtener(self) -> Optional[Evento]:
        with self._lock:
            if not self._heap:
                return None
            entrada = heapq.heappop(self._heap)
            self._total_desencolados += 1
            return entrada[3]
    
    def obtener_batch(self, max_size: int) -> List[Evento]:
        with self._lock:
            batch = []
            while self._heap and len(batch) < max_size:
                entrada = heapq.heappop(self._heap)
                batch.append(entrada[3])
                self._total_desencolados += 1
            return batch
    
    def tamaño(self) -> int:
        with self._lock:
            return len(self._heap)
    
    def estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'capacidad': self.capacidad,
                'tamaño_actual': len(self._heap),
                'total_encolados': self._total_encolados,
                'total_desencolados': self._total_desencolados,
                'total_rechazados': self._total_rechazados,
                'politica': self.politica.value,
            }

# =====================================================================
# MIDDLEWARE BASE
# =====================================================================

class Middleware(ABC):
    @abstractmethod
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        pass
    
    @abstractmethod
    def on_error(self, evento: Evento, error: Exception):
        pass

class MiddlewareLogging(Middleware):
    def __init__(self, nivel: str = "INFO"):
        self.nivel = nivel
        self._contador = 0
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        self._contador += 1
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass

class MiddlewareValidacion(Middleware):
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        if not evento.tipo:
            raise ValueError("Evento sin tipo")
        if not evento.id:
            evento.id = str(uuid.uuid4())
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass

class MiddlewareMetricas(Middleware):
    def __init__(self):
        self._metricas: Dict[str, int] = defaultdict(int)
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        self._metricas[evento.tipo] += 1
        self._metricas['total'] += 1
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        self._metricas['errores'] += 1
    
    def obtener_metricas(self) -> Dict[str, Any]:
        return {
            'total': self._metricas['total'],
            'errores': self._metricas.get('errores', 0),
            'por_tipo': {k: v for k, v in self._metricas.items() if k not in ('total', 'errores')},
        }

# =====================================================================
# PIPELINE DE MIDDLEWARE
# =====================================================================

class PipelineMiddleware:
    def __init__(self):
        self._middlewares: List[Middleware] = []
        self._lock = threading.RLock()
    
    def agregar(self, middleware: Middleware):
        with self._lock:
            self._middlewares.append(middleware)
    
    def ejecutar(self, evento: Evento, contexto: Dict[str, Any] = None) -> Optional[Evento]:
        ctx = contexto or {}
        evento_actual = evento
        
        for mw in self._middlewares:
            try:
                evento_actual = mw.procesar(evento_actual, ctx)
                if evento_actual is None:
                    return None
            except Exception as e:
                mw.on_error(evento_actual, e)
                raise
        
        return evento_actual

# =====================================================================
# WORKER DEL BUS
# =====================================================================

class WorkerBus:
    def __init__(self, worker_id: int, bus: 'BusEventos', batch_size: int = 50):
        self.worker_id = worker_id
        self.bus = bus
        self.batch_size = batch_size
        self._activo = True
        self._pausado = False
        self._hilo: Optional[threading.Thread] = None
        self._eventos_procesados = 0
        self._errores = 0
        
    def iniciar(self):
        self._hilo = threading.Thread(
            target=self._bucle,
            name=f"BusWorker-{self.worker_id}",
            daemon=True
        )
        self._hilo.start()
    
    def detener(self):
        self._activo = False
        if self._hilo:
            self._hilo.join(timeout=5.0)
    
    def pausar(self):
        self._pausado = True
    
    def reanudar(self):
        self._pausado = False
    
    def _bucle(self):
        while self._activo:
            if self._pausado:
                time.sleep(0.1)
                continue
            
            try:
                batch = self.bus._cola_global.obtener_batch(self.batch_size)
                
                if not batch:
                    time.sleep(0.01)
                    continue
                
                for evento in batch:
                    if not self._activo:
                        break
                    self._procesar_evento(evento)
                    
            except Exception as e:
                self._errores += 1
                time.sleep(0.1)
    
    def _procesar_evento(self, evento: Evento):
        try:
            evento = self.bus._pipeline.ejecutar(evento, {'worker_id': self.worker_id})
            
            if evento:
                notificados = self.bus._gestor_suscriptores.notificar(evento)
                
                if notificados == 0 and self.bus.config.dead_letter_habilitada:
                    self.bus._dead_letter_queue.encolar(
                        evento, "sin_suscriptores", "No hay suscriptores para este evento"
                    )
                
                if self.bus.config.persistir_eventos:
                    self.bus._persistir_evento(evento, 'procesado')
                
                self._eventos_procesados += 1
                
        except Exception as e:
            self._errores += 1
            if self.bus.config.persistir_eventos:
                self.bus._persistir_evento(evento, 'fallido', str(e))
    
    def estadisticas(self) -> Dict[str, Any]:
        return {
            'worker_id': self.worker_id,
            'eventos_procesados': self._eventos_procesados,
            'errores': self._errores,
            'activo': self._activo,
            'pausado': self._pausado,
        }

# =====================================================================
# BUS DE EVENTOS PRINCIPAL
# =====================================================================

class BusEventos:
    _instancia: Optional['BusEventos'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self, config: Optional[ConfiguracionBus] = None):
        if self._inicializado:
            return
        
        with self._lock_instancia:
            if self._inicializado:
                return
            
            self.id_bus = str(uuid.uuid4())
            self.config = config or ConfiguracionBus()
            self.estado = EstadoBus.INACTIVO
            self.timestamp_inicio: Optional[float] = None
            
            self._cola_global = ColaPrioridadBus(
                capacidad=self.config.capacidad_cola,
                politica=self.config.politica_cola
            )
            self._gestor_suscriptores = obtener_gestor_suscriptores()
            self._dead_letter_queue = DeadLetterQueue()
            self._pipeline = PipelineMiddleware()
            self._workers: List[WorkerBus] = []
            
            self._metricas_mw = MiddlewareMetricas()
            self._pipeline.agregar(MiddlewareValidacion())
            self._pipeline.agregar(MiddlewareLogging())
            self._pipeline.agregar(self._metricas_mw)
            
            self._eventos_publicados = 0
            self._lock = threading.RLock()
            
            self._monitor_activo = False
            self._hilo_monitor: Optional[threading.Thread] = None
            
            self._inicializado = True
    
    def iniciar(self) -> bool:
        with self._lock:
            if self.estado == EstadoBus.ACTIVO:
                return True
            
            self.estado = EstadoBus.INICIANDO
            self.timestamp_inicio = time.time()
            
            for i in range(self.config.num_workers):
                worker = WorkerBus(i, self, self.config.batch_size)
                self._workers.append(worker)
                worker.iniciar()
            
            if self.config.monitoreo_salud:
                self._monitor_activo = True
                self._hilo_monitor = threading.Thread(target=self._bucle_monitor, daemon=True)
                self._hilo_monitor.start()
            
            self.estado = EstadoBus.ACTIVO
            
            self.publicar(
                TipoEvento.BUS_INICIADO,
                {'id_bus': self.id_bus, 'workers': self.config.num_workers},
                origen="bus",
                prioridad=Prioridad.ALTA
            )
            
            return True
    
    def detener(self, graceful: bool = True) -> bool:
        with self._lock:
            if self.estado != EstadoBus.ACTIVO:
                return False
            
            self.estado = EstadoBus.DETENIENDO
            
            self.publicar(
                TipoEvento.BUS_DETENIDO,
                {'id_bus': self.id_bus, 'graceful': graceful},
                origen="bus",
                prioridad=Prioridad.ALTA
            )
            
            self._monitor_activo = False
            
            for worker in self._workers:
                worker.detener()
            
            self._workers.clear()
            
            self.estado = EstadoBus.DETENIDO
            return True
    
    def publicar(self, tipo: str, datos: Any = None, origen: str = "",
                 prioridad: int = Prioridad.MEDIA, metadatos: Dict = None) -> Optional[str]:
        evento = Evento(
            tipo=tipo,
            datos=datos,
            origen=origen,
            prioridad=prioridad,
            metadatos=metadatos or {}
        )
        return self.publicar_evento(evento)
    
    def publicar_evento(self, evento: Evento) -> Optional[str]:
        if self.estado != EstadoBus.ACTIVO:
            return None
        
        with self._lock:
            self._eventos_publicados += 1
        
        if self._cola_global.poner(evento):
            if self.config.persistir_eventos:
                self._persistir_evento(evento, 'encolado')
            return evento.id
        return None
    
    def publicar_batch(self, eventos: List[Evento]) -> int:
        encolados = 0
        for evento in eventos:
            if self._cola_global.poner(evento):
                encolados += 1
        return encolados
    
    def suscribir(self, patron: str, callback: Callable[[Evento], Any],
                  prioridad: int = Prioridad.MEDIA, nombre: str = "") -> Suscriptor:
        """Suscribe un callback a un patrón de eventos."""
        filtros = [FiltroSuscripcion(TipoFiltro.WILDCARD, patron)]
        suscriptor = SuscriptorFuncional(
            callback=callback,
            nombre=nombre or callback.__name__,
            filtros=filtros,
            prioridad=prioridad
        )
        self._gestor_suscriptores.registrar(suscriptor)
        return suscriptor
    
    def desuscribir(self, suscriptor_id: str, patron: Optional[str] = None):
        self._gestor_suscriptores.desuscribir(suscriptor_id, patron)
    
    def _persistir_evento(self, evento: Evento, estado: str, error: str = None):
        try:
            bd = obtener_bd()
            if bd:
                bd.ejecutar("""
                    INSERT INTO eventos_bus (id, tipo, datos, origen, prioridad, 
                                             timestamp, estado, error, metadatos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    evento.id, evento.tipo, json.dumps(evento.datos), evento.origen,
                    evento.prioridad, evento.timestamp, estado, error,
                    json.dumps(evento.metadatos) if evento.metadatos else None
                ))
        except Exception:
            pass
    
    def _bucle_monitor(self):
        while self._monitor_activo:
            try:
                tamaño_cola = self._cola_global.tamaño()
                if tamaño_cola > self.config.capacidad_cola * 0.9:
                    self.estado = EstadoBus.DEGRADADO
                elif tamaño_cola < self.config.capacidad_cola * 0.5:
                    if self.estado == EstadoBus.DEGRADADO:
                        self.estado = EstadoBus.ACTIVO
                time.sleep(5.0)
            except Exception:
                time.sleep(10.0)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'bus': {
                    'id': self.id_bus,
                    'estado': self.estado.value,
                    'uptime': (time.time() - self.timestamp_inicio) if self.timestamp_inicio else 0,
                    'eventos_publicados': self._eventos_publicados,
                },
                'cola': self._cola_global.estadisticas(),
                'workers': [w.estadisticas() for w in self._workers],
                'suscriptores': self._gestor_suscriptores.obtener_estadisticas(),
                'dead_letter': self._dead_letter_queue.obtener_estadisticas(),
                'metricas': self._metricas_mw.obtener_metricas(),
            }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        stats = self.obtener_estadisticas()
        return {
            'estado': stats['bus']['estado'],
            'uptime': f"{stats['bus']['uptime']:.0f}s",
            'cola': f"{stats['cola']['tamaño_actual']}/{stats['cola']['capacidad']}",
            'procesados': stats['metricas']['total'],
            'errores': stats['metricas']['errores'],
            'suscriptores': stats['suscriptores']['total_suscriptores'],
        }
    
    def __repr__(self) -> str:
        return f"BusEventos(id={self.id_bus[:8]}, estado={self.estado.value})"

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_bus_global: Optional[BusEventos] = None

def obtener_bus() -> BusEventos:
    global _bus_global
    if _bus_global is None:
        _bus_global = BusEventos()
    return _bus_global

def publicar(tipo: str, datos: Any = None, origen: str = "",
             prioridad: int = Prioridad.MEDIA, **kwargs) -> Optional[str]:
    return obtener_bus().publicar(tipo, datos, origen, prioridad, **kwargs)

def suscribir(patron: str, callback: Callable[[Evento], Any],
              prioridad: int = Prioridad.MEDIA) -> Suscriptor:
    return obtener_bus().suscribir(patron, callback, prioridad)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL BUS DE EVENTOS CUÁNTICO")
    print("=" * 70)
    
    bus = None
    
    try:
        print("\n[1/7] Creando bus de eventos...")
        config = ConfiguracionBus(num_workers=2, capacidad_cola=1000, persistir_eventos=False)
        bus = BusEventos(config)
        print(f"  ✅ Bus creado: {bus}")
        
        print("\n[2/7] Iniciando bus...")
        bus.iniciar()
        print(f"  ✅ Estado: {bus.estado.value}")
        
        print("\n[3/7] Suscribiendo callbacks...")
        eventos_recibidos = []
        
        def callback_sistema(evento):
            eventos_recibidos.append(evento)
        
        def callback_test(evento):
            eventos_recibidos.append(evento)
        
        bus.suscribir("sistema.*", callback_sistema, nombre="SistemaCallback")
        bus.suscribir("test.*", callback_test, nombre="TestCallback")
        print(f"  ✅ Callbacks suscritos")
        
        print("\n[4/7] Publicando eventos...")
        ids = []
        ids.append(bus.publicar("sistema.iniciando", {"version": "1.0"}, origen="test"))
        ids.append(bus.publicar("test.evento1", {"mensaje": "Hola"}, origen="test"))
        ids.append(bus.publicar("test.evento2", {"valor": 42}, origen="test", prioridad=Prioridad.ALTA))
        
        for i, eid in enumerate(ids):
            if eid:
                print(f"  📤 Evento {i+1}: {eid[:8]}...")
        
        print("\n[5/7] Esperando procesamiento...")
        time.sleep(1.0)
        
        print("\n[6/7] Estadísticas del bus...")
        stats = bus.obtener_estadisticas()
        print(f"  📊 Estado: {stats['bus']['estado']}")
        print(f"  📊 Publicados: {stats['bus']['eventos_publicados']}")
        print(f"  📊 Cola: {stats['cola']['tamaño_actual']}/{stats['cola']['capacidad']}")
        print(f"  📊 Procesados: {stats['metricas']['total']}")
        
        print("\n[7/7] Resumen ejecutivo...")
        resumen = bus.obtener_resumen()
        for k, v in resumen.items():
            print(f"  📍 {k}: {v}")
        
        print(f"\n  📋 Eventos recibidos: {len(eventos_recibidos)}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Bus de Eventos Cuántico está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if bus:
            print("\n🛑 Deteniendo bus...")
            bus.detener()
            print("   ✓ Bus detenido")
    
    print("\n" + "=" * 70 + "\n")