#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MotorBase — Clase base para todos los motores ANP
Compatible con Python 3.10+ (incluyendo 3.13)
Versión simplificada pero funcional para Nevula v0.0.1
"""

import sys, os, time, uuid, threading, traceback, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import OrderedDict

# ═══════════════════════════════════════════════
# ENUMERACIONES (compatibles con Python 3.13)
# ═══════════════════════════════════════════════

class EstadoMotor(str, Enum):
    """Estados del ciclo de vida de un motor."""
    NO_INICIALIZADO = "no_inicializado"
    INICIALIZANDO = "inicializando"
    ACTIVO = "activo"
    PAUSADO = "pausado"
    DEGRADADO = "degradado"
    ERROR = "error"
    DETENIDO = "detenido"

class CapacidadMotor(str, Enum):
    """Capacidades que un motor puede declarar."""
    SINCRONO = "sincrono"
    ASINCRONO = "asincrono"
    BATCH = "batch"
    CACHEABLE = "cacheable"
    PARALELIZABLE = "paralelizable"
    IDEMPOTENTE = "idempotente"
    REENTRANTE = "reentrante"
    MONITORIZABLE = "monitorizable"

# ═══════════════════════════════════════════════
# ESTRUCTURAS DE DATOS
# ═══════════════════════════════════════════════

@dataclass
class MetricaMotor:
    """Métrica individual recolectada por un motor."""
    nombre: str
    valor: float
    unidad: str = "count"
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def a_dict(self) -> dict:
        return {
            'nombre': self.nombre,
            'valor': self.valor,
            'unidad': self.unidad,
            'timestamp': self.timestamp,
            'tags': self.tags,
        }

@dataclass
class ResultadoMotor:
    """Resultado estandarizado del procesamiento de un motor."""
    exito: bool = True
    datos: Any = None
    error: Optional[str] = None
    tiempo_ejecucion_ms: float = 0.0
    metadatos: Dict[str, Any] = field(default_factory=dict)
    metricas_generadas: List[MetricaMotor] = field(default_factory=list)
    
    @classmethod
    def exitoso(cls, datos: Any = None, tiempo_ms: float = 0.0, **metadatos) -> 'ResultadoMotor':
        return cls(exito=True, datos=datos, tiempo_ejecucion_ms=tiempo_ms, metadatos=metadatos)
    
    @classmethod
    def fallido(cls, error: str, tiempo_ms: float = 0.0, **metadatos) -> 'ResultadoMotor':
        return cls(exito=False, error=error, tiempo_ejecucion_ms=tiempo_ms, metadatos=metadatos)
    
    def a_dict(self) -> dict:
        return {
            'exito': self.exito,
            'datos': str(self.datos)[:200] if self.datos else None,
            'error': self.error,
            'tiempo_ms': self.tiempo_ejecucion_ms,
        }

@dataclass
class ConfiguracionMotor:
    """Configuración base para todos los motores."""
    nombre: str = ""
    timeout_default: float = 30.0
    max_reintentos: int = 3
    retraso_reintento: float = 0.1
    cache_habilitado: bool = False
    cache_ttl: int = 300
    metricas_habilitadas: bool = True
    parametros: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EstadisticasMotor:
    """Estadísticas acumuladas del motor."""
    total_ejecuciones: int = 0
    total_exitos: int = 0
    total_fallos: int = 0
    tiempo_total_ms: float = 0.0
    tiempo_promedio_ms: float = 0.0
    tiempo_max_ms: float = 0.0
    tiempo_min_ms: float = float('inf')
    ultimo_error: Optional[str] = None
    cache_hits: int = 0
    cache_misses: int = 0
    
    def registrar_exito(self, tiempo_ms: float):
        self.total_ejecuciones += 1
        self.total_exitos += 1
        self.tiempo_total_ms += tiempo_ms
        self.tiempo_promedio_ms = self.tiempo_total_ms / self.total_exitos
        self.tiempo_max_ms = max(self.tiempo_max_ms, tiempo_ms)
        self.tiempo_min_ms = min(self.tiempo_min_ms, tiempo_ms)
    
    def registrar_fallo(self, error: str, tiempo_ms: float = 0.0):
        self.total_ejecuciones += 1
        self.total_fallos += 1
        self.ultimo_error = error
        if tiempo_ms > 0:
            self.tiempo_total_ms += tiempo_ms
    
    @property
    def tasa_exito(self) -> float:
        if self.total_ejecuciones == 0:
            return 1.0
        return self.total_exitos / self.total_ejecuciones

# ═══════════════════════════════════════════════
# MOTOR BASE
# ═══════════════════════════════════════════════

class MotorBase:
    """
    Clase base para todos los motores de ANP.
    
    Interfaz requerida:
    - inicializar() -> bool
    - procesar(entrada: Dict) -> ResultadoMotor  
    - detener() -> None
    """
    
    # Capacidades que el motor declara
    CAPACIDADES: Set[CapacidadMotor] = {
        CapacidadMotor.SINCRONO,
        CapacidadMotor.MONITORIZABLE,
    }
    
    def __init__(self, config: Optional[ConfiguracionMotor] = None):
        # Identidad
        self._id = str(uuid.uuid4())
        self.nombre = self.__class__.__name__
        
        # Configuración
        self.config = config or ConfiguracionMotor(nombre=self.nombre)
        
        # Estado
        self._estado = EstadoMotor.NO_INICIALIZADO
        
        # Estadísticas
        self.estadisticas = EstadisticasMotor()
        
        # Caché
        self._cache: OrderedDict = OrderedDict()
        self._cache_max_size = 100
        
        # Control
        self._lock = threading.RLock()
        self._metricas_pendientes: List[MetricaMotor] = []
        
        if self.config.cache_habilitado:
            self._cache.clear()
    
    # ═══════════ PROPIEDADES ═══════════
    
    @property
    def id_motor(self) -> str:
        return self._id
    
    @property
    def estado(self) -> EstadoMotor:
        return self._estado
    
    @property
    def esta_activo(self) -> bool:
        return self._estado == EstadoMotor.ACTIVO
    
    @property
    def puede_procesar(self) -> bool:
        return self._estado in (EstadoMotor.ACTIVO, EstadoMotor.DEGRADADO)
    
    # ═══════════ CAPACIDADES ═══════════
    
    @classmethod
    def tiene_capacidad(cls, capacidad: CapacidadMotor) -> bool:
        return capacidad in cls.CAPACIDADES
    
    @classmethod
    def listar_capacidades(cls) -> List[str]:
        return [c.value for c in cls.CAPACIDADES]
    
    # ═══════════ CICLO DE VIDA ═══════════
    
    def inicializar(self) -> bool:
        """Inicializa el motor. Retorna True si fue exitoso."""
        with self._lock:
            if self._estado != EstadoMotor.NO_INICIALIZADO:
                return False
            
            self._estado = EstadoMotor.INICIALIZANDO
            
            try:
                if self._on_inicializar():
                    self._estado = EstadoMotor.ACTIVO
                    return True
                else:
                    self._estado = EstadoMotor.ERROR
                    return False
            except Exception as e:
                self._estado = EstadoMotor.ERROR
                self.estadisticas.registrar_fallo(str(e))
                return False
    
    def detener(self) -> bool:
        """Detiene el motor. Retorna True si fue exitoso."""
        with self._lock:
            if self._estado in (EstadoMotor.DETENIDO, EstadoMotor.NO_INICIALIZADO):
                return False
            
            try:
                self._on_detener()
                self._estado = EstadoMotor.DETENIDO
                return True
            except Exception as e:
                self._estado = EstadoMotor.ERROR
                self.estadisticas.registrar_fallo(str(e))
                return False
    
    # ═══════════ PROCESAMIENTO ═══════════
    
    def procesar(self, entrada: Dict[str, Any]) -> ResultadoMotor:
        """
        Procesa una entrada y retorna un resultado.
        
        Args:
            entrada: Diccionario con los datos de entrada.
                    Debe contener al menos 'texto' o 'operacion'.
        
        Returns:
            ResultadoMotor con el resultado del procesamiento.
        """
        if not self.puede_procesar:
            return ResultadoMotor.fallido(
                f"Motor en estado {self._estado.value}, no puede procesar"
            )
        
        inicio = time.time()
        
        try:
            # Intentar _procesar_impl primero (nuevo formato)
            if hasattr(self, '_procesar_impl'):
                resultado_datos = self._procesar_impl(entrada)
            else:
                # Fallback para motores antiguos
                resultado_datos = self._procesar(entrada)
            
            tiempo_ms = (time.time() - inicio) * 1000
            self.estadisticas.registrar_exito(tiempo_ms)
            
            return ResultadoMotor.exitoso(
                datos=resultado_datos,
                tiempo_ms=tiempo_ms,
                motor_id=self._id,
                motor_nombre=self.nombre,
            )
            
        except Exception as e:
            tiempo_ms = (time.time() - inicio) * 1000
            self.estadisticas.registrar_fallo(str(e), tiempo_ms)
            
            return ResultadoMotor.fallido(
                error=str(e),
                tiempo_ms=tiempo_ms,
                motor_id=self._id,
                motor_nombre=self.nombre,
            )
    
    def _procesar_impl(self, entrada: Dict[str, Any]) -> Any:
        """
        Implementación concreta del procesamiento.
        SOBRESCRIBIR en subclases.
        
        Args:
            entrada: Diccionario con 'texto', 'operacion', etc.
        
        Returns:
            Resultado del procesamiento (dict, str, etc.)
        """
        raise NotImplementedError(
            f"Motor '{self.nombre}' debe implementar _procesar_impl()"
        )
    
    def _procesar(self, entrada: Dict[str, Any]) -> Any:
        """Método legacy para compatibilidad."""
        return self._procesar_impl(entrada)
    
    # ═══════════ HOOKS (sobrescribir en subclases) ═══════════
    
    def _on_inicializar(self) -> bool:
        """Hook llamado durante inicializar(). Retorna True si OK."""
        return True
    
    def _on_detener(self):
        """Hook llamado durante detener()."""
        pass
    
    # ═══════════ CACHÉ ═══════════
    
    def _generar_clave_cache(self, funcion: str, args: tuple, kwargs: dict) -> str:
        contenido = f"{funcion}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.sha256(contenido.encode()).hexdigest()
    
    def _obtener_de_cache(self, clave: str) -> Optional[Any]:
        if clave in self._cache:
            valor, timestamp = self._cache[clave]
            if time.time() - timestamp < self.config.cache_ttl:
                self._cache.move_to_end(clave)
                return valor
            else:
                del self._cache[clave]
        return None
    
    def _guardar_en_cache(self, clave: str, valor: Any):
        if len(self._cache) >= self._cache_max_size:
            self._cache.popitem(last=False)
        self._cache[clave] = (valor, time.time())
    
    def limpiar_cache(self):
        self._cache.clear()
    
    # ═══════════ MÉTRICAS ═══════════
    
    def _registrar_metrica(self, nombre: str, valor: float, unidad: str = "count", tags: dict = None):
        if not self.config.metricas_habilitadas:
            return
        
        metrica = MetricaMotor(
            nombre=f"{self.nombre}.{nombre}",
            valor=valor,
            unidad=unidad,
            tags=tags or {},
        )
        self._metricas_pendientes.append(metrica)
    
    def obtener_metricas(self) -> List[MetricaMotor]:
        return self._metricas_pendientes.copy()
    
    # ═══════════ ESTADÍSTICAS ═══════════
    
    def obtener_estadisticas(self) -> dict:
        return {
            'id': self._id,
            'nombre': self.nombre,
            'estado': self._estado.value,
            'ejecuciones': self.estadisticas.total_ejecuciones,
            'exitos': self.estadisticas.total_exitos,
            'fallos': self.estadisticas.total_fallos,
            'tasa_exito': f"{self.estadisticas.tasa_exito:.1%}",
            'tiempo_promedio_ms': f"{self.estadisticas.tiempo_promedio_ms:.2f}",
        }
    
    def obtener_resumen(self) -> dict:
        return {
            'nombre': self.nombre,
            'estado': self._estado.value,
            'tasa_exito': f"{self.estadisticas.tasa_exito:.1%}",
        }
    
    # ═══════════ MÉTODOS MÁGICOS ═══════════
    
    def __repr__(self) -> str:
        return f"{self.nombre}(id={self._id[:8]}, estado={self._estado.value})"
    
    def __str__(self) -> str:
        return f"Motor {self.nombre} [{self._estado.value}]"

# ═══════════════════════════════════════════════
# MOTOR DE EJEMPLO (para demostración)
# ═══════════════════════════════════════════════

class MotorEjemplo(MotorBase):
    """Motor de ejemplo para demostración."""
    
    CAPACIDADES = {
        CapacidadMotor.SINCRONO,
        CapacidadMotor.CACHEABLE,
        CapacidadMotor.IDEMPOTENTE,
        CapacidadMotor.MONITORIZABLE,
    }
    
    def _on_inicializar(self) -> bool:
        return True
    
    def _procesar_impl(self, entrada: Dict[str, Any]) -> Any:
        texto = entrada.get('texto', '')
        operacion = entrada.get('operacion', 'procesar')
        
        if isinstance(texto, str):
            return {
                'resultado': texto.upper() if operacion == 'uppercase' else texto,
                'operacion': operacion,
                'longitud': len(texto),
            }
        elif isinstance(texto, (int, float)):
            return {
                'resultado': texto * 2,
                'operacion': 'multiplicar',
            }
        else:
            return {
                'resultado': str(texto),
                'operacion': 'convertir',
            }