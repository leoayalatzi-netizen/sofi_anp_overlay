#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Contexto Cuántico (La Memoria de Trabajo del Ser)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
import time
import uuid
import json
import threading
import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple, Set, Iterator
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum
from collections import defaultdict, deque, OrderedDict, Counter
from datetime import datetime

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from ..bus_eventos import Evento, TipoEvento, PrioridadEvento, publicar, suscribir
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
    
    class TipoEvento:
        CONTEXTO_CREADO = "contexto.creado"
        CONTEXTO_ACTUALIZADO = "contexto.actualizado"
        CONTEXTO_DESTRUIDO = "contexto.destruido"
        CONTEXTO_CAMBIADO = "contexto.cambiado"
        MEMORIA_ACTUALIZADA = "memoria.actualizada"
        VENTANA_DESLIZADA = "ventana.deslizada"
    
    class PrioridadEvento:
        ALTA = 1
        MEDIA = 2
        BAJA = 3
    
    def publicar(tipo, datos=None, origen="", prioridad=2, **kwargs):
        pass
    
    def suscribir(patron, callback, prioridad=2):
        pass

try:
    from servicios.base_datos import obtener_bd
except ImportError:
    def obtener_bd():
        return None

# =====================================================================
# ENUMERACIONES AVANZADAS
# =====================================================================

class EstadoContexto(Enum):
    INACTIVO = "inactivo"
    ACTIVO = "activo"
    PAUSADO = "pausado"
    CONSOLIDANDO = "consolidando"
    ARCHIVADO = "archivado"
    CORRUPTO = "corrupto"

class ModoContexto(Enum):
    NORMAL = "normal"
    CONCISO = "conciso"
    EXPANDIDO = "expandido"
    TECNICO = "tecnico"
    CREATIVO = "creativo"
    ADAPTATIVO = "adaptativo"

class NivelImportancia(IntEnum):
    CRITICO = 0
    ALTO = 1
    MEDIO = 2
    BAJO = 3
    TRIVIAL = 4
    EFIMERO = 5

# =====================================================================
# ESTRUCTURAS DE DATOS FUNDAMENTALES
# =====================================================================

@dataclass
class ElementoContexto:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clave: str = ""
    valor: Any = None
    tipo: str = "any"
    importancia: NivelImportancia = NivelImportancia.MEDIO
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_acceso: float = field(default_factory=time.time)
    timestamp_modificacion: float = field(default_factory=time.time)
    contador_accesos: int = 0
    contador_modificaciones: int = 0
    ttl: Optional[float] = None
    metadatos: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    dependencias: List[str] = field(default_factory=list)
    version: int = 1
    
    def acceder(self) -> Any:
        self.timestamp_acceso = time.time()
        self.contador_accesos += 1
        return self.valor
    
    def modificar(self, nuevo_valor: Any) -> 'ElementoContexto':
        self.valor = nuevo_valor
        self.timestamp_modificacion = time.time()
        self.contador_modificaciones += 1
        self.version += 1
        return self
    
    def esta_expirado(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.timestamp_creacion > self.ttl
    
    def calcular_relevancia(self) -> float:
        ahora = time.time()
        edad = ahora - self.timestamp_creacion
        ultimo_acceso = ahora - self.timestamp_acceso
        
        factor_importancia = 1.0 - (self.importancia.value * 0.15)
        factor_accesos = min(1.0, self.contador_accesos / 50.0)
        factor_edad = math.exp(-edad / 3600.0)
        factor_ultimo_acceso = math.exp(-ultimo_acceso / 300.0)
        
        relevancia = (
            factor_importancia * 0.3 +
            factor_accesos * 0.3 +
            factor_edad * 0.2 +
            factor_ultimo_acceso * 0.2
        )
        return relevancia

@dataclass
class SesionContexto:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: Optional[str] = None
    conversacion_id: Optional[str] = None
    inicio: float = field(default_factory=time.time)
    fin: Optional[float] = None
    estado: EstadoContexto = EstadoContexto.ACTIVO
    modo: ModoContexto = ModoContexto.ADAPTATIVO
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    def finalizar(self):
        self.fin = time.time()
        self.estado = EstadoContexto.ARCHIVADO
    
    @property
    def duracion(self) -> Optional[float]:
        if self.fin:
            return self.fin - self.inicio
        return time.time() - self.inicio

@dataclass
class InstantaneaContexto:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sesion_id: str = ""
    timestamp: float = field(default_factory=time.time)
    elementos: Dict[str, Any] = field(default_factory=dict)
    metadatos: Dict[str, Any] = field(default_factory=dict)
    hash_estado: str = ""

# =====================================================================
# MEMORIA DE CORTO PLAZO (7±2)
# =====================================================================

class MemoriaCortoPlazo:
    def __init__(self, capacidad: int = 7, politica_olvido: str = "ebbinghaus"):
        self.capacidad = capacidad
        self.capacidad_min = 5
        self.capacidad_max = 9
        self.politica_olvido = politica_olvido
        self._elementos: OrderedDict[str, ElementoContexto] = OrderedDict()
        self._lock = threading.RLock()
        self._historial_olvidos: deque = deque(maxlen=100)
        
    def agregar(self, elemento: ElementoContexto) -> bool:
        with self._lock:
            if elemento.clave in self._elementos:
                self._elementos.move_to_end(elemento.clave)
                self._elementos[elemento.clave] = elemento
                return True
            
            if len(self._elementos) >= self.capacidad:
                self._olvidar_uno()
            
            self._elementos[elemento.clave] = elemento
            return True
    
    def obtener(self, clave: str) -> Optional[ElementoContexto]:
        with self._lock:
            if clave in self._elementos:
                self._elementos.move_to_end(clave)
                elemento = self._elementos[clave]
                elemento.acceder()
                return elemento
            return None
    
    def contiene(self, clave: str) -> bool:
        with self._lock:
            return clave in self._elementos
    
    def eliminar(self, clave: str) -> bool:
        with self._lock:
            if clave in self._elementos:
                del self._elementos[clave]
                return True
            return False
    
    def _olvidar_uno(self):
        if not self._elementos:
            return
        
        if self.politica_olvido == "ebbinghaus":
            elemento_a_olvidar = min(
                self._elementos.items(),
                key=lambda x: x[1].calcular_relevancia()
            )[0]
        elif self.politica_olvido == "fifo":
            elemento_a_olvidar = next(iter(self._elementos))
        elif self.politica_olvido == "lru":
            elemento_a_olvidar = next(iter(self._elementos))
        else:
            elemento_a_olvidar = next(iter(self._elementos))
        
        olvidado = self._elementos.pop(elemento_a_olvidar)
        self._historial_olvidos.append({
            'clave': elemento_a_olvidar,
            'timestamp': time.time(),
            'elemento': olvidado,
        })
    
    def ajustar_capacidad(self, nueva_capacidad: int):
        with self._lock:
            self.capacidad = max(self.capacidad_min, min(self.capacidad_max, nueva_capacidad))
            while len(self._elementos) > self.capacidad:
                self._olvidar_uno()
    
    def obtener_todos(self) -> List[ElementoContexto]:
        with self._lock:
            return list(self._elementos.values())
    
    def limpiar(self):
        with self._lock:
            self._elementos.clear()
    
    def __len__(self) -> int:
        return len(self._elementos)
    
    def __contains__(self, clave: str) -> bool:
        return self.contiene(clave)

# =====================================================================
# VENTANA DESLIZANTE DE CONTEXTO
# =====================================================================

class VentanaContexto:
    def __init__(self, tamaño_maximo: int = 4096, solapamiento: int = 512):
        self.tamaño_maximo = tamaño_maximo
        self.solapamiento = solapamiento
        self._ventanas: List[str] = []
        self._ventana_actual: int = 0
        self._contenido_total: str = ""
        self._resumenes: Dict[int, str] = {}
        self._lock = threading.RLock()
        
    def agregar(self, texto: str) -> bool:
        with self._lock:
            self._contenido_total += texto
            if len(self._contenido_total) > self.tamaño_maximo:
                self._deslizar()
            return True
    
    def _deslizar(self):
        if len(self._contenido_total) <= self.tamaño_maximo:
            return
        
        ventana_actual = self._contenido_total[:self.tamaño_maximo]
        self._ventanas.append(ventana_actual)
        self._ventana_actual = len(self._ventanas) - 1
        
        solapamiento_texto = ""
        if len(self._contenido_total) > self.tamaño_maximo - self.solapamiento:
            inicio_solape = max(0, self.tamaño_maximo - self.solapamiento)
            solapamiento_texto = self._contenido_total[inicio_solape:self.tamaño_maximo]
        
        self._contenido_total = solapamiento_texto + self._contenido_total[self.tamaño_maximo:]
        
        if len(self._ventanas) > 1:
            self._generar_resumen(len(self._ventanas) - 2)
    
    def _generar_resumen(self, indice_ventana: int):
        if indice_ventana >= len(self._ventanas):
            return
        
        texto = self._ventanas[indice_ventana]
        if len(texto) > 500:
            resumen = texto[:250] + " [...] " + texto[-250:]
        else:
            resumen = texto
        
        self._resumenes[indice_ventana] = resumen
    
    def obtener_contexto_completo(self, max_ventanas: int = 3) -> str:
        with self._lock:
            contexto = []
            inicio = max(0, len(self._ventanas) - max_ventanas + 1)
            for i in range(inicio, len(self._ventanas)):
                contexto.append(self._ventanas[i])
            contexto.append(self._contenido_total)
            return "\n".join(contexto)
    
    def obtener_contexto_resumido(self, max_ventanas: int = 5) -> str:
        with self._lock:
            partes = []
            for i in range(len(self._ventanas)):
                if i < len(self._ventanas) - max_ventanas:
                    if i in self._resumenes:
                        partes.append(f"[...{self._resumenes[i]}...]")
                else:
                    partes.append(self._ventanas[i])
            partes.append(self._contenido_total)
            return "\n".join(partes)
    
    def obtener_ventana_actual(self) -> str:
        with self._lock:
            return self._contenido_total
    
    def limpiar(self):
        with self._lock:
            self._ventanas.clear()
            self._resumenes.clear()
            self._contenido_total = ""
            self._ventana_actual = 0
    
    def estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_ventanas': len(self._ventanas),
                'ventana_actual': self._ventana_actual,
                'tamaño_actual': len(self._contenido_total),
                'tamaño_maximo': self.tamaño_maximo,
                'solapamiento': self.solapamiento,
                'resumenes_generados': len(self._resumenes),
            }

# =====================================================================
# CONTEXTO PRINCIPAL
# =====================================================================

class Contexto:
    _instancias: Dict[str, 'Contexto'] = {}
    _lock_instancias = threading.RLock()
    
    def __init__(self, 
                 sesion_id: Optional[str] = None,
                 usuario_id: Optional[str] = None,
                 modo: ModoContexto = ModoContexto.ADAPTATIVO,
                 capacidad_memoria: int = 7,
                 tamaño_ventana: int = 4096,
                 persistir: bool = True):
        
        self.sesion = SesionContexto(
            id=sesion_id or str(uuid.uuid4()),
            usuario_id=usuario_id,
            modo=modo
        )
        self.id = self.sesion.id
        
        self.memoria = MemoriaCortoPlazo(capacidad=capacidad_memoria)
        self.ventana = VentanaContexto(tamaño_maximo=tamaño_ventana)
        
        self._elementos: Dict[str, ElementoContexto] = {}
        self._historial_cambios: deque = deque(maxlen=1000)
        self._instantaneas: Dict[str, InstantaneaContexto] = {}
        
        self.persistir = persistir
        self.modo = modo
        self._lock = threading.RLock()
        
        self._estadisticas: Dict[str, int] = defaultdict(int)
        self._suscripciones: List[str] = []
        
        with self._lock_instancias:
            Contexto._instancias[self.id] = self
        
        if self.persistir:
            self._cargar_desde_bd()
        
        self._publicar_evento(TipoEvento.CONTEXTO_CREADO, {
            'sesion_id': self.id,
            'usuario_id': usuario_id,
            'modo': modo.value,
        })
    
    @property
    def estado(self) -> EstadoContexto:
        return self.sesion.estado
    
    @property
    def duracion(self) -> float:
        return self.sesion.duracion or 0.0
    
    def establecer(self, clave: str, valor: Any, 
                   importancia: NivelImportancia = NivelImportancia.MEDIO,
                   ttl: Optional[float] = None,
                   metadatos: Dict = None,
                   tags: Set[str] = None) -> ElementoContexto:
        with self._lock:
            if clave in self._elementos:
                elemento = self._elementos[clave].modificar(valor)
            else:
                elemento = ElementoContexto(
                    clave=clave,
                    valor=valor,
                    tipo=type(valor).__name__,
                    importancia=importancia,
                    ttl=ttl,
                    metadatos=metadatos or {},
                    tags=tags or set()
                )
                self._elementos[clave] = elemento
            
            self.memoria.agregar(elemento)
            self._historial_cambios.append(('establecer', clave, time.time()))
            self._estadisticas['total_establecimientos'] += 1
            
            if self.persistir:
                self._persistir_elemento(elemento)
            
            self._publicar_evento(TipoEvento.CONTEXTO_ACTUALIZADO, {
                'clave': clave,
                'operacion': 'establecer',
                'tipo': elemento.tipo,
            })
            
            return elemento
    
    def obtener(self, clave: str, default: Any = None) -> Any:
        with self._lock:
            if clave in self._elementos:
                elemento = self._elementos[clave]
                if elemento.esta_expirado():
                    self.eliminar(clave)
                    return default
                self.memoria.agregar(elemento)
                self._estadisticas['total_obtenciones'] += 1
                return elemento.acceder()
            return default
    
    def __getitem__(self, clave: str) -> Any:
        resultado = self.obtener(clave)
        if resultado is None:
            raise KeyError(f"Clave no encontrada: {clave}")
        return resultado
    
    def __setitem__(self, clave: str, valor: Any):
        self.establecer(clave, valor)
    
    def __contains__(self, clave: str) -> bool:
        return clave in self._elementos and not self._elementos[clave].esta_expirado()
    
    def __delitem__(self, clave: str):
        if not self.eliminar(clave):
            raise KeyError(f"Clave no encontrada: {clave}")
    
    def eliminar(self, clave: str) -> bool:
        with self._lock:
            if clave in self._elementos:
                del self._elementos[clave]
                self.memoria.eliminar(clave)
                self._historial_cambios.append(('eliminar', clave, time.time()))
                self._estadisticas['total_eliminaciones'] += 1
                if self.persistir:
                    self._eliminar_de_bd(clave)
                self._publicar_evento(TipoEvento.CONTEXTO_ACTUALIZADO, {
                    'clave': clave,
                    'operacion': 'eliminar',
                })
                return True
            return False
    
    def claves(self) -> List[str]:
        with self._lock:
            return [k for k, v in self._elementos.items() if not v.esta_expirado()]
    
    def valores(self) -> List[Any]:
        with self._lock:
            return [v.valor for k, v in self._elementos.items() if not v.esta_expirado()]
    
    def items(self) -> List[Tuple[str, Any]]:
        with self._lock:
            return [(k, v.valor) for k, v in self._elementos.items() if not v.esta_expirado()]
    
    def recordar(self, clave: str) -> Optional[Any]:
        elemento = self.memoria.obtener(clave)
        return elemento.valor if elemento else None
    
    def memorizar(self, clave: str, valor: Any, importancia: NivelImportancia = NivelImportancia.MEDIO):
        elemento = ElementoContexto(
            clave=clave,
            valor=valor,
            tipo=type(valor).__name__,
            importancia=importancia
        )
        self.memoria.agregar(elemento)
    
    def olvidar(self, clave: str) -> bool:
        return self.memoria.eliminar(clave)
    
    def recuerdos_recientes(self, n: int = None) -> List[Any]:
        elementos = self.memoria.obtener_todos()
        if n:
            elementos = elementos[-n:]
        return [e.valor for e in elementos]
    
    def agregar_texto(self, texto: str):
        self.ventana.agregar(texto)
        self._estadisticas['total_texto_agregado'] += len(texto)
        self._publicar_evento(TipoEvento.VENTANA_DESLIZADA, {'tamaño': len(texto)})
    
    def contexto_actual(self) -> str:
        return self.ventana.obtener_contexto_completo()
    
    def contexto_resumido(self) -> str:
        return self.ventana.obtener_contexto_resumido()
    
    def _persistir_elemento(self, elemento: ElementoContexto):
        try:
            bd = obtener_bd()
            if bd:
                bd.ejecutar("""
                    INSERT OR REPLACE INTO contexto_elementos 
                    (sesion_id, clave, valor, tipo, importancia, timestamp_creacion, 
                     timestamp_modificacion, contador_accesos, version, metadatos, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.id, elemento.clave,
                    json.dumps(elemento.valor) if not isinstance(elemento.valor, str) else elemento.valor,
                    elemento.tipo, elemento.importancia.value, elemento.timestamp_creacion,
                    elemento.timestamp_modificacion, elemento.contador_accesos,
                    elemento.version, json.dumps(elemento.metadatos), json.dumps(list(elemento.tags))
                ))
        except Exception:
            pass
    
    def _eliminar_de_bd(self, clave: str):
        try:
            bd = obtener_bd()
            if bd:
                bd.ejecutar("DELETE FROM contexto_elementos WHERE sesion_id = ? AND clave = ?", 
                           (self.id, clave))
        except Exception:
            pass
    
    def _cargar_desde_bd(self):
        try:
            bd = obtener_bd()
            if bd:
                rows = bd.consultar_todos(
                    "SELECT * FROM contexto_elementos WHERE sesion_id = ?",
                    (self.id,)
                )
                for row in rows:
                    try:
                        valor = row['valor']
                        if row['tipo'] in ('dict', 'list', 'int', 'float', 'bool'):
                            valor = json.loads(valor)
                        elemento = ElementoContexto(
                            clave=row['clave'], valor=valor, tipo=row['tipo'],
                            importancia=NivelImportancia(row['importancia']),
                            timestamp_creacion=row['timestamp_creacion'],
                            timestamp_modificacion=row['timestamp_modificacion'],
                            contador_accesos=row['contador_accesos'],
                            version=row['version'],
                            metadatos=json.loads(row['metadatos']) if row['metadatos'] else {},
                            tags=set(json.loads(row['tags'])) if row['tags'] else set()
                        )
                        self._elementos[elemento.clave] = elemento
                    except Exception:
                        pass
        except Exception:
            pass
    
    def crear_instantanea(self, nombre: str = "") -> str:
        with self._lock:
            datos = {k: v.valor for k, v in self._elementos.items() if not v.esta_expirado()}
            hash_estado = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()
            instantanea = InstantaneaContexto(
                sesion_id=self.id, elementos=datos, hash_estado=hash_estado,
                metadatos={'nombre': nombre, 'modo': self.modo.value}
            )
            self._instantaneas[instantanea.id] = instantanea
            return instantanea.id
    
    def restaurar_instantanea(self, instantanea_id: str) -> bool:
        with self._lock:
            if instantanea_id not in self._instantaneas:
                return False
            instantanea = self._instantaneas[instantanea_id]
            self._elementos.clear()
            self.memoria.limpiar()
            for clave, valor in instantanea.elementos.items():
                self.establecer(clave, valor)
            self._historial_cambios.append(('restaurar', instantanea_id, time.time()))
            return True
    
    def _publicar_evento(self, tipo: str, datos: Dict[str, Any]):
        try:
            publicar(tipo, datos={**datos, 'sesion_id': self.id}, origen="contexto", prioridad=PrioridadEvento.MEDIA)
        except Exception:
            pass
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'sesion': {
                    'id': self.sesion.id, 'usuario_id': self.sesion.usuario_id,
                    'inicio': self.sesion.inicio, 'duracion': self.duracion,
                    'estado': self.sesion.estado.value, 'modo': self.sesion.modo.value,
                },
                'elementos': {
                    'total': len(self._elementos), 'en_memoria': len(self.memoria),
                    'por_tipo': dict(Counter(e.tipo for e in self._elementos.values())),
                    'por_importancia': dict(Counter(e.importancia.value for e in self._elementos.values())),
                },
                'ventana': self.ventana.estadisticas(),
                'operaciones': dict(self._estadisticas),
                'instantaneas': len(self._instantaneas),
                'historial_cambios': len(self._historial_cambios),
            }
    
    def limpiar_expirados(self) -> int:
        with self._lock:
            expirados = [k for k, v in self._elementos.items() if v.esta_expirado()]
            for clave in expirados:
                self.eliminar(clave)
            return len(expirados)
    
    def pausar(self):
        with self._lock:
            self.sesion.estado = EstadoContexto.PAUSADO
    
    def reanudar(self):
        with self._lock:
            self.sesion.estado = EstadoContexto.ACTIVO
    
    def finalizar(self):
        with self._lock:
            self.sesion.finalizar()
            with Contexto._lock_instancias:
                if self.id in Contexto._instancias:
                    del Contexto._instancias[self.id]
    
    def __repr__(self) -> str:
        return f"Contexto(id={self.id[:8]}, estado={self.estado.value}, elementos={len(self._elementos)})"
    
    def __len__(self) -> int:
        return len(self._elementos)

# =====================================================================
# FÁBRICA DE CONTEXTOS
# =====================================================================

class FabricaContextos:
    @staticmethod
    def crear_contexto_conversacion(usuario_id: str = None) -> Contexto:
        ctx = Contexto(usuario_id=usuario_id, modo=ModoContexto.ADAPTATIVO, capacidad_memoria=7, tamaño_ventana=8192)
        ctx.establecer('historial_mensajes', [], importancia=NivelImportancia.ALTO)
        ctx.establecer('turno_actual', 0, importancia=NivelImportancia.MEDIO)
        return ctx
    
    @staticmethod
    def crear_contexto_razonamiento() -> Contexto:
        ctx = Contexto(modo=ModoContexto.TECNICO, capacidad_memoria=9, tamaño_ventana=4096)
        ctx.establecer('premisas', [], importancia=NivelImportancia.CRITICO)
        ctx.establecer('conclusiones', [], importancia=NivelImportancia.ALTO)
        return ctx

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE CONTEXTO CUÁNTICO")
    print("=" * 70)
    
    ctx = None
    
    try:
        print("\n[1/8] Creando contexto...")
        ctx = Contexto(usuario_id="test_user", persistir=False)
        print(f"  ✅ Contexto creado: {ctx}")
        
        print("\n[2/8] Estableciendo valores...")
        ctx.establecer('nombre', 'ANP', importancia=NivelImportancia.CRITICO)
        ctx.establecer('version', '0.0.1-NEBULA', importancia=NivelImportancia.ALTO)
        ctx.establecer('contador', 0, importancia=NivelImportancia.MEDIO)
        ctx.establecer('config', {'tema': 'oscuro', 'idioma': 'es'}, importancia=NivelImportancia.BAJO)
        print(f"  ✅ 4 elementos establecidos")
        
        print("\n[3/8] Obteniendo valores...")
        print(f"  📍 nombre: {ctx.obtener('nombre')}")
        print(f"  📍 version: {ctx['version']}")
        print(f"  📍 ¿contador existe?: {'contador' in ctx}")
        
        print("\n[4/8] Probando memoria de corto plazo...")
        for i in range(10):
            ctx.memorizar(f"item_{i}", f"valor_{i}")
        print(f"  📍 Memoria: {len(ctx.memoria)}/{ctx.memoria.capacidad} elementos")
        print(f"  📍 Recuerdos recientes: {ctx.recuerdos_recientes(3)}")
        
        print("\n[5/8] Probando ventana deslizante...")
        for i in range(5):
            ctx.agregar_texto(f"Este es el mensaje número {i} de la conversación. ")
        print(f"  📍 Ventanas: {ctx.ventana.estadisticas()['total_ventanas']}")
        print(f"  📍 Contexto actual: {ctx.contexto_actual()[:100]}...")
        
        print("\n[6/8] Creando instantánea...")
        instantanea_id = ctx.crear_instantanea("antes_modificacion")
        print(f"  ✅ Instantánea creada: {instantanea_id[:8]}")
        ctx['contador'] = 42
        print(f"  📍 contador modificado: {ctx['contador']}")
        
        print("\n[7/8] Restaurando instantánea...")
        ctx.restaurar_instantanea(instantanea_id)
        print(f"  📍 contador restaurado: {ctx['contador']}")
        
        print("\n[8/8] Estadísticas del contexto...")
        stats = ctx.obtener_estadisticas()
        print(f"  📊 Sesión: {stats['sesion']['id'][:8]}...")
        print(f"  📊 Duración: {stats['sesion']['duracion']:.2f}s")
        print(f"  📊 Elementos: {stats['elementos']['total']}")
        print(f"  📊 En memoria: {stats['elementos']['en_memoria']}")
        print(f"  📊 Operaciones: {stats['operaciones']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Contexto Cuántico está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if ctx:
            print("\n🛑 Finalizando contexto...")
            ctx.finalizar()
            print("   ✓ Contexto finalizado")
    
    print("\n" + "=" * 70 + "\n")