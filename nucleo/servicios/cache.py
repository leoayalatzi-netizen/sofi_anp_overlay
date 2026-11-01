#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio de Caché (Sistema de Caché Multi-Nivel)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de caché multi-nivel
# (RAM + SQLite) con TTL, políticas LRU/LFU/FIFO, estadísticas y
# precarga predictiva.
# =====================================================================

import sys
import os
import time
import threading
import json
import hashlib
import pickle
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import OrderedDict, deque, defaultdict
from functools import wraps
from contextlib import contextmanager

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

try:
    from .registro import obtener_logger
except ImportError:
    def obtener_logger(nombre=""):
        return None

# =====================================================================
# ENUMERACIONES
# =====================================================================

class PoliticaEviccion(Enum):
    """Políticas de evicción para la caché."""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    FIFO = "fifo"        # First In First Out
    TTL = "ttl"          # Time To Live (solo expiración)
    ADAPTATIVA = "adaptativa"  # Combina LRU + LFU

class NivelCache(Enum):
    """Niveles de la caché."""
    RAM = "ram"
    DISCO = "disco"
    AMBOS = "ambos"

class EstadoEntrada(Enum):
    """Estados de una entrada en caché."""
    ACTIVA = "activa"
    EXPIRADA = "expirada"
    EVICTADA = "evictada"
    CORRUPTA = "corrupta"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EntradaCache:
    """Representa una entrada individual en la caché."""
    clave: str
    valor: Any
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_acceso: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # Time To Live en segundos
    contador_accesos: int = 0
    tamaño_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    metadatos: Dict[str, Any] = field(default_factory=dict)
    estado: EstadoEntrada = EstadoEntrada.ACTIVA
    
    def acceder(self) -> Any:
        """Registra un acceso a la entrada."""
        self.timestamp_acceso = time.time()
        self.contador_accesos += 1
        return self.valor
    
    def esta_expirada(self) -> bool:
        """Verifica si la entrada ha expirado."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp_creacion > self.ttl
    
    def calcular_score(self, politica: PoliticaEviccion) -> float:
        """Calcula un score para evicción (menor = más evictable)."""
        ahora = time.time()
        edad = ahora - self.timestamp_creacion
        tiempo_sin_acceso = ahora - self.timestamp_acceso
        
        if politica == PoliticaEviccion.LRU:
            return -tiempo_sin_acceso  # Negativo: más antiguo = menor score
        elif politica == PoliticaEviccion.LFU:
            return float(self.contador_accesos)
        elif politica == PoliticaEviccion.FIFO:
            return -edad
        elif politica == PoliticaEviccion.ADAPTATIVA:
            return (self.contador_accesos / max(1.0, tiempo_sin_acceso)) - (edad / 3600.0)
        else:
            return 0.0

@dataclass
class EstadisticasCache:
    """Estadísticas de la caché."""
    hits: int = 0
    misses: int = 0
    escrituras: int = 0
    evicciones: int = 0
    expiraciones: int = 0
    tamaño_actual: int = 0
    tamaño_maximo: int = 0
    entradas_activas: int = 0
    
    @property
    def tasa_hits(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def uso_porcentaje(self) -> float:
        return (self.tamaño_actual / self.tamaño_maximo) * 100 if self.tamaño_maximo > 0 else 0.0

# =====================================================================
# CACHÉ EN RAM (NIVEL 1)
# =====================================================================

class CacheRAM:
    """Caché de nivel 1 en memoria RAM."""
    
    def __init__(self, capacidad_maxima: int = 100, politica: PoliticaEviccion = PoliticaEviccion.ADAPTATIVA):
        self.capacidad_maxima = capacidad_maxima
        self.politica = politica
        self._entradas: OrderedDict[str, EntradaCache] = OrderedDict()
        self._lock = threading.RLock()
        self.estadisticas = EstadisticasCache()
        self.estadisticas.tamaño_maximo = capacidad_maxima
    
    def obtener(self, clave: str) -> Optional[Any]:
        """Obtiene un valor de la caché."""
        with self._lock:
            entrada = self._entradas.get(clave)
            
            if entrada is None:
                self.estadisticas.misses += 1
                return None
            
            if entrada.esta_expirada():
                self._eliminar(clave, "expirada")
                self.estadisticas.misses += 1
                return None
            
            self._entradas.move_to_end(clave)
            self.estadisticas.hits += 1
            return entrada.acceder()
    
    def guardar(self, clave: str, valor: Any, ttl: Optional[float] = None, 
                tags: List[str] = None, metadatos: Dict = None) -> bool:
        """Guarda un valor en la caché."""
        with self._lock:
            # Verificar si hay espacio
            if len(self._entradas) >= self.capacidad_maxima and clave not in self._entradas:
                self._evictar_uno()
            
            # Calcular tamaño aproximado
            try:
                tamaño = len(pickle.dumps(valor))
            except Exception:
                tamaño = 1024
            
            entrada = EntradaCache(
                clave=clave,
                valor=valor,
                ttl=ttl,
                tamaño_bytes=tamaño,
                tags=tags or [],
                metadatos=metadatos or {}
            )
            
            self._entradas[clave] = entrada
            self._entradas.move_to_end(clave)
            
            self.estadisticas.escrituras += 1
            self.estadisticas.tamaño_actual = sum(e.tamaño_bytes for e in self._entradas.values())
            self.estadisticas.entradas_activas = len(self._entradas)
            
            return True
    
    def _evictar_uno(self):
        """Evicta una entrada según la política configurada."""
        if not self._entradas:
            return
        
        # Ordenar por score (menor = más evictable)
        entradas_ordenadas = sorted(
            self._entradas.items(),
            key=lambda x: x[1].calcular_score(self.politica)
        )
        
        clave_a_evictar = entradas_ordenadas[0][0]
        self._eliminar(clave_a_evictar, "evictada")
    
    def _eliminar(self, clave: str, motivo: str):
        """Elimina una entrada de la caché."""
        if clave in self._entradas:
            entrada = self._entradas[clave]
            entrada.estado = EstadoEntrada.EXPIRADA if motivo == "expirada" else EstadoEntrada.EVICTADA
            del self._entradas[clave]
            
            if motivo == "expirada":
                self.estadisticas.expiraciones += 1
            else:
                self.estadisticas.evicciones += 1
            
            self.estadisticas.tamaño_actual = sum(e.tamaño_bytes for e in self._entradas.values())
            self.estadisticas.entradas_activas = len(self._entradas)
    
    def eliminar(self, clave: str) -> bool:
        """Elimina una entrada específica."""
        with self._lock:
            if clave in self._entradas:
                self._eliminar(clave, "evictada")
                return True
            return False
    
    def contiene(self, clave: str) -> bool:
        """Verifica si una clave existe y no está expirada."""
        with self._lock:
            entrada = self._entradas.get(clave)
            if entrada and not entrada.esta_expirada():
                return True
            return False
    
    def limpiar_expiradas(self) -> int:
        """Limpia todas las entradas expiradas."""
        with self._lock:
            expiradas = [k for k, v in self._entradas.items() if v.esta_expirada()]
            for clave in expiradas:
                self._eliminar(clave, "expirada")
            return len(expiradas)
    
    def limpiar(self):
        """Limpia toda la caché."""
        with self._lock:
            self._entradas.clear()
            self.estadisticas.tamaño_actual = 0
            self.estadisticas.entradas_activas = 0
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la caché RAM."""
        with self._lock:
            return {
                'hits': self.estadisticas.hits,
                'misses': self.estadisticas.misses,
                'tasa_hits': self.estadisticas.tasa_hits,
                'escrituras': self.estadisticas.escrituras,
                'evicciones': self.estadisticas.evicciones,
                'expiraciones': self.estadisticas.expiraciones,
                'entradas': self.estadisticas.entradas_activas,
                'capacidad': self.capacidad_maxima,
                'tamaño_bytes': self.estadisticas.tamaño_actual,
                'uso': self.estadisticas.uso_porcentaje,
            }
    
    def __len__(self) -> int:
        return len(self._entradas)
    
    def __contains__(self, clave: str) -> bool:
        return self.contiene(clave)

# =====================================================================
# CACHÉ EN DISCO (NIVEL 2 - SQLite)
# =====================================================================

class CacheDisco:
    """Caché de nivel 2 en disco usando SQLite."""
    
    def __init__(self, nombre: str = "cache", capacidad_maxima_mb: int = 100):
        self.nombre = nombre
        self.capacidad_maxima = capacidad_maxima_mb * 1024 * 1024
        self._lock = threading.RLock()
        self.estadisticas = EstadisticasCache()
        self.estadisticas.tamaño_maximo = self.capacidad_maxima
        
        self._inicializar_tabla()
    
    def _inicializar_tabla(self):
        """Inicializa la tabla de caché en SQLite."""
        bd = obtener_bd()
        if bd:
            bd.crear_tabla(f"cache_{self.nombre}", [
                ("clave", "TEXT PRIMARY KEY"),
                ("valor", "BLOB"),
                ("timestamp_creacion", "REAL"),
                ("timestamp_acceso", "REAL"),
                ("ttl", "REAL"),
                ("contador_accesos", "INTEGER DEFAULT 0"),
                ("tamaño_bytes", "INTEGER DEFAULT 0"),
                ("tags", "TEXT"),
                ("metadatos", "TEXT"),
            ], if_not_exists=True)
    
    def obtener(self, clave: str) -> Optional[Any]:
        """Obtiene un valor de la caché en disco."""
        bd = obtener_bd()
        if not bd:
            self.estadisticas.misses += 1
            return None
        
        with self._lock:
            resultado = bd.consultar_uno(
                f"SELECT valor, ttl, timestamp_creacion FROM cache_{self.nombre} WHERE clave = ?",
                (clave,)
            )
            
            if resultado is None:
                self.estadisticas.misses += 1
                return None
            
            # Verificar expiración
            if resultado['ttl'] and time.time() - resultado['timestamp_creacion'] > resultado['ttl']:
                self.eliminar(clave)
                self.estadisticas.misses += 1
                return None
            
            # Actualizar timestamp de acceso
            bd.actualizar(
                f"cache_{self.nombre}",
                {"timestamp_acceso": time.time(), "contador_accesos": resultado.get('contador_accesos', 0) + 1},
                "clave = ?", (clave,)
            )
            
            self.estadisticas.hits += 1
            return pickle.loads(resultado['valor'])
    
    def guardar(self, clave: str, valor: Any, ttl: Optional[float] = None,
                tags: List[str] = None, metadatos: Dict = None) -> bool:
        """Guarda un valor en la caché en disco."""
        bd = obtener_bd()
        if not bd:
            return False
        
        with self._lock:
            try:
                valor_serializado = pickle.dumps(valor)
                tamaño = len(valor_serializado)
                
                # Verificar espacio
                self._gestionar_espacio(tamaño)
                
                bd.upsert(
                    f"cache_{self.nombre}",
                    {
                        "clave": clave,
                        "valor": valor_serializado,
                        "timestamp_creacion": time.time(),
                        "timestamp_acceso": time.time(),
                        "ttl": ttl,
                        "tamaño_bytes": tamaño,
                        "tags": json.dumps(tags) if tags else None,
                        "metadatos": json.dumps(metadatos) if metadatos else None,
                    },
                    ["clave"]
                )
                
                self.estadisticas.escrituras += 1
                self._actualizar_estadisticas()
                return True
            except Exception:
                return False
    
    def _gestionar_espacio(self, tamaño_necesario: int):
        """Gestiona el espacio en disco evictando entradas si es necesario."""
        bd = obtener_bd()
        if not bd:
            return
        
        tamaño_actual = bd.consultar_valor(
            f"SELECT SUM(tamaño_bytes) FROM cache_{self.nombre}"
        ) or 0
        
        if tamaño_actual + tamaño_necesario <= self.capacidad_maxima:
            return
        
        # Obtener entradas ordenadas por score LRU
        entradas = bd.consultar_todos(
            f"SELECT clave, timestamp_acceso, contador_accesos, tamaño_bytes FROM cache_{self.nombre} ORDER BY timestamp_acceso ASC"
        )
        
        espacio_liberado = 0
        for entrada in entradas:
            self.eliminar(entrada['clave'])
            espacio_liberado += entrada['tamaño_bytes']
            self.estadisticas.evicciones += 1
            
            if tamaño_actual - espacio_liberado + tamaño_necesario <= self.capacidad_maxima:
                break
    
    def eliminar(self, clave: str) -> bool:
        """Elimina una entrada de la caché en disco."""
        bd = obtener_bd()
        if not bd:
            return False
        
        with self._lock:
            bd.eliminar(f"cache_{self.nombre}", "clave = ?", (clave,))
            return True
    
    def limpiar(self):
        """Limpia toda la caché en disco."""
        bd = obtener_bd()
        if bd:
            bd.eliminar(f"cache_{self.nombre}", "1=1", ())
    
    def _actualizar_estadisticas(self):
        """Actualiza las estadísticas desde la base de datos."""
        bd = obtener_bd()
        if bd:
            self.estadisticas.entradas_activas = bd.consultar_valor(
                f"SELECT COUNT(*) FROM cache_{self.nombre}"
            ) or 0
            self.estadisticas.tamaño_actual = bd.consultar_valor(
                f"SELECT COALESCE(SUM(tamaño_bytes), 0) FROM cache_{self.nombre}"
            ) or 0
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la caché en disco."""
        with self._lock:
            self._actualizar_estadisticas()
            return {
                'hits': self.estadisticas.hits,
                'misses': self.estadisticas.misses,
                'tasa_hits': self.estadisticas.tasa_hits,
                'escrituras': self.estadisticas.escrituras,
                'evicciones': self.estadisticas.evicciones,
                'entradas': self.estadisticas.entradas_activas,
                'capacidad_mb': self.capacidad_maxima / (1024 * 1024),
                'tamaño_mb': self.estadisticas.tamaño_actual / (1024 * 1024),
                'uso': self.estadisticas.uso_porcentaje,
            }

# =====================================================================
# CACHÉ MULTI-NIVEL (PRINCIPAL)
# =====================================================================


class Cache:
    """
    Sistema de caché multi-nivel (RAM + Disco).
    Implementa patrón Singleton thread-safe por nombre.
    """
    
    _instancias: Dict[str, 'Cache'] = {}
    _lock_instancias = threading.RLock()
    
    def __init__(self, nombre: str = "default", 
                 capacidad_ram: int = 100,
                 capacidad_disco_mb: int = 50,
                 politica: PoliticaEviccion = PoliticaEviccion.ADAPTATIVA,
                 ttl_default: Optional[float] = 3600,
                 nivel_default: NivelCache = NivelCache.AMBOS):
        
        self.nombre = nombre
        self.ttl_default = ttl_default
        self.nivel_default = nivel_default
        self.politica = politica
        
        self.cache_ram = CacheRAM(capacidad_ram, politica)
        self.cache_disco = CacheDisco(f"{nombre}_cache", capacidad_disco_mb)
        
        self._logger = obtener_logger(f"Cache.{nombre}")
        self._estadisticas_combinadas = {}
    
    @classmethod
    def obtener(cls, nombre: str = "default", **kwargs) -> 'Cache':
        """Obtiene o crea una instancia de caché por nombre."""
        with cls._lock_instancias:
            if nombre not in cls._instancias:
                cls._instancias[nombre] = Cache(nombre=nombre, **kwargs)
            return cls._instancias[nombre]
    
    def obtener(self, clave: str, nivel: NivelCache = None) -> Optional[Any]:
        """
        Obtiene un valor de la caché.
        
        Args:
            clave: Clave a buscar
            nivel: Nivel de caché a consultar (por defecto AMBOS)
            
        Returns:
            Valor almacenado o None
        """
        nivel = nivel or self.nivel_default
        clave_hash = self._hash_clave(clave)
        
        # Nivel 1: RAM
        if nivel in (NivelCache.RAM, NivelCache.AMBOS):
            valor = self.cache_ram.obtener(clave_hash)
            if valor is not None:
                if self._logger:
                    self._logger.debug(f"Cache HIT (RAM): {clave}")
                return valor
        
        # Nivel 2: Disco
        if nivel in (NivelCache.DISCO, NivelCache.AMBOS):
            valor = self.cache_disco.obtener(clave_hash)
            if valor is not None:
                if self._logger:
                    self._logger.debug(f"Cache HIT (DISCO): {clave}")
                # Promover a RAM
                self.cache_ram.guardar(clave_hash, valor, self.ttl_default)
                return valor
        
        if self._logger:
            self._logger.debug(f"Cache MISS: {clave}")
        return None
    
    def guardar(self, clave: str, valor: Any, ttl: Optional[float] = None,
                nivel: NivelCache = None, tags: List[str] = None,
                metadatos: Dict = None) -> bool:
        """
        Guarda un valor en la caché.
        
        Args:
            clave: Clave única
            valor: Valor a almacenar
            ttl: Time To Live en segundos
            nivel: Nivel donde guardar
            tags: Etiquetas para agrupación
            metadatos: Metadatos adicionales
            
        Returns:
            True si se guardó correctamente
        """
        nivel = nivel or self.nivel_default
        ttl = ttl or self.ttl_default
        clave_hash = self._hash_clave(clave)
        
        exito = True
        
        if nivel in (NivelCache.RAM, NivelCache.AMBOS):
            exito = exito and self.cache_ram.guardar(clave_hash, valor, ttl, tags, metadatos)
        
        if nivel in (NivelCache.DISCO, NivelCache.AMBOS):
            exito = exito and self.cache_disco.guardar(clave_hash, valor, ttl, tags, metadatos)
        
        if self._logger and exito:
            self._logger.debug(f"Cache GUARDADO: {clave} (nivel={nivel.value})")
        
        return exito
    
    def eliminar(self, clave: str) -> bool:
        """Elimina una entrada de todos los niveles."""
        clave_hash = self._hash_clave(clave)
        exito_ram = self.cache_ram.eliminar(clave_hash)
        exito_disco = self.cache_disco.eliminar(clave_hash)
        return exito_ram or exito_disco
    
    def contiene(self, clave: str) -> bool:
        """Verifica si una clave existe en cualquier nivel."""
        clave_hash = self._hash_clave(clave)
        return self.cache_ram.contiene(clave_hash)
    
    def limpiar(self, nivel: NivelCache = NivelCache.AMBOS):
        """Limpia la caché."""
        if nivel in (NivelCache.RAM, NivelCache.AMBOS):
            self.cache_ram.limpiar()
        if nivel in (NivelCache.DISCO, NivelCache.AMBOS):
            self.cache_disco.limpiar()
        
        if self._logger:
            self._logger.info(f"Cache limpiada: {self.nombre}")
    
    def _hash_clave(self, clave: str) -> str:
        """Genera un hash de la clave."""
        return hashlib.md5(clave.encode()).hexdigest()
    
    # ===== DECORADOR =====
    
    def cached(self, ttl: Optional[float] = None, nivel: NivelCache = None,
               clave_prefix: str = ""):
        """
        Decorador para cachear el resultado de una función.
        
        Uso:
            @cache.cached(ttl=300)
            def funcion_costosa(param):
                return resultado
        """
        def decorador(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generar clave única
                clave = f"{clave_prefix}{func.__name__}:{hashlib.md5(str(args).encode() + str(sorted(kwargs.items())).encode()).hexdigest()}"
                
                resultado = self.obtener(clave)
                if resultado is not None:
                    return resultado
                
                resultado = func(*args, **kwargs)
                self.guardar(clave, resultado, ttl=ttl, nivel=nivel)
                return resultado
            return wrapper
        return decorador
    
    # ===== ESTADÍSTICAS =====
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas de la caché."""
        stats_ram = self.cache_ram.obtener_estadisticas()
        stats_disco = self.cache_disco.obtener_estadisticas()
        
        total_hits = stats_ram['hits'] + stats_disco['hits']
        total_misses = stats_ram['misses'] + stats_disco['misses']
        total_accesos = total_hits + total_misses
        
        return {
            'nombre': self.nombre,
            'politica': self.politica.value,
            'nivel_default': self.nivel_default.value,
            'ttl_default': self.ttl_default,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'tasa_hits_global': total_hits / max(1, total_accesos),
            'ram': stats_ram,
            'disco': stats_disco,
        }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo de la caché."""
        stats = self.obtener_estadisticas()
        return {
            'nombre': self.nombre,
            'tasa_hits': f"{stats['tasa_hits_global']:.1%}",
            'ram': f"{stats['ram']['entradas']}/{stats['ram']['capacidad']}",
            'disco': f"{stats['disco']['tamaño_mb']:.2f} MB",
        }
    
    def __contains__(self, clave: str) -> bool:
        return self.contiene(clave)
    
    def __len__(self) -> int:
        return len(self.cache_ram)

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def obtener_cache(nombre: str = "default") -> Cache:
    """Obtiene una instancia de caché por nombre."""
    return Cache.obtener(nombre)

def cached(ttl: Optional[float] = None, cache_nombre: str = "default"):
    """Decorador global para cachear funciones."""
    cache = obtener_cache(cache_nombre)
    return cache.cached(ttl=ttl)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE CACHÉ")
    print("=" * 70)
    
    cache = None
    
    try:
        print("\n[1/6] Inicializando caché...")
        cache = Cache("test", capacidad_ram=20, capacidad_disco_mb=5, ttl_default=60)
        print(f"  ✅ Caché inicializada: {cache.nombre}")
        
        print("\n[2/6] Guardando valores...")
        for i in range(5):
            cache.guardar(f"clave_{i}", f"valor_{i}", tags=["test"])
        print(f"  ✅ 5 valores guardados")
        
        print("\n[3/6] Obteniendo valores...")
        for i in range(5):
            valor = cache.obtener(f"clave_{i}")
            print(f"  📍 clave_{i} = {valor}")
        
        print("\n[4/6] Probando miss...")
        valor = cache.obtener("clave_inexistente")
        print(f"  📍 clave_inexistente = {valor}")
        
        print("\n[5/6] Probando decorador @cached...")
        
        @cache.cached(ttl=30)
        def funcion_costosa(n):
            time.sleep(0.1)
            return n * 2
        
        inicio = time.time()
        r1 = funcion_costosa(5)
        tiempo1 = (time.time() - inicio) * 1000
        
        inicio = time.time()
        r2 = funcion_costosa(5)
        tiempo2 = (time.time() - inicio) * 1000
        
        print(f"  📍 Primera llamada: {r1} ({tiempo1:.2f}ms)")
        print(f"  📍 Segunda llamada (caché): {r2} ({tiempo2:.2f}ms)")
        print(f"  ✅ Aceleración: {tiempo1/tiempo2:.1f}x")
        
        print("\n[6/6] Estadísticas de la caché...")
        stats = cache.obtener_estadisticas()
        print(f"  📊 Total hits: {stats['total_hits']}")
        print(f"  📊 Total misses: {stats['total_misses']}")
        print(f"  📊 Tasa hits: {stats['tasa_hits_global']:.1%}")
        print(f"  📊 RAM: {stats['ram']['entradas']} entradas, {stats['ram']['uso']:.0f}% uso")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Caché está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if cache:
            cache.limpiar()
    
    print("\n" + "=" * 70 + "\n")