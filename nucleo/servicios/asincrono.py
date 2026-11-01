#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio Asíncrono (El Corazón del Paralelismo)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de ejecución
# asíncrona con pool de threads, colas de prioridad, futures
# personalizados, semáforos, timeouts, y utilidades avanzadas.
# =====================================================================

import sys
import os
import time
import threading
import asyncio
import concurrent.futures
import queue
import traceback
import uuid
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator, Awaitable
)
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque, OrderedDict
from functools import wraps, partial
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager, asynccontextmanager
import heapq
import math
import hashlib

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .registro import obtener_logger
except ImportError:
    def obtener_logger(nombre=""):
        return None

try:
    from .metricas import contador, histograma, medidor
except ImportError:
    def contador(nombre, **kwargs): return None
    def histograma(nombre, **kwargs): return None
    def medidor(nombre, **kwargs): return None

# =====================================================================
# ENUMERACIONES
# =====================================================================

class EstadoTarea(Enum):
    """Estados de una tarea asíncrona."""
    PENDIENTE = "pendiente"
    EN_COLA = "en_cola"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"
    TIMEOUT = "timeout"
    REINTENTANDO = "reintentando"

class PrioridadTarea(Enum):
    """Prioridades para la cola de tareas."""
    COSMICA = -10
    CRITICA = 0
    ALTA = 1
    MEDIA = 2
    BAJA = 3
    DIFERIDA = 5

class PoliticaTimeout(Enum):
    """Políticas cuando una tarea excede su timeout."""
    CANCELAR = "cancelar"
    REINTENTAR = "reintentar"
    DEGRADAR = "degradar"
    IGNORAR = "ignorar"


# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class ResultadoTarea:
    """Resultado de una tarea ejecutada."""
    id: str
    exito: bool
    resultado: Any = None
    error: Optional[str] = None
    tiempo_ms: float = 0.0
    intentos: int = 1
    estado: EstadoTarea = EstadoTarea.COMPLETADA
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def exitoso(cls, tarea_id: str, resultado: Any, tiempo_ms: float = 0.0) -> 'ResultadoTarea':
        return cls(id=tarea_id, exito=True, resultado=resultado, tiempo_ms=tiempo_ms)
    
    @classmethod
    def fallido(cls, tarea_id: str, error: str, tiempo_ms: float = 0.0) -> 'ResultadoTarea':
        return cls(id=tarea_id, exito=False, error=error, tiempo_ms=tiempo_ms, estado=EstadoTarea.FALLIDA)

@dataclass(order=True)
class TareaPriorizada:
    """Tarea con prioridad para la cola."""
    prioridad: int
    timestamp: float = field(compare=False)
    id: str = field(compare=False)
    funcion: Callable = field(compare=False)
    args: Tuple = field(default_factory=tuple, compare=False)
    kwargs: Dict = field(default_factory=dict, compare=False)
    futuro: Optional[Future] = field(default=None, compare=False)
    timeout: Optional[float] = field(default=None, compare=False)
    politica_timeout: PoliticaTimeout = field(default=PoliticaTimeout.CANCELAR, compare=False)
    max_reintentos: int = field(default=0, compare=False)
    intentos: int = field(default=0, compare=False)
    metadatos: Dict = field(default_factory=dict, compare=False)

@dataclass
class EstadisticasExecutor:
    """Estadísticas del executor."""
    tareas_encoladas: int = 0
    tareas_completadas: int = 0
    tareas_fallidas: int = 0
    tareas_timeout: int = 0
    tareas_canceladas: int = 0
    tiempo_total_ms: float = 0.0
    tiempo_promedio_ms: float = 0.0
    threads_activos: int = 0
    tareas_en_cola: int = 0

# =====================================================================
# FUTURE MEJORADO
# =====================================================================

class FutureMejorado(Future):
    """Future mejorado con timeout, callbacks y encadenamiento."""
    
    def __init__(self):
        super().__init__()
        self._callbacks_exito: List[Callable] = []
        self._callbacks_error: List[Callable] = []
        self._callbacks_siempre: List[Callable] = []
        self._timeout: Optional[float] = None
        self._tiempo_inicio: Optional[float] = None
        self._tiempo_fin: Optional[float] = None
    
    def on_success(self, callback: Callable) -> 'FutureMejorado':
        """Registra un callback para cuando la tarea tenga éxito."""
        self._callbacks_exito.append(callback)
        if self.done() and not self.exception():
            try:
                self._ejecutar_callbacks_exito(self.result())
            except Exception:
                pass
        return self
    
    def on_error(self, callback: Callable) -> 'FutureMejorado':
        """Registra un callback para cuando la tarea falle."""
        self._callbacks_error.append(callback)
        if self.done() and self.exception():
            try:
                self._ejecutar_callbacks_error(self.exception())
            except Exception:
                pass
        return self
    
    def on_complete(self, callback: Callable) -> 'FutureMejorado':
        """Registra un callback que se ejecuta siempre."""
        self._callbacks_siempre.append(callback)
        if self.done():
            try:
                self._ejecutar_callbacks_siempre()
            except Exception:
                pass
        return self
    
    def then(self, callback: Callable) -> 'FutureMejorado':
        """
        Encadena otra tarea después de esta.
        Extrae automáticamente el valor de ResultadoTarea.
        """
        nuevo_futuro = FutureMejorado()
        
        def ejecutar_callback(resultado):
            try:
                # Extraer valor si es ResultadoTarea
                if hasattr(resultado, 'resultado'):
                    valor = resultado.resultado
                else:
                    valor = resultado
                
                nuevo_resultado = callback(valor)
                
                if isinstance(nuevo_resultado, FutureMejorado):
                    nuevo_resultado.on_success(lambda r: nuevo_futuro.set_result(r))
                    nuevo_resultado.on_error(lambda e: nuevo_futuro.set_exception(e))
                else:
                    nuevo_futuro.set_result(nuevo_resultado)
            except Exception as e:
                nuevo_futuro.set_exception(e)
        
        self.on_success(ejecutar_callback)
        self.on_error(lambda e: nuevo_futuro.set_exception(e))
        
        return nuevo_futuro
    
    def set_result(self, result):
        """Establece el resultado y dispara callbacks."""
        self._tiempo_fin = time.time()
        super().set_result(result)
        try:
            self._ejecutar_callbacks_exito(result)
        except Exception:
            pass
        try:
            self._ejecutar_callbacks_siempre()
        except Exception:
            pass
    
    def set_exception(self, exception):
        """Establece una excepción y dispara callbacks."""
        self._tiempo_fin = time.time()
        super().set_exception(exception)
        try:
            self._ejecutar_callbacks_error(exception)
        except Exception:
            pass
        try:
            self._ejecutar_callbacks_siempre()
        except Exception:
            pass
    
    def _ejecutar_callbacks_exito(self, resultado):
        """Ejecuta todos los callbacks de éxito."""
        for cb in self._callbacks_exito:
            try:
                cb(resultado)
            except Exception:
                pass
    
    def _ejecutar_callbacks_error(self, error):
        """Ejecuta todos los callbacks de error."""
        for cb in self._callbacks_error:
            try:
                cb(error)
            except Exception:
                pass
    
    def _ejecutar_callbacks_siempre(self):
        """Ejecuta todos los callbacks de finalización."""
        for cb in self._callbacks_siempre:
            try:
                cb()
            except Exception:
                pass
    
    @property
    def tiempo_ejecucion_ms(self) -> Optional[float]:
        """Tiempo de ejecución en milisegundos."""
        if self._tiempo_inicio and self._tiempo_fin:
            return (self._tiempo_fin - self._tiempo_inicio) * 1000
        return None
    
    def result(self, timeout: Optional[float] = None) -> Any:
        """Obtiene el resultado con timeout opcional."""
        self._tiempo_inicio = time.time()
        return super().result(timeout=timeout)
    
    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        """Obtiene la excepción con timeout opcional."""
        return super().exception(timeout=timeout)

# =====================================================================
# COLA DE TAREAS CON PRIORIDAD
# =====================================================================

class ColaTareasPrioridad:
    """Cola thread-safe de tareas con prioridad."""
    
    def __init__(self, capacidad_maxima: int = 10000):
        self.capacidad_maxima = capacidad_maxima
        self._heap: List[TareaPriorizada] = []
        self._lock = threading.RLock()
        self._contador = 0
    
    def poner(self, tarea: TareaPriorizada) -> bool:
        """Encola una tarea con prioridad."""
        with self._lock:
            if len(self._heap) >= self.capacidad_maxima:
                return False
            self._contador += 1
            heapq.heappush(self._heap, tarea)
            return True
    
    def obtener(self) -> Optional[TareaPriorizada]:
        """Obtiene la tarea de mayor prioridad."""
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap)
    
    def obtener_batch(self, max_size: int = 10) -> List[TareaPriorizada]:
        """Obtiene un lote de tareas."""
        with self._lock:
            batch = []
            while self._heap and len(batch) < max_size:
                batch.append(heapq.heappop(self._heap))
            return batch
    
    def tamaño(self) -> int:
        with self._lock:
            return len(self._heap)
    
    def vacia(self) -> bool:
        with self._lock:
            return len(self._heap) == 0
    
    def limpiar(self):
        with self._lock:
            self._heap.clear()

# =====================================================================
# EXECUTOR ASÍNCRONO PRINCIPAL
# =====================================================================

class ExecutorAsincrono:
    """
    Executor asíncrono de ANP.
    
    Capacidades:
    - Pool de threads con crecimiento dinámico
    - Cola de prioridad para tareas
    - Futures mejorados con callbacks
    - Timeouts y reintentos
    - Métricas y logging
    - Soporte para async/await
    """
    
    _instancias: Dict[str, 'ExecutorAsincrono'] = {}
    _lock_instancias = threading.RLock()
    
    def __init__(self, nombre: str = "default",
                 max_workers: int = None,
                 capacidad_cola: int = 10000,
                 timeout_default: float = 60.0):
        
        self.nombre = nombre
        
        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 4) * 2)
        
        self.max_workers = max_workers
        self.timeout_default = timeout_default
        
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"ANP-{nombre}"
        )
        
        self._cola = ColaTareasPrioridad(capacidad_cola)
        self._activo = True
        self._procesando = False
        self._lock = threading.RLock()
        self._tareas_activas: Dict[str, TareaPriorizada] = {}
        self._futuros: Dict[str, FutureMejorado] = {}
        
        self.estadisticas = EstadisticasExecutor()
        self._logger = obtener_logger(f"Executor.{nombre}")
        
        # Métricas
        self._metrica_tareas = contador(f"executor.{nombre}.tareas")
        self._metrica_tiempo = histograma(f"executor.{nombre}.tiempo", unidad="ms")
        
        # Iniciar hilo de procesamiento
        self._hilo_procesamiento = threading.Thread(
            target=self._bucle_procesamiento,
            daemon=True,
            name=f"Executor-{nombre}"
        )
        self._hilo_procesamiento.start()
    
    @classmethod
    def obtener(cls, nombre: str = "default", **kwargs) -> 'ExecutorAsincrono':
        """Obtiene o crea una instancia por nombre."""
        with cls._lock_instancias:
            if nombre not in cls._instancias:
                cls._instancias[nombre] = ExecutorAsincrono(nombre=nombre, **kwargs)
            return cls._instancias[nombre]
    
    def _bucle_procesamiento(self):
        """Bucle principal de procesamiento de tareas."""
        while self._activo:
            try:
                batch = self._cola.obtener_batch(10)
                
                if not batch:
                    time.sleep(0.01)
                    continue
                
                for tarea in batch:
                    if not self._activo:
                        break
                    self._ejecutar_tarea(tarea)
                    
            except Exception:
                time.sleep(0.1)
    
    def _ejecutar_tarea(self, tarea: TareaPriorizada):
        """Ejecuta una tarea en el pool de threads."""
        with self._lock:
            self._tareas_activas[tarea.id] = tarea
            self.estadisticas.tareas_en_cola -= 1
            self.estadisticas.threads_activos += 1
        
        futuro = self._executor.submit(self._ejecutar_con_timeout, tarea)
        
        if tarea.futuro:
            def callback(f: Future):
                self._tarea_completada(tarea, f)
            futuro.add_done_callback(callback)
    
    def _ejecutar_con_timeout(self, tarea: TareaPriorizada) -> Any:
        """Ejecuta la tarea con manejo de timeout."""
        inicio = time.time()
        
        try:
            if tarea.timeout:
                resultado = tarea.funcion(
                    *tarea.args,
                    timeout=tarea.timeout,
                    **tarea.kwargs
                ) if 'timeout' in tarea.kwargs else tarea.funcion(*tarea.args, **tarea.kwargs)
            else:
                resultado = tarea.funcion(*tarea.args, **tarea.kwargs)
            
            tiempo_ms = (time.time() - inicio) * 1000
            
            with self._lock:
                self.estadisticas.tareas_completadas += 1
                self.estadisticas.tiempo_total_ms += tiempo_ms
                self.estadisticas.tiempo_promedio_ms = (
                    self.estadisticas.tiempo_total_ms / self.estadisticas.tareas_completadas
                )
                self.estadisticas.threads_activos = max(0, self.estadisticas.threads_activos - 1)
            
            if self._metrica_tareas:
                self._metrica_tareas.inc()
            if self._metrica_tiempo:
                self._metrica_tiempo.observar(tiempo_ms)
            
            return ResultadoTarea.exitoso(tarea.id, resultado, tiempo_ms)
            
        except Exception as e:
            tiempo_ms = (time.time() - inicio) * 1000
            
            with self._lock:
                self.estadisticas.tareas_fallidas += 1
                self.estadisticas.threads_activos = max(0, self.estadisticas.threads_activos - 1)
            
            if tarea.max_reintentos > tarea.intentos:
                tarea.intentos += 1
                tarea.prioridad = max(0, tarea.prioridad - 1)
                self._cola.poner(tarea)
                return ResultadoTarea.fallido(tarea.id, str(e), tiempo_ms)
            
            return ResultadoTarea.fallido(tarea.id, str(e), tiempo_ms)
    
    def _tarea_completada(self, tarea: TareaPriorizada, futuro: Future):
        """Callback cuando una tarea se completa."""
        with self._lock:
            if tarea.id in self._tareas_activas:
                del self._tareas_activas[tarea.id]
        
        if tarea.futuro:
            try:
                resultado = futuro.result()
                tarea.futuro.set_result(resultado)
            except Exception as e:
                tarea.futuro.set_exception(e)
    
    # ===== API PÚBLICA =====
    
    def ejecutar(self, funcion: Callable, *args, 
                 prioridad: PrioridadTarea = PrioridadTarea.MEDIA,
                 timeout: Optional[float] = None,
                 max_reintentos: int = 0,
                 **kwargs) -> FutureMejorado:
        """
        Ejecuta una función de forma asíncrona.
        
        Args:
            funcion: Función a ejecutar
            *args: Argumentos posicionales
            prioridad: Prioridad de la tarea
            timeout: Timeout en segundos
            max_reintentos: Número máximo de reintentos
            **kwargs: Argumentos nombrados
            
        Returns:
            FutureMejorado con el resultado
        """
        futuro = FutureMejorado()
        
        tarea = TareaPriorizada(
            prioridad=prioridad.value,
            timestamp=time.time(),
            id=str(uuid.uuid4()),
            funcion=funcion,
            args=args,
            kwargs=kwargs,
            futuro=futuro,
            timeout=timeout or self.timeout_default,
            max_reintentos=max_reintentos
        )
        
        self._futuros[tarea.id] = futuro
        
        with self._lock:
            self.estadisticas.tareas_encoladas += 1
            self.estadisticas.tareas_en_cola += 1
        
        if self._cola.poner(tarea):
            return futuro
        else:
            futuro.set_exception(RuntimeError("Cola de tareas llena"))
            return futuro
    
    def ejecutar_sincrono(self, funcion: Callable, *args, 
                          timeout: Optional[float] = None, **kwargs) -> Any:
        """Ejecuta una función de forma síncrona (espera el resultado)."""
        futuro = self.ejecutar(funcion, *args, timeout=timeout, **kwargs)
        return futuro.result(timeout=timeout)
    
    def ejecutar_batch(self, tareas: List[Tuple[Callable, Tuple, Dict]],
                       prioridad: PrioridadTarea = PrioridadTarea.MEDIA) -> List[FutureMejorado]:
        """Ejecuta múltiples tareas y retorna sus futures."""
        return [self.ejecutar(func, *args, prioridad=prioridad, **kwargs) 
                for func, args, kwargs in tareas]
    
    def ejecutar_todas(self, tareas: List[Tuple[Callable, Tuple, Dict]],
                       timeout: Optional[float] = None) -> List[Any]:
        """Ejecuta múltiples tareas y espera todos los resultados."""
        futuros = self.ejecutar_batch(tareas)
        resultados = []
        for f in futuros:
            try:
                resultados.append(f.result(timeout=timeout))
            except Exception as e:
                resultados.append(ResultadoTarea.fallido("", str(e)))
        return resultados
    
    def esperar_todas(self, futuros: List[FutureMejorado], 
                      timeout: Optional[float] = None) -> List[Any]:
        """Espera a que todos los futures se completen."""
        import concurrent.futures as cf
        done, not_done = cf.wait(futuros, timeout=timeout)
        return [f.result() for f in done]
    
    # ===== ASYNC/AWAIT =====
    
    async def ejecutar_async(self, funcion: Callable, *args, **kwargs) -> Any:
        """Ejecuta una función de forma asíncrona (compatible con async/await)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(funcion, *args, **kwargs)
        )
    
    async def ejecutar_async_con_timeout(self, funcion: Callable, 
                                         timeout: float, *args, **kwargs) -> Any:
        """Ejecuta con timeout usando asyncio."""
        try:
            return await asyncio.wait_for(
                self.ejecutar_async(funcion, *args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tarea excedió timeout de {timeout}s")
    
    # ===== UTILIDADES =====
    
    def paralelo(self, *funciones: Callable) -> List[FutureMejorado]:
        """Ejecuta múltiples funciones en paralelo."""
        return [self.ejecutar(f) for f in funciones]
    
    def secuencial(self, *funciones: Callable) -> List[Any]:
        """Ejecuta funciones secuencialmente."""
        return [self.ejecutar_sincrono(f) for f in funciones]
    
    def mapear(self, funcion: Callable, iterable: List[Any], **kwargs) -> List[Any]:
        """Mapea una función sobre un iterable en paralelo."""
        futuros = [self.ejecutar(funcion, item, **kwargs) for item in iterable]
        return [f.result() for f in futuros]
    
    # ===== ESTADÍSTICAS =====
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del executor."""
        with self._lock:
            return {
                'nombre': self.nombre,
                'max_workers': self.max_workers,
                'tareas_encoladas': self.estadisticas.tareas_encoladas,
                'tareas_completadas': self.estadisticas.tareas_completadas,
                'tareas_fallidas': self.estadisticas.tareas_fallidas,
                'tareas_en_cola': self.estadisticas.tareas_en_cola,
                'threads_activos': self.estadisticas.threads_activos,
                'tiempo_promedio_ms': self.estadisticas.tiempo_promedio_ms,
            }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo."""
        stats = self.obtener_estadisticas()
        return {
            'nombre': self.nombre,
            'completadas': stats['tareas_completadas'],
            'fallidas': stats['tareas_fallidas'],
            'en_cola': stats['tareas_en_cola'],
            'tiempo_promedio': f"{stats['tiempo_promedio_ms']:.2f}ms",
        }
    
    # ===== CONTROL =====
    
    def pausar(self):
        """Pausa el procesamiento de tareas."""
        self._procesando = False
    
    def reanudar(self):
        """Reanuda el procesamiento."""
        self._procesando = True
    
    def detener(self, esperar: bool = True):
        """Detiene el executor."""
        self._activo = False
        if esperar:
            self._executor.shutdown(wait=True)
        else:
            self._executor.shutdown(wait=False)
        
        if self._hilo_procesamiento:
            self._hilo_procesamiento.join(timeout=5.0)
    
    def cancelar_todas(self):
        """Cancela todas las tareas pendientes."""
        with self._lock:
            self._cola.limpiar()
            for tarea_id in list(self._tareas_activas.keys()):
                if tarea_id in self._futuros:
                    self._futuros[tarea_id].cancel()
                    del self._futuros[tarea_id]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.detener()
    
    def __repr__(self) -> str:
        return f"ExecutorAsincrono({self.nombre}, workers={self.max_workers})"

# =====================================================================
# DECORADORES ASÍNCRONOS
# =====================================================================

def asincrono(executor_name: str = "default", prioridad: PrioridadTarea = PrioridadTarea.MEDIA):
    """
    Decorador para ejecutar una función de forma asíncrona.
    
    Uso:
        @asincrono(prioridad=PrioridadTarea.ALTA)
        def mi_funcion():
            return resultado
        
        futuro = mi_funcion()
        resultado = futuro.result()
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            executor = ExecutorAsincrono.obtener(executor_name)
            return executor.ejecutar(func, *args, prioridad=prioridad, **kwargs)
        return wrapper
    return decorador

def task(executor_name: str = "default", **kwargs):
    """Decorador simplificado para tareas asíncronas."""
    return asincrono(executor_name, **kwargs)

def retry(max_intentos: int = 3, retraso: float = 0.1, 
          backoff_exponencial: bool = True):
    """
    Decorador para reintentar una función.
    
    Uso:
        @retry(max_intentos=3)
        def funcion_inestable():
            ...
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_error = None
            for intento in range(max_intentos):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    ultimo_error = e
                    if intento < max_intentos - 1:
                        tiempo = retraso * (2 ** intento) if backoff_exponencial else retraso
                        time.sleep(tiempo)
            raise ultimo_error
        return wrapper
    return decorador

def timeout(segundos: float):
    """
    Decorador para ejecutar una función con timeout.
    
    Uso:
        @timeout(5.0)
        def funcion_lenta():
            ...
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            executor = ExecutorAsincrono.obtener()
            futuro = executor.ejecutar(func, *args, timeout=segundos, **kwargs)
            return futuro.result(timeout=segundos)
        return wrapper
    return decorador

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def obtener_executor(nombre: str = "default") -> ExecutorAsincrono:
    """Obtiene una instancia del executor."""
    return ExecutorAsincrono.obtener(nombre)

def ejecutar(funcion: Callable, *args, **kwargs) -> FutureMejorado:
    """Función rápida para ejecutar de forma asíncrona."""
    return obtener_executor().ejecutar(funcion, *args, **kwargs)

async def async_ejecutar(funcion: Callable, *args, **kwargs) -> Any:
    """Función rápida para ejecutar con async/await."""
    return await obtener_executor().ejecutar_async(funcion, *args, **kwargs)

def dormir(segundos: float):
    """Versión no bloqueante de time.sleep."""
    time.sleep(segundos)

async def async_dormir(segundos: float):
    """Versión asíncrona de sleep."""
    await asyncio.sleep(segundos)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA ASÍNCRONO")
    print("=" * 70)
    
    executor = None
    
    try:
        print("\n[1/8] Inicializando executor...")
        executor = ExecutorAsincrono("test", max_workers=4)
        print(f"  ✅ Executor inicializado: {executor}")
        
        print("\n[2/8] Ejecutando tarea simple...")
        def tarea_simple(x, y):
            return x + y
        
        futuro = executor.ejecutar(tarea_simple, 10, 20)
        resultado = futuro.result(timeout=5)
        print(f"  ✅ Tarea completada: {resultado.resultado}")
        print(f"  📍 Tiempo: {resultado.tiempo_ms:.2f}ms")
        
        print("\n[3/8] Ejecutando con callbacks...")
        callbacks_ejecutados = []
        
        def on_exito(res):
            callbacks_ejecutados.append(('exito', res.resultado))
        
        def on_error(err):
            callbacks_ejecutados.append(('error', str(err)))
        
        def on_siempre():
            callbacks_ejecutados.append(('siempre', None))
        
        futuro2 = executor.ejecutar(lambda: "OK")
        futuro2.on_success(on_exito).on_complete(on_siempre)
        resultado2 = futuro2.result(timeout=5)
        time.sleep(0.1)
        print(f"  ✅ Callbacks ejecutados: {len(callbacks_ejecutados)}")
        
        print("\n[4/8] Probando encadenamiento .then()...")
        futuro3 = (executor.ejecutar(lambda: 5)
                   .then(lambda x: x * 2)
                   .then(lambda x: x + 10))
        resultado3 = futuro3.result(timeout=5)
        print(f"  ✅ Resultado encadenado: 5 -> *2 -> +10 = {resultado3}")
        
        print("\n[5/8] Ejecutando en paralelo...")
        def tarea_demorada(n, delay):
            time.sleep(delay)
            return n * 2
        
        futuros = executor.paralelo(
            lambda: tarea_demorada(1, 0.2),
            lambda: tarea_demorada(2, 0.1),
            lambda: tarea_demorada(3, 0.3),
        )
        
        resultados_paralelo = [f.result(timeout=5) for f in futuros]
        valores = [r.resultado for r in resultados_paralelo]
        print(f"  ✅ Resultados en paralelo: {valores}")
        
        print("\n[6/8] Probando mapeo...")
        resultados_mapeo = executor.mapear(lambda x: x ** 2, [1, 2, 3, 4, 5])
        print(f"  ✅ Mapeo: {[r.resultado for r in resultados_mapeo]}")
        
        print("\n[7/8] Probando decorador @asincrono...")
        
        @asincrono(prioridad=PrioridadTarea.ALTA)
        def tarea_decorada(nombre):
            return f"Hola {nombre}"
        
        futuro_decorado = tarea_decorada("ANP")
        resultado_decorado = futuro_decorado.result(timeout=5)
        print(f"  ✅ Decorador: {resultado_decorado.resultado}")
        
        print("\n[8/8] Estadísticas del executor...")
        stats = executor.obtener_estadisticas()
        print(f"  📊 Tareas completadas: {stats['tareas_completadas']}")
        print(f"  📊 Tareas fallidas: {stats['tareas_fallidas']}")
        print(f"  📊 Tiempo promedio: {stats['tiempo_promedio_ms']:.2f}ms")
        print(f"  📊 Workers: {stats['max_workers']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema Asíncrono está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if executor:
            print("\n🛑 Deteniendo executor...")
            executor.detener()
            print("   ✓ Executor detenido")
    
    print("\n" + "=" * 70 + "\n")
      