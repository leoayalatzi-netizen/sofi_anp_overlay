#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Núcleo Base (El ADN de Todos los Núcleos Especializados)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo contiene la clase abstracta fundamental
# de la que heredarán TODOS los núcleos de ANP. Es el contrato sagrado
# que define qué es un núcleo, cómo se comporta, y cómo se comunica
# con el orquestador y el resto del sistema.
# =====================================================================

import sys
import os
import time
import uuid
import threading
import asyncio
import traceback
import json
import hashlib
import math
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator, Awaitable
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict, Counter
from abc import ABC, ABCMeta, abstractmethod
from functools import wraps, lru_cache
from contextlib import contextmanager

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .motor_base import MotorBase, EstadoMotor, ConfiguracionMotor, ResultadoMotor
except ImportError:
    class EstadoMotor(Enum):
        NO_INICIALIZADO = "no_inicializado"
        ACTIVO = "activo"
        DETENIDO = "detenido"
        ERROR = "error"
    
    class MotorBase(ABC):
        pass
    
    @dataclass
    class ConfiguracionMotor:
        nombre: str = ""
    
    @dataclass
    class ResultadoMotor:
        exito: bool = True
        datos: Any = None
        error: Optional[str] = None

try:
    from ..bus_eventos import Evento, TipoEvento, PrioridadEvento, publicar, suscribir, obtener_bus
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
        NUCLEO_REGISTRADO = "nucleo.registrado"
        NUCLEO_ACTIVADO = "nucleo.activado"
        NUCLEO_DESACTIVADO = "nucleo.desactivado"
        NUCLEO_DEGRADADO = "nucleo.degradado"
        NUCLEO_FALLBACK = "nucleo.fallback"
        NUCLEO_ERROR = "nucleo.error"
        NUCLEO_LATIDO = "nucleo.latido"
        NUCLEO_METRICA = "nucleo.metrica"
        TAREA_RECIBIDA = "tarea.recibida"
        TAREA_COMPLETADA = "tarea.completada"
        TAREA_FALLIDA = "tarea.fallida"
    
    class PrioridadEvento(IntEnum):
        CRITICA = 0
        ALTA = 1
        MEDIA = 2
        BAJA = 3
        DIFERIDA = 4
    
    def publicar(tipo, datos=None, origen="", prioridad=2, **kwargs):
        pass
    
    def suscribir(patron, callback, prioridad=2):
        pass
    
    def obtener_bus():
        return None

try:
    from ..contexto.contexto import Contexto
except ImportError:
    class Contexto:
        pass

try:
    from ..orquestador.maestro import Orquestador, obtener_orquestador
except ImportError:
    class Orquestador:
        def registrar_nucleo(self, nombre, version, metadatos): return True
        def latido_nucleo(self, nombre, carga): return True
    
    def obtener_orquestador():
        return Orquestador()

try:
    from ..fallback import GestorFallback, obtener_gestor_fallback
except ImportError:
    class GestorFallback:
        def activar_fallback(self, motivo, contexto): return "Fallback activado"
        def esta_en_fallback(self): return False
    
    def obtener_gestor_fallback():
        return GestorFallback()

try:
    from ..metricas import Metrica, RecolectorMetricas
except ImportError:
    class Metrica:
        pass

# =====================================================================
# ENUMERACIONES FUNDAMENTALES
# =====================================================================

class PrioridadNucleo(IntEnum):
    """
    Prioridad del núcleo en el sistema.
    P0 = ESENCIAL (si falla, el sistema colapsa)
    P1 = ALTA (si falla, el sistema se degrada significativamente)
    P2 = MEDIA (si falla, funcionalidad reducida)
    P3 = BAJA (si falla, apenas se nota)
    """
    P0_ESENCIAL = 0
    P1_ALTA = 1
    P2_MEDIA = 2
    P3_BAJA = 3
    P4_AUXILIAR = 4
    P5_EXPERIMENTAL = 5

class EstadoNucleo(Enum):
    """Estados del ciclo de vida de un núcleo."""
    NO_INICIALIZADO = "no_inicializado"
    INICIALIZANDO = "inicializando"
    REGISTRANDO = "registrando"
    ACTIVO = "activo"
    DEGRADADO = "degradado"
    FALLBACK = "fallback"
    PAUSADO = "pausado"
    RECUPERANDO = "recuperando"
    DETENIENDO = "deteniendo"
    DETENIDO = "detenido"
    ERROR = "error"
    DESTRUIDO = "destruido"

class ModoOperacionNucleo(Enum):
    """Modos de operación del núcleo."""
    NORMAL = "normal"
    DEGRADADO = "degradado"
    FALLBACK = "fallback"
    MANTENIMIENTO = "mantenimiento"
    APRENDIZAJE = "aprendizaje"
    OPTIMIZACION = "optimizacion"

class CapacidadNucleo(Enum):
    """Capacidades que un núcleo puede declarar."""
    PROCESAMIENTO_SINCRONO = "procesamiento_sincrono"
    PROCESAMIENTO_ASINCRONO = "procesamiento_asincrono"
    PROCESAMIENTO_BATCH = "procesamiento_batch"
    PROCESAMIENTO_STREAMING = "procesamiento_streaming"
    PARALELIZABLE = "paralelizable"
    CACHEABLE = "cacheable"
    CON_ESTADO = "con_estado"
    SIN_ESTADO = "sin_estado"
    PERSISTENTE = "persistente"
    AUTO_RECUPERABLE = "auto_recuperable"
    FALLBACK_HABILITADO = "fallback_habilitado"
    METRICAS_HABILITADAS = "metricas_habilitadas"
    EVENTOS_HABILITADOS = "eventos_habilitados"

class TipoMotorNucleo(Enum):
    """Tipos de motores que puede contener un núcleo."""
    PRINCIPAL = "principal"
    SECUNDARIO = "secundario"
    FALLBACK = "fallback"
    AUXILIAR = "auxiliar"
    OPTIMIZACION = "optimizacion"
    VALIDACION = "validacion"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class MetadatosNucleo:
    """Metadatos que describen un núcleo."""
    nombre: str = ""
    version: str = "0.0.1"
    autor: str = "ANP Team"
    descripcion: str = ""
    prioridad: PrioridadNucleo = PrioridadNucleo.P2_MEDIA
    capacidades: Set[CapacidadNucleo] = field(default_factory=set)
    dependencias: List[str] = field(default_factory=list)
    nucleo_fallback: Optional[str] = None
    timeout_default: float = 30.0
    max_reintentos: int = 3
    intervalo_latido: float = 5.0
    tags: List[str] = field(default_factory=list)
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'nombre': self.nombre,
            'version': self.version,
            'autor': self.autor,
            'descripcion': self.descripcion,
            'prioridad': self.prioridad.name,
            'capacidades': [c.value for c in self.capacidades],
            'dependencias': self.dependencias,
            'nucleo_fallback': self.nucleo_fallback,
            'tags': self.tags,
        }

@dataclass
class EstadisticasNucleo:
    """Estadísticas acumuladas del núcleo."""
    total_tareas: int = 0
    total_exitos: int = 0
    total_fallos: int = 0
    total_fallbacks: int = 0
    tiempo_total_procesamiento: float = 0.0
    tiempo_promedio_ms: float = 0.0
    tiempo_max_ms: float = 0.0
    tiempo_min_ms: float = float('inf')
    ultimo_latido: float = field(default_factory=time.time)
    ultimo_exito: Optional[float] = None
    ultimo_fallo: Optional[float] = None
    carga_actual: int = 0
    carga_maxima: int = 100
    reintentos_realizados: int = 0
    
    def registrar_exito(self, tiempo_ms: float):
        self.total_tareas += 1
        self.total_exitos += 1
        self.tiempo_total_procesamiento += tiempo_ms
        self.tiempo_promedio_ms = self.tiempo_total_procesamiento / self.total_exitos
        self.tiempo_max_ms = max(self.tiempo_max_ms, tiempo_ms)
        self.tiempo_min_ms = min(self.tiempo_min_ms, tiempo_ms)
        self.ultimo_exito = time.time()
        self.carga_actual = max(0, self.carga_actual - 1)
    
    def registrar_fallo(self, tiempo_ms: float = 0.0):
        self.total_tareas += 1
        self.total_fallos += 1
        self.ultimo_fallo = time.time()
        self.carga_actual = max(0, self.carga_actual - 1)
    
    def registrar_fallback(self):
        self.total_fallbacks += 1
    
    @property
    def tasa_exito(self) -> float:
        if self.total_tareas == 0:
            return 1.0
        return self.total_exitos / self.total_tareas
    
    @property
    def carga_porcentaje(self) -> float:
        return (self.carga_actual / self.carga_maxima) * 100 if self.carga_maxima > 0 else 0
    
    @property
    def saludable(self) -> bool:
        return self.tasa_exito >= 0.95 and self.carga_porcentaje < 80

@dataclass
class ResultadoNucleo:
    """Resultado del procesamiento de un núcleo."""
    exito: bool
    datos: Any = None
    error: Optional[str] = None
    nucleo_usado: str = ""
    modo_usado: ModoOperacionNucleo = ModoOperacionNucleo.NORMAL
    tiempo_ejecucion_ms: float = 0.0
    fallback_activado: bool = False
    metadatos: Dict[str, Any] = field(default_factory=dict)
    metricas: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def exitoso(cls, datos: Any, tiempo_ms: float = 0.0, **metadatos) -> 'ResultadoNucleo':
        return cls(exito=True, datos=datos, tiempo_ejecucion_ms=tiempo_ms, metadatos=metadatos)
    
    @classmethod
    def fallido(cls, error: str, tiempo_ms: float = 0.0, **metadatos) -> 'ResultadoNucleo':
        return cls(exito=False, error=error, tiempo_ejecucion_ms=tiempo_ms, metadatos=metadatos)
    
    @classmethod
    def fallback(cls, datos: Any, nucleo_original: str, tiempo_ms: float = 0.0) -> 'ResultadoNucleo':
        return cls(
            exito=True, datos=datos, tiempo_ejecucion_ms=tiempo_ms,
            modo_usado=ModoOperacionNucleo.FALLBACK, fallback_activado=True,
            metadatos={'nucleo_original': nucleo_original}
        )

@dataclass
class RegistroMotor:
    """Registro de un motor dentro del núcleo."""
    motor: MotorBase
    tipo: TipoMotorNucleo
    prioridad: int = 50
    peso: float = 1.0
    activo: bool = True
    metricas: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# DECORADORES PARA NÚCLEOS
# =====================================================================

def requiere_estado(estados: List[EstadoNucleo]):
    """Decorador que verifica que el núcleo esté en un estado específico."""
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.estado not in estados:
                raise RuntimeError(
                    f"Núcleo debe estar en uno de estos estados: {[s.value for s in estados]}, "
                    f"actual: {self.estado.value}"
                )
            return func(self, *args, **kwargs)
        return wrapper
    return decorador

def medir_tiempo_nucleo(func: Callable) -> Callable:
    """Decorador para medir tiempo de ejecución en el núcleo."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        inicio = time.time()
        try:
            resultado = func(self, *args, **kwargs)
            tiempo_ms = (time.time() - inicio) * 1000
            self._registrar_metrica("tiempo_ejecucion", tiempo_ms, "ms", {"metodo": func.__name__})
            return resultado
        except Exception as e:
            tiempo_ms = (time.time() - inicio) * 1000
            self._registrar_metrica("tiempo_error", tiempo_ms, "ms", {"metodo": func.__name__, "error": str(e)})
            raise
    return wrapper

def publica_evento_nucleo(tipo_evento: str):
    """Decorador que publica un evento al ejecutar el método."""
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            resultado = func(self, *args, **kwargs)
            self._publicar_evento(tipo_evento, {
                'metodo': func.__name__,
                'resultado': str(resultado)[:100] if resultado else None,
            })
            return resultado
        return wrapper
    return decorador

def con_fallback(motivo: str = "fallo_en_procesamiento"):
    """Decorador que activa fallback si el método falla."""
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if self.tiene_capacidad(CapacidadNucleo.FALLBACK_HABILITADO):
                    return self._activar_fallback_y_procesar(
                        f"{motivo}: {str(e)}", args, kwargs
                    )
                raise
        return wrapper
    return decorador

# =====================================================================
# METACLASE PARA REGISTRO AUTOMÁTICO DE NÚCLEOS
# =====================================================================

class MetaNucleo(ABCMeta):
    """Metaclase que registra automáticamente todos los núcleos."""
    
    _nucleos_registrados: Dict[str, Type] = {}
    _lock = threading.RLock()
    
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        
        if not namespace.get('__abstract__', False):
            with mcs._lock:
                mcs._nucleos_registrados[name] = cls
        
        return cls
    
    @classmethod
    def obtener_nucleo(mcs, nombre: str) -> Optional[Type]:
        return mcs._nucleos_registrados.get(nombre)
    
    @classmethod
    def listar_nucleos(mcs) -> List[str]:
        return list(mcs._nucleos_registrados.keys())

# =====================================================================
# NÚCLEO BASE - LA OBRA MAESTRA
# =====================================================================


class NucleoBase(ABC, metaclass=MetaNucleo):
    """
    Núcleo Base de ANP - El ADN de Todos los Núcleos Especializados.
    
    Esta clase abstracta define el contrato fundamental que TODO núcleo
    en ANP debe cumplir. Es el corazón de la inteligencia del sistema.
    
    Capacidades:
    - Gestión de motores internos (principal, secundario, fallback)
    - Ciclo de vida completo (inicializar, procesar, detener)
    - Comunicación con el orquestador (latidos, registro)
    - Sistema de fallback integrado
    - Métricas y estadísticas en tiempo real
    - Publicación de eventos al bus
    - Modos de operación (NORMAL, DEGRADADO, FALLBACK)
    - Prioridades P0-P5
    - Contexto compartido
    """
    
    # ===== METADATOS DE CLASE =====
    __abstract__: ClassVar[bool] = False
    
    # Metadatos del núcleo (sobrescribir en subclases)
    METADATOS: ClassVar[MetadatosNucleo] = MetadatosNucleo(
        nombre="NucleoBase",
        descripcion="Núcleo base abstracto",
        prioridad=PrioridadNucleo.P2_MEDIA,
        capacidades={
            CapacidadNucleo.PROCESAMIENTO_SINCRONO,
            CapacidadNucleo.METRICAS_HABILITADAS,
        }
    )
    
    def __init__(self, contexto: Optional[Contexto] = None):
        """
        Inicializa el núcleo base.
        
        Args:
            contexto: Contexto compartido (opcional)
        """
        # Identidad
        self._id = str(uuid.uuid4())
        self.nombre = self.__class__.__name__
        
        # Estado
        self._estado = EstadoNucleo.NO_INICIALIZADO
        self._modo = ModoOperacionNucleo.NORMAL
        
        # Contexto
        self._contexto = contexto
        
        # Motores
        self._motores: Dict[str, RegistroMotor] = {}
        self._motor_principal: Optional[str] = None
        self._motor_fallback: Optional[str] = None
        
        # Estadísticas
        self.estadisticas = EstadisticasNucleo()
        
        # Control de concurrencia
        self._lock = threading.RLock()
        self._procesando = False
        self._tareas_pendientes: deque = deque()
        
        # Comunicación
        self._orquestador: Optional[Orquestador] = None
        self._gestor_fallback: Optional[GestorFallback] = None
        self._suscripciones: List[str] = []
        self._latido_activo = False
        self._hilo_latido: Optional[threading.Thread] = None
        
        # Métricas
        self._metricas_pendientes: List[Dict] = []
        
        # Inicializar motores por defecto
        self._inicializar_motores()
    
    # ===== PROPIEDADES =====
    
    @property
    def id_nucleo(self) -> str:
        return self._id
    
    @property
    def estado(self) -> EstadoNucleo:
        return self._estado
    
    @property
    def modo(self) -> ModoOperacionNucleo:
        return self._modo
    
    @property
    def contexto(self) -> Optional[Contexto]:
        return self._contexto
    
    @property
    def esta_activo(self) -> bool:
        return self._estado == EstadoNucleo.ACTIVO
    
    @property
    def puede_procesar(self) -> bool:
        return self._estado in (EstadoNucleo.ACTIVO, EstadoNucleo.DEGRADADO, EstadoNucleo.FALLBACK)
    
    @property
    def carga_actual(self) -> int:
        return self.estadisticas.carga_actual
    
    # ===== MÉTODOS DE CAPACIDADES =====
    
    @classmethod
    def tiene_capacidad(cls, capacidad: CapacidadNucleo) -> bool:
        return capacidad in cls.METADATOS.capacidades
    
    @classmethod
    def listar_capacidades(cls) -> List[str]:
        return [c.value for c in cls.METADATOS.capacidades]
    
    @classmethod
    def obtener_ficha_tecnica(cls) -> Dict[str, Any]:
        return cls.METADATOS.a_dict()
    
    @classmethod
    def prioridad(cls) -> PrioridadNucleo:
        return cls.METADATOS.prioridad
    
    # ===== GESTIÓN DE MOTORES =====
    
    def _inicializar_motores(self):
        """Inicializa los motores del núcleo. Sobrescribir en subclases."""
        pass
    
    def registrar_motor(self, nombre: str, motor: MotorBase, 
                        tipo: TipoMotorNucleo = TipoMotorNucleo.PRINCIPAL,
                        prioridad: int = 50, peso: float = 1.0) -> bool:
        """Registra un motor en el núcleo."""
        with self._lock:
            if nombre in self._motores:
                return False
            
            registro = RegistroMotor(
                motor=motor,
                tipo=tipo,
                prioridad=prioridad,
                peso=peso
            )
            self._motores[nombre] = registro
            
            if tipo == TipoMotorNucleo.PRINCIPAL and self._motor_principal is None:
                self._motor_principal = nombre
            elif tipo == TipoMotorNucleo.FALLBACK and self._motor_fallback is None:
                self._motor_fallback = nombre
            
            return True
    
    def obtener_motor(self, nombre: str) -> Optional[MotorBase]:
        """Obtiene un motor por nombre."""
        registro = self._motores.get(nombre)
        return registro.motor if registro else None
    
    def obtener_motor_principal(self) -> Optional[MotorBase]:
        """Obtiene el motor principal."""
        if self._motor_principal:
            return self.obtener_motor(self._motor_principal)
        return None
    
    def obtener_motor_fallback(self) -> Optional[MotorBase]:
        """Obtiene el motor de fallback."""
        if self._motor_fallback:
            return self.obtener_motor(self._motor_fallback)
        return None
    
    def listar_motores(self) -> List[str]:
        """Lista todos los motores registrados."""
        return list(self._motores.keys())
    
    def _inicializar_motores_internos(self) -> bool:
        """Inicializa todos los motores registrados."""
        for nombre, registro in self._motores.items():
            if registro.activo:
                if not registro.motor.inicializar(self._contexto):
                    return False
        return True
    
    def _detener_motores_internos(self):
        """Detiene todos los motores registrados."""
        for nombre, registro in self._motores.items():
            if registro.activo:
                registro.motor.detener()
    
    # ===== CICLO DE VIDA =====
    
    @publica_evento_nucleo("nucleo.inicializando")
    def inicializar(self, contexto: Optional[Contexto] = None) -> bool:
        """
        Inicializa el núcleo.
        
        Args:
            contexto: Contexto compartido (opcional)
            
        Returns:
            True si se inicializó correctamente
        """
        with self._lock:
            if self._estado != EstadoNucleo.NO_INICIALIZADO:
                return False
            
            self._estado = EstadoNucleo.INICIALIZANDO
            
            try:
                if contexto:
                    self._contexto = contexto
                
                # Inicializar motores
                if not self._inicializar_motores_internos():
                    self._estado = EstadoNucleo.ERROR
                    return False
                
                # Hook de inicialización
                if not self._on_inicializar():
                    self._estado = EstadoNucleo.ERROR
                    return False
                
                self._estado = EstadoNucleo.REGISTRANDO
                
                # Registrar en orquestador
                self._registrar_en_orquestador()
                
                self._estado = EstadoNucleo.ACTIVO
                
                # Iniciar latido
                self._iniciar_latido()
                
                self._publicar_evento(TipoEvento.NUCLEO_ACTIVADO, {
                    'id': self._id,
                    'nombre': self.nombre,
                    'capacidades': self.listar_capacidades(),
                })
                
                return True
                
            except Exception as e:
                self._estado = EstadoNucleo.ERROR
                self.estadisticas.registrar_fallo()
                self._publicar_evento(TipoEvento.NUCLEO_ERROR, {'error': str(e)})
                return False
    
    @publica_evento_nucleo("nucleo.deteniendo")
    def detener(self) -> bool:
        """
        Detiene el núcleo.
        
        Returns:
            True si se detuvo correctamente
        """
        with self._lock:
            if self._estado in (EstadoNucleo.DETENIDO, EstadoNucleo.DESTRUIDO):
                return False
            
            self._estado = EstadoNucleo.DETENIENDO
            
            try:
                # Detener latido
                self._detener_latido()
                
                # Detener motores
                self._detener_motores_internos()
                
                # Hook de detención
                self._on_detener()
                
                self._flush_metricas()
                self._estado = EstadoNucleo.DETENIDO
                
                self._publicar_evento(TipoEvento.NUCLEO_DESACTIVADO, {
                    'id': self._id,
                    'nombre': self.nombre,
                    'estadisticas': asdict(self.estadisticas),
                })
                
                return True
                
            except Exception as e:
                self._estado = EstadoNucleo.ERROR
                return False
    
    def pausar(self) -> bool:
        """Pausa el núcleo."""
        with self._lock:
            if self._estado != EstadoNucleo.ACTIVO:
                return False
            self._estado = EstadoNucleo.PAUSADO
            return self._on_pausar()
    
    def reanudar(self) -> bool:
        """Reanuda el núcleo."""
        with self._lock:
            if self._estado != EstadoNucleo.PAUSADO:
                return False
            self._estado = EstadoNucleo.ACTIVO
            return self._on_reanudar()
    
    def degradar(self, motivo: str = "") -> bool:
        """Degrada el núcleo a modo degradado."""
        with self._lock:
            if self._estado != EstadoNucleo.ACTIVO:
                return False
            self._estado = EstadoNucleo.DEGRADADO
            self._modo = ModoOperacionNucleo.DEGRADADO
            self._publicar_evento(TipoEvento.NUCLEO_DEGRADADO, {'motivo': motivo})
            return True
    
    def recuperar(self) -> bool:
        """Recupera el núcleo de estado degradado."""
        with self._lock:
            if self._estado not in (EstadoNucleo.DEGRADADO, EstadoNucleo.FALLBACK):
                return False
            self._estado = EstadoNucleo.RECUPERANDO
            if self._on_recuperar():
                self._estado = EstadoNucleo.ACTIVO
                self._modo = ModoOperacionNucleo.NORMAL
                return True
            return False
    
    # ===== HOOKS (para sobrescribir en subclases) =====
    
    def _on_inicializar(self) -> bool:
        """Hook de inicialización."""
        return True
    
    def _on_detener(self):
        """Hook de detención."""
        pass
    
    def _on_pausar(self) -> bool:
        """Hook de pausa."""
        return True
    
    def _on_reanudar(self) -> bool:
        """Hook de reanudación."""
        return True
    
    def _on_recuperar(self) -> bool:
        """Hook de recuperación."""
        return True
    
    # ===== PROCESAMIENTO =====
    
    @abstractmethod
    def _procesar_impl(self, entrada: Any, contexto: Optional[Contexto] = None) -> Any:
        """
        Implementación concreta del procesamiento.
        DEBE ser sobrescrito por todas las subclases.
        """
        raise NotImplementedError("Las subclases deben implementar _procesar_impl")
    
    @medir_tiempo_nucleo
    @requiere_estado([EstadoNucleo.ACTIVO, EstadoNucleo.DEGRADADO, EstadoNucleo.FALLBACK])
    def procesar(self, entrada: Any, contexto: Optional[Contexto] = None) -> ResultadoNucleo:
        """
        Procesa una entrada.
        
        Args:
            entrada: Datos de entrada
            contexto: Contexto compartido
            
        Returns:
            ResultadoNucleo con el resultado o error
        """
        with self._lock:
            if self._procesando and not self.tiene_capacidad(CapacidadNucleo.PARALELIZABLE):
                self._tareas_pendientes.append((entrada, contexto))
                return ResultadoNucleo.fallido("Núcleo ocupado, tarea encolada")
            
            self._procesando = True
            self.estadisticas.carga_actual += 1
        
        ctx = contexto if contexto is not None else self._contexto
        inicio = time.time()
        
        try:
            # Publicar evento de tarea recibida
            self._publicar_evento(TipoEvento.TAREA_RECIBIDA, {
                'nucleo': self.nombre,
                'modo': self._modo.value,
            })
            
            # Procesar según el modo
            if self._modo == ModoOperacionNucleo.FALLBACK:
                resultado_datos = self._procesar_fallback(entrada, ctx)
                fallback_activado = True
            else:
                resultado_datos = self._procesar_impl(entrada, ctx)
                fallback_activado = False
            
            tiempo_ms = (time.time() - inicio) * 1000
            self.estadisticas.registrar_exito(tiempo_ms)
            
            resultado = ResultadoNucleo.exitoso(
                datos=resultado_datos,
                tiempo_ms=tiempo_ms,
                nucleo=self.nombre,
                modo=self._modo,
                fallback=fallback_activado
            )
            resultado.nucleo_usado = self.nombre
            resultado.modo_usado = self._modo
            
            self._publicar_evento(TipoEvento.TAREA_COMPLETADA, {
                'nucleo': self.nombre,
                'tiempo_ms': tiempo_ms,
            })
            
            return resultado
            
        except Exception as e:
            tiempo_ms = (time.time() - inicio) * 1000
            self.estadisticas.registrar_fallo(tiempo_ms)
            
            self._publicar_evento(TipoEvento.TAREA_FALLIDA, {
                'nucleo': self.nombre,
                'error': str(e),
            })
            
            # Intentar fallback si está habilitado
            if self.tiene_capacidad(CapacidadNucleo.FALLBACK_HABILITADO) and self._modo != ModoOperacionNucleo.FALLBACK:
                return self._activar_fallback_y_procesar(str(e), (entrada,), {'contexto': ctx})
            
            return ResultadoNucleo.fallido(
                error=str(e),
                tiempo_ms=tiempo_ms,
                nucleo=self.nombre,
                modo=self._modo
            )
            
        finally:
            self._procesando = False
            self._procesar_siguiente_tarea()
    
    def _procesar_fallback(self, entrada: Any, contexto: Optional[Contexto] = None) -> Any:
        """Procesa en modo fallback."""
        motor_fallback = self.obtener_motor_fallback()
        if motor_fallback:
            resultado = motor_fallback.procesar(entrada, contexto)
            if resultado.exito:
                return resultado.datos
        
        # Fallback último recurso
        if self._gestor_fallback:
            respuesta = self._gestor_fallback.activar_fallback(
                f"Fallo en núcleo {self.nombre}",
                {'entrada': str(entrada)[:100]}
            )
            return respuesta
        
        raise RuntimeError(f"Núcleo {self.nombre} en fallback sin capacidad de procesar")
    
    def _activar_fallback_y_procesar(self, motivo: str, args: Tuple, kwargs: Dict) -> ResultadoNucleo:
        """Activa el modo fallback y procesa."""
        with self._lock:
            self._modo = ModoOperacionNucleo.FALLBACK
            self.estadisticas.registrar_fallback()
            self._publicar_evento(TipoEvento.NUCLEO_FALLBACK, {'motivo': motivo})
        
        return self.procesar(*args, **kwargs)
    
    def _procesar_siguiente_tarea(self):
        """Procesa la siguiente tarea encolada."""
        if self._tareas_pendientes:
            entrada, contexto = self._tareas_pendientes.popleft()
            threading.Thread(target=self.procesar, args=(entrada, contexto), daemon=True).start()
    
    async def procesar_async(self, entrada: Any, contexto: Optional[Contexto] = None) -> ResultadoNucleo:
        """Versión asíncrona del procesamiento."""
        if not self.tiene_capacidad(CapacidadNucleo.PROCESAMIENTO_ASINCRONO):
            raise RuntimeError("Este núcleo no soporta procesamiento asíncrono")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.procesar, entrada, contexto)
    
    def procesar_batch(self, entradas: List[Any], contexto: Optional[Contexto] = None) -> List[ResultadoNucleo]:
        """Procesa un lote de entradas."""
        if not self.tiene_capacidad(CapacidadNucleo.PROCESAMIENTO_BATCH):
            raise RuntimeError("Este núcleo no soporta procesamiento batch")
        
        return [self.procesar(entrada, contexto) for entrada in entradas]
    
    # ===== COMUNICACIÓN CON ORQUESTADOR =====
    
    def _registrar_en_orquestador(self):
        """Registra el núcleo en el orquestador."""
        try:
            self._orquestador = obtener_orquestador()
            self._orquestador.registrar_nucleo(
                self.nombre,
                version=self.METADATOS.version,
                metadatos=self.METADATOS.a_dict()
            )
        except Exception as e:
            self._publicar_evento(TipoEvento.NUCLEO_ERROR, {'error': f"Registro fallido: {e}"})
    
    def _iniciar_latido(self):
        """Inicia el hilo de latido."""
        self._latido_activo = True
        self._hilo_latido = threading.Thread(target=self._bucle_latido, daemon=True)
        self._hilo_latido.start()
    
    def _detener_latido(self):
        """Detiene el hilo de latido."""
        self._latido_activo = False
        if self._hilo_latido:
            self._hilo_latido.join(timeout=2.0)
    
    def _bucle_latido(self):
        """Bucle de envío de latidos al orquestador."""
        while self._latido_activo:
            try:
                if self._orquestador and self.esta_activo:
                    self._orquestador.latido_nucleo(self.nombre, self.estadisticas.carga_actual)
                    self.estadisticas.ultimo_latido = time.time()
                    
                    self._publicar_evento(TipoEvento.NUCLEO_LATIDO, {
                        'carga': self.estadisticas.carga_actual,
                        'tasa_exito': self.estadisticas.tasa_exito,
                    })
            except Exception:
                pass
            
            time.sleep(self.METADATOS.intervalo_latido)
    
    # ===== MÉTRICAS Y EVENTOS =====
    
    def _registrar_metrica(self, nombre: str, valor: float, unidad: str = "count", tags: Dict = None):
        """Registra una métrica."""
        if not self.tiene_capacidad(CapacidadNucleo.METRICAS_HABILITADAS):
            return
        
        metrica = {
            'nombre': f"{self.nombre}.{nombre}",
            'valor': valor,
            'unidad': unidad,
            'timestamp': time.time(),
            'tags': tags or {},
        }
        self._metricas_pendientes.append(metrica)
        
        if len(self._metricas_pendientes) >= 10:
            self._flush_metricas()
    
    def _flush_metricas(self):
        """Envía todas las métricas pendientes."""
        for metrica in self._metricas_pendientes:
            self._publicar_evento(TipoEvento.NUCLEO_METRICA, metrica)
        self._metricas_pendientes.clear()
    
    def _publicar_evento(self, tipo: str, datos: Dict[str, Any]):
        """Publica un evento al bus."""
        if not self.tiene_capacidad(CapacidadNucleo.EVENTOS_HABILITADOS):
            return
        
        datos_completos = {
            'nucleo_id': self._id,
            'nucleo_nombre': self.nombre,
            'nucleo_estado': self._estado.value,
            'nucleo_modo': self._modo.value,
            **datos,
        }
        
        try:
            publicar(tipo, datos_completos, origen=f"nucleo.{self.nombre}", prioridad=PrioridadEvento.MEDIA)
        except Exception:
            pass
    
    def suscribir_a_eventos(self, patron: str, callback: Callable):
        """Suscribe un callback a eventos del bus."""
        try:
            suscribir(patron, callback)
            self._suscripciones.append(patron)
        except Exception:
            pass
    
    # ===== ESTADÍSTICAS =====
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del núcleo."""
        return {
            'id': self._id,
            'nombre': self.nombre,
            'estado': self._estado.value,
            'modo': self._modo.value,
            'capacidades': self.listar_capacidades(),
            'estadisticas': asdict(self.estadisticas),
            'motores': {
                nombre: {
                    'tipo': reg.tipo.value,
                    'activo': reg.activo,
                    'estado': reg.motor.estado.value if hasattr(reg.motor, 'estado') else 'desconocido',
                }
                for nombre, reg in self._motores.items()
            },
            'tareas_pendientes': len(self._tareas_pendientes),
        }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo del núcleo."""
        return {
            'nombre': self.nombre,
            'estado': self._estado.value,
            'modo': self._modo.value,
            'tareas': self.estadisticas.total_tareas,
            'tasa_exito': f"{self.estadisticas.tasa_exito:.1%}",
            'carga': f"{self.estadisticas.carga_porcentaje:.0f}%",
            'tiempo_promedio': f"{self.estadisticas.tiempo_promedio_ms:.2f}ms",
        }
    
    # ===== MÉTODOS MÁGICOS =====
    
    def __repr__(self) -> str:
        return f"{self.nombre}(id={self._id[:8]}, estado={self._estado.value}, modo={self._modo.value})"
    
    def __str__(self) -> str:
        return f"Núcleo {self.nombre} [{self._estado.value}] - {self.METADATOS.prioridad.name}"
    
    def __enter__(self):
        self.inicializar()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.detener()

# =====================================================================
# EJEMPLO DE NÚCLEO CONCRETO (para demostración)
# =====================================================================

class NucleoEjemplo(NucleoBase):
    """Núcleo de ejemplo que demuestra el uso de NucleoBase."""
    
    METADATOS = MetadatosNucleo(
        nombre="NucleoEjemplo",
        version="1.0.0",
        autor="ANP Team",
        descripcion="Núcleo de ejemplo para demostración",
        prioridad=PrioridadNucleo.P2_MEDIA,
        capacidades={
            CapacidadNucleo.PROCESAMIENTO_SINCRONO,
            CapacidadNucleo.PROCESAMIENTO_ASINCRONO,
            CapacidadNucleo.METRICAS_HABILITADAS,
            CapacidadNucleo.EVENTOS_HABILITADOS,
            CapacidadNucleo.FALLBACK_HABILITADO,
        },
        nucleo_fallback="NucleoEjemploFallback",
        tags=["ejemplo", "demo"],
    )
    
    def _on_inicializar(self) -> bool:
        self._contador = 0
        return True
    
    def _procesar_impl(self, entrada: Any, contexto: Optional[Contexto] = None) -> Any:
        self._contador += 1
        
        if isinstance(entrada, str):
            return f"[{self.nombre}] {entrada.upper()}"
        elif isinstance(entrada, (int, float)):
            return entrada * 3
        else:
            return str(entrada)
    
    def _procesar_fallback(self, entrada: Any, contexto: Optional[Contexto] = None) -> Any:
        return f"[FALLBACK] Procesado con limitaciones: {entrada}"
    
    def _on_detener(self):
        self._contador = 0

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL NÚCLEO BASE")
    print("=" * 70)
    
    nucleo = None
    
    try:
        print("\n[1/7] Información del núcleo...")
        print(f"  📍 Ficha técnica:")
        ficha = NucleoEjemplo.obtener_ficha_tecnica()
        for k, v in ficha.items():
            print(f"     - {k}: {v}")
        
        print("\n[2/7] Creando núcleo...")
        nucleo = NucleoEjemplo()
        print(f"  ✅ Núcleo creado: {nucleo}")
        
        print("\n[3/7] Inicializando núcleo...")
        nucleo.inicializar()
        print(f"  ✅ Estado: {nucleo.estado.value}")
        print(f"  ✅ Modo: {nucleo.modo.value}")
        print(f"  ✅ ID: {nucleo.id_nucleo[:8]}...")
        
        print("\n[4/7] Procesando entradas...")
        entradas = ["hola", "mundo", 42, 3.14, "ANP"]
        for entrada in entradas:
            resultado = nucleo.procesar(entrada)
            icono = "✅" if resultado.exito else "❌"
            print(f"  {icono} {entrada} -> {resultado.datos} ({resultado.tiempo_ejecucion_ms:.2f}ms)")
        
        print("\n[5/7] Estadísticas del núcleo...")
        stats = nucleo.obtener_estadisticas()
        print(f"  📊 Tareas totales: {stats['estadisticas']['total_tareas']}")
        print(f"  📊 Éxitos: {stats['estadisticas']['total_exitos']}")
        print(f"  📊 Fallos: {stats['estadisticas']['total_fallos']}")
        print(f"  📊 Fallbacks: {stats['estadisticas']['total_fallbacks']}")
        
        tasa_exito = stats['estadisticas']['total_exitos'] / max(1, stats['estadisticas']['total_tareas'])
        print(f"  📊 Tasa de éxito: {tasa_exito:.1%}")
        print(f"  📊 Tiempo promedio: {stats['estadisticas']['tiempo_promedio_ms']:.2f}ms")
        print(f"  📊 Tiempo máximo: {stats['estadisticas']['tiempo_max_ms']:.2f}ms")
        print(f"  📊 Tiempo mínimo: {stats['estadisticas']['tiempo_min_ms']:.2f}ms")
        
        print("\n[6/7] Probando modo fallback...")
        nucleo.degradar("prueba de diagnóstico")
        print(f"  📍 Estado después de degradar: {nucleo.estado.value}")
        print(f"  📍 Modo después de degradar: {nucleo.modo.value}")
        
        resultado_fb = nucleo.procesar("test_fallback")
        print(f"  📍 Resultado en fallback: {resultado_fb.datos}")
        print(f"  📍 Fallback activado: {resultado_fb.fallback_activado}")
        
        print("\n[7/7] Probando recuperación...")
        nucleo.recuperar()
        print(f"  📍 Estado después de recuperar: {nucleo.estado.value}")
        print(f"  📍 Modo después de recuperar: {nucleo.modo.value}")
        
        resultado_normal = nucleo.procesar("test_normal")
        print(f"  📍 Resultado en modo normal: {resultado_normal.datos}")
        
        print("\n" + "=" * 70)
        print("   RESUMEN FINAL")
        print("=" * 70)
        resumen = nucleo.obtener_resumen()
        for k, v in resumen.items():
            print(f"  📍 {k}: {v}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Núcleo Base funciona perfectamente.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if nucleo:
            print("\n🛑 Deteniendo núcleo...")
            nucleo.detener()
            print(f"   ✓ Estado final: {nucleo.estado.value}")
    
    print("\n" + "=" * 70 + "\n")