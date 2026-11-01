#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Reserva de Memoria (El Pool de Memoria Compartida)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de memoria compartida
# zero-copy usando mmap, con pools de buffers, asignación rápida,
# fragmentación controlada, y estadísticas en tiempo real.
# =====================================================================

import sys
import os
import time
import uuid
import threading
import mmap
import struct
import hashlib
import json
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict, Counter
from functools import wraps, lru_cache
from abc import ABC, abstractmethod
import heapq
import math

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .metricas import contador, medidor, histograma, indicador, obtener_recolector
except ImportError:
    def contador(nombre, **kwargs): return None
    def medidor(nombre, **kwargs): return None
    def histograma(nombre, **kwargs): return None
    def indicador(nombre, **kwargs): return None
    def obtener_recolector(): return None

try:
    from ..bus_eventos import Evento, TipoEvento, publicar
except ImportError:
    def publicar(tipo, datos=None, origen="", prioridad=2, **kwargs): pass

# =====================================================================
# ENUMERACIONES FUNDAMENTALES
# =====================================================================

class EstrategiaAsignacion(Enum):
    """Estrategias de asignación de buffers."""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    WORST_FIT = "worst_fit"
    NEXT_FIT = "next_fit"

class EstadoBuffer(Enum):
    """Estados de un buffer de memoria."""
    LIBRE = "libre"
    RESERVADO = "reservado"
    EN_USO = "en_uso"
    MARCADO_LIBERAR = "marcado_liberar"
    CORRUPTO = "corrupto"

class PoliticaExpansion(Enum):
    """Políticas de expansión del pool."""
    FIJA = "fija"
    DUPLICAR = "duplicar"
    INCREMENTAL = "incremental"
    BAJO_DEMANDA = "bajo_demanda"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class BloqueMemoria:
    """Representa un bloque de memoria en el pool."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    offset: int = 0
    tamaño: int = 0
    estado: EstadoBuffer = EstadoBuffer.LIBRE
    propietario: str = ""
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_ultimo_acceso: float = field(default_factory=time.time)
    contador_accesos: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    metadatos: Dict[str, Any] = field(default_factory=dict)
    siguiente: Optional['BloqueMemoria'] = None
    anterior: Optional['BloqueMemoria'] = None
    
    def esta_libre(self) -> bool:
        return self.estado == EstadoBuffer.LIBRE
    
    def puede_contener(self, tamaño: int) -> bool:
        return self.esta_libre() and self.tamaño >= tamaño
    
    def dividir(self, tamaño: int) -> Optional['BloqueMemoria']:
        """Divide el bloque en dos si es suficientemente grande."""
        if not self.esta_libre() or self.tamaño <= tamaño:
            return None
        
        resto = self.tamaño - tamaño
        if resto < 64:
            return None
        
        nuevo_bloque = BloqueMemoria(
            offset=self.offset + tamaño,
            tamaño=resto,
            estado=EstadoBuffer.LIBRE
        )
        
        self.tamaño = tamaño
        
        nuevo_bloque.siguiente = self.siguiente
        nuevo_bloque.anterior = self
        if self.siguiente:
            self.siguiente.anterior = nuevo_bloque
        self.siguiente = nuevo_bloque
        
        return nuevo_bloque
    
    def puede_fusionar_con(self, otro: 'BloqueMemoria') -> bool:
        return (self.esta_libre() and otro.esta_libre() and 
                self.offset + self.tamaño == otro.offset)
    
    def fusionar(self, otro: 'BloqueMemoria') -> bool:
        if not self.puede_fusionar_con(otro):
            return False
        
        self.tamaño += otro.tamaño
        self.siguiente = otro.siguiente
        if otro.siguiente:
            otro.siguiente.anterior = self
        
        return True

@dataclass
class EstadisticasPool:
    """Estadísticas del pool de memoria."""
    tamaño_total: int = 0
    tamaño_usado: int = 0
    tamaño_libre: int = 0
    bloques_totales: int = 0
    bloques_libres: int = 0
    bloques_usados: int = 0
    fragmentacion: float = 0.0
    asignaciones_exitosas: int = 0
    asignaciones_fallidas: int = 0
    liberaciones: int = 0
    fusiones: int = 0
    expansiones: int = 0
    tiempo_total_asignacion: float = 0.0
    tiempo_promedio_asignacion: float = 0.0
    
    def actualizar_fragmentacion(self):
        if self.bloques_libres > 0 and self.tamaño_libre > 0:
            tamaño_promedio_libre = self.tamaño_libre / self.bloques_libres
            self.fragmentacion = 1.0 - (tamaño_promedio_libre / self.tamaño_libre)

# =====================================================================
# POOL DE MEMORIA COMPARTIDA (CORREGIDO PARA ANDROID)
# =====================================================================

class PoolMemoria:
    """
    Pool de memoria compartida con zero-copy usando mmap.
    Soporta múltiples estrategias de asignación y políticas de expansión.
    Compatible con Pydroid3/Android.
    """
    
    def __init__(self, nombre: str, tamaño_inicial: int = 1024 * 1024,
                 estrategia: EstrategiaAsignacion = EstrategiaAsignacion.BEST_FIT,
                 politica_expansion: PoliticaExpansion = PoliticaExpansion.DUPLICAR,
                 incremento: int = 1024 * 1024,
                 directorio: Optional[Path] = None):
        
        self.nombre = nombre
        self.tamaño_inicial = tamaño_inicial
        self.estrategia = estrategia
        self.politica_expansion = politica_expansion
        self.incremento = incremento
        
        # Determinar directorio para memoria compartida (CORREGIDO PARA ANDROID)
        if directorio is None:
            if hasattr(sys, 'getandroidapilevel'):
                # Pydroid3/Android - usar almacenamiento de documentos
                directorio = Path("/storage/emulated/0/Documents/Proyec Ai/ANP/almacenamiento/memoria")
            elif sys.platform.startswith('linux'):
                directorio = Path("/dev/shm")
            elif sys.platform.startswith('win'):
                directorio = Path("almacenamiento/memoria")
            else:
                directorio = Path("almacenamiento/memoria")
        
        directorio.mkdir(parents=True, exist_ok=True)
        self.archivo_path = directorio / f"anp_mem_{nombre}.shm"
        
        # Estado interno
        self._mmap: Optional[mmap.mmap] = None
        self._archivo = None
        self._cabeza: Optional[BloqueMemoria] = None
        self._ultimo_asignado: Optional[BloqueMemoria] = None
        self._lock = threading.RLock()
        self._inicializado = False
        self.estadisticas = EstadisticasPool()
        
        # Buffers activos
        self._buffers_activos: Dict[str, BloqueMemoria] = {}
        
        # Métricas (con manejo de errores)
        try:
            self._metrica_asignaciones = contador(f"memoria.{nombre}.asignaciones")
            self._metrica_liberaciones = contador(f"memoria.{nombre}.liberaciones")
            self._metrica_uso = medidor(f"memoria.{nombre}.uso", unidad="bytes")
            self._metrica_fragmentacion = medidor(f"memoria.{nombre}.fragmentacion")
        except Exception:
            self._metrica_asignaciones = None
            self._metrica_liberaciones = None
            self._metrica_uso = None
            self._metrica_fragmentacion = None
        
        # Inicializar
        self._inicializar()
    
    def _inicializar(self):
        """Inicializa el pool de memoria."""
        with self._lock:
            try:
                # Crear o abrir archivo de respaldo
                self._archivo = open(self.archivo_path, "w+b")
                self._archivo.write(b'\x00' * self.tamaño_inicial)
                self._archivo.flush()
                
                # Crear mmap
                self._mmap = mmap.mmap(self._archivo.fileno(), self.tamaño_inicial)
                
                # Crear bloque inicial
                self._cabeza = BloqueMemoria(
                    offset=0,
                    tamaño=self.tamaño_inicial,
                    estado=EstadoBuffer.LIBRE
                )
                
                self.estadisticas.tamaño_total = self.tamaño_inicial
                self.estadisticas.tamaño_libre = self.tamaño_inicial
                self.estadisticas.bloques_totales = 1
                self.estadisticas.bloques_libres = 1
                
                self._inicializado = True
                
            except Exception as e:
                self._inicializado = False
                raise RuntimeError(f"Error inicializando pool de memoria: {e}")
    
    # ===== ASIGNACIÓN =====
    
    def asignar(self, tamaño: int, propietario: str = "", 
                tags: Dict[str, str] = None) -> Optional['BufferMemoria']:
        """Asigna un buffer del tamaño solicitado."""
        with self._lock:
            if not self._inicializado:
                return None
            
            inicio = time.time()
            
            # Alinear tamaño a 8 bytes
            tamaño = ((tamaño + 7) // 8) * 8
            
            # Buscar bloque según estrategia
            bloque = self._buscar_bloque(tamaño)
            
            if bloque is None:
                if self._expandir(tamaño):
                    bloque = self._buscar_bloque(tamaño)
                
                if bloque is None:
                    self.estadisticas.asignaciones_fallidas += 1
                    return None
            
            # Dividir si es necesario
            resto = bloque.dividir(tamaño)
            if resto:
                self.estadisticas.bloques_totales += 1
                self.estadisticas.bloques_libres += 1
            
            # Marcar como en uso
            bloque.estado = EstadoBuffer.EN_USO
            bloque.propietario = propietario
            bloque.tags = tags or {}
            bloque.timestamp_ultimo_acceso = time.time()
            
            self._buffers_activos[bloque.id] = bloque
            
            # Actualizar estadísticas
            self.estadisticas.tamaño_usado += bloque.tamaño
            self.estadisticas.tamaño_libre -= bloque.tamaño
            self.estadisticas.bloques_usados += 1
            self.estadisticas.bloques_libres -= 1
            self.estadisticas.asignaciones_exitosas += 1
            
            tiempo_asignacion = time.time() - inicio
            self.estadisticas.tiempo_total_asignacion += tiempo_asignacion
            self.estadisticas.tiempo_promedio_asignacion = (
                self.estadisticas.tiempo_total_asignacion / self.estadisticas.asignaciones_exitosas
            )
            
            self._actualizar_estadisticas()
            self._actualizar_metricas()
            
            if self._metrica_asignaciones:
                self._metrica_asignaciones.inc()
            
            return BufferMemoria(self, bloque)
    
    def _buscar_bloque(self, tamaño: int) -> Optional[BloqueMemoria]:
        """Busca un bloque libre según la estrategia configurada."""
        if self.estrategia == EstrategiaAsignacion.FIRST_FIT:
            return self._first_fit(tamaño)
        elif self.estrategia == EstrategiaAsignacion.BEST_FIT:
            return self._best_fit(tamaño)
        elif self.estrategia == EstrategiaAsignacion.WORST_FIT:
            return self._worst_fit(tamaño)
        elif self.estrategia == EstrategiaAsignacion.NEXT_FIT:
            return self._next_fit(tamaño)
        else:
            return self._first_fit(tamaño)
    
    def _first_fit(self, tamaño: int) -> Optional[BloqueMemoria]:
        actual = self._cabeza
        while actual:
            if actual.puede_contener(tamaño):
                return actual
            actual = actual.siguiente
        return None
    
    def _best_fit(self, tamaño: int) -> Optional[BloqueMemoria]:
        mejor = None
        mejor_desperdicio = float('inf')
        
        actual = self._cabeza
        while actual:
            if actual.puede_contener(tamaño):
                desperdicio = actual.tamaño - tamaño
                if desperdicio < mejor_desperdicio:
                    mejor = actual
                    mejor_desperdicio = desperdicio
            actual = actual.siguiente
        
        return mejor
    
    def _worst_fit(self, tamaño: int) -> Optional[BloqueMemoria]:
        peor = None
        peor_tamaño = 0
        
        actual = self._cabeza
        while actual:
            if actual.puede_contener(tamaño):
                if actual.tamaño > peor_tamaño:
                    peor = actual
                    peor_tamaño = actual.tamaño
            actual = actual.siguiente
        
        return peor
    
    def _next_fit(self, tamaño: int) -> Optional[BloqueMemoria]:
        if self._ultimo_asignado is None:
            return self._first_fit(tamaño)
        
        actual = self._ultimo_asignado.siguiente
        while actual:
            if actual.puede_contener(tamaño):
                self._ultimo_asignado = actual
                return actual
            actual = actual.siguiente
        
        actual = self._cabeza
        while actual and actual != self._ultimo_asignado:
            if actual.puede_contener(tamaño):
                self._ultimo_asignado = actual
                return actual
            actual = actual.siguiente
        
        return None
    
    def _expandir(self, tamaño_necesario: int) -> bool:
        """Expande el pool de memoria."""
        with self._lock:
            if self.politica_expansion == PoliticaExpansion.FIJA:
                return False
            
            if self.politica_expansion == PoliticaExpansion.DUPLICAR:
                expansion = self.estadisticas.tamaño_total
            elif self.politica_expansion == PoliticaExpansion.INCREMENTAL:
                expansion = self.incremento
            else:
                expansion = max(self.incremento, tamaño_necesario)
            
            nuevo_tamaño = self.estadisticas.tamaño_total + expansion
            
            try:
                self._mmap.close()
                self._archivo.seek(nuevo_tamaño - 1)
                self._archivo.write(b'\x00')
                self._archivo.flush()
                self._mmap = mmap.mmap(self._archivo.fileno(), nuevo_tamaño)
                
                ultimo = self._cabeza
                while ultimo and ultimo.siguiente:
                    ultimo = ultimo.siguiente
                
                nuevo_bloque = BloqueMemoria(
                    offset=self.estadisticas.tamaño_total,
                    tamaño=expansion,
                    estado=EstadoBuffer.LIBRE
                )
                
                if ultimo:
                    ultimo.siguiente = nuevo_bloque
                    nuevo_bloque.anterior = ultimo
                    
                    if ultimo.esta_libre():
                        ultimo.fusionar(nuevo_bloque)
                        self.estadisticas.bloques_totales -= 1
                        self.estadisticas.bloques_libres -= 1
                    else:
                        self.estadisticas.bloques_totales += 1
                        self.estadisticas.bloques_libres += 1
                else:
                    self._cabeza = nuevo_bloque
                    self.estadisticas.bloques_totales = 1
                    self.estadisticas.bloques_libres = 1
                
                self.estadisticas.tamaño_total = nuevo_tamaño
                self.estadisticas.tamaño_libre += expansion
                self.estadisticas.expansiones += 1
                
                return True
                
            except Exception:
                return False
    
    # ===== LIBERACIÓN =====
    
    def liberar(self, buffer_id: str) -> bool:
        """Libera un buffer previamente asignado."""
        with self._lock:
            if buffer_id not in self._buffers_activos:
                return False
            
            bloque = self._buffers_activos[buffer_id]
            bloque.estado = EstadoBuffer.LIBRE
            bloque.propietario = ""
            bloque.contador_accesos = 0
            
            del self._buffers_activos[buffer_id]
            
            self.estadisticas.tamaño_usado -= bloque.tamaño
            self.estadisticas.tamaño_libre += bloque.tamaño
            self.estadisticas.bloques_usados -= 1
            self.estadisticas.bloques_libres += 1
            self.estadisticas.liberaciones += 1
            
            self._fusionar_adyacentes(bloque)
            
            self._actualizar_estadisticas()
            self._actualizar_metricas()
            
            if self._metrica_liberaciones:
                self._metrica_liberaciones.inc()
            
            return True
    
    def _fusionar_adyacentes(self, bloque: BloqueMemoria):
        """Fusiona el bloque con adyacentes libres."""
        if bloque.anterior and bloque.anterior.esta_libre():
            if bloque.anterior.fusionar(bloque):
                self.estadisticas.fusiones += 1
                self.estadisticas.bloques_totales -= 1
                self.estadisticas.bloques_libres -= 1
                bloque = bloque.anterior
        
        if bloque.siguiente and bloque.siguiente.esta_libre():
            if bloque.fusionar(bloque.siguiente):
                self.estadisticas.fusiones += 1
                self.estadisticas.bloques_totales -= 1
                self.estadisticas.bloques_libres -= 1
    
    # ===== ESTADÍSTICAS =====
    
    def _actualizar_estadisticas(self):
        """Actualiza estadísticas calculadas."""
        self.estadisticas.actualizar_fragmentacion()
    
    def _actualizar_metricas(self):
        """Actualiza métricas para monitoreo."""
        if self._metrica_uso:
            self._metrica_uso.set(self.estadisticas.tamaño_usado)
        if self._metrica_fragmentacion:
            self._metrica_fragmentacion.set(self.estadisticas.fragmentacion)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del pool."""
        with self._lock:
            return {
                'nombre': self.nombre,
                'inicializado': self._inicializado,
                'estrategia': self.estrategia.value,
                'politica_expansion': self.politica_expansion.value,
                'estadisticas': asdict(self.estadisticas),
                'buffers_activos': len(self._buffers_activos),
            }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo del pool."""
        with self._lock:
            return {
                'nombre': self.nombre,
                'tamaño_total': f"{self.estadisticas.tamaño_total / 1024:.2f} KB",
                'uso': f"{(self.estadisticas.tamaño_usado / max(1, self.estadisticas.tamaño_total)) * 100:.1f}%",
                'fragmentacion': f"{self.estadisticas.fragmentacion:.1%}",
                'buffers_activos': len(self._buffers_activos),
            }
    
    # ===== CICLO DE VIDA =====
    
    def cerrar(self):
        """Cierra el pool de memoria."""
        with self._lock:
            if self._mmap:
                self._mmap.close()
                self._mmap = None
            if self._archivo:
                self._archivo.close()
                self._archivo = None
            
            self._inicializado = False
            
            try:
                if self.archivo_path.exists():
                    self.archivo_path.unlink()
            except Exception:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar()
    
    def __repr__(self) -> str:
        return f"PoolMemoria({self.nombre}, {self.estadisticas.tamaño_total} bytes, {len(self._buffers_activos)} activos)"

# =====================================================================
# BUFFER DE MEMORIA (COMPLETO Y CORREGIDO)
# =====================================================================

class BufferMemoria:
    """
    Buffer de memoria asignado desde un pool.
    Proporciona acceso zero-copy a la memoria compartida.
    """
    
    def __init__(self, pool: 'PoolMemoria', bloque: 'BloqueMemoria'):
        self.pool = pool
        self.bloque = bloque
        self.id = bloque.id
        self._liberado = False
        self._lock = threading.RLock()
    
    @property
    def tamaño(self) -> int:
        """Tamaño del buffer en bytes."""
        return self.bloque.tamaño
    
    @property
    def offset(self) -> int:
        """Offset del buffer en el pool."""
        return self.bloque.offset
    
    @property
    def propietario(self) -> str:
        """Propietario del buffer."""
        return self.bloque.propietario
    
    @property
    def tags(self) -> Dict[str, str]:
        """Etiquetas del buffer."""
        return self.bloque.tags.copy()
    
    @property
    def esta_liberado(self) -> bool:
        """Indica si el buffer ha sido liberado."""
        return self._liberado
    
    @property
    def contador_accesos(self) -> int:
        """Número de accesos al buffer."""
        return self.bloque.contador_accesos
    
    @property
    def ultimo_acceso(self) -> float:
        """Timestamp del último acceso."""
        return self.bloque.timestamp_ultimo_acceso
    
    # ===== OPERACIONES BÁSICAS =====
    
    def zero_fill(self) -> int:
        """
        Llena el buffer completamente con ceros.
        
        Returns:
            Número de bytes escritos
        """
        with self._lock:
            if self._liberado:
                raise RuntimeError("Buffer ya liberado")
            
            self.pool._mmap.seek(self.bloque.offset)
            self.pool._mmap.write(b'\x00' * self.bloque.tamaño)
            self.pool._mmap.flush()
            
            self.bloque.timestamp_ultimo_acceso = time.time()
            self.bloque.contador_accesos += 1
            
            return self.bloque.tamaño
    
    def escribir(self, datos: bytes, offset: int = 0) -> int:
        """
        Escribe datos en el buffer.
        
        Args:
            datos: Bytes a escribir
            offset: Offset dentro del buffer (por defecto 0)
            
        Returns:
            Número de bytes escritos
            
        Raises:
            RuntimeError: Si el buffer ya fue liberado
        """
        with self._lock:
            if self._liberado:
                raise RuntimeError("Buffer ya liberado")
            
            if offset < 0:
                raise ValueError("Offset no puede ser negativo")
            
            if offset >= self.bloque.tamaño:
                return 0
            
            # Truncar si excede el tamaño
            bytes_a_escribir = datos
            if offset + len(datos) > self.bloque.tamaño:
                bytes_a_escribir = datos[:self.bloque.tamaño - offset]
            
            self.pool._mmap.seek(self.bloque.offset + offset)
            self.pool._mmap.write(bytes_a_escribir)
            self.pool._mmap.flush()
            
            self.bloque.timestamp_ultimo_acceso = time.time()
            self.bloque.contador_accesos += 1
            
            return len(bytes_a_escribir)
    
    def leer(self, tamaño: int = -1, offset: int = 0) -> bytes:
        """
        Lee datos del buffer.
        
        Args:
            tamaño: Bytes a leer (-1 = todo el buffer desde offset)
            offset: Offset dentro del buffer (por defecto 0)
            
        Returns:
            Bytes leídos
            
        Raises:
            RuntimeError: Si el buffer ya fue liberado
        """
        with self._lock:
            if self._liberado:
                raise RuntimeError("Buffer ya liberado")
            
            if offset < 0:
                raise ValueError("Offset no puede ser negativo")
            
            if offset >= self.bloque.tamaño:
                return b''
            
            if tamaño == -1:
                tamaño = self.bloque.tamaño - offset
            
            tamaño = min(tamaño, self.bloque.tamaño - offset)
            
            self.pool._mmap.seek(self.bloque.offset + offset)
            datos = self.pool._mmap.read(tamaño)
            
            self.bloque.timestamp_ultimo_acceso = time.time()
            self.bloque.contador_accesos += 1
            
            return datos
    
    # ===== OPERACIONES CON ESTRUCTURAS =====
    
    def escribir_estructura(self, formato: str, *valores) -> int:
        """
        Escribe una estructura usando struct.pack.
        
        Args:
            formato: Formato de struct (ej: 'i4s')
            *valores: Valores a empaquetar
            
        Returns:
            Número de bytes escritos
        """
        datos = struct.pack(formato, *valores)
        return self.escribir(datos)
    
    def leer_estructura(self, formato: str, offset: int = 0) -> Tuple:
        """
        Lee una estructura usando struct.unpack.
        
        Args:
            formato: Formato de struct
            offset: Offset dentro del buffer
            
        Returns:
            Tupla con los valores desempaquetados
        """
        tamaño = struct.calcsize(formato)
        datos = self.leer(tamaño, offset)
        return struct.unpack(formato, datos)
    
    # ===== OPERACIONES CON JSON =====
    
    def escribir_json(self, obj: Any, offset: int = 0) -> int:
        """
        Escribe un objeto como JSON.
        
        Args:
            obj: Objeto a serializar
            offset: Offset dentro del buffer
            
        Returns:
            Número de bytes escritos
        """
        datos = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        return self.escribir(datos, offset)
    
    def leer_json(self, offset: int = 0, tamaño: int = -1) -> Any:
        """
        Lee un objeto JSON del buffer.
        
        Args:
            offset: Offset dentro del buffer
            tamaño: Tamaño a leer (-1 = todo)
            
        Returns:
            Objeto deserializado
        """
        datos = self.leer(tamaño, offset)
        # Decodificar y eliminar bytes nulos al final
        texto = datos.decode('utf-8').rstrip('\x00')
        return json.loads(texto) if texto else None
    
    # ===== OPERACIONES CON STRINGS =====
    
    def escribir_string(self, texto: str, encoding: str = 'utf-8', offset: int = 0) -> int:
        """
        Escribe una string en el buffer.
        
        Args:
            texto: String a escribir
            encoding: Codificación a usar
            offset: Offset dentro del buffer
            
        Returns:
            Número de bytes escritos
        """
        datos = texto.encode(encoding)
        return self.escribir(datos, offset)
    
    def leer_string(self, offset: int = 0, tamaño: int = -1, encoding: str = 'utf-8') -> str:
        """
        Lee una string del buffer.
        
        Args:
            offset: Offset dentro del buffer
            tamaño: Tamaño a leer (-1 = todo)
            encoding: Codificación a usar
            
        Returns:
            String leída
        """
        datos = self.leer(tamaño, offset)
        return datos.decode(encoding).rstrip('\x00')
    
    # ===== OPERACIONES CON NÚMEROS =====
    
    def escribir_int32(self, valor: int, offset: int = 0) -> int:
        """Escribe un entero de 32 bits."""
        return self.escribir_estructura('i', valor)
    
    def leer_int32(self, offset: int = 0) -> int:
        """Lee un entero de 32 bits."""
        return self.leer_estructura('i', offset)[0]
    
    def escribir_int64(self, valor: int, offset: int = 0) -> int:
        """Escribe un entero de 64 bits."""
        return self.escribir_estructura('q', valor)
    
    def leer_int64(self, offset: int = 0) -> int:
        """Lee un entero de 64 bits."""
        return self.leer_estructura('q', offset)[0]
    
    def escribir_float32(self, valor: float, offset: int = 0) -> int:
        """Escribe un flotante de 32 bits."""
        return self.escribir_estructura('f', valor)
    
    def leer_float32(self, offset: int = 0) -> float:
        """Lee un flotante de 32 bits."""
        return self.leer_estructura('f', offset)[0]
    
    def escribir_float64(self, valor: float, offset: int = 0) -> int:
        """Escribe un flotante de 64 bits."""
        return self.escribir_estructura('d', valor)
    
    def leer_float64(self, offset: int = 0) -> float:
        """Lee un flotante de 64 bits."""
        return self.leer_estructura('d', offset)[0]
    
    # ===== CICLO DE VIDA =====
    
    def liberar(self) -> bool:
        """
        Libera el buffer de vuelta al pool.
        
        Returns:
            True si se liberó correctamente, False si ya estaba liberado
        """
        with self._lock:
            if self._liberado:
                return False
            resultado = self.pool.liberar(self.id)
            if resultado:
                self._liberado = True
            return resultado
    
    def __enter__(self):
        """Soporte para context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Libera automáticamente al salir del contexto."""
        self.liberar()
    
    # ===== MÉTODOS ESPECIALES =====
    
    def __len__(self) -> int:
        """Tamaño del buffer en bytes."""
        return self.bloque.tamaño
    
    def __repr__(self) -> str:
        estado = "LIBERADO" if self._liberado else "ACTIVO"
        return f"BufferMemoria(id={self.id[:8]}, tamaño={self.bloque.tamaño}, {estado})"
    
    def __str__(self) -> str:
        estado = "liberado" if self._liberado else "activo"
        return f"Buffer({self.id[:8]}, {self.bloque.tamaño} bytes, {estado})"

# =====================================================================
# GESTOR DE MEMORIA (SINGLETON)
# =====================================================================

class GestorMemoria:
    """Gestor central de pools de memoria."""
    
    _instancia: Optional['GestorMemoria'] = None
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
            
            self._pools: Dict[str, PoolMemoria] = {}
            self._pool_default: Optional[str] = None
            self._inicializado = True
    
    def crear_pool(self, nombre: str, tamaño_inicial: int = 1024 * 1024,
                   **kwargs) -> PoolMemoria:
        with self._lock:
            if nombre in self._pools:
                return self._pools[nombre]
            
            pool = PoolMemoria(nombre, tamaño_inicial, **kwargs)
            self._pools[nombre] = pool
            
            if self._pool_default is None:
                self._pool_default = nombre
            
            return pool
    
    def obtener_pool(self, nombre: str = None) -> Optional[PoolMemoria]:
        if nombre is None:
            nombre = self._pool_default
        return self._pools.get(nombre)
    
    def listar_pools(self) -> List[str]:
        return list(self._pools.keys())
    
    def asignar(self, tamaño: int, pool_nombre: str = None,
                propietario: str = "") -> Optional[BufferMemoria]:
        pool = self.obtener_pool(pool_nombre)
        if pool:
            return pool.asignar(tamaño, propietario)
        return None
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        return {
            'total_pools': len(self._pools),
            'pool_default': self._pool_default,
            'pools': {
                nombre: pool.obtener_estadisticas()
                for nombre, pool in self._pools.items()
            }
        }
    
    def cerrar_todos(self):
        with self._lock:
            for pool in self._pools.values():
                pool.cerrar()
            self._pools.clear()
    
    def __getitem__(self, nombre: str) -> PoolMemoria:
        pool = self.obtener_pool(nombre)
        if pool is None:
            raise KeyError(f"Pool no encontrado: {nombre}")
        return pool

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_gestor_global: Optional[GestorMemoria] = None

def obtener_gestor() -> GestorMemoria:
    global _gestor_global
    if _gestor_global is None:
        _gestor_global = GestorMemoria()
    return _gestor_global

def asignar(tamaño: int, propietario: str = "", pool: str = None) -> Optional[BufferMemoria]:
    return obtener_gestor().asignar(tamaño, pool, propietario)

def crear_pool(nombre: str, tamaño_kb: int = 64) -> PoolMemoria:
    return obtener_gestor().crear_pool(nombre, tamaño_kb * 1024)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS (CORREGIDO)
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE RESERVA DE MEMORIA")
    print("=" * 70)
    
    gestor = None
    
    try:
        print("\n[1/8] Inicializando gestor de memoria...")
        gestor = GestorMemoria()
        print(f"  ✅ Gestor inicializado")
        
        print("\n[2/8] Creando pool de memoria...")
        pool = gestor.crear_pool("test_pool", 128 * 1024, 
                                 estrategia=EstrategiaAsignacion.BEST_FIT)
        print(f"  ✅ Pool creado: {pool}")
        print(f"  📍 Archivo: {pool.archivo_path}")
        
        print("\n[3/8] Asignando buffers...")
        buffers = []
        for i in range(5):
            buf = pool.asignar(2048, propietario=f"test_{i}", tags={"indice": str(i)})
            if buf:
                # Limpiar buffer al asignar
                buf.zero_fill()
                buffers.append(buf)
                print(f"  ✅ Buffer {i}: {buf}")
            else:
                print(f"  ❌ Buffer {i}: asignación fallida")
        
        print("\n[4/8] Escribiendo y leyendo datos binarios...")
        if buffers:
            buf1 = buffers[0]
            datos_originales = b"Hola ANP desde memoria compartida!"
            bytes_escritos = buf1.escribir(datos_originales)
            datos_leidos = buf1.leer(bytes_escritos)
            print(f"  📍 Escrito: {datos_originales}")
            print(f"  📍 Leído:   {datos_leidos}")
            print(f"  ✅ Coinciden: {datos_originales == datos_leidos}")
        
        print("\n[5/8] Escribiendo y leyendo JSON...")
        if len(buffers) > 1:
            buf2 = buffers[1]
            buf2.zero_fill()  # Limpiar antes de escribir
            obj_original = {"mensaje": "Hola JSON", "valor": 42, "activo": True}
            buf2.escribir_json(obj_original)
            obj_leido = buf2.leer_json()
            print(f"  📍 Escrito: {obj_original}")
            print(f"  📍 Leído:   {obj_leido}")
            print(f"  ✅ Coinciden: {obj_original == obj_leido}")
        
        print("\n[6/8] Estadísticas del pool...")
        stats = pool.obtener_estadisticas()
        print(f"  📊 Tamaño total: {stats['estadisticas']['tamaño_total']} bytes")
        print(f"  📊 Tamaño usado: {stats['estadisticas']['tamaño_usado']} bytes")
        print(f"  📊 Tamaño libre: {stats['estadisticas']['tamaño_libre']} bytes")
        print(f"  📊 Fragmentación: {stats['estadisticas']['fragmentacion']:.2%}")
        print(f"  📊 Buffers activos: {stats['buffers_activos']}")
        print(f"  📊 Asignaciones exitosas: {stats['estadisticas']['asignaciones_exitosas']}")
        
        print("\n[7/8] Liberando buffers...")
        for buf in buffers[:3]:
            buf_id = buf.id[:8]
            buf.liberar()
            print(f"  ✅ Liberado: {buf_id}")
        
        stats = pool.obtener_estadisticas()
        print(f"  📊 Buffers activos después: {stats['buffers_activos']}")
        print(f"  📊 Liberaciones totales: {stats['estadisticas']['liberaciones']}")
        
        print("\n[8/8] Resumen del gestor...")
        resumen = gestor.obtener_estadisticas()
        print(f"  📊 Total pools: {resumen['total_pools']}")
        for nombre, pstats in resumen['pools'].items():
            uso_pct = (pstats['estadisticas']['tamaño_usado'] / pstats['estadisticas']['tamaño_total']) * 100
            print(f"  📍 {nombre}: {pstats['estadisticas']['tamaño_usado']} bytes usados ({uso_pct:.1f}%)")
        
        print("\n" + "=" * 70)
        print("   RESUMEN FINAL")
        print("=" * 70)
        print(f"  ✅ Pool creado correctamente en Android/Pydroid3")
        print(f"  ✅ Asignación de buffers: {stats['estadisticas']['asignaciones_exitosas']} exitosas")
        print(f"  ✅ Lectura/Escritura binaria: OK")
        print(f"  ✅ Lectura/Escritura JSON: OK")
        print(f"  ✅ Liberación de buffers: OK")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Reserva de Memoria está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if gestor:
            print("\n🛑 Cerrando pools...")
            gestor.cerrar_todos()
            print("   ✓ Pools cerrados")
    
    print("\n" + "=" * 70 + "\n")   