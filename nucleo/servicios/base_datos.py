#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio de Base de Datos (El Corazón de la Persistencia)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de base de datos
# SQLite optimizado con WAL mode, conexiones thread-safe, migraciones
# automáticas, pooling de conexiones y un ORM ligero.
# =====================================================================

import sys
import os
import time
import sqlite3
import json
import threading
import hashlib
import uuid
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict
from functools import wraps, lru_cache
from contextlib import contextmanager
from datetime import datetime
import traceback

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from ..metricas import contador, medidor, histograma, indicador
except ImportError:
    def contador(nombre, **kwargs): return None
    def medidor(nombre, **kwargs): return None
    def histograma(nombre, **kwargs): return None
    def indicador(nombre, **kwargs): return None

# =====================================================================
# ENUMERACIONES
# =====================================================================

class TipoDato(Enum):
    """Tipos de datos soportados para columnas."""
    TEXTO = "TEXT"
    ENTERO = "INTEGER"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEANO = "BOOLEAN"
    FECHA = "DATETIME"
    JSON = "JSON"

class OperadorComparacion(Enum):
    """Operadores de comparación para consultas."""
    IGUAL = "="
    DIFERENTE = "!="
    MAYOR = ">"
    MENOR = "<"
    MAYOR_IGUAL = ">="
    MENOR_IGUAL = "<="
    LIKE = "LIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"

class OrdenDireccion(Enum):
    """Dirección de ordenamiento."""
    ASC = "ASC"
    DESC = "DESC"

class EstadoConexion(Enum):
    """Estados de una conexión."""
    LIBRE = "libre"
    EN_USO = "en_uso"
    CERRADA = "cerrada"
    ERROR = "error"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class Columna:
    """Definición de una columna en una tabla."""
    nombre: str
    tipo: TipoDato
    primaria: bool = False
    autoincrement: bool = False
    unica: bool = False
    no_nula: bool = False
    valor_default: Any = None
    referencia: Optional[str] = None  # tabla(columna)
    on_delete: Optional[str] = None   # CASCADE, SET NULL, etc.
    
    def a_sql(self) -> str:
        """Genera la definición SQL de la columna."""
        partes = [self.nombre, self.tipo.value]
        if self.primaria:
            partes.append("PRIMARY KEY")
            if self.autoincrement:
                partes.append("AUTOINCREMENT")
        if self.unica:
            partes.append("UNIQUE")
        if self.no_nula:
            partes.append("NOT NULL")
        if self.valor_default is not None:
            if isinstance(self.valor_default, str):
                partes.append(f"DEFAULT '{self.valor_default}'")
            else:
                partes.append(f"DEFAULT {self.valor_default}")
        if self.referencia:
            partes.append(f"REFERENCES {self.referencia}")
            if self.on_delete:
                partes.append(f"ON DELETE {self.on_delete}")
        return " ".join(partes)

@dataclass
class Indice:
    """Definición de un índice."""
    nombre: str
    columnas: List[str]
    unico: bool = False
    where: Optional[str] = None
    
    def a_sql(self, tabla: str) -> str:
        """Genera la definición SQL del índice."""
        tipo = "UNIQUE INDEX" if self.unico else "INDEX"
        columnas_str = ", ".join(self.columnas)
        sql = f"CREATE {tipo} IF NOT EXISTS {self.nombre} ON {tabla} ({columnas_str})"
        if self.where:
            sql += f" WHERE {self.where}"
        return sql

@dataclass
class EstadisticasBD:
    """Estadísticas de la base de datos."""
    consultas_ejecutadas: int = 0
    consultas_fallidas: int = 0
    tiempo_total_consultas: float = 0.0
    tiempo_promedio_consulta: float = 0.0
    transacciones: int = 0
    conexiones_activas: int = 0
    conexiones_max: int = 0
    tamaño_bd: int = 0
    tablas: int = 0
    indices: int = 0
    
    def registrar_consulta(self, exito: bool, tiempo_ms: float):
        self.consultas_ejecutadas += 1
        if not exito:
            self.consultas_fallidas += 1
        self.tiempo_total_consultas += tiempo_ms
        self.tiempo_promedio_consulta = self.tiempo_total_consultas / self.consultas_ejecutadas

# =====================================================================
# CONEXIÓN A BASE DE DATOS
# =====================================================================

class ConexionBD:
    """Wrapper thread-safe para conexiones SQLite."""
    
    def __init__(self, ruta_bd: Path, timeout: float = 30.0):
        self.ruta_bd = ruta_bd
        self.timeout = timeout
        self._conn: Optional[sqlite3.Connection] = None
        self._estado = EstadoConexion.LIBRE
        self._creada = time.time()
        self._ultimo_uso = time.time()
        self._contador_usos = 0
        self._lock = threading.RLock()
        self._id = str(uuid.uuid4())[:8]
    
    def conectar(self) -> bool:
        """Establece la conexión a la base de datos."""
        with self._lock:
            try:
                self._conn = sqlite3.connect(
                    str(self.ruta_bd),
                    timeout=self.timeout,
                    check_same_thread=False,
                    isolation_level=None  # Modo autocommit
                )
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
                self._conn.execute("PRAGMA cache_size=-64000")
                self._conn.execute("PRAGMA temp_store=MEMORY")
                self._conn.execute("PRAGMA foreign_keys=ON")
                self._estado = EstadoConexion.LIBRE
                return True
            except Exception:
                self._estado = EstadoConexion.ERROR
                return False
    
    @property
    def conn(self) -> Optional[sqlite3.Connection]:
        """Obtiene la conexión subyacente."""
        return self._conn
    
    @property
    def estado(self) -> EstadoConexion:
        return self._estado
    
    @property
    def esta_libre(self) -> bool:
        return self._estado == EstadoConexion.LIBRE
    
    def marcar_en_uso(self):
        self._estado = EstadoConexion.EN_USO
        self._ultimo_uso = time.time()
        self._contador_usos += 1
    
    def marcar_libre(self):
        self._estado = EstadoConexion.LIBRE
    
    def cerrar(self):
        """Cierra la conexión."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
            self._estado = EstadoConexion.CERRADA
    
    def __repr__(self) -> str:
        return f"ConexionBD(id={self._id}, estado={self._estado.value}, usos={self._contador_usos})"


# =====================================================================
# POOL DE CONEXIONES
# =====================================================================

class PoolConexiones:
    """Pool de conexiones thread-safe para SQLite."""
    
    def __init__(self, ruta_bd: Path, tamaño_pool: int = 5, timeout: float = 30.0):
        self.ruta_bd = ruta_bd
        self.tamaño_pool = tamaño_pool
        self.timeout = timeout
        self._conexiones: List[ConexionBD] = []
        self._lock = threading.RLock()
        self._inicializado = False
    
    def inicializar(self) -> bool:
        """Inicializa el pool de conexiones."""
        with self._lock:
            if self._inicializado:
                return True
            
            for i in range(self.tamaño_pool):
                conn = ConexionBD(self.ruta_bd, self.timeout)
                if conn.conectar():
                    self._conexiones.append(conn)
            
            self._inicializado = len(self._conexiones) > 0
            return self._inicializado
    
    def obtener(self) -> Optional[ConexionBD]:
        """Obtiene una conexión libre del pool."""
        with self._lock:
            for conn in self._conexiones:
                if conn.esta_libre:
                    conn.marcar_en_uso()
                    return conn
            
            # Si no hay libres, crear una nueva (si no excede límite)
            if len(self._conexiones) < self.tamaño_pool * 2:
                conn = ConexionBD(self.ruta_bd, self.timeout)
                if conn.conectar():
                    conn.marcar_en_uso()
                    self._conexiones.append(conn)
                    return conn
            
            # Esperar a que se libere una
            for _ in range(10):
                time.sleep(0.1)
                for conn in self._conexiones:
                    if conn.esta_libre:
                        conn.marcar_en_uso()
                        return conn
            
            return None
    
    def liberar(self, conexion: ConexionBD):
        """Marca una conexión como libre."""
        with self._lock:
            conexion.marcar_libre()
    
    def cerrar_todas(self):
        """Cierra todas las conexiones del pool."""
        with self._lock:
            for conn in self._conexiones:
                conn.cerrar()
            self._conexiones.clear()
            self._inicializado = False
    
    def estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del pool."""
        with self._lock:
            return {
                'tamaño_pool': self.tamaño_pool,
                'conexiones_activas': len(self._conexiones),
                'conexiones_libres': sum(1 for c in self._conexiones if c.esta_libre),
                'conexiones_en_uso': sum(1 for c in self._conexiones if c.estado == EstadoConexion.EN_USO),
            }


# =====================================================================
# CONSTRUCTOR DE CONSULTAS (QUERY BUILDER)
# =====================================================================

class QueryBuilder:
    """Constructor de consultas SQL fluido."""
    
    def __init__(self, tabla: str):
        self._tabla = tabla
        self._select: List[str] = ["*"]
        self._where: List[str] = []
        self._params: List[Any] = []
        self._order_by: List[Tuple[str, OrdenDireccion]] = []
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._joins: List[str] = []
    
    def select(self, *columnas: str) -> 'QueryBuilder':
        """Especifica las columnas a seleccionar."""
        self._select = list(columnas) if columnas else ["*"]
        return self
    
    def where(self, condicion: str, *params: Any) -> 'QueryBuilder':
        """Agrega una condición WHERE."""
        if self._where:
            self._where.append(f"AND {condicion}")
        else:
            self._where.append(condicion)
        self._params.extend(params)
        return self
    
    def or_where(self, condicion: str, *params: Any) -> 'QueryBuilder':
        """Agrega una condición OR WHERE."""
        if self._where:
            self._where.append(f"OR {condicion}")
        else:
            self._where.append(condicion)
        self._params.extend(params)
        return self
    
    def where_in(self, columna: str, valores: List[Any]) -> 'QueryBuilder':
        """Agrega una condición WHERE IN."""
        placeholders = ", ".join(["?"] * len(valores))
        condicion = f"{columna} IN ({placeholders})"
        self.where(condicion, *valores)
        return self
    
    def order_by(self, columna: str, direccion: OrdenDireccion = OrdenDireccion.ASC) -> 'QueryBuilder':
        """Agrega ordenamiento."""
        self._order_by.append((columna, direccion))
        return self
    
    def group_by(self, *columnas: str) -> 'QueryBuilder':
        """Agrega agrupamiento."""
        self._group_by.extend(columnas)
        return self
    
    def limit(self, limite: int) -> 'QueryBuilder':
        """Establece límite de resultados."""
        self._limit = limite
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """Establece offset para paginación."""
        self._offset = offset
        return self
    
    def join(self, tabla: str, condicion: str, tipo: str = "INNER") -> 'QueryBuilder':
        """Agrega un JOIN."""
        self._joins.append(f"{tipo} JOIN {tabla} ON {condicion}")
        return self
    
    def build_select(self) -> Tuple[str, List[Any]]:
        """Construye la consulta SELECT."""
        sql = f"SELECT {', '.join(self._select)} FROM {self._tabla}"
        
        if self._joins:
            sql += " " + " ".join(self._joins)
        
        if self._where:
            sql += " WHERE " + " ".join(self._where)
        
        if self._group_by:
            sql += " GROUP BY " + ", ".join(self._group_by)
        
        if self._order_by:
            order_parts = [f"{col} {dir.value}" for col, dir in self._order_by]
            sql += " ORDER BY " + ", ".join(order_parts)
        
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        
        return sql, self._params

# =====================================================================
# BASE DE DATOS PRINCIPAL (SINGLETON)
# =====================================================================

class BaseDatos:
    """
    Servicio central de base de datos de ANP.
    Implementa patrón Singleton thread-safe con pool de conexiones.
    """
    
    _instancia: Optional['BaseDatos'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self, ruta_bd: Optional[Path] = None, tamaño_pool: int = 5):
        if self._inicializado:
            return
        
        with self._lock_instancia:
            if self._inicializado:
                return
            
            if ruta_bd is None:
                ruta_bd = Path("almacenamiento/anp.db")
            
            self.ruta_bd = ruta_bd
            self.ruta_bd.parent.mkdir(parents=True, exist_ok=True)
            
            self.pool = PoolConexiones(self.ruta_bd, tamaño_pool)
            self.pool.inicializar()
            
            self.estadisticas = EstadisticasBD()
            self._lock = threading.RLock()
            
            # Métricas
            try:
                self._metrica_consultas = contador("bd.consultas")
                self._metrica_errores = contador("bd.errores")
                self._metrica_tiempo = histograma("bd.tiempo_consulta")
            except Exception:
                self._metrica_consultas = None
                self._metrica_errores = None
                self._metrica_tiempo = None
            
            # Inicializar tablas del sistema
            self._inicializar_tablas_sistema()
            
            self._inicializado = True
    
    def _inicializar_tablas_sistema(self):
        """Crea las tablas del sistema si no existen."""
        
        # Tabla de configuración
        self.crear_tabla("configuracion", [
            Columna("clave", TipoDato.TEXTO, primaria=True),
            Columna("valor", TipoDato.TEXTO, no_nula=True),
            Columna("tipo", TipoDato.TEXTO, valor_default="string"),
            Columna("descripcion", TipoDato.TEXTO),
            Columna("modificado", TipoDato.REAL),
            Columna("categoria", TipoDato.TEXTO),
        ], if_not_exists=True)
        
        # Tabla de fallos
        self.crear_tabla("fallos", [
            Columna("id", TipoDato.TEXTO, primaria=True),
            Columna("tipo", TipoDato.TEXTO, no_nula=True),
            Columna("severidad", TipoDato.ENTERO, valor_default=3),
            Columna("mensaje", TipoDato.TEXTO),
            Columna("origen", TipoDato.TEXTO),
            Columna("nucleo_afectado", TipoDato.TEXTO),
            Columna("timestamp", TipoDato.REAL, no_nula=True),
            Columna("estado", TipoDato.TEXTO, valor_default="activo"),
            Columna("stacktrace", TipoDato.TEXTO),
            Columna("contexto", TipoDato.TEXTO),
            Columna("intentos_recuperacion", TipoDato.ENTERO, valor_default=0),
            Columna("tiempo_resolucion", TipoDato.REAL),
            Columna("metadatos", TipoDato.TEXTO),
        ], if_not_exists=True)
        
        # Índices para fallos
        self.crear_indice("idx_fallos_timestamp", "fallos", ["timestamp"])
        self.crear_indice("idx_fallos_tipo", "fallos", ["tipo"])
        self.crear_indice("idx_fallos_nucleo", "fallos", ["nucleo_afectado"])
        
        # Tabla de signos vitales
        self.crear_tabla("signos_vitales", [
            Columna("id", TipoDato.ENTERO, primaria=True, autoincrement=True),
            Columna("nombre", TipoDato.TEXTO, no_nula=True),
            Columna("valor", TipoDato.REAL, no_nula=True),
            Columna("unidad", TipoDato.TEXTO),
            Columna("timestamp", TipoDato.REAL, no_nula=True),
            Columna("tendencia", TipoDato.REAL),
            Columna("prediccion_5s", TipoDato.REAL),
            Columna("prediccion_30s", TipoDato.REAL),
        ], if_not_exists=True)
        
        self.crear_indice("idx_signos_timestamp", "signos_vitales", ["timestamp"])
        self.crear_indice("idx_signos_nombre", "signos_vitales", ["nombre"])
        
        # Tabla de eventos del bus
        self.crear_tabla("eventos_bus", [
            Columna("id", TipoDato.TEXTO, primaria=True),
            Columna("tipo", TipoDato.TEXTO, no_nula=True),
            Columna("datos", TipoDato.TEXTO),
            Columna("origen", TipoDato.TEXTO),
            Columna("prioridad", TipoDato.ENTERO),
            Columna("timestamp", TipoDato.REAL, no_nula=True),
            Columna("estado", TipoDato.TEXTO),
            Columna("error", TipoDato.TEXTO),
            Columna("metadatos", TipoDato.TEXTO),
        ], if_not_exists=True)
        
        # Tabla de métricas
        self.crear_tabla("metricas", [
            Columna("id", TipoDato.ENTERO, primaria=True, autoincrement=True),
            Columna("nombre", TipoDato.TEXTO, no_nula=True),
            Columna("valor", TipoDato.REAL, no_nula=True),
            Columna("unidad", TipoDato.TEXTO),
            Columna("timestamp", TipoDato.REAL, no_nula=True),
            Columna("tags", TipoDato.TEXTO),
        ], if_not_exists=True)
        
        self.crear_indice("idx_metricas_timestamp", "metricas", ["timestamp"])
        self.crear_indice("idx_metricas_nombre", "metricas", ["nombre"])
        
        # Tabla de contexto
        self.crear_tabla("contexto_sesiones", [
            Columna("id", TipoDato.TEXTO, primaria=True),
            Columna("usuario_id", TipoDato.TEXTO),
            Columna("inicio", TipoDato.REAL, no_nula=True),
            Columna("fin", TipoDato.REAL),
            Columna("estado", TipoDato.TEXTO),
            Columna("modo", TipoDato.TEXTO),
            Columna("metadatos", TipoDato.TEXTO),
        ], if_not_exists=True)
        
        self.crear_tabla("contexto_elementos", [
            Columna("sesion_id", TipoDato.TEXTO, no_nula=True),
            Columna("clave", TipoDato.TEXTO, no_nula=True),
            Columna("valor", TipoDato.TEXTO),
            Columna("tipo", TipoDato.TEXTO),
            Columna("importancia", TipoDato.ENTERO),
            Columna("timestamp_creacion", TipoDato.REAL),
            Columna("timestamp_modificacion", TipoDato.REAL),
            Columna("contador_accesos", TipoDato.ENTERO),
            Columna("version", TipoDato.ENTERO),
            Columna("metadatos", TipoDato.TEXTO),
            Columna("tags", TipoDato.TEXTO),
        ], if_not_exists=True)
    
    # ===== MÉTODOS DDL (Data Definition Language) =====
    
    def crear_tabla(self, nombre: str, columnas: List[Columna], 
                    if_not_exists: bool = True) -> bool:
        """Crea una tabla en la base de datos."""
        with self.transaccion() as conn:
            try:
                columnas_sql = [c.a_sql() for c in columnas]
                sql = f"CREATE TABLE "
                if if_not_exists:
                    sql += "IF NOT EXISTS "
                sql += f"{nombre} ({', '.join(columnas_sql)})"
                
                conn.execute(sql)
                self.estadisticas.tablas += 1
                return True
            except Exception:
                return False
    
    def crear_indice(self, nombre: str, tabla: str, columnas: List[str], 
                     unico: bool = False) -> bool:
        """Crea un índice en una tabla."""
        with self.transaccion() as conn:
            try:
                indice = Indice(nombre, columnas, unico)
                sql = indice.a_sql(tabla)
                conn.execute(sql)
                self.estadisticas.indices += 1
                return True
            except Exception:
                return False
    
    def eliminar_tabla(self, nombre: str, if_exists: bool = True) -> bool:
        """Elimina una tabla."""
        with self.transaccion() as conn:
            try:
                sql = "DROP TABLE "
                if if_exists:
                    sql += "IF EXISTS "
                sql += nombre
                conn.execute(sql)
                return True
            except Exception:
                return False
    
    def tabla_existe(self, nombre: str) -> bool:
        """Verifica si una tabla existe."""
        resultado = self.consultar_uno(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,)
        )
        return resultado is not None
    
    # ===== MÉTODOS DML (Data Manipulation Language) =====
    
    @contextmanager
    def transaccion(self):
        """Context manager para transacciones."""
        conexion = self.pool.obtener()
        if not conexion:
            raise RuntimeError("No hay conexiones disponibles en el pool")
        
        try:
            conn = conexion.conn
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
            self.estadisticas.transacciones += 1
        except Exception as e:
            conn.execute("ROLLBACK")
            raise e
        finally:
            self.pool.liberar(conexion)
    
    def _ejecutar(self, sql: str, params: Tuple = ()) -> int:
        """Ejecuta una consulta que modifica datos."""
        inicio = time.time()
        exito = False
        
        conexion = self.pool.obtener()
        if not conexion:
            raise RuntimeError("No hay conexiones disponibles")
        
        try:
            cursor = conexion.conn.cursor()
            cursor.execute(sql, params)
            filas_afectadas = cursor.rowcount
            exito = True
            return filas_afectadas
        except Exception as e:
            self.estadisticas.registrar_consulta(False, 0)
            if self._metrica_errores:
                self._metrica_errores.inc()
            raise e
        finally:
            self.pool.liberar(conexion)
            tiempo_ms = (time.time() - inicio) * 1000
            if exito:
                self.estadisticas.registrar_consulta(True, tiempo_ms)
                if self._metrica_consultas:
                    self._metrica_consultas.inc()
                if self._metrica_tiempo:
                    self._metrica_tiempo.observar(tiempo_ms)
    
    def ejecutar(self, sql: str, params: Union[Tuple, Dict] = ()) -> int:
        """
        Ejecuta una consulta SQL que modifica datos.
        
        Args:
            sql: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Número de filas afectadas
        """
        if isinstance(params, dict):
            sql, params = self._convertir_params_nombrados(sql, params)
        
        return self._ejecutar(sql, params)
    
    def _convertir_params_nombrados(self, sql: str, params: Dict) -> Tuple[str, Tuple]:
        """Convierte parámetros nombrados (:nombre) a posicionales (?)."""
        import re
        nombres = re.findall(r':(\w+)', sql)
        valores = tuple(params.get(nombre) for nombre in nombres)
        sql_posicional = re.sub(r':\w+', '?', sql)
        return sql_posicional, valores
    
    def consultar_uno(self, sql: str, params: Union[Tuple, Dict] = ()) -> Optional[Dict[str, Any]]:
        """
        Consulta un solo registro.
        
        Returns:
            Diccionario con el registro o None
        """
        if isinstance(params, dict):
            sql, params = self._convertir_params_nombrados(sql, params)
        
        inicio = time.time()
        exito = False
        
        conexion = self.pool.obtener()
        if not conexion:
            raise RuntimeError("No hay conexiones disponibles")
        
        try:
            cursor = conexion.conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            exito = True
            return dict(row) if row else None
        finally:
            self.pool.liberar(conexion)
            tiempo_ms = (time.time() - inicio) * 1000
            if exito:
                self.estadisticas.registrar_consulta(True, tiempo_ms)
                if self._metrica_consultas:
                    self._metrica_consultas.inc()
                if self._metrica_tiempo:
                    self._metrica_tiempo.observar(tiempo_ms)
    
    def consultar_todos(self, sql: str, params: Union[Tuple, Dict] = ()) -> List[Dict[str, Any]]:
        """
        Consulta múltiples registros.
        
        Returns:
            Lista de diccionarios con los registros
        """
        if isinstance(params, dict):
            sql, params = self._convertir_params_nombrados(sql, params)
        
        inicio = time.time()
        exito = False
        
        conexion = self.pool.obtener()
        if not conexion:
            raise RuntimeError("No hay conexiones disponibles")
        
        try:
            cursor = conexion.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            exito = True
            return [dict(row) for row in rows]
        finally:
            self.pool.liberar(conexion)
            tiempo_ms = (time.time() - inicio) * 1000
            if exito:
                self.estadisticas.registrar_consulta(True, tiempo_ms)
                if self._metrica_consultas:
                    self._metrica_consultas.inc()
                if self._metrica_tiempo:
                    self._metrica_tiempo.observar(tiempo_ms)
    
    def consultar_valor(self, sql: str, params: Union[Tuple, Dict] = (), 
                        default: Any = None) -> Any:
        """
        Consulta un valor escalar.
        
        Returns:
            El valor consultado o default
        """
        resultado = self.consultar_uno(sql, params)
        if resultado:
            return list(resultado.values())[0]
        return default
    
    # ===== MÉTODOS CRUD =====
    
    def insertar(self, tabla: str, datos: Dict[str, Any], 
                 conflicto: Optional[str] = None) -> Optional[int]:
        """
        Inserta un registro en una tabla.
        
        Args:
            tabla: Nombre de la tabla
            datos: Diccionario con los datos a insertar
            conflicto: Estrategia de conflicto (REPLACE, IGNORE, etc.)
            
        Returns:
            ID del registro insertado o None
        """
        columnas = list(datos.keys())
        placeholders = ", ".join(["?"] * len(columnas))
        valores = tuple(datos.values())
        
        sql = f"INSERT "
        if conflicto:
            sql += f"OR {conflicto} "
        sql += f"INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        
        self.ejecutar(sql, valores)
        return self.consultar_valor("SELECT last_insert_rowid()")
    
    def insertar_batch(self, tabla: str, datos: List[Dict[str, Any]]) -> int:
        """
        Inserta múltiples registros en una transacción.
        
        Returns:
            Número de registros insertados
        """
        if not datos:
            return 0
        
        columnas = list(datos[0].keys())
        placeholders = ", ".join(["?"] * len(columnas))
        sql = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        
        with self.transaccion() as conn:
            cursor = conn.cursor()
            for registro in datos:
                valores = tuple(registro[col] for col in columnas)
                cursor.execute(sql, valores)
            return cursor.rowcount
    
    def actualizar(self, tabla: str, datos: Dict[str, Any], 
                   where: str, params: Union[Tuple, List] = ()) -> int:
        """
        Actualiza registros en una tabla.
        
        Returns:
            Número de filas afectadas
        """
        set_parts = [f"{col} = ?" for col in datos.keys()]
        sql = f"UPDATE {tabla} SET {', '.join(set_parts)} WHERE {where}"
        valores = tuple(datos.values()) + tuple(params)
        
        return self.ejecutar(sql, valores)
    
    def eliminar(self, tabla: str, where: str, params: Union[Tuple, List] = ()) -> int:
        """
        Elimina registros de una tabla.
        
        Returns:
            Número de filas afectadas
        """
        sql = f"DELETE FROM {tabla} WHERE {where}"
        return self.ejecutar(sql, params)
    
    def upsert(self, tabla: str, datos: Dict[str, Any], 
               conflicto_columnas: List[str]) -> int:
        """
        Inserta o actualiza un registro (UPSERT).
        """
        columnas = list(datos.keys())
        placeholders = ", ".join(["?"] * len(columnas))
        valores = tuple(datos.values())
        
        update_parts = [f"{col} = excluded.{col}" for col in columnas 
                       if col not in conflicto_columnas]
        
        sql = f"""
            INSERT INTO {tabla} ({', '.join(columnas)}) 
            VALUES ({placeholders})
            ON CONFLICT({', '.join(conflicto_columnas)}) 
            DO UPDATE SET {', '.join(update_parts)}
        """
        
        return self.ejecutar(sql, valores)
    
    # ===== QUERY BUILDER =====
    
    def tabla(self, nombre: str) -> QueryBuilder:
        """Crea un constructor de consultas para una tabla."""
        return QueryBuilder(nombre)
    
    # ===== CONFIGURACIÓN =====
    
    def guardar_configuracion(self, clave: str, valor: Any, tipo: str = "string",
                              descripcion: str = "", categoria: str = ""):
        """Guarda un valor de configuración."""
        valor_str = json.dumps(valor) if not isinstance(valor, str) else valor
        
        self.upsert("configuracion", {
            "clave": clave,
            "valor": valor_str,
            "tipo": tipo,
            "descripcion": descripcion,
            "modificado": time.time(),
            "categoria": categoria,
        }, ["clave"])
    
    def obtener_configuracion(self, clave: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración."""
        row = self.consultar_uno(
            "SELECT valor, tipo FROM configuracion WHERE clave = ?",
            (clave,)
        )
        if row:
            if row['tipo'] == 'json':
                return json.loads(row['valor'])
            elif row['tipo'] == 'int':
                return int(row['valor'])
            elif row['tipo'] == 'float':
                return float(row['valor'])
            elif row['tipo'] == 'bool':
                return row['valor'].lower() in ('true', '1', 'yes')
            return row['valor']
        return default
    
    # ===== FALLOS =====
    
    def guardar_fallo(self, fallo_id: str, tipo: str, mensaje: str, origen: str = "",
                      severidad: int = 3, nucleo_afectado: str = None,
                      stacktrace: str = None, contexto: Dict = None) -> bool:
        """Guarda un fallo en la base de datos."""
        try:
            self.insertar("fallos", {
                "id": fallo_id,
                "tipo": tipo,
                "severidad": severidad,
                "mensaje": mensaje,
                "origen": origen,
                "nucleo_afectado": nucleo_afectado,
                "timestamp": time.time(),
                "stacktrace": stacktrace,
                "contexto": json.dumps(contexto) if contexto else None,
            })
            return True
        except Exception:
            return False
    
    # ===== MÉTRICAS =====
    
    def guardar_metrica(self, nombre: str, valor: float, unidad: str = "",
                        tags: Dict = None):
        """Guarda una métrica en la base de datos."""
        try:
            self.insertar("metricas", {
                "nombre": nombre,
                "valor": valor,
                "unidad": unidad,
                "timestamp": time.time(),
                "tags": json.dumps(tags) if tags else None,
            })
            return True
        except Exception:
            return False
    
    # ===== MANTENIMIENTO =====
    
    def vacuum(self):
        """Optimiza la base de datos."""
        self.ejecutar("VACUUM")
    
    def analizar(self):
        """Analiza la base de datos para optimizar consultas."""
        self.ejecutar("ANALYZE")
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas de la base de datos."""
        with self._lock:
            return {
                'ruta': str(self.ruta_bd),
                'tamaño': self.ruta_bd.stat().st_size if self.ruta_bd.exists() else 0,
                'pool': self.pool.estadisticas(),
                'estadisticas': asdict(self.estadisticas),
                'tablas': self.consultar_valor(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ),
                'indices': self.consultar_valor(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
                ),
            }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo de la base de datos."""
        stats = self.obtener_estadisticas()
        return {
            'conexiones': f"{stats['pool']['conexiones_en_uso']}/{stats['pool']['conexiones_activas']}",
            'consultas': stats['estadisticas']['consultas_ejecutadas'],
            'tamaño': f"{stats['tamaño'] / 1024 / 1024:.2f} MB",
            'tablas': stats['tablas'],
        }
    
    def cerrar(self):
        """Cierra todas las conexiones."""
        self.pool.cerrar_todas()
        self._inicializado = False
    
    def __repr__(self) -> str:
        return f"BaseDatos(ruta={self.ruta_bd}, conexiones={self.pool.estadisticas()['conexiones_activas']})"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar()
        
# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_bd_global: Optional[BaseDatos] = None

def obtener_bd() -> BaseDatos:
    """Obtiene la instancia global de la base de datos."""
    global _bd_global
    if _bd_global is None:
        _bd_global = BaseDatos()
    return _bd_global

def inicializar_bd(ruta: Optional[Path] = None) -> BaseDatos:
    """Inicializa la base de datos global."""
    global _bd_global
    _bd_global = BaseDatos(ruta)
    return _bd_global

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SERVICIO DE BASE DE DATOS")
    print("=" * 70)
    
    bd = None
    
    try:
        print("\n[1/7] Inicializando base de datos...")
        bd = BaseDatos(Path("almacenamiento/test_anp.db"))
        print(f"  ✅ Base de datos inicializada: {bd}")
        
        print("\n[2/7] Verificando tablas del sistema...")
        tablas = ["configuracion", "fallos", "signos_vitales", "eventos_bus", "metricas", "contexto_sesiones"]
        for tabla in tablas:
            existe = bd.tabla_existe(tabla)
            icono = "✅" if existe else "❌"
            print(f"  {icono} {tabla}")
        
        print("\n[3/7] Probando CRUD...")
        bd.insertar("configuracion", {
            "clave": "test.clave",
            "valor": "valor_prueba",
            "tipo": "string",
            "modificado": time.time()
        })
        valor = bd.obtener_configuracion("test.clave")
        print(f"  ✅ Insertado: test.clave = {valor}")
        
        bd.actualizar("configuracion", {"valor": "nuevo_valor"}, "clave = ?", ("test.clave",))
        nuevo_valor = bd.obtener_configuracion("test.clave")
        print(f"  ✅ Actualizado: test.clave = {nuevo_valor}")
        
        print("\n[4/7] Probando QueryBuilder...")
        resultados = bd.tabla("configuracion").where("clave = ?", "test.clave").select("clave", "valor")
        sql, params = resultados.build_select()
        print(f"  📍 SQL: {sql}")
        print(f"  📍 Params: {params}")
        
        print("\n[5/7] Probando guardado de fallos...")
        bd.guardar_fallo("test_fallo_001", "test", "Fallo de prueba", "diagnostico", severidad=2)
        fallos = bd.consultar_todos("SELECT * FROM fallos WHERE id = ?", ("test_fallo_001",))
        print(f"  ✅ Fallo guardado: {len(fallos)} registros")
        
        print("\n[6/7] Probando métricas...")
        bd.guardar_metrica("test.metrica", 42.5, "unidades", {"test": True})
        metricas = bd.consultar_todos("SELECT * FROM metricas WHERE nombre = ?", ("test.metrica",))
        print(f"  ✅ Métrica guardada: {len(metricas)} registros")
        
        print("\n[7/7] Estadísticas de la base de datos...")
        stats = bd.obtener_estadisticas()
        print(f"  📊 Tamaño: {stats['tamaño']} bytes")
        print(f"  📊 Pool: {stats['pool']['conexiones_en_uso']}/{stats['pool']['conexiones_activas']} conexiones")
        print(f"  📊 Consultas ejecutadas: {stats['estadisticas']['consultas_ejecutadas']}")
        print(f"  📊 Tablas: {stats['tablas']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Servicio de Base de Datos está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if bd:
            print("\n🛑 Cerrando base de datos...")
            bd.cerrar()
            print("   ✓ Base de datos cerrada")
            
            # Limpiar archivo de prueba
            try:
                Path("almacenamiento/test_anp.db").unlink()
            except Exception:
                pass
    
    print("\n" + "=" * 70 + "\n")              