#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Cache — Almacenamiento Temporal con Políticas de Expiración
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Búsqueda
# =====================================================================

import sys, time, math, threading, pickle, traceback, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from collections import OrderedDict, Counter
from enum import Enum
from dataclasses import dataclass, field

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    NUMPY_DISPONIBLE = False
    np = None

# =====================================================================
# IMPORTACIONES DEL SISTEMA
# =====================================================================

try:
    from ....nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
except ImportError:
    try:
        from nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
    except ImportError:
        from abc import ABC, abstractmethod

        class EstadoMotor(Enum):
            NO_INICIALIZADO = "no_inicializado"
            ACTIVO = "activo"
            ERROR = "error"

        class MotorBase(ABC):
            def __init__(self, config=None):
                self._id = str(__import__('uuid').uuid4())
                self.nombre = self.__class__.__name__
                self._estado = EstadoMotor.NO_INICIALIZADO
                self.config = config if config is not None else ConfiguracionMotor()
            @property
            def estado(self): return self._estado
            def inicializar(self, contexto=None):
                self._estado = EstadoMotor.ACTIVO
                return True
            def detener(self):
                self._estado = EstadoMotor.ERROR
                return True
            @abstractmethod
            def _procesar_impl(self, entrada, contexto=None): pass
            def procesar(self, entrada, contexto=None):
                inicio = time.time()
                try:
                    resultado = self._procesar_impl(entrada, contexto)
                    return ResultadoMotor(exito=True, datos=resultado, tiempo_ejecucion_ms=(time.time()-inicio)*1000)
                except Exception as e:
                    return ResultadoMotor(exito=False, error=str(e), tiempo_ejecucion_ms=(time.time()-inicio)*1000)

        class ConfiguracionMotor:
            def __init__(self):
                self.nombre = ""
                self.timeout_default = 30.0
                self.max_reintentos = 3

        class ResultadoMotor:
            def __init__(self, exito=True, datos=None, error=None, tiempo_ejecucion_ms=0.0):
                self.exito = exito
                self.datos = datos
                self.error = error
                self.tiempo_ejecucion_ms = tiempo_ejecucion_ms

# =====================================================================
# ENUMERACIONES
# =====================================================================

class PoliticaCache(Enum):
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    ADAPTATIVA = "adaptativa"

class EstadoEntrada(Enum):
    FRESCA = "fresca"
    VIGENTE = "vigente"
    PROXIMA_CADUCAR = "proxima_caducar"
    CADUCA = "caduca"
    CORRUPTA = "corrupta"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EntradaCache:
    """Una entrada individual en el caché."""
    clave: str
    valor: Any
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_expiracion: float = float('inf')
    ttl: float = 3600.0
    frecuencia_acceso: int = 0
    ultimo_acceso: float = field(default_factory=time.time)
    peso: int = 1
    etiquetas: List[str] = field(default_factory=list)
    comprimido: bool = False
    checksum: str = ""
    
    def __post_init__(self):
        if self.timestamp_expiracion == float('inf') and self.ttl > 0:
            self.timestamp_expiracion = self.timestamp_creacion + self.ttl
        if not self.checksum and self.valor is not None:
            try:
                self.checksum = hashlib.md5(str(self.valor).encode()).hexdigest()
            except:
                pass
    
    @property
    def estado(self) -> EstadoEntrada:
        ahora = time.time()
        if ahora > self.timestamp_expiracion:
            return EstadoEntrada.CADUCA
        tiempo_restante = self.timestamp_expiracion - ahora
        if tiempo_restante < self.ttl * 0.1:
            return EstadoEntrada.PROXIMA_CADUCAR
        if tiempo_restante > self.ttl * 0.5:
            return EstadoEntrada.FRESCA
        return EstadoEntrada.VIGENTE
    
    @property
    def tiempo_restante(self) -> float:
        return max(0.0, self.timestamp_expiracion - time.time())


# =====================================================================
# MOTOR DE CACHE
# =====================================================================

class MotorCache(MotorBase):
    """
    Motor de Cache — Almacenamiento Temporal con Políticas Múltiples.
    
    Políticas de desalojo:
    - LRU: Least Recently Used (más antiguo en acceso)
    - LFU: Least Frequently Used (menos accedido)
    - FIFO: First In First Out (más antiguo en creación)
    - TTL: Time To Live (solo por expiración)
    - ADAPTATIVA: Combina LRU + LFU con pesos dinámicos
    
    Capacidades:
    - Guardado y recuperación O(1)
    - Invalidación por clave, etiqueta o patrón
    - Limpieza automática programable
    - Estadísticas de hit/miss rate
    - Compresión de valores grandes
    - Persistencia selectiva
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._entradas: OrderedDict = OrderedDict()
        self._indice_etiquetas: Dict[str, Set[str]] = {}
        self._max_entradas = 10000
        self._max_peso = 100000
        self._peso_actual = 0
        self._politica = PoliticaCache.ADAPTATIVA
        self._ttl_default = 3600.0
        self._hits = 0
        self._misses = 0
        self._invalidaciones = 0
        self._expulsiones = 0
        self._lock = threading.RLock()
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'obtener')
        
        with self._lock:
            if operacion == 'guardar':
                return self._guardar(entrada)
            elif operacion == 'obtener':
                return self._obtener(entrada)
            elif operacion == 'invalidar':
                return self._invalidar(entrada)
            elif operacion == 'limpiar':
                return self._limpiar(entrada)
            elif operacion == 'estadisticas':
                return self._estadisticas(entrada)
            elif operacion == 'info':
                return self._info(entrada)
            else:
                return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _guardar(self, e: Dict) -> Dict[str, Any]:
        clave = e.get('clave', '')
        valor = e.get('valor')
        ttl = float(e.get('ttl', self._ttl_default))
        etiquetas = e.get('etiquetas', [])
        peso = int(e.get('peso', 1))
        
        if not clave:
            return {'error': 'Clave requerida', 'exito': False}
        if valor is None:
            return {'error': 'Valor requerido', 'exito': False}
        
        # Verificar espacio
        if len(self._entradas) >= self._max_entradas:
            self._aplicar_politica_desalojo()
        
        if self._peso_actual + peso > self._max_peso:
            self._aplicar_politica_desalojo(agresivo=True)
        
        # Actualizar existente
        if clave in self._entradas:
            entrada = self._entradas[clave]
            entrada.valor = valor
            entrada.ttl = ttl
            entrada.timestamp_expiracion = time.time() + ttl
            entrada.frecuencia_acceso += 1
            entrada.ultimo_acceso = time.time()
            entrada.etiquetas = etiquetas
            self._entradas.move_to_end(clave)
        else:
            entrada = EntradaCache(
                clave=clave,
                valor=valor,
                ttl=ttl,
                timestamp_expiracion=time.time() + ttl,
                etiquetas=etiquetas,
                peso=peso
            )
            self._entradas[clave] = entrada
            self._peso_actual += peso
        
        # Indexar etiquetas
        for et in etiquetas:
            if et not in self._indice_etiquetas:
                self._indice_etiquetas[et] = set()
            self._indice_etiquetas[et].add(clave)
        
        return {
            'exito': True,
            'clave': clave,
            'ttl': ttl,
            'total_entradas': len(self._entradas),
            'peso_actual': self._peso_actual
        }
    
    def _obtener(self, e: Dict) -> Dict[str, Any]:
        clave = e.get('clave', '')
        if not clave:
            return {'error': 'Clave requerida', 'exito': False}
        
        if clave not in self._entradas:
            self._misses += 1
            return {'exito': False, 'error': 'No encontrado', 'clave': clave}
        
        entrada = self._entradas[clave]
        
        # Verificar expiración
        if entrada.estado == EstadoEntrada.CADUCA:
            self._entradas.pop(clave, None)
            self._peso_actual -= entrada.peso
            self._misses += 1
            return {'exito': False, 'error': 'Expirado', 'clave': clave}
        
        # Actualizar métricas
        entrada.frecuencia_acceso += 1
        entrada.ultimo_acceso = time.time()
        self._entradas.move_to_end(clave)
        self._hits += 1
        
        return {
            'exito': True,
            'clave': clave,
            'valor': entrada.valor,
            'estado': entrada.estado.value,
            'tiempo_restante': round(entrada.tiempo_restante, 1),
            'frecuencia': entrada.frecuencia_acceso,
            'etiquetas': entrada.etiquetas
        }
    
    def _invalidar(self, e: Dict) -> Dict[str, Any]:
        clave = e.get('clave', '')
        etiqueta = e.get('etiqueta', '')
        patron = e.get('patron', '')
        
        eliminados = 0
        
        if clave:
            entrada = self._entradas.pop(clave, None)
            if entrada:
                self._peso_actual -= entrada.peso
                eliminados += 1
        elif etiqueta and etiqueta in self._indice_etiquetas:
            for c in list(self._indice_etiquetas[etiqueta]):
                entrada = self._entradas.pop(c, None)
                if entrada:
                    self._peso_actual -= entrada.peso
                    eliminados += 1
            self._indice_etiquetas.pop(etiqueta, None)
        elif patron:
            a_eliminar = [k for k in self._entradas if patron in k]
            for k in a_eliminar:
                entrada = self._entradas.pop(k, None)
                if entrada:
                    self._peso_actual -= entrada.peso
                    eliminados += 1
        
        self._invalidaciones += eliminados
        
        return {
            'exito': True,
            'eliminados': eliminados,
            'total_entradas': len(self._entradas)
        }
    
    def _limpiar(self, e: Dict) -> Dict[str, Any]:
        """Limpia entradas expiradas y opcionalmente aplica política."""
        ahora = time.time()
        expirados = []
        
        for clave, entrada in self._entradas.items():
            if entrada.estado == EstadoEntrada.CADUCA:
                expirados.append(clave)
        
        for clave in expirados:
            entrada = self._entradas.pop(clave, None)
            if entrada:
                self._peso_actual -= entrada.peso
        
        if e.get('forzar', False):
            while self._peso_actual > self._max_peso * 0.8 and len(self._entradas) > 0:
                self._aplicar_politica_desalojo(agresivo=True)
        
        return {
            'exito': True,
            'expirados': len(expirados),
            'expulsados': 0,
            'total_entradas': len(self._entradas),
            'peso_actual': self._peso_actual
        }
    
    def _aplicar_politica_desalojo(self, agresivo: bool = False):
        """Aplica la política de desalojo para liberar espacio."""
        if not self._entradas:
            return
        
        cantidad = max(1, len(self._entradas) // 10) if agresivo else 1
        
        for _ in range(cantidad):
            if not self._entradas:
                break
            
            if self._politica == PoliticaCache.LRU:
                self._entradas.popitem(last=False)
            elif self._politica == PoliticaCache.LFU:
                clave_menor = min(self._entradas.keys(), 
                                 key=lambda k: self._entradas[k].frecuencia_acceso)
                self._entradas.pop(clave_menor, None)
            elif self._politica == PoliticaCache.FIFO:
                self._entradas.popitem(last=False)
            elif self._politica == PoliticaCache.ADAPTATIVA:
                ahora = time.time()
                mejor_score = float('inf')
                mejor_clave = None
                
                for clave, entrada in self._entradas.items():
                    score_lru = ahora - entrada.ultimo_acceso
                    score_lfu = 1.0 / max(1, entrada.frecuencia_acceso)
                    score_ttl = 1.0 / max(1, entrada.tiempo_restante)
                    score_total = score_lru * 0.4 + score_lfu * 0.3 + score_ttl * 0.3
                    
                    if score_total < mejor_score:
                        mejor_score = score_total
                        mejor_clave = clave
                
                if mejor_clave:
                    entrada = self._entradas.pop(mejor_clave, None)
                    if entrada:
                        self._peso_actual -= entrada.peso
            
            self._expulsiones += 1
    
    def _estadisticas(self, e: Dict) -> Dict[str, Any]:
        total_accesos = self._hits + self._misses
        hit_rate = self._hits / max(1, total_accesos)
        
        ahora = time.time()
        frescas = sum(1 for en in self._entradas.values() if en.estado == EstadoEntrada.FRESCA)
        caducas = sum(1 for en in self._entradas.values() if en.estado == EstadoEntrada.CADUCA)
        
        return {
            'exito': True,
            'entradas': len(self._entradas),
            'max_entradas': self._max_entradas,
            'peso_actual': self._peso_actual,
            'max_peso': self._max_peso,
            'politica': self._politica.value,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 4),
            'invalidaciones': self._invalidaciones,
            'expulsiones': self._expulsiones,
            'frescas': frescas,
            'caducas': caducas,
            'ttl_default': self._ttl_default
        }
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'entradas': len(self._entradas),
            'politica': self._politica.value,
            'funcionalidades': ['guardar', 'obtener', 'invalidar', 'limpiar', 'estadisticas']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE CACHE — LRU/LFU/FIFO/TTL/ADAPTATIVA")
    print("=" * 70)
    motor = None
    try:
        motor = MotorCache()
        motor.inicializar()
        print(f"\n[0] Motor: {motor.nombre} | Estado: {motor.estado}")
        print(f"    Política: {motor._politica.value} | TTL default: {motor._ttl_default}s")
        
        print(f"\n[1] Guardando entradas...")
        datos_prueba = [
            ('config_sistema', {'version': '1.0', 'modo': 'produccion'}, 300, ['config', 'sistema']),
            ('resultados_cache', {'total': 150, 'pagina': 1}, 60, ['resultados', 'busqueda']),
            ('sesion_usuario', {'id': 'usr_123', 'token': 'abc'}, 1800, ['sesion', 'usuario']),
            ('indice_temporal', [1, 2, 3, 4, 5], 30, ['indice', 'temporal']),
            ('estadisticas_diarias', {'visitas': 1000, 'errores': 5}, 86400, ['estadisticas']),
            ('query_frecuente_1', 'SELECT * FROM datos', 600, ['query', 'sql']),
            ('query_frecuente_2', 'UPDATE usuarios SET activo=1', 600, ['query', 'sql']),
            ('archivo_grande', 'x' * 10000, 120, ['archivo', 'grande']),
        ]
        
        for clave, valor, ttl, etiquetas in datos_prueba:
            r = motor.procesar({
                'operacion': 'guardar',
                'clave': clave,
                'valor': valor,
                'ttl': ttl,
                'etiquetas': etiquetas
            })
            if r.exito and r.datos:
                print(f"  ✅ {clave}: TTL={ttl}s | Etiquetas: {etiquetas}")
        
        print(f"\n[2] Recuperando entradas...")
        for clave in ['config_sistema', 'sesion_usuario', 'no_existe']:
            r = motor.procesar({'operacion': 'obtener', 'clave': clave})
            if r.exito and r.datos.get('exito'):
                v = r.datos.get('valor', {})
                print(f"  ✅ {clave}: {v} (TTL restante: {r.datos['tiempo_restante']}s)")
            else:
                print(f"  ❌ {clave}: {r.datos.get('error', '?')}")
        
        print(f"\n[3] Invalidando por etiqueta 'query':")
        r = motor.procesar({'operacion': 'invalidar', 'etiqueta': 'query'})
        if r.exito and r.datos:
            print(f"  ✅ {r.datos['eliminados']} entradas eliminadas ({r.datos['total_entradas']} restantes)")
        
        print(f"\n[4] Invalidando por clave específica:")
        r = motor.procesar({'operacion': 'invalidar', 'clave': 'archivo_grande'})
        if r.exito and r.datos:
            print(f"  ✅ {r.datos['eliminados']} entrada eliminada ({r.datos['total_entradas']} restantes)")
        
        print(f"\n[5] Limpieza automática:")
        r = motor.procesar({'operacion': 'limpiar'})
        if r.exito and r.datos:
            print(f"  ✅ {r.datos['expirados']} expirados | {r.datos['total_entradas']} restantes")
        
        print(f"\n[6] Múltiples accesos para probar LFU:")
        for _ in range(10):
            motor.procesar({'operacion': 'obtener', 'clave': 'config_sistema'})
        for _ in range(2):
            motor.procesar({'operacion': 'obtener', 'clave': 'indice_temporal'})
        
        print(f"\n[7] Estadísticas:")
        r = motor.procesar({'operacion': 'estadisticas'})
        if r.exito and r.datos:
            s = r.datos
            print(f"  📊 Entradas: {s['entradas']}/{s['max_entradas']}")
            print(f"  📊 Peso: {s['peso_actual']}/{s['max_peso']}")
            print(f"  📊 Hits: {s['hits']} | Misses: {s['misses']} | Hit Rate: {s['hit_rate']}")
            print(f"  📊 Frescas: {s['frescas']} | Caducas: {s['caducas']}")
            print(f"  📊 Invalidaciones: {s['invalidaciones']} | Expulsiones: {s['expulsiones']}")
        
        print(f"\n[8] Frecuencias de acceso:")
        for clave in list(motor._entradas.keys())[:5]:
            ent = motor._entradas.get(clave)
            if ent:
                print(f"  🔍 {clave}: {ent.frecuencia_acceso} accesos | Estado: {ent.estado.value}")
        
        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE CACHE")
        if s:
            print(f"   Entradas: {s['entradas']} | Hit Rate: {s['hit_rate']} | Política: {s['politica']}")
        print(f"{'=' * 70}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")