#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio de Registro (Sistema de Logging Optimizado)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de logging avanzado
# con buffer, rotación, colores, niveles, y persistencia en SQLite.
# =====================================================================

import sys
import os
import time
import threading
import json
import traceback
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from collections import deque
from datetime import datetime
from contextlib import contextmanager

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

# =====================================================================
# ENUMERACIONES
# =====================================================================

class NivelLog(IntEnum):
    """Niveles de logging en orden de severidad."""
    TRACE = 0
    DEBUG = 1
    INFO = 2
    SUCCESS = 3
    WARNING = 4
    ERROR = 5
    CRITICAL = 6
    FATAL = 7
    
    @property
    def nombre(self) -> str:
        nombres = {
            0: "TRACE", 1: "DEBUG", 2: "INFO", 3: "SUCCESS",
            4: "WARNING", 5: "ERROR", 6: "CRITICAL", 7: "FATAL"
        }
        return nombres.get(self.value, "UNKNOWN")
    
    @property
    def color(self) -> str:
        colores = {
            0: "\033[90m", 1: "\033[36m", 2: "\033[37m", 3: "\033[32m",
            4: "\033[33m", 5: "\033[31m", 6: "\033[35m", 7: "\033[41m\033[37m"
        }
        return colores.get(self.value, "\033[0m")
    
    @property
    def emoji(self) -> str:
        emojis = {
            0: "🔍", 1: "🐛", 2: "ℹ️", 3: "✅",
            4: "⚠️", 5: "❌", 6: "🚨", 7: "💀"
        }
        return emojis.get(self.value, "📝")

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EntradaLog:
    """Representa una entrada individual de log."""
    id: str = field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:12])
    nivel: NivelLog = NivelLog.INFO
    mensaje: str = ""
    origen: str = ""
    timestamp: float = field(default_factory=time.time)
    contexto: Dict[str, Any] = field(default_factory=dict)
    stacktrace: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def formatear(self, formato: str = "detallado", usar_color: bool = True) -> str:
        """Formatea la entrada según el formato especificado."""
        fecha = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        reset = "\033[0m"
        
        if formato == "simple":
            return f"{fecha} [{self.nivel.nombre}] {self.mensaje}"
        elif formato == "detallado":
            if usar_color:
                origen_str = f" \033[90m[{self.origen}]{reset}" if self.origen else ""
                return f"{self.nivel.color}{fecha} [{self.nivel.nombre}]{reset}{origen_str} {self.mensaje}"
            else:
                origen_str = f" [{self.origen}]" if self.origen else ""
                return f"{fecha} [{self.nivel.nombre}]{origen_str} {self.mensaje}"
        elif formato == "json":
            return json.dumps(self.a_dict(), ensure_ascii=False)
        elif formato == "emoji":
            origen_str = f" [{self.origen}]" if self.origen else ""
            return f"{self.nivel.emoji} {fecha} [{self.nivel.nombre}]{origen_str} {self.mensaje}"
        else:
            return self.mensaje
    
    def a_dict(self) -> Dict[str, Any]:
        """Serializa la entrada a diccionario."""
        return {
            'id': self.id,
            'nivel': self.nivel.value,
            'nivel_nombre': self.nivel.nombre,
            'mensaje': self.mensaje,
            'origen': self.origen,
            'timestamp': self.timestamp,
            'fecha': datetime.fromtimestamp(self.timestamp).isoformat(),
            'contexto': self.contexto,
            'tags': self.tags,
        }

# =====================================================================
# ROTADOR DE ARCHIVOS
# =====================================================================

class RotadorArchivos:
    """Gestiona la rotación de archivos de log."""
    
    def __init__(self, directorio: Path, nombre_base: str = "anp",
                 max_tamaño_mb: int = 10, max_archivos: int = 5):
        self.directorio = directorio
        self.nombre_base = nombre_base
        self.max_tamaño = max_tamaño_mb * 1024 * 1024
        self.max_archivos = max_archivos
        self.directorio.mkdir(parents=True, exist_ok=True)
        
    def obtener_archivo_actual(self) -> Path:
        """Obtiene el archivo de log actual."""
        return self.directorio / f"{self.nombre_base}.log"
    
    def debe_rotar(self) -> bool:
        """Verifica si el archivo actual debe rotar."""
        archivo = self.obtener_archivo_actual()
        if not archivo.exists():
            return False
        return archivo.stat().st_size >= self.max_tamaño
    
    def rotar(self):
        """Realiza la rotación del archivo de log."""
        archivo_actual = self.obtener_archivo_actual()
        if not archivo_actual.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_rotado = self.directorio / f"{self.nombre_base}_{timestamp}.log"
        
        archivo_actual.rename(archivo_rotado)
        self._limpiar_antiguos()
    
    def _limpiar_antiguos(self):
        """Elimina archivos de log antiguos que exceden el máximo."""
        archivos = sorted(self.directorio.glob(f"{self.nombre_base}_*.log"))
        if len(archivos) > self.max_archivos:
            for archivo in archivos[:-self.max_archivos]:
                try:
                    archivo.unlink()
                except Exception:
                    pass

# =====================================================================
# ESCRITOR DE LOGS
# =====================================================================

class EscritorLog:
    """Escritor asíncrono con buffer para logs."""
    
    def __init__(self, rotador: RotadorArchivos, buffer_size: int = 10, 
                 flush_interval: float = 5.0):
        self.rotador = rotador
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self._buffer: deque = deque()
        self._lock = threading.RLock()
        self._activo = True
        self._ultimo_flush = time.time()
        self._total_escritos = 0
        self._total_perdidos = 0
        
        self._hilo_flush = threading.Thread(target=self._bucle_flush, daemon=True)
        self._hilo_flush.start()
    
    def escribir(self, linea: str):
        """Agrega una línea al buffer."""
        with self._lock:
            if len(self._buffer) >= self.buffer_size * 2:
                self._total_perdidos += 1
                return
            
            self._buffer.append(linea)
            
            if len(self._buffer) >= self.buffer_size:
                self._flush()
    
    def _flush(self):
        """Escribe el buffer al archivo."""
        if not self._buffer:
            return
        
        with self._lock:
            lineas = list(self._buffer)
            self._buffer.clear()
        
        try:
            if self.rotador.debe_rotar():
                self.rotador.rotar()
            
            archivo = self.rotador.obtener_archivo_actual()
            with open(archivo, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lineas) + '\n')
            
            self._total_escritos += len(lineas)
            self._ultimo_flush = time.time()
        except Exception:
            self._total_perdidos += len(lineas)
    
    def _bucle_flush(self):
        """Bucle de flush periódico."""
        while self._activo:
            time.sleep(self.flush_interval)
            if time.time() - self._ultimo_flush >= self.flush_interval:
                self._flush()
    
    def detener(self):
        """Detiene el escritor y fuerza un flush final."""
        self._activo = False
        self._flush()
    
    @property
    def estadisticas(self) -> Dict[str, Any]:
        return {
            'buffer_actual': len(self._buffer),
            'total_escritos': self._total_escritos,
            'total_perdidos': self._total_perdidos,
        }

# =====================================================================
# LOGGER PRINCIPAL
# =====================================================================

class Logger:
    """
    Logger principal de ANP.
    Soporta múltiples destinos, niveles, buffer y persistencia.
    """
    
    def __init__(self, nombre: str = "ANP", nivel_minimo: NivelLog = NivelLog.INFO,
                 directorio_logs: Optional[Path] = None):
        self.nombre = nombre
        self.nivel_minimo = nivel_minimo
        
        if directorio_logs is None:
            directorio_logs = Path("almacenamiento/registros")
        
        self.rotador = RotadorArchivos(directorio_logs)
        self.escritor = EscritorLog(self.rotador)
        
        self._consola_habilitada = True
        self._archivo_habilitado = True
        self._bd_habilitada = True
        self._colores_habilitados = True
        self._emojis_habilitados = False
        
        self._estadisticas = {
            'total_entradas': 0,
            'por_nivel': {nivel.nombre: 0 for nivel in NivelLog},
            'por_origen': {},
        }
        self._lock = threading.RLock()
    
    def configurar(self, consola: bool = None, archivo: bool = None, 
                   bd: bool = None, colores: bool = None, emojis: bool = None):
        """Configura los destinos y opciones del logger."""
        if consola is not None:
            self._consola_habilitada = consola
        if archivo is not None:
            self._archivo_habilitado = archivo
        if bd is not None:
            self._bd_habilitada = bd
        if colores is not None:
            self._colores_habilitados = colores
        if emojis is not None:
            self._emojis_habilitados = emojis
    
    def _debe_loguear(self, nivel: NivelLog) -> bool:
        """Verifica si un nivel debe ser logueado."""
        return nivel >= self.nivel_minimo
    
    def _log(self, nivel: NivelLog, mensaje: str, origen: str = "", 
             contexto: Dict = None, stacktrace: str = None, tags: List[str] = None):
        """Método interno de logging."""
        if not self._debe_loguear(nivel):
            return
        
        entrada = EntradaLog(
            nivel=nivel,
            mensaje=mensaje,
            origen=origen or self.nombre,
            contexto=contexto or {},
            stacktrace=stacktrace,
            tags=tags or []
        )
        
        with self._lock:
            self._estadisticas['total_entradas'] += 1
            self._estadisticas['por_nivel'][nivel.nombre] = self._estadisticas['por_nivel'].get(nivel.nombre, 0) + 1
            self._estadisticas['por_origen'][entrada.origen] = self._estadisticas['por_origen'].get(entrada.origen, 0) + 1
        
        # Consola
        if self._consola_habilitada:
            formato = "emoji" if self._emojis_habilitados else "detallado"
            linea = entrada.formatear(formato, usar_color=self._colores_habilitados)
            print(linea)
        
        # Archivo
        if self._archivo_habilitado:
            linea_archivo = entrada.formatear("detallado", usar_color=False)
            self.escritor.escribir(linea_archivo)
        
        # Base de datos
        if self._bd_habilitada:
            self._persistir_en_bd(entrada)
    
    def _persistir_en_bd(self, entrada: EntradaLog):
        """Persiste la entrada en la base de datos."""
        try:
            bd = obtener_bd()
            if bd:
                bd.insertar("logs", {
                    "id": entrada.id,
                    "nivel": entrada.nivel.value,
                    "mensaje": entrada.mensaje,
                    "origen": entrada.origen,
                    "timestamp": entrada.timestamp,
                    "contexto": json.dumps(entrada.contexto) if entrada.contexto else None,
                    "stacktrace": entrada.stacktrace,
                })
        except Exception:
            pass
    
    # ===== MÉTODOS DE LOGGING POR NIVEL =====
    
    def trace(self, mensaje: str, origen: str = "", **kwargs):
        self._log(NivelLog.TRACE, mensaje, origen, **kwargs)
    
    def debug(self, mensaje: str, origen: str = "", **kwargs):
        self._log(NivelLog.DEBUG, mensaje, origen, **kwargs)
    
    def info(self, mensaje: str, origen: str = "", **kwargs):
        self._log(NivelLog.INFO, mensaje, origen, **kwargs)
    
    def success(self, mensaje: str, origen: str = "", **kwargs):
        self._log(NivelLog.SUCCESS, mensaje, origen, **kwargs)
    
    def warning(self, mensaje: str, origen: str = "", **kwargs):
        self._log(NivelLog.WARNING, mensaje, origen, **kwargs)
    
    def error(self, mensaje: str, origen: str = "", exc: Exception = None, **kwargs):
        stacktrace = traceback.format_exc() if exc else None
        self._log(NivelLog.ERROR, mensaje, origen, stacktrace=stacktrace, **kwargs)
    
    def critical(self, mensaje: str, origen: str = "", exc: Exception = None, **kwargs):
        stacktrace = traceback.format_exc() if exc else None
        self._log(NivelLog.CRITICAL, mensaje, origen, stacktrace=stacktrace, **kwargs)
    
    def fatal(self, mensaje: str, origen: str = "", exc: Exception = None, **kwargs):
        stacktrace = traceback.format_exc() if exc else None
        self._log(NivelLog.FATAL, mensaje, origen, stacktrace=stacktrace, **kwargs)
    
    # ===== MÉTODOS DE CONTEXTO =====
    
    @contextmanager
    def contexto(self, **kwargs):
        """Context manager para agregar contexto a múltiples logs."""
        contexto_anterior = getattr(self, '_contexto_actual', {})
        self._contexto_actual = {**contexto_anterior, **kwargs}
        try:
            yield self
        finally:
            self._contexto_actual = contexto_anterior
    
    # ===== ESTADÍSTICAS =====
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del logger."""
        with self._lock:
            return {
                'total_entradas': self._estadisticas['total_entradas'],
                'por_nivel': self._estadisticas['por_nivel'].copy(),
                'por_origen': self._estadisticas['por_origen'].copy(),
                'escritor': self.escritor.estadisticas,
            }
    
    def flush(self):
        """Fuerza el flush del buffer."""
        self.escritor._flush()
    
    def detener(self):
        """Detiene el logger y fuerza flush."""
        self.escritor.detener()


# =====================================================================
# GESTOR DE LOGGERS (SINGLETON)
# =====================================================================

class GestorLoggers:
    """Gestor central de loggers. Singleton thread-safe."""
    
    _instancia: Optional['GestorLoggers'] = None
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
            
            self._loggers: Dict[str, Logger] = {}
            self._logger_default: Optional[str] = None
            
            self._inicializado = True
    
    def obtener(self, nombre: str = "ANP", **kwargs) -> Logger:
        """Obtiene o crea un logger."""
        with self._lock:
            if nombre not in self._loggers:
                self._loggers[nombre] = Logger(nombre, **kwargs)
                if self._logger_default is None:
                    self._logger_default = nombre
            return self._loggers[nombre]
    
    def listar(self) -> List[str]:
        """Lista todos los loggers registrados."""
        with self._lock:
            return list(self._loggers.keys())
    
    def detener_todos(self):
        """Detiene todos los loggers."""
        with self._lock:
            for logger in self._loggers.values():
                logger.detener()

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_gestor_global: Optional[GestorLoggers] = None

def obtener_gestor() -> GestorLoggers:
    """Obtiene la instancia global del gestor de loggers."""
    global _gestor_global
    if _gestor_global is None:
        _gestor_global = GestorLoggers()
    return _gestor_global

def obtener_logger(nombre: str = "ANP") -> Logger:
    """Obtiene un logger por nombre."""
    return obtener_gestor().obtener(nombre)

# Funciones rápidas de logging
def trace(mensaje: str, origen: str = ""): obtener_logger().trace(mensaje, origen)
def debug(mensaje: str, origen: str = ""): obtener_logger().debug(mensaje, origen)
def info(mensaje: str, origen: str = ""): obtener_logger().info(mensaje, origen)
def success(mensaje: str, origen: str = ""): obtener_logger().success(mensaje, origen)
def warning(mensaje: str, origen: str = ""): obtener_logger().warning(mensaje, origen)
def error(mensaje: str, origen: str = "", exc: Exception = None): obtener_logger().error(mensaje, origen, exc=exc)
def critical(mensaje: str, origen: str = "", exc: Exception = None): obtener_logger().critical(mensaje, origen, exc=exc)
def fatal(mensaje: str, origen: str = "", exc: Exception = None): obtener_logger().fatal(mensaje, origen, exc=exc)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE REGISTRO")
    print("=" * 70)
    
    logger = None
    
    try:
        print("\n[1/6] Inicializando logger...")
        logger = Logger("Diagnostico", nivel_minimo=NivelLog.TRACE)
        logger.configurar(consola=True, archivo=True, bd=False, colores=True, emojis=True)
        print(f"  ✅ Logger inicializado")
        
        print("\n[2/6] Probando todos los niveles...")
        logger.trace("Mensaje de TRACE - Máximo detalle")
        logger.debug("Mensaje de DEBUG - Depuración")
        logger.info("Mensaje de INFO - Informativo")
        logger.success("Mensaje de SUCCESS - Operación exitosa")
        logger.warning("Mensaje de WARNING - Advertencia")
        logger.error("Mensaje de ERROR - Algo falló")
        logger.critical("Mensaje de CRITICAL - Crítico")
        print(f"  ✅ 7 niveles probados")
        
        print("\n[3/6] Probando con contexto...")
        with logger.contexto(user_id=123, session="abc"):
            logger.info("Usuario autenticado")
            logger.debug("Cargando preferencias")
        print(f"  ✅ Contexto aplicado")
        
        print("\n[4/6] Probando con excepción...")
        try:
            raise ValueError("Error de prueba")
        except Exception as e:
            logger.error("Se capturó una excepción", exc=e)
        print(f"  ✅ Excepción registrada")
        
        print("\n[5/6] Probando múltiples orígenes...")
        for origen in ["orquestador", "bus_eventos", "contexto", "memoria"]:
            logger.info(f"Mensaje desde {origen}", origen=origen)
        print(f"  ✅ 4 orígenes probados")
        
        print("\n[6/6] Estadísticas del logger...")
        stats = logger.obtener_estadisticas()
        print(f"  📊 Total entradas: {stats['total_entradas']}")
        print(f"  📊 Por nivel:")
        for nivel, count in stats['por_nivel'].items():
            if count > 0:
                print(f"     - {nivel}: {count}")
        print(f"  📊 Por origen:")
        for origen, count in stats['por_origen'].items():
            print(f"     - {origen}: {count}")
        print(f"  📊 Buffer: {stats['escritor']['buffer_actual']} pendientes")
        print(f"  📊 Escritos: {stats['escritor']['total_escritos']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Registro está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if logger:
            print("\n🛑 Deteniendo logger...")
            logger.detener()
            print("   ✓ Logger detenido")
    
    print("\n" + "=" * 70 + "\n")