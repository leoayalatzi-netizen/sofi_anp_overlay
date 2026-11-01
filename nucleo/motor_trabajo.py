#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Trabajo — Memoria Operativa 7±2 (Ley de Miller)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, json, uuid, traceback, threading, heapq
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque, OrderedDict
from enum import Enum
from datetime import datetime

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
                    return ResultadoMotor(exito=True, datos=resultado,
                                          tiempo_ejecucion_ms=(time.time() - inicio) * 1000)
                except Exception as e:
                    return ResultadoMotor(exito=False, error=str(e),
                                          tiempo_ejecucion_ms=(time.time() - inicio) * 1000)

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

class PrioridadItem(Enum):
    CRITICA = 0
    ALTA = 1
    MEDIA = 2
    BAJA = 3
    FONDO = 4

class EstadoItem(Enum):
    ACTIVO = "activo"
    FOCAL = "focal"
    LATENTE = "latente"
    DECAYENDO = "decayendo"
    EXPULSADO = "expulsado"

class Modalidad(Enum):
    VERBAL = "verbal"
    VISUAL = "visual"
    ESPACIAL = "espacial"
    EJECUTIVA = "ejecutiva"
    EPISODICA = "episodica"
    ABSTRACTA = "abstracta"
    MIXTA = "mixta"

class EventoTrabajo(Enum):
    INSERCION = "insercion"
    ACCESO = "acceso"
    ACTUALIZACION = "actualizacion"
    EXPULSION = "expulsion"
    DECAIMIENTO = "decaimiento"
    CONSOLIDACION = "consolidacion"
    CAMBIO_FOCO = "cambio_foco"
    LIMPIEZA = "limpieza"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class ItemTrabajo:
    """Unidad mínima de información en la memoria de trabajo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contenido: Any = None
    resumen: str = ""
    modalidad: Modalidad = Modalidad.ABSTRACTA
    prioridad: PrioridadItem = PrioridadItem.MEDIA
    estado: EstadoItem = EstadoItem.ACTIVO
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_ultimo_acceso: float = field(default_factory=time.time)
    timestamp_expiracion: float = float('inf')
    peso_atencion: float = 0.5
    carga_cognitiva: float = 1.0
    chunk_grupo: Optional[str] = None
    asociaciones: List[str] = field(default_factory=list)
    contador_accesos: int = 0
    ttl_personalizado: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Chunk:
    """Agrupación de items relacionados (chunking)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    items_ids: List[str] = field(default_factory=list)
    peso: float = 1.0
    timestamp_creacion: float = field(default_factory=time.time)

@dataclass
class RegistroEvento:
    """Registro de auditoría para operaciones de memoria de trabajo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tipo: EventoTrabajo = EventoTrabajo.INSERCION
    item_id: str = ""
    timestamp: float = field(default_factory=time.time)
    detalle: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# EJECUTIVO CENTRAL (CONTROL ATENCIONAL)
# =====================================================================

class EjecutivoCentral:
    """
    Sistema de control atencional de la memoria de trabajo.
    Basado en el modelo de Baddeley & Hitch (1974) + Norman & Shallice (1986).
    
    Implementa:
    - Foco atencional con capacidad limitada (1-4 items)
    - Competencia por activación (spreading activation)
    - Programación de tareas (SJF con prioridades)
    - Monitorización de conflicto
    """
    
    def __init__(self, capacidad_foco: int = 3):
        self.capacidad_foco = capacidad_foco
        self._foco_actual: OrderedDict[str, float] = OrderedDict()
        self._cola_tareas: List[Tuple[float, float, str]] = []
        self._nivel_alerta: float = 0.8
        self._fatiga: float = 0.0
        self._historial_cambios: List[Dict] = []
    
    def seleccionar_foco(self, items: Dict[str, ItemTrabajo], 
                         max_items: int = None) -> List[str]:
        """
        Selecciona los items que deben estar en el foco atencional.
        Usa spreading activation con decaimiento temporal.
        """
        if max_items is None:
            max_items = self.capacidad_foco
        
        ahora = time.time()
        candidatos = []
        
        for item_id, item in items.items():
            if item.estado in (EstadoItem.EXPULSADO, EstadoItem.DECAYENDO):
                continue
            
            antiguedad = ahora - item.timestamp_ultimo_acceso
            decaimiento = math.exp(-antiguedad / 30.0)
            
            score_prioridad = (4 - item.prioridad.value) / 4.0
            score_accesos = min(1.0, item.contador_accesos / 10.0)
            score_atencion = item.peso_atencion
            
            activacion = (
                score_prioridad * 0.35 +
                score_accesos * 0.20 +
                score_atencion * 0.25 +
                decaimiento * 0.20
            )
            
            heapq.heappush(candidatos, (-activacion, item_id))
        
        foco = []
        for _ in range(min(max_items, len(candidatos))):
            if candidatos:
                _, item_id = heapq.heappop(candidatos)
                foco.append(item_id)
        
        return foco
    
    def calcular_carga(self, items: Dict[str, ItemTrabajo]) -> float:
        """Calcula la carga cognitiva total del sistema."""
        if not items:
            return 0.0
        cargas = [item.carga_cognitiva for item in items.values()
                 if item.estado != EstadoItem.EXPULSADO]
        return sum(cargas) / len(cargas) if cargas else 0.0
    

# =====================================================================
# BUCLES ESPECIALIZADOS
# =====================================================================

class BucleFonologico:
    """Almacén verbal: información basada en lenguaje."""
    
    def __init__(self, capacidad: int = 7):
        self.capacidad = capacidad
        self._items: OrderedDict[str, float] = OrderedDict()
    
    def agregar(self, item_id: str, peso: float = 1.0):
        self._items[item_id] = peso
        self._items.move_to_end(item_id)
        while len(self._items) > self.capacidad:
            self._items.popitem(last=False)
    
    def contiene(self, item_id: str) -> bool:
        return item_id in self._items

class AgendaVisoespacial:
    """Almacén visual y espacial."""
    
    def __init__(self, capacidad: int = 4):
        self.capacidad = capacidad
        self._items: OrderedDict[str, float] = OrderedDict()
    
    def agregar(self, item_id: str, peso: float = 1.0):
        self._items[item_id] = peso
        self._items.move_to_end(item_id)
        while len(self._items) > self.capacidad:
            self._items.popitem(last=False)

class BufferEpisodico:
    """
    Buffer episódico: integración multimodal con timestamp.
    Vincula información de distintas fuentes.
    """
    
    def __init__(self, capacidad: int = 4):
        self.capacidad = capacidad
        self._items: OrderedDict[str, float] = OrderedDict()
    
    def integrar(self, item_id: str, peso: float = 1.0):
        self._items[item_id] = peso
        self._items.move_to_end(item_id)
        while len(self._items) > self.capacidad:
            self._items.popitem(last=False)


# =====================================================================
# SISTEMA DE CHUNKING
# =====================================================================

class SistemaChunking:
    """
    Agrupa items relacionados para superar el límite 7±2.
    Un chunk cuenta como 1 item independientemente de su contenido.
    """
    
    def __init__(self):
        self._chunks: Dict[str, Chunk] = {}
        self._item_a_chunk: Dict[str, str] = {}
    
    def crear_chunk(self, nombre: str, items_ids: List[str], peso: float = 1.0) -> str:
        chunk = Chunk(nombre=nombre, items_ids=items_ids, peso=peso)
        self._chunks[chunk.id] = chunk
        for iid in items_ids:
            self._item_a_chunk[iid] = chunk.id
        return chunk.id
    
    def desagrupar(self, chunk_id: str) -> List[str]:
        chunk = self._chunks.pop(chunk_id, None)
        if chunk:
            for iid in chunk.items_ids:
                self._item_a_chunk.pop(iid, None)
            return chunk.items_ids
        return []
    
    def obtener_chunk_de_item(self, item_id: str) -> Optional[str]:
        return self._item_a_chunk.get(item_id)
    
    @property
    def total_chunks(self) -> int:
        return len(self._chunks)


# =====================================================================
# MOTOR DE TRABAJO PRINCIPAL
# =====================================================================

class MotorTrabajo(MotorBase):
    """
    Motor de Trabajo de ANP — Memoria Operativa 7±2.
    
    Arquitectura basada en el modelo multicomponente de Baddeley:
    - Ejecutivo Central: control atencional y foco
    - Bucle Fonológico: información verbal (capacidad ~7)
    - Agenda Visoespacial: información visual/espacial (capacidad ~4)
    - Buffer Episódico: integración multimodal
    
    Características avanzadas:
    - Chunking para superar límite 7±2
    - Decaimiento temporal con repaso
    - Competencia por activación (spreading activation)
    - Múltiples niveles de prioridad
    - Métricas de carga cognitiva
    - Persistencia completa
    - Auditoría de eventos
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._items: Dict[str, ItemTrabajo] = {}
        self._ejecutivo = EjecutivoCentral(capacidad_foco=3)
        self._fonologico = BucleFonologico(capacidad=7)
        self._visoespacial = AgendaVisoespacial(capacidad=4)
        self._episodico = BufferEpisodico(capacidad=4)
        self._chunking = SistemaChunking()
        self._registro_eventos: deque = deque(maxlen=500)
        self._lock = threading.RLock()
        self._max_items = 20
        self._ttl_default = 300.0
        self._estadisticas = {
            'total_inserciones': 0, 'total_accesos': 0,
            'total_expulsiones': 0, 'total_decaimientos': 0,
            'total_chunks': 0, 'carga_cognitiva_promedio': 0.0,
            'items_activos': 0, 'ultimo_mantenimiento': 0.0
        }
        self._dir = Path("almacenamiento/trabajo")
        self._dir.mkdir(parents=True, exist_ok=True)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        accion = entrada.get('accion', 'info')
        with self._lock:
            metodos = {
                'insertar': self._insertar,
                'acceder': self._acceder,
                'actualizar': self._actualizar,
                'expulsar': self._expulsar,
                'foco': self._foco,
                'chunk_crear': self._chunk_crear,
                'chunk_desagrupar': self._chunk_desagrupar,
                'repasar': self._repasar,
                'limpiar': self._limpiar,
                'estado': self._estado,
                'metrica_carga': self._metrica_carga,
                'historial': self._historial,
                'estadisticas': self._estadisticas,
                'guardar': self._guardar,
                'cargar': self._cargar,
                'info': self._info,
            }
            func = metodos.get(accion)
            return func(entrada) if func else {'error': f'Acción: {accion}', 'exito': False}
    
    def _registrar_evento(self, tipo: EventoTrabajo, item_id: str, detalle: Dict = None):
        evento = RegistroEvento(tipo=tipo, item_id=item_id, detalle=detalle or {})
        self._registro_eventos.append(evento)
    
    def _insertar(self, e: Dict) -> Dict[str, Any]:
        if len(self._items) >= self._max_items:
            self._limpiar({'agresivo': True})
            if len(self._items) >= self._max_items:
                return {'error': 'Memoria de trabajo llena', 'exito': False}
        
        try:
            modalidad_str = e.get('modalidad', 'abstracta')
            try:
                modalidad = Modalidad(modalidad_str)
            except ValueError:
                modalidad = Modalidad.ABSTRACTA
            
            prioridad_str = e.get('prioridad', 'media')
            try:
                prioridad = PrioridadItem(prioridad_str)
            except ValueError:
                prioridad = PrioridadItem.MEDIA
            
            ttl = e.get('ttl', self._ttl_default)
            
            item = ItemTrabajo(
                contenido=e.get('contenido'),
                resumen=e.get('resumen', str(e.get('contenido', ''))[:100]),
                modalidad=modalidad,
                prioridad=prioridad,
                peso_atencion=e.get('peso_atencion', 0.5),
                carga_cognitiva=e.get('carga_cognitiva', 1.0),
                chunk_grupo=e.get('chunk_grupo'),
                asociaciones=e.get('asociaciones', []),
                ttl_personalizado=ttl,
                timestamp_expiracion=time.time() + ttl,
                metadata=e.get('metadata', {})
            )
            
            self._items[item.id] = item
            self._estadisticas['total_inserciones'] += 1
            self._estadisticas['items_activos'] += 1
            
            if item.modalidad == Modalidad.VERBAL:
                self._fonologico.agregar(item.id)
            elif item.modalidad in (Modalidad.VISUAL, Modalidad.ESPACIAL):
                self._visoespacial.agregar(item.id)
            
            self._registrar_evento(EventoTrabajo.INSERCION, item.id,
                                  {'modalidad': item.modalidad.value,
                                   'prioridad': item.prioridad.value})
            
            return {
                'exito': True,
                'id': item.id,
                'resumen': item.resumen[:80],
                'modalidad': item.modalidad.value,
                'prioridad': item.prioridad.value,
                'ttl': ttl,
                'total_items': len(self._items)
            }
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _acceder(self, e: Dict) -> Dict[str, Any]:
        item_id = e.get('id', '')
        if not item_id or item_id not in self._items:
            return {'error': f'Item no encontrado: {item_id}', 'exito': False}
        
        item = self._items[item_id]
        
        if item.estado == EstadoItem.EXPULSADO:
            return {'error': 'Item expulsado', 'exito': False}
        
        ahora = time.time()
        item.timestamp_ultimo_acceso = ahora
        item.contador_accesos += 1
        item.estado = EstadoItem.FOCAL
        item.peso_atencion = min(1.0, item.peso_atencion + 0.1)
        
        if item.ttl_personalizado:
            item.timestamp_expiracion = ahora + item.ttl_personalizado
        
        self._estadisticas['total_accesos'] += 1
        self._registrar_evento(EventoTrabajo.ACCESO, item_id,
                              {'contador': item.contador_accesos})
        
        return {
            'exito': True,
            'id': item.id,
            'resumen': item.resumen[:100],
            'contenido': item.contenido,
            'modalidad': item.modalidad.value,
            'estado': item.estado.value,
            'peso_atencion': round(item.peso_atencion, 3),
            'contador_accesos': item.contador_accesos,
            'carga_cognitiva': item.carga_cognitiva,
            'asociaciones': item.asociaciones,
            'chunk': self._chunking.obtener_chunk_de_item(item_id),
            'metadata': item.metadata
        }
    
    def _actualizar(self, e: Dict) -> Dict[str, Any]:
        item_id = e.get('id', '')
        if not item_id or item_id not in self._items:
            return {'error': f'Item no encontrado: {item_id}', 'exito': False}
        
        item = self._items[item_id]
        
        if 'contenido' in e:
            item.contenido = e['contenido']
        if 'resumen' in e:
            item.resumen = e['resumen']
        if 'peso_atencion' in e:
            item.peso_atencion = max(0.0, min(1.0, float(e['peso_atencion'])))
        if 'carga_cognitiva' in e:
            item.carga_cognitiva = max(0.1, float(e['carga_cognitiva']))
        if 'prioridad' in e:
            try:
                item.prioridad = PrioridadItem(e['prioridad'])
            except ValueError:
                pass
        if 'ttl' in e:
            item.ttl_personalizado = float(e['ttl'])
            item.timestamp_expiracion = time.time() + item.ttl_personalizado
        
        item.timestamp_ultimo_acceso = time.time()
        self._registrar_evento(EventoTrabajo.ACTUALIZACION, item_id)
        
        return {'exito': True, 'id': item_id, 'resumen': item.resumen[:80]}
    
    def _expulsar(self, e: Dict) -> Dict[str, Any]:
        item_id = e.get('id', '')
        if item_id and item_id in self._items:
            item = self._items[item_id]
            item.estado = EstadoItem.EXPULSADO
            item.peso_atencion = 0.0
            self._estadisticas['total_expulsiones'] += 1
            self._estadisticas['items_activos'] -= 1
            self._registrar_evento(EventoTrabajo.EXPULSION, item_id)
            return {'exito': True, 'id': item_id, 'expulsado': True}
        elif not item_id:
            expulsados = 0
            for iid, item in list(self._items.items()):
                if item.estado == EstadoItem.DECAYENDO:
                    item.estado = EstadoItem.EXPULSADO
                    item.peso_atencion = 0.0
                    expulsados += 1
                    self._estadisticas['total_expulsiones'] += 1
                    self._estadisticas['items_activos'] -= 1
            return {'exito': True, 'expulsados': expulsados}
        return {'error': 'Item no encontrado', 'exito': False}
    
    def _foco(self, e: Dict) -> Dict[str, Any]:
        """Obtiene o establece el foco atencional."""
        if 'establecer' in e:
            ids = e['establecer']
            for iid in ids:
                if iid in self._items:
                    self._items[iid].estado = EstadoItem.FOCAL
                    self._items[iid].peso_atencion = min(1.0, 
                        self._items[iid].peso_atencion + 0.2)
        
        foco = self._ejecutivo.seleccionar_foco(self._items)
        resultado = []
        for iid in foco:
            if iid in self._items:
                item = self._items[iid]
                resultado.append({
                    'id': item.id,
                    'resumen': item.resumen[:60],
                    'modalidad': item.modalidad.value,
                    'prioridad': item.prioridad.value,
                    'activacion': round(item.peso_atencion, 3),
                    'accesos': item.contador_accesos
                })
        
        return {'exito': True, 'foco': resultado, 'capacidad_foco': self._ejecutivo.capacidad_foco}
    
    def _chunk_crear(self, e: Dict) -> Dict[str, Any]:
        nombre = e.get('nombre', f'chunk_{len(self._chunking._chunks)+1}')
        items_ids = e.get('items_ids', [])
        
        valids = [iid for iid in items_ids if iid in self._items]
        if len(valids) < 2:
            return {'error': 'Mínimo 2 items válidos para chunk', 'exito': False}
        
        chunk_id = self._chunking.crear_chunk(nombre, valids, e.get('peso', 1.0))
        self._estadisticas['total_chunks'] += 1
        self._registrar_evento(EventoTrabajo.CONSOLIDACION, chunk_id,
                              {'tipo': 'chunk', 'items': valids})
        
        return {'exito': True, 'chunk_id': chunk_id, 'nombre': nombre, 'items': len(valids)}
    
    def _chunk_desagrupar(self, e: Dict) -> Dict[str, Any]:
        chunk_id = e.get('chunk_id', '')
        if not chunk_id:
            return {'error': 'chunk_id requerido', 'exito': False}
        
        items = self._chunking.desagrupar(chunk_id)
        self._estadisticas['total_chunks'] -= 1
        return {'exito': True, 'items_liberados': len(items), 'items_ids': items}
    
    def _repasar(self, e: Dict) -> Dict[str, Any]:
        """Repaso articulatorio: refresca items del bucle fonológico."""
        ahora = time.time()
        repasados = 0
        
        for iid in list(self._fonologico._items.keys()):
            if iid in self._items:
                item = self._items[iid]
                if item.estado not in (EstadoItem.EXPULSADO,):
                    item.timestamp_ultimo_acceso = ahora
                    item.estado = EstadoItem.ACTIVO
                    if item.ttl_personalizado:
                        item.timestamp_expiracion = ahora + item.ttl_personalizado
                    else:
                        item.timestamp_expiracion = ahora + self._ttl_default
                    repasados += 1
        
        self._registrar_evento(EventoTrabajo.CONSOLIDACION, '',
                              {'tipo': 'repaso', 'repasados': repasados})
        
        return {'exito': True, 'repasados': repasados}
    
    def _limpiar(self, e: Dict = None) -> Dict[str, Any]:
        """Limpia items decaídos o expulsados."""
        if e is None:
            e = {}
        
        ahora = time.time()
        eliminados = 0
        decaidos = 0
        
        for iid, item in list(self._items.items()):
            if item.estado == EstadoItem.EXPULSADO:
                del self._items[iid]
                eliminados += 1
                continue
            
            if item.estado == EstadoItem.DECAYENDO:
                if e.get('agresivo') or ahora > item.timestamp_expiracion:
                    del self._items[iid]
                    eliminados += 1
                    self._estadisticas['items_activos'] -= 1
                continue
            
            if ahora > item.timestamp_expiracion:
                if item.estado == EstadoItem.FOCAL:
                    item.estado = EstadoItem.ACTIVO
                else:
                    item.estado = EstadoItem.DECAYENDO
                    decaidos += 1
                    self._estadisticas['total_decaimientos'] += 1
                    self._registrar_evento(EventoTrabajo.DECAIMIENTO, iid)
        
        self._estadisticas['ultimo_mantenimiento'] = ahora
        self._registrar_evento(EventoTrabajo.LIMPIEZA, '',
                              {'eliminados': eliminados, 'decaidos': decaidos})
        
        return {'exito': True, 'eliminados': eliminados, 'decaidos': decaidos,
                'total_activos': len(self._items)}
    
    def _estado(self, e: Dict) -> Dict[str, Any]:
        """Retorna el estado completo de la memoria de trabajo."""
        ahora = time.time()
        items_estado = []
        
        for item in sorted(self._items.values(), 
                          key=lambda x: (x.prioridad.value, -x.peso_atencion)):
            if item.estado == EstadoItem.EXPULSADO:
                continue
            items_estado.append({
                'id': item.id,
                'resumen': item.resumen[:50],
                'modalidad': item.modalidad.value,
                'prioridad': item.prioridad.value,
                'estado': item.estado.value,
                'peso_atencion': round(item.peso_atencion, 3),
                'accesos': item.contador_accesos,
                'carga': round(item.carga_cognitiva, 2),
                'tiempo_restante': round(max(0, item.timestamp_expiracion - ahora), 1),
                'en_chunk': self._chunking.obtener_chunk_de_item(item.id)
            })
        
        return {
            'exito': True,
            'total_activos': len(items_estado),
            'capacidad_maxima': self._max_items,
            'foco': [i['id'] for i in items_estado if i['estado'] == 'focal'],
            'fonologico': list(self._fonologico._items.keys()),
            'visoespacial': list(self._visoespacial._items.keys()),
            'episodico': list(self._episodico._items.keys()),
            'total_chunks': self._chunking.total_chunks,
            'items': items_estado
        }
    
    def _metrica_carga(self, e: Dict) -> Dict[str, Any]:
        """Calcula la carga cognitiva actual."""
        carga = self._ejecutivo.calcular_carga(self._items)
        self._estadisticas['carga_cognitiva_promedio'] = (
            self._estadisticas['carga_cognitiva_promedio'] * 0.9 + carga * 0.1
        )
        
        nivel = "óptimo"
        if carga > 0.8:
            nivel = "sobrecarga"
        elif carga > 0.6:
            nivel = "alto"
        elif carga > 0.3:
            nivel = "moderado"
        else:
            nivel = "bajo"
        
        return {
            'exito': True,
            'carga_actual': round(carga, 3),
            'carga_promedio': round(self._estadisticas['carga_cognitiva_promedio'], 3),
            'nivel': nivel,
            'items_en_foco': len([i for i in self._items.values() if i.estado == EstadoItem.FOCAL]),
            'total_activos': len([i for i in self._items.values() if i.estado != EstadoItem.EXPULSADO])
        }
    
    def _historial(self, e: Dict) -> Dict[str, Any]:
        """Retorna el historial de eventos."""
        limite = e.get('limite', 20)
        tipo_filtro = e.get('tipo')
        
        eventos = list(self._registro_eventos)
        if tipo_filtro:
            try:
                tipo_enum = EventoTrabajo(tipo_filtro)
                eventos = [ev for ev in eventos if ev.tipo == tipo_enum]
            except ValueError:
                pass
        
        eventos = eventos[-limite:]
        resultado = []
        for ev in eventos:
            resultado.append({
                'id': ev.id,
                'tipo': ev.tipo.value,
                'item_id': ev.item_id[:8] if ev.item_id else '',
                'timestamp': datetime.fromtimestamp(ev.timestamp).isoformat(),
                'detalle': ev.detalle
            })
        
        return {'exito': True, 'total_eventos': len(self._registro_eventos),
                'mostrados': len(resultado), 'eventos': resultado}
    
    def _estadisticas(self, e: Dict) -> Dict[str, Any]:
        """Retorna estadísticas completas."""
        return {
            'exito': True,
            'total_inserciones': self._estadisticas['total_inserciones'],
            'total_accesos': self._estadisticas['total_accesos'],
            'total_expulsiones': self._estadisticas['total_expulsiones'],
            'total_decaimientos': self._estadisticas['total_decaimientos'],
            'items_activos': self._estadisticas['items_activos'],
            'total_chunks': self._chunking.total_chunks,
            'carga_promedio': round(self._estadisticas['carga_cognitiva_promedio'], 3),
            'capacidad_maxima': self._max_items,
            'capacidad_foco': self._ejecutivo.capacidad_foco,
            'capacidad_fonologica': self._fonologico.capacidad,
            'capacidad_visoespacial': self._visoespacial.capacidad,
            'capacidad_episodica': self._episodico.capacidad,
            'ttl_default': self._ttl_default
        }
    
    def _guardar(self, e: Dict) -> Dict[str, Any]:
        try:
            ruta = e.get('ruta', str(self._dir / 'memoria_trabajo'))
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            data = {
                'items': {},
                'chunks': [],
                'estadisticas': self._estadisticas,
                'version': '0.0.1-NEBULA',
                'timestamp': time.time()
            }
            
            for iid, item in self._items.items():
                data['items'][iid] = {
                    'id': item.id,
                    'contenido': item.contenido,
                    'resumen': item.resumen,
                    'modalidad': item.modalidad.value,
                    'prioridad': item.prioridad.value,
                    'estado': item.estado.value,
                    'timestamp_creacion': item.timestamp_creacion,
                    'timestamp_ultimo_acceso': item.timestamp_ultimo_acceso,
                    'timestamp_expiracion': item.timestamp_expiracion,
                    'peso_atencion': item.peso_atencion,
                    'carga_cognitiva': item.carga_cognitiva,
                    'asociaciones': item.asociaciones,
                    'contador_accesos': item.contador_accesos,
                    'ttl_personalizado': item.ttl_personalizado,
                    'metadata': item.metadata
                }
            
            for chunk in self._chunking._chunks.values():
                data['chunks'].append({
                    'id': chunk.id,
                    'nombre': chunk.nombre,
                    'items_ids': chunk.items_ids,
                    'peso': chunk.peso,
                    'timestamp_creacion': chunk.timestamp_creacion
                })
            
            with open(ruta + '.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
            return {'exito': True, 'ruta': ruta + '.pkl',
                   'items': len(data['items']), 'chunks': len(data['chunks'])}
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _cargar(self, e: Dict) -> Dict[str, Any]:
        try:
            ruta = e.get('ruta', '')
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            if not Path(ruta + '.pkl').exists():
                return {'error': f'Archivo no encontrado: {ruta}.pkl', 'exito': False}
            
            with open(ruta + '.pkl', 'rb') as f:
                data = pickle.load(f)
            
            self._items.clear()
            self._ejecutivo = EjecutivoCentral()
            self._fonologico = BucleFonologico()
            self._visoespacial = AgendaVisoespacial()
            self._episodico = BufferEpisodico()
            self._chunking = SistemaChunking()
            self._registro_eventos.clear()
            
            for iid, idict in data.get('items', {}).items():
                try:
                    modalidad = Modalidad(idict['modalidad'])
                except (ValueError, KeyError):
                    modalidad = Modalidad.ABSTRACTA
                try:
                    prioridad = PrioridadItem(idict['prioridad'])
                except (ValueError, KeyError):
                    prioridad = PrioridadItem.MEDIA
                try:
                    estado = EstadoItem(idict['estado'])
                except (ValueError, KeyError):
                    estado = EstadoItem.ACTIVO
                
                item = ItemTrabajo(
                    id=idict['id'],
                    contenido=idict.get('contenido'),
                    resumen=idict.get('resumen', ''),
                    modalidad=modalidad,
                    prioridad=prioridad,
                    estado=estado,
                    timestamp_creacion=idict.get('timestamp_creacion', time.time()),
                    timestamp_ultimo_acceso=idict.get('timestamp_ultimo_acceso', time.time()),
                    timestamp_expiracion=idict.get('timestamp_expiracion', float('inf')),
                    peso_atencion=idict.get('peso_atencion', 0.5),
                    carga_cognitiva=idict.get('carga_cognitiva', 1.0),
                    asociaciones=idict.get('asociaciones', []),
                    contador_accesos=idict.get('contador_accesos', 0),
                    ttl_personalizado=idict.get('ttl_personalizado'),
                    metadata=idict.get('metadata', {})
                )
                self._items[item.id] = item
                
                if item.modalidad == Modalidad.VERBAL:
                    self._fonologico.agregar(item.id)
                elif item.modalidad in (Modalidad.VISUAL, Modalidad.ESPACIAL):
                    self._visoespacial.agregar(item.id)
            
            for cdict in data.get('chunks', []):
                self._chunking.crear_chunk(
                    nombre=cdict.get('nombre', ''),
                    items_ids=cdict.get('items_ids', []),
                    peso=cdict.get('peso', 1.0)
                )
            
            self._estadisticas = data.get('estadisticas', self._estadisticas)
            
            return {'exito': True, 'items': len(self._items),
                   'chunks': self._chunking.total_chunks}
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'modelo': 'Baddeley-Hitch multicomponente',
            'capacidad_maxima': self._max_items,
            'capacidad_foco': self._ejecutivo.capacidad_foco,
            'capacidad_fonologica': self._fonologico.capacidad,
            'capacidad_visoespacial': self._visoespacial.capacidad,
            'capacidad_episodica': self._episodico.capacidad,
            'ttl_default': self._ttl_default,
            'items_activos': len([i for i in self._items.values() if i.estado != EstadoItem.EXPULSADO]),
            'total_chunks': self._chunking.total_chunks,
            'funcionalidades': ['insertar', 'acceder', 'actualizar', 'expulsar',
                               'foco_selectivo', 'chunking', 'repaso',
                               'metrica_carga', 'historial', 'persistencia']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE TRABAJO — MEMORIA 7±2")
    print("=" * 70)
    motor = None
    try:
        print("\n[0] Inicializando...")
        motor = MotorTrabajo()
        motor.inicializar()
        print(f"  ✅ Motor: {motor.nombre} | Estado: {motor.estado}")

        print(f"\n[1] Insertando items en memoria de trabajo...")
        items_prueba = [
            {'resumen': 'Tarea: completar motor_embebido.py', 'modalidad': 'verbal', 
             'prioridad': 'critica', 'carga_cognitiva': 2.0, 'ttl': 120},
            {'resumen': 'Resultado: similitud perro-gato = 0.32', 'modalidad': 'verbal',
             'prioridad': 'alta', 'carga_cognitiva': 1.2, 'ttl': 60},
            {'resumen': 'Imagen: diagrama_arquitectura_ANP.png', 'modalidad': 'visual',
             'prioridad': 'media', 'carga_cognitiva': 1.5, 'ttl': 90},
            {'resumen': 'Posición: archivo en almacenamiento/modelos/', 'modalidad': 'espacial',
             'prioridad': 'baja', 'carga_cognitiva': 0.8, 'ttl': 180},
            {'resumen': 'Error detectado en motor_neuronal.py línea 342', 'modalidad': 'verbal',
             'prioridad': 'critica', 'carga_cognitiva': 2.5, 'ttl': 300},
            {'resumen': 'Python 3.11 sintaxis match-case disponible', 'modalidad': 'verbal',
             'prioridad': 'media', 'carga_cognitiva': 0.5, 'ttl': 200},
            {'resumen': 'Usuario solicita velocidad de respuesta < 100ms', 'modalidad': 'ejecutiva',
             'prioridad': 'alta', 'carga_cognitiva': 1.0, 'ttl': 150},
            {'resumen': 'Secuencia: inicializar -> entrenar -> predecir', 'modalidad': 'verbal',
             'prioridad': 'media', 'carga_cognitiva': 0.6, 'ttl': 100},
        ]
        
        ids = []
        for item in items_prueba:
            r = motor.procesar({'accion': 'insertar', **item})
            if r.exito and r.datos and r.datos.get('exito'):
                ids.append(r.datos['id'])
                print(f"  ✅ [{r.datos['prioridad']}] {r.datos['resumen'][:55]}... (TTL: {r.datos['ttl']}s)")
        
        print(f"\n[2] Estado de la memoria:")
        r = motor.procesar({'accion': 'estado'})
        if r.exito and r.datos:
            estado = r.datos
            print(f"  📊 Activos: {estado['total_activos']}/{estado['capacidad_maxima']}")
            print(f"  🎯 Foco: {len(estado['foco'])} items")
            print(f"  🗣️ Fonológico: {len(estado['fonologico'])} | 👁️ Visoespacial: {len(estado['visoespacial'])}")
            print(f"  📦 Chunks: {estado['total_chunks']}")

        print(f"\n[3] Métrica de carga cognitiva:")
        r = motor.procesar({'accion': 'metrica_carga'})
        if r.exito and r.datos:
            print(f"  🧠 Carga: {r.datos['carga_actual']} ({r.datos['nivel']})")

        print(f"\n[4] Foco atencional:")
        r = motor.procesar({'accion': 'foco'})
        if r.exito and r.datos:
            for item in r.datos['foco']:
                print(f"  🔦 [{item['prioridad']}] {item['resumen'][:50]}... (act: {item['activacion']})")

        print(f"\n[5] Accediendo items críticos:")
        if ids:
            for iid in ids[:2]:
                r = motor.procesar({'accion': 'acceder', 'id': iid})
                if r.exito and r.datos:
                    print(f"  📖 {r.datos['resumen'][:40]}... (accesos: {r.datos['contador_accesos']})")

        print(f"\n[6] Creando chunk (agrupación):")
        if len(ids) >= 3:
            r = motor.procesar({'accion': 'chunk_crear', 'nombre': 'Tareas ANP',
                               'items_ids': ids[:3]})
            if r.exito and r.datos:
                print(f"  📦 Chunk: {r.datos['nombre']} ({r.datos['items']} items)")

        print(f"\n[7] Repaso articulatorio:")
        r = motor.procesar({'accion': 'repasar'})
        if r.exito and r.datos:
            print(f"  🔄 Repasados: {r.datos['repasados']} items")

        print(f"\n[8] Limpieza de items decaídos:")
        r = motor.procesar({'accion': 'limpiar'})
        if r.exito and r.datos:
            print(f"  🧹 Eliminados: {r.datos['eliminados']} | Decaídos: {r.datos['decaidos']}")

        print(f"\n[9] Estadísticas finales:")
        r = motor.procesar({'accion': 'estadisticas'})
        if r.exito and r.datos:
            print(f"  📈 Inserciones: {r.datos['total_inserciones']}")
            print(f"  📈 Accesos: {r.datos['total_accesos']}")
            print(f"  📈 Carga promedio: {r.datos['carga_promedio']}")

        ruta = 'almacenamiento/trabajo/memoria_test'
        print(f"\n[10] Guardar: {'✅' if motor.procesar({'accion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")
        
        rc = motor.procesar({'accion':'cargar','ruta':ruta})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[11] Cargar: {'✅' if ok else '❌'} ({rc.datos.get('items','?') if ok else ''} items)")

        if ok:
            r = motor.procesar({'accion': 'estado'})
            if r.exito and r.datos:
                print(f"[12] Post-carga: {r.datos['total_activos']} activos | "
                      f"{r.datos['total_chunks']} chunks | "
                      f"Fonológico: {len(r.datos['fonologico'])} items")

        print(f"\n{'='*70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'='*70}\n")
      