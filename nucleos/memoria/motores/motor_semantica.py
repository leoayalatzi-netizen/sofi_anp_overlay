#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Semántico — Memoria de Conceptos y Relaciones
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, json, hashlib, uuid, traceback, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, Counter, deque, OrderedDict
from enum import Enum
from datetime import datetime
import threading

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
# TIPOS DE RELACIONES SEMÁNTICAS
# =====================================================================

class TipoRelacion(Enum):
    ES_UN = "es_un"                    # herencia taxonómica
    TIENE_UN = "tiene_un"             # posesión/atributo
    PARTE_DE = "parte_de"             # composición
    CAUSA = "causa"                    # causalidad
    PRECEDE = "precede"               # orden temporal
    EQUIVALE = "equivale"             # sinonimia
    OPUESTO = "opuesto"               # antonimia
    SIMILAR = "similar"               # semejanza
    ASOCIADO = "asociado"             # asociación libre
    DEPENDE = "depende"               # dependencia funcional
    PRODUCE = "produce"               # producción/generación
    UBICADO_EN = "ubicado_en"         # localización
    INSTANCIA_DE = "instancia_de"     # instanciación
    PROPIEDAD_DE = "propiedad_de"     # atributo de concepto
    MIEMBRO_DE = "miembro_de"         # pertenencia a conjunto
    DERIVA_DE = "deriva_de"           # derivación
    IMPLICA = "implica"               # implicación lógica
    EXCLUYE = "excluye"               # exclusión mutua
    REQUIERE = "requiere"             # requisito
    FINALIDAD = "finalidad"           # propósito

class TipoNodo(Enum):
    CONCEPTO = "concepto"
    ENTIDAD = "entidad"
    ATRIBUTO = "atributo"
    EVENTO = "evento"
    ACCION = "accion"
    CATEGORIA = "categoria"
    PROPIEDAD = "propiedad"
    REGLA = "regla"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class NodoSemantico:
    """Nodo del grafo de conocimiento."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    tipo: TipoNodo = TipoNodo.CONCEPTO
    atributos: Dict[str, Any] = field(default_factory=dict)
    definicion: str = ""
    embedding: Optional[List[float]] = None
    confianza: float = 1.0
    frecuencia: int = 0
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_actualizacion: float = field(default_factory=time.time)
    fuentes: List[str] = field(default_factory=list)
    idioma: str = "es"
    version: int = 1
    activo: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AristaSemantica:
    """Arista dirigida entre nodos del grafo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    origen_id: str = ""
    destino_id: str = ""
    tipo: TipoRelacion = TipoRelacion.ASOCIADO
    peso: float = 0.5
    confianza: float = 1.0
    bidireccional: bool = False
    atributos: Dict[str, Any] = field(default_factory=dict)
    timestamp_creacion: float = field(default_factory=time.time)
    fuentes: List[str] = field(default_factory=list)
    activo: bool = True

@dataclass
class Ontologia:
    """Ontología que agrupa conceptos y reglas."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    descripcion: str = ""
    conceptos_raiz: List[str] = field(default_factory=list)
    reglas: List[Dict[str, Any]] = field(default_factory=list)
    axiomas: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp_creacion: float = field(default_factory=time.time)

# =====================================================================
# ÍNDICES DEL GRAFO
# =====================================================================

class IndiceSemantico:
    """Índices ultra-rápidos para el grafo de conocimiento."""
    
    def __init__(self):
        self._por_tipo_nodo: Dict[TipoNodo, Set[str]] = defaultdict(set)
        self._por_tipo_relacion: Dict[TipoRelacion, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        self._por_nombre: Dict[str, str] = {}
        self._adyacencia_entrada: Dict[str, Set[str]] = defaultdict(set)
        self._adyacencia_salida: Dict[str, Set[str]] = defaultdict(set)
        self._por_atributo: Dict[str, Dict[Any, Set[str]]] = defaultdict(lambda: defaultdict(set))
        self._por_confianza: Dict[str, float] = {}
        self._frecuencias: Dict[str, int] = {}
        self._jerarquia: Dict[str, Set[str]] = defaultdict(set)
        self._herencia_cache: Dict[str, Set[str]] = {}
    
    def indexar_nodo(self, nodo: NodoSemantico):
        self._por_tipo_nodo[nodo.tipo].add(nodo.id)
        nombre_norm = nodo.nombre.lower().strip()
        self._por_nombre[nombre_norm] = nodo.id
        self._por_confianza[nodo.id] = nodo.confianza
        self._frecuencias[nodo.id] = nodo.frecuencia
        self._herencia_cache.pop(nodo.id, None)
        for clave, valor in nodo.atributos.items():
            if isinstance(valor, (str, int, float, bool)):
                self._por_atributo[clave][valor].add(nodo.id)
    
    def indexar_arista(self, arista: AristaSemantica):
        self._por_tipo_relacion[arista.tipo][arista.origen_id].add(arista.destino_id)
        self._adyacencia_salida[arista.origen_id].add(arista.destino_id)
        self._adyacencia_entrada[arista.destino_id].add(arista.origen_id)
        if arista.tipo in (TipoRelacion.ES_UN, TipoRelacion.INSTANCIA_DE):
            self._jerarquia[arista.origen_id].add(arista.destino_id)
        self._herencia_cache.clear()
        if arista.bidireccional:
            self._adyacencia_salida[arista.destino_id].add(arista.origen_id)
            self._adyacencia_entrada[arista.origen_id].add(arista.destino_id)
    
    def desindexar_nodo(self, nodo: NodoSemantico):
        self._por_tipo_nodo[nodo.tipo].discard(nodo.id)
        self._por_nombre.pop(nodo.nombre.lower().strip(), None)
        self._por_confianza.pop(nodo.id, None)
        self._frecuencias.pop(nodo.id, None)
        self._jerarquia.pop(nodo.id, None)
        self._adyacencia_entrada.pop(nodo.id, None)
        self._adyacencia_salida.pop(nodo.id, None)
        self._herencia_cache.clear()
    
    def desindexar_arista(self, arista: AristaSemantica):
        self._por_tipo_relacion[arista.tipo][arista.origen_id].discard(arista.destino_id)
        self._adyacencia_salida[arista.origen_id].discard(arista.destino_id)
        self._adyacencia_entrada[arista.destino_id].discard(arista.origen_id)
        if arista.tipo in (TipoRelacion.ES_UN, TipoRelacion.INSTANCIA_DE):
            self._jerarquia[arista.origen_id].discard(arista.destino_id)
        self._herencia_cache.clear()
        if arista.bidireccional:
            self._adyacencia_salida[arista.destino_id].discard(arista.origen_id)
            self._adyacencia_entrada[arista.origen_id].discard(arista.destino_id)
    
    def ancestros(self, nodo_id: str) -> Set[str]:
        if nodo_id in self._herencia_cache:
            return self._herencia_cache[nodo_id]
        visitados = set()
        cola = deque([nodo_id])
        while cola:
            actual = cola.popleft()
            for padre in self._jerarquia.get(actual, set()):
                if padre not in visitados:
                    visitados.add(padre)
                    cola.append(padre)
        self._herencia_cache[nodo_id] = visitados
        return visitados
    
    def hereda_de(self, nodo_id: str, ancestro_id: str) -> bool:
        return ancestro_id in self.ancestros(nodo_id)


# =====================================================================
# RAZONADOR SEMÁNTICO
# =====================================================================

class RazonadorSemantico:
    """Motor de inferencia sobre el grafo de conocimiento."""
    
    def __init__(self):
        self._reglas_inferencia: List[Dict] = []
        self._cache_inferencias: Dict[str, Any] = {}
        self._contador_inferencias: int = 0
    
    def agregar_regla(self, nombre: str, condicion: Callable, conclusion: Callable, prioridad: int = 0):
        self._reglas_inferencia.append({
            'nombre': nombre,
            'condicion': condicion,
            'conclusion': conclusion,
            'prioridad': prioridad
        })
        self._reglas_inferencia.sort(key=lambda x: x['prioridad'], reverse=True)
    
    def inferir(self, grafo: Any, nodo_id: str, max_profundidad: int = 3) -> List[Dict]:
        resultados = []
        for regla in self._reglas_inferencia:
            try:
                if regla['condicion'](grafo, nodo_id):
                    conclusion = regla['conclusion'](grafo, nodo_id)
                    if conclusion:
                        resultados.append({
                            'regla': regla['nombre'],
                            'nodo': nodo_id,
                            'conclusion': conclusion
                        })
                        self._contador_inferencias += 1
            except Exception:
                pass
        return resultados
    
    def propagar_herencia(self, grafo: Any, nodo_id: str) -> Dict[str, Any]:
        """Propaga atributos por la jerarquía ES_UN."""
        ancestros = grafo._indice.ancestros(nodo_id)
        atributos_heredados = {}
        relaciones_heredadas = []
        
        for aid in ancestros:
            ancestro = grafo._nodos.get(aid)
            if ancestro:
                for k, v in ancestro.atributos.items():
                    if k not in atributos_heredados:
                        atributos_heredados[k] = v
                for arista_id in grafo._indice._adyacencia_salida.get(aid, set()):
                    arista = grafo._aristas.get(arista_id)
                    if arista and arista.destino_id != nodo_id:
                        relaciones_heredadas.append({
                            'origen': nodo_id,
                            'destino': arista.destino_id,
                            'tipo': arista.tipo.value,
                            'heredado_de': aid
                        })
        
        return {
            'atributos_heredados': atributos_heredados,
            'relaciones_heredadas': relaciones_heredadas,
            'ancestros': list(ancestros)
        }


# =====================================================================
# GRAFO DE CONOCIMIENTO
# =====================================================================

class GrafoConocimiento:
    """Grafo semántico con soporte para ontologías, herencia e inferencia."""
    
    def __init__(self, nombre: str = "ANP-Semantica"):
        self.nombre = nombre
        self._nodos: Dict[str, NodoSemantico] = {}
        self._aristas: Dict[str, AristaSemantica] = {}
        self._ontologias: Dict[str, Ontologia] = {}
        self._indice = IndiceSemantico()
        self._razonador = RazonadorSemantico()
        self._lock = threading.RLock()
        self._estadisticas = {
            'nodos_creados': 0, 'aristas_creadas': 0,
            'inferencias_realizadas': 0, 'consultas_realizadas': 0,
            'ontologias_creadas': 0
        }
        self._inicializar_reglas_base()
    
    def _inicializar_reglas_base(self):
        """Reglas de inferencia fundamentales."""
        
        def regla_transitiva(grafo, nodo_id):
            """Si A es_un B y B es_un C, entonces A es_un C."""
            nuevas = []
            ancestros = grafo._indice.ancestros(nodo_id)
            for aid in list(ancestros):
                abuelos = grafo._indice.ancestros(aid)
                for abuelo in abuelos:
                    if abuelo not in ancestros and abuelo != nodo_id:
                        nuevas.append(abuelo)
            return nuevas if nuevas else None
        
        self._razonador.agregar_regla(
            'transitividad_es_un',
            lambda g, n: True,
            regla_transitiva,
            prioridad=10
        )
        
        def regla_herencia_atributos(grafo, nodo_id):
            """Hereda atributos de ancestros."""
            herencia = grafo._razonador.propagar_herencia(grafo, nodo_id)
            if herencia['atributos_heredados']:
                return herencia
            return None
        
        self._razonador.agregar_regla(
            'herencia_atributos',
            lambda g, n: True,
            regla_herencia_atributos,
            prioridad=9
        )
    
    def agregar_nodo(self, nombre: str, tipo: TipoNodo = TipoNodo.CONCEPTO,
                    atributos: Dict = None, definicion: str = "",
                    embedding: List[float] = None, confianza: float = 1.0,
                    idioma: str = "es") -> Dict[str, Any]:
        with self._lock:
            nombre_norm = nombre.lower().strip()
            if nombre_norm in self._indice._por_nombre:
                existente = self._indice._por_nombre[nombre_norm]
                self._nodos[existente].frecuencia += 1
                return {'exito': True, 'id': existente, 'existente': True, 'nombre': nombre}
            
            nodo = NodoSemantico(
                nombre=nombre, tipo=tipo,
                atributos=atributos or {},
                definicion=definicion,
                embedding=embedding,
                confianza=confianza,
                idioma=idioma
            )
            self._nodos[nodo.id] = nodo
            self._indice.indexar_nodo(nodo)
            self._estadisticas['nodos_creados'] += 1
            return {'exito': True, 'id': nodo.id, 'existente': False, 'nombre': nombre}
    
    def agregar_arista(self, origen_id: str, destino_id: str, tipo: TipoRelacion,
                       peso: float = 0.5, confianza: float = 1.0,
                       bidireccional: bool = False, atributos: Dict = None) -> Dict[str, Any]:
        with self._lock:
            if origen_id not in self._nodos:
                return {'error': f'Nodo origen no encontrado: {origen_id}', 'exito': False}
            if destino_id not in self._nodos:
                return {'error': f'Nodo destino no encontrado: {destino_id}', 'exito': False}
            
            # Verificar duplicados
            for aid, arista in self._aristas.items():
                if (arista.origen_id == origen_id and arista.destino_id == destino_id 
                    and arista.tipo == tipo and arista.activo):
                    arista.peso = (arista.peso + peso) / 2
                    arista.confianza = max(arista.confianza, confianza)
                    return {'exito': True, 'id': aid, 'existente': True}
            
            arista = AristaSemantica(
                origen_id=origen_id, destino_id=destino_id,
                tipo=tipo, peso=peso, confianza=confianza,
                bidireccional=bidireccional,
                atributos=atributos or {}
            )
            self._aristas[arista.id] = arista
            self._indice.indexar_arista(arista)
            self._estadisticas['aristas_creadas'] += 1
            
            # Actualizar frecuencia de nodos conectados
            self._nodos[origen_id].frecuencia += 1
            self._nodos[destino_id].frecuencia += 1
            
            return {'exito': True, 'id': arista.id, 'existente': False}
    
    def obtener_nodo(self, id_o_nombre: str) -> Optional[Dict[str, Any]]:
        nombre_norm = id_o_nombre.lower().strip()
        nodo_id = self._indice._por_nombre.get(nombre_norm, id_o_nombre)
        nodo = self._nodos.get(nodo_id)
        if not nodo:
            return None
        
        ancestros = self._indice.ancestros(nodo.id)
        herencia = self._razonador.propagar_herencia(self, nodo.id)
        
        return {
            'id': nodo.id,
            'nombre': nodo.nombre,
            'tipo': nodo.tipo.value,
            'atributos': nodo.atributos,
            'atributos_heredados': herencia['atributos_heredados'],
            'definicion': nodo.definicion,
            'confianza': nodo.confianza,
            'frecuencia': nodo.frecuencia,
            'ancestros': [self._nodos[a].nombre for a in ancestros if a in self._nodos],
            'idioma': nodo.idioma,
            'version': nodo.version,
            'activo': nodo.activo
        }
    
    def buscar(self, texto: str = None, tipo: TipoNodo = None,
              atributo: str = None, valor: Any = None,
              limite: int = 20) -> List[Dict[str, Any]]:
        self._estadisticas['consultas_realizadas'] += 1
        
        resultados_ids = set(self._nodos.keys())
        
        if tipo:
            resultados_ids &= self._indice._por_tipo_nodo.get(tipo, set())
        
        if texto:
            texto_norm = texto.lower().strip()
            resultados_ids = {nid for nid in resultados_ids 
                            if nid in self._nodos and 
                            (texto_norm in self._nodos[nid].nombre.lower() or
                             texto_norm in self._nodos[nid].definicion.lower())}
        
        if atributo and valor is not None:
            ids_atributo = self._indice._por_atributo.get(atributo, {}).get(valor, set())
            resultados_ids &= ids_atributo
        
        resultados = []
        for nid in list(resultados_ids)[:limite]:
            nodo = self._nodos.get(nid)
            if nodo:
                resultados.append({
                    'id': nodo.id, 'nombre': nodo.nombre,
                    'tipo': nodo.tipo.value, 'confianza': nodo.confianza,
                    'definicion': nodo.definicion[:150]
                })
        
        return resultados
    
    def obtener_relaciones(self, nodo_id: str, direccion: str = 'ambas',
                          tipos: List[TipoRelacion] = None) -> List[Dict[str, Any]]:
        if nodo_id not in self._nodos:
            return []
        
        relaciones = []
        
        if direccion in ('salida', 'ambas'):
            for dest_id in self._indice._adyacencia_salida.get(nodo_id, set()):
                for aid in self._aristas:
                    arista = self._aristas[aid]
                    if arista.origen_id == nodo_id and arista.destino_id == dest_id and arista.activo:
                        if not tipos or arista.tipo in tipos:
                            dest_nombre = self._nodos[dest_id].nombre if dest_id in self._nodos else '?'
                            relaciones.append({
                                'id': arista.id,
                                'direccion': '→',
                                'origen': self._nodos[nodo_id].nombre,
                                'tipo': arista.tipo.value,
                                'destino': dest_nombre,
                                'peso': arista.peso,
                                'confianza': arista.confianza
                            })
        
        if direccion in ('entrada', 'ambas'):
            for orig_id in self._indice._adyacencia_entrada.get(nodo_id, set()):
                for aid in self._aristas:
                    arista = self._aristas[aid]
                    if arista.destino_id == nodo_id and arista.origen_id == orig_id and arista.activo:
                        if not tipos or arista.tipo in tipos:
                            orig_nombre = self._nodos[orig_id].nombre if orig_id in self._nodos else '?'
                            relaciones.append({
                                'id': arista.id,
                                'direccion': '←',
                                'origen': orig_nombre,
                                'tipo': arista.tipo.value,
                                'destino': self._nodos[nodo_id].nombre,
                                'peso': arista.peso,
                                'confianza': arista.confianza
                            })
        
        return relaciones
    
    def camino_mas_corto(self, origen_id: str, destino_id: str,
                         max_profundidad: int = 5) -> Optional[List[Dict]]:
        if origen_id not in self._nodos or destino_id not in self._nodos:
            return None
        
        visitados = {origen_id}
        cola = deque([(origen_id, [])])
        
        while cola:
            actual, camino = cola.popleft()
            if len(camino) >= max_profundidad:
                continue
            
            for vecino in self._indice._adyacencia_salida.get(actual, set()):
                if vecino == destino_id:
                    camino_final = camino + [{
                        'desde': self._nodos[actual].nombre,
                        'hasta': self._nodos[vecino].nombre,
                        'relacion': self._obtener_tipo_relacion(actual, vecino)
                    }]
                    return camino_final
                
                if vecino not in visitados:
                    visitados.add(vecino)
                    nuevo_camino = camino + [{
                        'desde': self._nodos[actual].nombre,
                        'hasta': self._nodos[vecino].nombre,
                        'relacion': self._obtener_tipo_relacion(actual, vecino)
                    }]
                    cola.append((vecino, nuevo_camino))
        
        return None
    
    def _obtener_tipo_relacion(self, origen_id: str, destino_id: str) -> str:
        for arista in self._aristas.values():
            if arista.origen_id == origen_id and arista.destino_id == destino_id and arista.activo:
                return arista.tipo.value
        return "conectado"
    
    def crear_ontologia(self, nombre: str, descripcion: str = "",
                       conceptos_raiz: List[str] = None) -> Dict[str, Any]:
        ont = Ontologia(
            nombre=nombre, descripcion=descripcion,
            conceptos_raiz=conceptos_raiz or []
        )
        self._ontologias[ont.id] = ont
        self._estadisticas['ontologias_creadas'] += 1
        return {'exito': True, 'id': ont.id, 'nombre': nombre}
    
    def consultar_ontologia(self, ontologia_id: str) -> Optional[Dict[str, Any]]:
        ont = self._ontologias.get(ontologia_id)
        if not ont:
            return None
        return {
            'id': ont.id, 'nombre': ont.nombre,
            'descripcion': ont.descripcion,
            'conceptos_raiz': [self._nodos[c].nombre if c in self._nodos else c 
                              for c in ont.conceptos_raiz],
            'total_reglas': len(ont.reglas),
            'total_axiomas': len(ont.axiomas)
        }
    
    def estadisticas(self) -> Dict[str, Any]:
        return {
            'nombre': self.nombre,
            'total_nodos': len(self._nodos),
            'total_aristas': len(self._aristas),
            'total_ontologias': len(self._ontologias),
            'nodos_por_tipo': {t.value: len(ids) for t, ids in self._indice._por_tipo_nodo.items()},
            'aristas_por_tipo': {t.value: sum(len(dests) for dests in origs.values()) 
                                for t, origs in self._indice._por_tipo_relacion.items()},
            'nodos_creados': self._estadisticas['nodos_creados'],
            'aristas_creadas': self._estadisticas['aristas_creadas'],
            'inferencias': self._razonador._contador_inferencias,
            'consultas': self._estadisticas['consultas_realizadas'],
            'ontologias': self._estadisticas['ontologias_creadas']
        }
    
    def guardar(self, ruta: str) -> bool:
        try:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            data = {
                'nombre': self.nombre,
                'nodos': {},
                'aristas': {},
                'ontologias': {},
                'estadisticas': self._estadisticas,
                'version': '0.0.1-NEBULA',
                'timestamp': time.time()
            }
            for nid, nodo in self._nodos.items():
                data['nodos'][nid] = {
                    'id': nodo.id, 'nombre': nodo.nombre, 'tipo': nodo.tipo.value,
                    'atributos': nodo.atributos, 'definicion': nodo.definicion,
                    'embedding': nodo.embedding, 'confianza': nodo.confianza,
                    'frecuencia': nodo.frecuencia,
                    'timestamp_creacion': nodo.timestamp_creacion,
                    'timestamp_actualizacion': nodo.timestamp_actualizacion,
                    'fuentes': nodo.fuentes, 'idioma': nodo.idioma,
                    'version': nodo.version, 'activo': nodo.activo,
                    'metadata': nodo.metadata
                }
            for aid, arista in self._aristas.items():
                data['aristas'][aid] = {
                    'id': arista.id, 'origen_id': arista.origen_id,
                    'destino_id': arista.destino_id, 'tipo': arista.tipo.value,
                    'peso': arista.peso, 'confianza': arista.confianza,
                    'bidireccional': arista.bidireccional,
                    'atributos': arista.atributos,
                    'timestamp_creacion': arista.timestamp_creacion,
                    'fuentes': arista.fuentes, 'activo': arista.activo
                }
            for oid, ont in self._ontologias.items():
                data['ontologias'][oid] = {
                    'id': ont.id, 'nombre': ont.nombre,
                    'descripcion': ont.descripcion,
                    'conceptos_raiz': ont.conceptos_raiz,
                    'reglas': ont.reglas, 'axiomas': ont.axiomas,
                    'metadata': ont.metadata,
                    'timestamp_creacion': ont.timestamp_creacion
                }
            with open(ruta + '.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            return True
        except Exception:
            return False
    
    @classmethod
    def cargar(cls, ruta: str) -> Optional['GrafoConocimiento']:
        try:
            with open(ruta + '.pkl', 'rb') as f:
                data = pickle.load(f)
            grafo = cls(data.get('nombre', 'ANP-Semantica'))
            for nid, ndict in data.get('nodos', {}).items():
                try:
                    tipo = TipoNodo(ndict['tipo'])
                except (ValueError, KeyError):
                    tipo = TipoNodo.CONCEPTO
                nodo = NodoSemantico(
                    id=ndict['id'], nombre=ndict['nombre'], tipo=tipo,
                    atributos=ndict.get('atributos', {}),
                    definicion=ndict.get('definicion', ''),
                    embedding=ndict.get('embedding'),
                    confianza=ndict.get('confianza', 1.0),
                    frecuencia=ndict.get('frecuencia', 0),
                    timestamp_creacion=ndict.get('timestamp_creacion', time.time()),
                    timestamp_actualizacion=ndict.get('timestamp_actualizacion', time.time()),
                    fuentes=ndict.get('fuentes', []),
                    idioma=ndict.get('idioma', 'es'),
                    version=ndict.get('version', 1),
                    activo=ndict.get('activo', True),
                    metadata=ndict.get('metadata', {})
                )
                grafo._nodos[nodo.id] = nodo
                grafo._indice.indexar_nodo(nodo)
            for aid, adict in data.get('aristas', {}).items():
                try:
                    tipo = TipoRelacion(adict['tipo'])
                except (ValueError, KeyError):
                    tipo = TipoRelacion.ASOCIADO
                arista = AristaSemantica(
                    id=adict['id'], origen_id=adict['origen_id'],
                    destino_id=adict['destino_id'], tipo=tipo,
                    peso=adict.get('peso', 0.5), confianza=adict.get('confianza', 1.0),
                    bidireccional=adict.get('bidireccional', False),
                    atributos=adict.get('atributos', {}),
                    timestamp_creacion=adict.get('timestamp_creacion', time.time()),
                    fuentes=adict.get('fuentes', []), activo=adict.get('activo', True)
                )
                grafo._aristas[arista.id] = arista
                grafo._indice.indexar_arista(arista)
            for oid, odict in data.get('ontologias', {}).items():
                ont = Ontologia(
                    id=odict['id'], nombre=odict.get('nombre', ''),
                    descripcion=odict.get('descripcion', ''),
                    conceptos_raiz=odict.get('conceptos_raiz', []),
                    reglas=odict.get('reglas', []), axiomas=odict.get('axiomas', []),
                    metadata=odict.get('metadata', {}),
                    timestamp_creacion=odict.get('timestamp_creacion', time.time())
                )
                grafo._ontologias[ont.id] = ont
            grafo._estadisticas = data.get('estadisticas', grafo._estadisticas)
            return grafo
        except Exception:
            return None


# =====================================================================
# MOTOR SEMÁNTICO PRINCIPAL
# =====================================================================

class MotorSemantico(MotorBase):
    """
    Motor Semántico de ANP — Núcleo de Memoria.
    
    Implementa memoria semántica con:
    - Grafo de conocimiento dirigido con 20 tipos de relaciones
    - Ontologías con reglas y axiomas
    - Herencia de atributos por jerarquía ES_UN
    - Razonador con reglas de inferencia extensibles
    - Búsqueda por nombre, tipo, atributos
    - Navegación de grafos (camino más corto, adyacencia)
    - Índices multidimensionales para consultas O(1)
    - Persistencia completa
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._grafo = GrafoConocimiento("ANP-Semantica")
        self._dir = Path("almacenamiento/semantica")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache_consultas = OrderedDict()
        self._max_cache = 100
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        accion = entrada.get('accion', 'info')
        metodos = {
            'agregar_concepto': self._agregar_concepto,
            'agregar_relacion': self._agregar_relacion,
            'obtener_concepto': self._obtener_concepto,
            'buscar': self._buscar,
            'relaciones': self._relaciones,
            'camino': self._camino,
            'ontologia_crear': self._ontologia_crear,
            'ontologia_consultar': self._ontologia_consultar,
            'estadisticas': self._estadisticas,
            'guardar': self._guardar,
            'cargar': self._cargar,
            'info': self._info,
        }
        func = metodos.get(accion)
        return func(entrada) if func else {'error': f'Acción: {accion}', 'exito': False}
    
    def _agregar_concepto(self, e: Dict) -> Dict[str, Any]:
        try:
            tipo_str = e.get('tipo', 'concepto')
            try:
                tipo = TipoNodo(tipo_str)
            except ValueError:
                tipo = TipoNodo.CONCEPTO
            return self._grafo.agregar_nodo(
                nombre=e.get('nombre', ''),
                tipo=tipo,
                atributos=e.get('atributos', {}),
                definicion=e.get('definicion', ''),
                embedding=e.get('embedding'),
                confianza=e.get('confianza', 1.0),
                idioma=e.get('idioma', 'es')
            )
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _agregar_relacion(self, e: Dict) -> Dict[str, Any]:
        try:
            tipo_str = e.get('tipo', 'asociado')
            try:
                tipo = TipoRelacion(tipo_str)
            except ValueError:
                tipo = TipoRelacion.ASOCIADO
            
            origen = e.get('origen_id', e.get('origen', ''))
            destino = e.get('destino_id', e.get('destino', ''))
            
            if not origen or not destino:
                return {'error': 'origen_id y destino_id requeridos', 'exito': False}
            
            return self._grafo.agregar_arista(
                origen_id=origen, destino_id=destino,
                tipo=tipo, peso=e.get('peso', 0.5),
                confianza=e.get('confianza', 1.0),
                bidireccional=e.get('bidireccional', False),
                atributos=e.get('atributos', {})
            )
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _obtener_concepto(self, e: Dict) -> Dict[str, Any]:
        id_o_nombre = e.get('id', e.get('nombre', ''))
        if not id_o_nombre:
            return {'error': 'ID o nombre requerido', 'exito': False}
        resultado = self._grafo.obtener_nodo(id_o_nombre)
        if not resultado:
            return {'error': f'Concepto no encontrado: {id_o_nombre}', 'exito': False}
        return {'exito': True, 'concepto': resultado}
    
    def _buscar(self, e: Dict) -> Dict[str, Any]:
        tipo_str = e.get('tipo')
        tipo = None
        if tipo_str:
            try:
                tipo = TipoNodo(tipo_str)
            except ValueError:
                pass
        
        resultados = self._grafo.buscar(
            texto=e.get('texto'),
            tipo=tipo,
            atributo=e.get('atributo'),
            valor=e.get('valor'),
            limite=e.get('limite', 20)
        )
        return {'exito': True, 'total': len(resultados), 'resultados': resultados}
    
    def _relaciones(self, e: Dict) -> Dict[str, Any]:
        nodo_id = e.get('id', '')
        if not nodo_id:
            return {'error': 'ID de nodo requerido', 'exito': False}
        
        tipos_str = e.get('tipos')
        tipos = None
        if tipos_str:
            try:
                tipos = [TipoRelacion(t) for t in tipos_str] if isinstance(tipos_str, list) else None
            except ValueError:
                pass
        
        rels = self._grafo.obtener_relaciones(nodo_id, e.get('direccion', 'ambas'), tipos)
        return {'exito': True, 'total': len(rels), 'relaciones': rels}
    
    def _camino(self, e: Dict) -> Dict[str, Any]:
        origen = e.get('origen', '')
        destino = e.get('destino', '')
        if not origen or not destino:
            return {'error': 'origen y destino requeridos', 'exito': False}
        
        camino = self._grafo.camino_mas_corto(origen, destino, e.get('max_profundidad', 5))
        if camino is None:
            return {'exito': False, 'error': 'Sin camino encontrado'}
        return {'exito': True, 'longitud': len(camino), 'camino': camino}
    
    def _ontologia_crear(self, e: Dict) -> Dict[str, Any]:
        return self._grafo.crear_ontologia(
            nombre=e.get('nombre', ''),
            descripcion=e.get('descripcion', ''),
            conceptos_raiz=e.get('conceptos_raiz', [])
        )
    
    def _ontologia_consultar(self, e: Dict) -> Dict[str, Any]:
        resultado = self._grafo.consultar_ontologia(e.get('id', ''))
        if not resultado:
            return {'error': 'Ontología no encontrada', 'exito': False}
        return {'exito': True, 'ontologia': resultado}
    
    def _estadisticas(self, e: Dict) -> Dict[str, Any]:
        stats = self._grafo.estadisticas()
        stats['exito'] = True
        return stats
    
    def _guardar(self, e: Dict) -> Dict[str, Any]:
        ruta = e.get('ruta', str(self._dir / 'memoria_semantica'))
        if ruta.endswith('.pkl'): ruta = ruta[:-4]
        return {'exito': self._grafo.guardar(ruta), 'ruta': ruta + '.pkl'}
    
    def _cargar(self, e: Dict) -> Dict[str, Any]:
        ruta = e.get('ruta', '')
        if ruta.endswith('.pkl'): ruta = ruta[:-4]
        if not Path(ruta + '.pkl').exists():
            return {'error': f'Archivo no encontrado: {ruta}.pkl', 'exito': False}
        grafo = GrafoConocimiento.cargar(ruta)
        if grafo:
            self._grafo = grafo
            return {'exito': True, 'nodos': len(grafo._nodos), 'aristas': len(grafo._aristas)}
        return {'error': 'Error cargando', 'exito': False}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        stats = self._grafo.estadisticas()
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'grafo': self._grafo.nombre,
            'total_nodos': stats['total_nodos'],
            'total_aristas': stats['total_aristas'],
            'total_ontologias': stats['total_ontologias'],
            'tipos_relaciones': [t.value for t in TipoRelacion],
            'tipos_nodos': [t.value for t in TipoNodo]
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR SEMÁNTICO — GRAFO DE CONOCIMIENTO")
    print("=" * 70)
    motor = None
    try:
        print("\n[0] Inicializando...")
        motor = MotorSemantico()
        motor.inicializar()
        print(f"  ✅ Motor: {motor.nombre} | Estado: {motor.estado}")

        print("\n[1] Creando conceptos...")
        conceptos = [
            {'nombre': 'animal', 'tipo': 'categoria', 'definicion': 'Ser vivo heterótrofo multicelular'},
            {'nombre': 'mamifero', 'tipo': 'categoria', 'definicion': 'Animal de sangre caliente con pelo'},
            {'nombre': 'perro', 'tipo': 'concepto', 'definicion': 'Mamífero doméstico de la familia Canidae'},
            {'nombre': 'gato', 'tipo': 'concepto', 'definicion': 'Mamífero doméstico de la familia Felidae'},
            {'nombre': 'felino', 'tipo': 'categoria', 'definicion': 'Mamífero de la familia Felidae'},
            {'nombre': 'canino', 'tipo': 'categoria', 'definicion': 'Mamífero de la familia Canidae'},
            {'nombre': 'vertebrado', 'tipo': 'categoria', 'definicion': 'Animal con columna vertebral'},
            {'nombre': 'mascota', 'tipo': 'concepto', 'definicion': 'Animal de compañía'},
            {'nombre': 'domestico', 'tipo': 'atributo', 'definicion': 'Adaptado a vivir con humanos'},
            {'nombre': 'salvaje', 'tipo': 'atributo', 'definicion': 'No domesticado'},
            {'nombre': 'leon', 'tipo': 'concepto', 'definicion': 'Gran felino salvaje africano'},
            {'nombre': 'tigre', 'tipo': 'concepto', 'definicion': 'Gran felino salvaje asiático'},
        ]
        ids = {}
        for c in conceptos:
            r = motor.procesar({'accion': 'agregar_concepto', **c})
            if r.exito and r.datos and r.datos.get('exito'):
                ids[c['nombre']] = r.datos['id']
                estado = '🔄' if r.datos.get('existente') else '✅'
                print(f"  {estado} {c['nombre']}: {c['definicion'][:50]}...")
        
        print(f"\n[2] Creando relaciones jerárquicas...")
        relaciones = [
            ('mamifero', 'animal', 'es_un'),
            ('vertebrado', 'animal', 'es_un'),
            ('perro', 'canino', 'es_un'),
            ('gato', 'felino', 'es_un'),
            ('canino', 'mamifero', 'es_un'),
            ('felino', 'mamifero', 'es_un'),
            ('perro', 'domestico', 'es_un'),
            ('gato', 'domestico', 'es_un'),
            ('leon', 'salvaje', 'es_un'),
            ('tigre', 'salvaje', 'es_un'),
            ('leon', 'felino', 'es_un'),
            ('tigre', 'felino', 'es_un'),
            ('perro', 'mascota', 'es_un'),
            ('gato', 'mascota', 'es_un'),
        ]
        for orig, dest, tipo in relaciones:
            if orig in ids and dest in ids:
                r = motor.procesar({
                    'accion': 'agregar_relacion',
                    'origen_id': ids[orig], 'destino_id': ids[dest],
                    'tipo': tipo, 'peso': 0.9, 'confianza': 1.0
                })
                if r.exito and r.datos:
                    ok = '🔄' if r.datos.get('existente') else '✅'
                    print(f"  {ok} {orig} → {dest} ({tipo})")

        print(f"\n[3] Creando ontología...")
        r = motor.procesar({
            'accion': 'ontologia_crear',
            'nombre': 'Taxonomía Animal',
            'descripcion': 'Clasificación biológica de animales comunes',
            'conceptos_raiz': [ids['animal']]
        })
        if r.exito and r.datos:
            print(f"  ✅ Ontología: {r.datos['nombre']} (ID: {r.datos['id'][:8]}...)")

        print(f"\n[4] Consultando concepto 'perro':")
        r = motor.procesar({'accion': 'obtener_concepto', 'id': ids['perro']})
        if r.exito and r.datos:
            c = r.datos['concepto']
            print(f"  📋 {c['nombre']}: {c['definicion']}")
            print(f"  📋 Tipo: {c['tipo']} | Confianza: {c['confianza']}")
            print(f"  📋 Ancestros: {c['ancestros']}")
            print(f"  📋 Atributos heredados: {c['atributos_heredados']}")

        print(f"\n[5] Buscando 'felino':")
        r = motor.procesar({'accion': 'buscar', 'texto': 'felino'})
        if r.exito and r.datos:
            for res in r.datos['resultados']:
                print(f"  🔍 {res['nombre']} [{res['tipo']}]: {res['definicion'][:60]}")

        print(f"\n[6] Relaciones de 'perro':")
        r = motor.procesar({'accion': 'relaciones', 'id': ids['perro']})
        if r.exito and r.datos:
            for rel in r.datos['relaciones'][:5]:
                print(f"  🔗 {rel['direccion']} {rel['tipo']}: {rel['origen']} → {rel['destino']}")

        print(f"\n[7] Camino más corto 'gato' → 'animal':")
        r = motor.procesar({'accion': 'camino', 'origen': ids['gato'], 'destino': ids['animal']})
        if r.exito and r.datos:
            for paso in r.datos['camino']:
                print(f"  🛤️ {paso['desde']} → {paso['hasta']} ({paso['relacion']})")

        print(f"\n[8] Estadísticas:")
        r = motor.procesar({'accion': 'estadisticas'})
        if r.exito and r.datos:
            stats = r.datos
            print(f"  📊 Nodos: {stats['total_nodos']} | Aristas: {stats['total_aristas']} | "
                  f"Ontologías: {stats['total_ontologias']}")

        ruta = 'almacenamiento/semantica/memoria_test'
        print(f"\n[9] Guardar: {'✅' if motor.procesar({'accion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")

        rc = motor.procesar({'accion':'cargar','ruta':ruta})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[10] Cargar: {'✅' if ok else '❌'} "
              f"({rc.datos.get('nodos','?') if ok else ''} nodos, "
              f"{rc.datos.get('aristas','?') if ok else ''} aristas)")

        if ok:
            rv = motor.procesar({'accion':'obtener_concepto','id':ids['leon']})
            if rv.exito and rv.datos:
                c = rv.datos['concepto']
                print(f"[11] Verificación post-carga: {c['nombre']} | Ancestros: {c['ancestros']}")

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