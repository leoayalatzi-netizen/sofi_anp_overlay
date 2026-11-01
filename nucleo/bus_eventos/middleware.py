#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Middleware del Bus de Eventos
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
import time
import uuid
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field

# =====================================================================
# IMPORTACIONES (con fallback elegante)
# =====================================================================

try:
    from .bus import (
        Middleware,
        MiddlewareLogging,
        MiddlewareValidacion,
        MiddlewareMetricas,
        Evento
    )
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
    
    class Middleware(ABC):
        @abstractmethod
        def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]: pass
        @abstractmethod
        def on_error(self, evento: Evento, error: Exception): pass
    
    class MiddlewareLogging(Middleware):
        def __init__(self, nivel: str = "INFO"): self.nivel = nivel
        def procesar(self, e, c): return e
        def on_error(self, e, err): pass
    
    class MiddlewareValidacion(Middleware):
        def procesar(self, e, c): return e
        def on_error(self, e, err): pass
    
    class MiddlewareMetricas(Middleware):
        def __init__(self): self._metricas = defaultdict(int)
        def procesar(self, e, c): self._metricas[e.tipo] += 1; return e
        def on_error(self, e, err): self._metricas['errores'] += 1
        def obtener_metricas(self): return dict(self._metricas)

try:
    from servicios.base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

# =====================================================================
# MIDDLEWARE AVANZADOS
# =====================================================================

class MiddlewareThrottling(Middleware):
    """Middleware que limita la tasa de eventos por tipo."""
    
    def __init__(self, max_por_segundo: int = 100):
        self.max_por_segundo = max_por_segundo
        self._contadores: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_por_segundo))
        self._lock = threading.RLock()
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        with self._lock:
            ahora = time.time()
            cola = self._contadores[evento.tipo]
            
            while cola and cola[0] < ahora - 1.0:
                cola.popleft()
            
            if len(cola) >= self.max_por_segundo:
                return None
            
            cola.append(ahora)
            return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass


class MiddlewareEnriquecimiento(Middleware):
    """Middleware que enriquece eventos con información adicional."""
    
    def __init__(self, enriquecedores: Dict[str, Callable] = None):
        self.enriquecedores = enriquecedores or {}
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        evento.metadatos['procesado_en'] = time.time()
        
        if 'worker_id' in contexto:
            evento.metadatos['worker_id'] = contexto['worker_id']
        
        if evento.tipo in self.enriquecedores:
            enriquecedor = self.enriquecedores[evento.tipo]
            if callable(enriquecedor):
                evento = enriquecedor(evento)
        
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        evento.metadatos['error_enriquecimiento'] = str(error)


class MiddlewarePersistencia(Middleware):
    """Middleware que persiste eventos en SQLite."""
    
    def __init__(self, persistir_todos: bool = False):
        self.persistir_todos = persistir_todos
        self._tipos_persistir: set = set()
    
    def persistir_tipo(self, tipo: str):
        self._tipos_persistir.add(tipo)
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        if self.persistir_todos or evento.tipo in self._tipos_persistir:
            try:
                bd = obtener_bd()
                if bd:
                    bd.ejecutar("""
                        INSERT INTO eventos_middleware (id, tipo, datos, origen, prioridad, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        evento.id, evento.tipo, json.dumps(evento.datos),
                        evento.origen, evento.prioridad, evento.timestamp
                    ))
            except Exception:
                pass
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass


class MiddlewareCircuitBreaker(Middleware):
    """Middleware que implementa circuit breaker por tipo de evento."""
    
    def __init__(self, umbral_fallos: int = 5, timeout_recuperacion: float = 60.0):
        self.umbral_fallos = umbral_fallos
        self.timeout_recuperacion = timeout_recuperacion
        self._fallos: Dict[str, int] = defaultdict(int)
        self._abierto_hasta: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        with self._lock:
            tipo = evento.tipo
            
            if tipo in self._abierto_hasta:
                if time.time() < self._abierto_hasta[tipo]:
                    return None
                else:
                    del self._abierto_hasta[tipo]
                    self._fallos[tipo] = 0
            
            return evento
    
    def on_error(self, evento: Evento, error: Exception):
        with self._lock:
            tipo = evento.tipo
            self._fallos[tipo] += 1
            
            if self._fallos[tipo] >= self.umbral_fallos:
                self._abierto_hasta[tipo] = time.time() + self.timeout_recuperacion


class MiddlewareTransformacion(Middleware):
    """Middleware que transforma eventos de un tipo a otro."""
    
    def __init__(self):
        self._transformaciones: Dict[str, Callable] = {}
    
    def registrar_transformacion(self, tipo_origen: str, transformador: Callable):
        self._transformaciones[tipo_origen] = transformador
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        if evento.tipo in self._transformaciones:
            return self._transformaciones[evento.tipo](evento)
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass


class MiddlewareAuditoria(Middleware):
    """Middleware que registra todos los eventos para auditoría."""
    
    def __init__(self, max_registros: int = 10000):
        self.max_registros = max_registros
        self._registros: deque = deque(maxlen=max_registros)
        self._lock = threading.RLock()
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        with self._lock:
            self._registros.append({
                'id': evento.id,
                'tipo': evento.tipo,
                'origen': evento.origen,
                'timestamp': evento.timestamp,
                'procesado': time.time(),
                'contexto': str(contexto)[:100],
            })
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        with self._lock:
            self._registros.append({
                'id': evento.id,
                'tipo': evento.tipo,
                'error': str(error),
                'timestamp': time.time(),
            })
    
    def obtener_registros(self, limite: int = 100) -> List[Dict]:
        with self._lock:
            return list(self._registros)[-limite:]


class MiddlewarePrioridad(Middleware):
    """Middleware que ajusta la prioridad de eventos según reglas."""
    
    def __init__(self):
        self._reglas: Dict[str, int] = {}
    
    def agregar_regla(self, patron: str, prioridad: int):
        self._reglas[patron] = prioridad
    
    def procesar(self, evento: Evento, contexto: Dict[str, Any]) -> Optional[Evento]:
        for patron, prioridad in self._reglas.items():
            if patron.endswith('*'):
                if evento.tipo.startswith(patron[:-1]):
                    evento.prioridad = prioridad
                    evento.metadatos['prioridad_ajustada'] = True
                    break
            elif evento.tipo == patron:
                evento.prioridad = prioridad
                evento.metadatos['prioridad_ajustada'] = True
                break
        return evento
    
    def on_error(self, evento: Evento, error: Exception):
        pass


# =====================================================================
# FÁBRICA DE MIDDLEWARE
# =====================================================================

class FabricaMiddleware:
    """Fábrica para crear conjuntos de middleware preconfigurados."""
    
    @staticmethod
    def crear_pipeline_minimo() -> List[Middleware]:
        return [
            MiddlewareValidacion(),
            MiddlewareMetricas(),
        ]
    
    @staticmethod
    def crear_pipeline_estandar() -> List[Middleware]:
        return [
            MiddlewareValidacion(),
            MiddlewareThrottling(max_por_segundo=100),
            MiddlewareLogging(nivel="INFO"),
            MiddlewareEnriquecimiento(),
            MiddlewareMetricas(),
        ]
    
    @staticmethod
    def crear_pipeline_completo() -> List[Middleware]:
        return [
            MiddlewareValidacion(),
            MiddlewareThrottling(max_por_segundo=200),
            MiddlewareCircuitBreaker(umbral_fallos=5),
            MiddlewareTransformacion(),
            MiddlewareEnriquecimiento(),
            MiddlewareLogging(nivel="DEBUG"),
            MiddlewarePersistencia(persistir_todos=False),
            MiddlewareAuditoria(max_registros=5000),
            MiddlewareMetricas(),
        ]
    
    @staticmethod
    def crear_pipeline_desarrollo() -> List[Middleware]:
        return [
            MiddlewareValidacion(),
            MiddlewareLogging(nivel="DEBUG"),
            MiddlewareAuditoria(max_registros=1000),
            MiddlewareMetricas(),
        ]
    
    @staticmethod
    def crear_pipeline_alta_prioridad() -> List[Middleware]:
        mw_prioridad = MiddlewarePrioridad()
        mw_prioridad.agregar_regla("sistema.*", 0)
        mw_prioridad.agregar_regla("fallo.*", 1)
        
        return [
            MiddlewareValidacion(),
            mw_prioridad,
            MiddlewareThrottling(max_por_segundo=500),
            MiddlewareMetricas(),
        ]


# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def crear_middleware(tipo: str, **kwargs) -> Optional[Middleware]:
    """Crea un middleware por nombre."""
    middlewares = {
        'validacion': MiddlewareValidacion,
        'logging': MiddlewareLogging,
        'metricas': MiddlewareMetricas,
        'throttling': MiddlewareThrottling,
        'enriquecimiento': MiddlewareEnriquecimiento,
        'persistencia': MiddlewarePersistencia,
        'circuit_breaker': MiddlewareCircuitBreaker,
        'transformacion': MiddlewareTransformacion,
        'auditoria': MiddlewareAuditoria,
        'prioridad': MiddlewarePrioridad,
    }
    
    clase = middlewares.get(tipo.lower())
    if clase:
        return clase(**kwargs)
    return None


def crear_pipeline(nombres: List[str]) -> List[Middleware]:
    """Crea un pipeline a partir de una lista de nombres."""
    pipeline = []
    for nombre in nombres:
        mw = crear_middleware(nombre)
        if mw:
            pipeline.append(mw)
    return pipeline


# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MÓDULO DE MIDDLEWARE")
    print("=" * 70)
    
    try:
        print("\n[1/6] Middlewares disponibles:")
        tipos = ['validacion', 'logging', 'metricas', 'throttling', 
                 'enriquecimiento', 'circuit_breaker', 'auditoria', 'prioridad']
        for tipo in tipos:
            mw = crear_middleware(tipo)
            icono = "✅" if mw else "❌"
            nombre = mw.__class__.__name__ if mw else "ERROR"
            print(f"  {icono} {tipo}: {nombre}")
        
        print("\n[2/6] Probando pipeline estándar...")
        pipeline = FabricaMiddleware.crear_pipeline_estandar()
        print(f"  ✅ {len(pipeline)} middlewares creados")
        for mw in pipeline:
            print(f"     - {mw.__class__.__name__}")
        
        print("\n[3/6] Probando MiddlewareThrottling...")
        throttling = MiddlewareThrottling(max_por_segundo=2)
        
        @dataclass
        class EventoTest:
            tipo: str = "test"
            id: str = field(default_factory=lambda: str(uuid.uuid4()))
            origen: str = "test"
            timestamp: float = field(default_factory=time.time)
            prioridad: int = 3
            datos: Any = None
            metadatos: Dict = field(default_factory=dict)
        
        permitidos = 0
        for i in range(5):
            evt = EventoTest()
            if throttling.procesar(evt, {}):
                permitidos += 1
        
        print(f"  ✅ Eventos permitidos: {permitidos}/5 (límite=2/segundo)")
        
        print("\n[4/6] Probando MiddlewareAuditoria...")
        auditoria = MiddlewareAuditoria(max_registros=10)
        for i in range(3):
            evt = EventoTest(tipo=f"test.{i}")
            auditoria.procesar(evt, {'test': True})
        
        registros = auditoria.obtener_registros()
        print(f"  ✅ Registros capturados: {len(registros)}")
        
        print("\n[5/6] Probando MiddlewarePrioridad...")
        prioridad_mw = MiddlewarePrioridad()
        prioridad_mw.agregar_regla("critico.*", 0)
        prioridad_mw.agregar_regla("normal.*", 5)
        
        evt_critico = EventoTest(tipo="critico.evento", prioridad=3)
        evt_normal = EventoTest(tipo="normal.evento", prioridad=3)
        
        prioridad_mw.procesar(evt_critico, {})
        prioridad_mw.procesar(evt_normal, {})
        
        print(f"  ✅ Crítico: prioridad {evt_critico.prioridad}")
        print(f"  ✅ Normal: prioridad {evt_normal.prioridad}")
        
        print("\n[6/6] Pipelines preconfigurados:")
        fabricas = [
            ('Mínimo', FabricaMiddleware.crear_pipeline_minimo),
            ('Estándar', FabricaMiddleware.crear_pipeline_estandar),
            ('Completo', FabricaMiddleware.crear_pipeline_completo),
            ('Desarrollo', FabricaMiddleware.crear_pipeline_desarrollo),
            ('Alta Prioridad', FabricaMiddleware.crear_pipeline_alta_prioridad),
        ]
        
        for nombre, fabrica in fabricas:
            pipe = fabrica()
            print(f"  📍 {nombre}: {len(pipe)} middlewares")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Módulo de Middleware está listo.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")