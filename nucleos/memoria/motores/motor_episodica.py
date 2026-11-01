#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Episódico — Memoria de Experiencias con Timestamp
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, json, hashlib, uuid, traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, OrderedDict, deque
from enum import Enum
from datetime import datetime, timedelta
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
# ESTRUCTURAS DE DATOS
# =====================================================================

class TipoEpisodio(Enum):
    CONVERSACION = "conversacion"
    APRENDIZAJE = "aprendizaje"
    ERROR = "error"
    LOGRO = "logro"
    OBSERVACION = "observacion"
    DECISION = "decision"
    REFLEXION = "reflexion"
    SISTEMA = "sistema"
    PERSONALIZADO = "personalizado"

class IntensidadEmocional(Enum):
    NEUTRA = 0.0
    LEVE = 0.25
    MODERADA = 0.5
    FUERTE = 0.75
    INTENSA = 1.0

class EstadoEpisodio(Enum):
    ACTIVO = "activo"
    ARCHIVADO = "archivado"
    CONSOLIDADO = "consolidado"
    OLVIDADO = "olvidado"

@dataclass
class Episodio:
    """Estructura central de un episodio en la memoria."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    timestamp_str: str = ""
    tipo: TipoEpisodio = TipoEpisodio.OBSERVACION
    contenido: Dict[str, Any] = field(default_factory=dict)
    resumen: str = ""
    contexto: Dict[str, Any] = field(default_factory=dict)
    emocion: IntensidadEmocional = IntensidadEmocional.NEUTRA
    importancia: float = 0.5
    etiquetas: List[str] = field(default_factory=list)
    entidades: List[str] = field(default_factory=list)
    relaciones: List[Tuple[str, str, str]] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    estado: EstadoEpisodio = EstadoEpisodio.ACTIVO
    acceso_count: int = 0
    ultimo_acceso: float = 0.0
    consolidacion_count: int = 0
    olvido_factor: float = 1.0
    version: int = 1
    padre_id: Optional[str] = None
    hijos_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp_str:
            self.timestamp_str = datetime.fromtimestamp(self.timestamp).isoformat()
        if not self.ultimo_acceso:
            self.ultimo_acceso = self.timestamp

@dataclass
class ContextoEpisodico:
    """Contexto compartido entre episodios relacionados."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    episodios_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_actualizacion: float = field(default_factory=time.time)

# =====================================================================
# ÍNDICES AVANZADOS
# =====================================================================

class IndiceEpisodico:
    """Índices multidimensionales para búsqueda ultra-rápida."""
    
    def __init__(self):
        self._por_tipo: Dict[TipoEpisodio, List[str]] = defaultdict(list)
        self._por_etiqueta: Dict[str, List[str]] = defaultdict(list)
        self._por_entidad: Dict[str, List[str]] = defaultdict(list)
        self._por_emocion: Dict[IntensidadEmocional, List[str]] = defaultdict(list)
        self._por_estado: Dict[EstadoEpisodio, List[str]] = defaultdict(list)
        self._por_importancia: Dict[str, List[str]] = defaultdict(list)
        self._por_fecha: Dict[str, List[str]] = defaultdict(list)
        self._por_padre: Dict[str, List[str]] = defaultdict(list)
        self._temporal: List[Tuple[float, str]] = []
        self._accesos: Dict[str, int] = {}
        self._embeddings_cache: Optional[Dict[str, np.ndarray]] = None
    
    def indexar(self, ep: Episodio):
        eid = ep.id
        self._por_tipo[ep.tipo].append(eid)
        for et in ep.etiquetas:
            self._por_etiqueta[et].append(eid)
        for ent in ep.entidades:
            self._por_entidad[ent].append(eid)
        self._por_emocion[ep.emocion].append(eid)
        self._por_estado[ep.estado].append(eid)
        imp = "alta" if ep.importancia > 0.7 else "media" if ep.importancia > 0.3 else "baja"
        self._por_importancia[imp].append(eid)
        fecha = datetime.fromtimestamp(ep.timestamp).strftime("%Y-%m-%d")
        self._por_fecha[fecha].append(eid)
        if ep.padre_id:
            self._por_padre[ep.padre_id].append(eid)
        self._temporal.append((ep.timestamp, eid))
        self._accesos[eid] = ep.acceso_count
    
    def desindexar(self, ep: Episodio):
        eid = ep.id
        self._por_tipo[ep.tipo].remove(eid)
        for et in ep.etiquetas:
            if eid in self._por_etiqueta[et]:
                self._por_etiqueta[et].remove(eid)
        for ent in ep.entidades:
            if eid in self._por_entidad[ent]:
                self._por_entidad[ent].remove(eid)
        self._por_emocion[ep.emocion].remove(eid)
        self._por_estado[ep.estado].remove(eid)
        imp = "alta" if ep.importancia > 0.7 else "media" if ep.importancia > 0.3 else "baja"
        if eid in self._por_importancia[imp]:
            self._por_importancia[imp].remove(eid)
        self._temporal = [(t, e) for t, e in self._temporal if e != eid]
        self._accesos.pop(eid, None)
    
    def ordenar_temporal(self):
        self._temporal.sort(key=lambda x: x[0])
    
    def obtener_por_ventana(self, inicio: float, fin: float) -> List[str]:
        return [eid for t, eid in self._temporal if inicio <= t <= fin]


# =====================================================================
# MECANISMO DE OLVIDO
# =====================================================================

class MecanismoOlvido:
    """
    Implementa la curva de olvido de Ebbinghaus modificada:
    R = e^(-t/S) donde S = importancia * repeticiones^0.5
    
    También incorpora:
    - Interferencia retroactiva (episodios similares compiten)
    - Consolidación por repetición espaciada
    - Decaimiento emocional
    """
    
    def __init__(self, umbral_olvido: float = 0.05, tasa_base: float = 0.1):
        self.umbral_olvido = umbral_olvido
        self.tasa_base = tasa_base
        self._historial_olvidos: List[Dict] = []
    
    def calcular_factor_olvido(self, ep: Episodio, tiempo_actual: float = None) -> float:
        if tiempo_actual is None:
            tiempo_actual = time.time()
        
        antiguedad = max(0, tiempo_actual - ep.timestamp)
        antiguedad_dias = antiguedad / 86400.0
        
        # Fuerza de la memoria basada en accesos y consolidación
        fuerza = ep.importancia * (1 + ep.acceso_count * 0.3) * (1 + ep.consolidacion_count * 0.15)
        fuerza = max(0.01, min(fuerza, 10.0))
        
        # Curva de olvido
        olvido = math.exp(-antiguedad_dias / (fuerza * 7.0))
        
        # Factor emocional (emociones fuertes se olvidan más lento)
        factor_emocional = 1.0 - ep.emocion.value * 0.5
        
        # Factor de interferencia (muchos episodios similares aceleran olvido)
        factor_interferencia = min(1.0, len(ep.etiquetas) * 0.02)
        
        resultado = olvido * factor_emocional * (1.0 + factor_interferencia)
        return max(0.0, min(1.0, resultado))
    
    def debe_olvidar(self, ep: Episodio) -> bool:
        factor = self.calcular_factor_olvido(ep)
        ep.olvido_factor = factor
        return factor < self.umbral_olvido
    
    def consolidar(self, ep: Episodio) -> float:
        """Consolida un episodio, reforzándolo."""
        ep.consolidacion_count += 1
        ganancia = 0.1 * (1.0 / (1 + ep.consolidacion_count))
        ep.importancia = min(1.0, ep.importancia + ganancia)
        return ep.importancia


# =====================================================================
# SIMILITUD SEMÁNTICA ENTRE EPISODIOS
# =====================================================================

class SimilitudEpisodica:
    """Calcula similitud entre episodios usando múltiples métricas."""
    
    @staticmethod
    def jaccard_etiquetas(ep1: Episodio, ep2: Episodio) -> float:
        s1, s2 = set(ep1.etiquetas), set(ep2.etiquetas)
        if not s1 and not s2:
            return 0.0
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return inter / union if union > 0 else 0.0
    
    @staticmethod
    def jaccard_entidades(ep1: Episodio, ep2: Episodio) -> float:
        s1, s2 = set(ep1.entidades), set(ep2.entidades)
        if not s1 and not s2:
            return 0.0
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return inter / union if union > 0 else 0.0
    
    @staticmethod
    def coseno_embeddings(ep1: Episodio, ep2: Episodio) -> float:
        if not ep1.embedding or not ep2.embedding:
            return 0.0
        if not NUMPY_DISPONIBLE:
            return 0.0
        v1 = np.array(ep1.embedding)
        v2 = np.array(ep2.embedding)
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-12 or n2 < 1e-12:
            return 0.0
        return float(np.dot(v1, v2) / (n1 * n2))
    
    @staticmethod
    def similitud_temporal(ep1: Episodio, ep2: Episodio) -> float:
        diff = abs(ep1.timestamp - ep2.timestamp)
        return math.exp(-diff / 3600.0)
    
    @staticmethod
    def similitud_compuesta(ep1: Episodio, ep2: Episodio,
                           pesos: Dict[str, float] = None) -> float:
        if pesos is None:
            pesos = {'etiquetas': 0.3, 'entidades': 0.25, 'embedding': 0.3, 'temporal': 0.15}
        
        score = 0.0
        score += SimilitudEpisodica.jaccard_etiquetas(ep1, ep2) * pesos.get('etiquetas', 0)
        score += SimilitudEpisodica.jaccard_entidades(ep1, ep2) * pesos.get('entidades', 0)
        score += SimilitudEpisodica.coseno_embeddings(ep1, ep2) * pesos.get('embedding', 0)
        score += SimilitudEpisodica.similitud_temporal(ep1, ep2) * pesos.get('temporal', 0)
        return min(1.0, max(0.0, score))


# =====================================================================
# MOTOR EPISÓDICO PRINCIPAL
# =====================================================================

class MotorEpisodico(MotorBase):
    """
    Motor Episódico de ANP — Núcleo de Memoria.
    
    Implementa memoria episódica con:
    - Almacenamiento estructurado de experiencias
    - Indexación multidimensional para búsqueda O(log n)
    - Mecanismo de olvido basado en Ebbinghaus
    - Similitud semántica entre episodios
    - Consolidación por repetición espaciada
    - Contextos compartidos entre episodios
    - Persistencia completa con serialización eficiente
    - Búsqueda por ventana temporal, etiquetas, entidades, importancia
    - Encadenamiento de episodios (padre-hijo)
    - Métricas de memoria (capacidad, tasa de olvido, acceso)
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._episodios: Dict[str, Episodio] = {}
        self._contextos: Dict[str, ContextoEpisodico] = {}
        self._indice = IndiceEpisodico()
        self._olvido = MecanismoOlvido()
        self._similitud = SimilitudEpisodica()
        self._lock = threading.RLock()
        self._max_episodios = 100000
        self._max_contextos = 10000
        self._estadisticas = {
            'total_creados': 0, 'total_olvidados': 0, 'total_consolidados': 0,
            'total_accesos': 0, 'total_busquedas': 0, 'total_contextos': 0,
            'memoria_bytes': 0, 'ultimo_mantenimiento': 0.0
        }
        self._dir = Path("almacenamiento/episodica")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        accion = entrada.get('accion', 'info')
        with self._lock:
            metodos = {
                'registrar': self._registrar,
                'recuperar': self._recuperar,
                'buscar': self._buscar,
                'actualizar': self._actualizar,
                'olvidar': self._olvidar_episodios,
                'consolidar': self._consolidar,
                'encadenar': self._encadenar,
                'contexto_crear': self._contexto_crear,
                'contexto_vincular': self._contexto_vincular,
                'similares': self._similares,
                'estadisticas': self._estadisticas,
                'mantenimiento': self._mantenimiento,
                'guardar': self._guardar,
                'cargar': self._cargar,
                'info': self._info,
            }
            func = metodos.get(accion)
            if func:
                resultado = func(entrada)
                self._estadisticas['total_accesos'] += 1
                return resultado
            return {'error': f'Acción desconocida: {accion}', 'exito': False}

    def _registrar(self, e: Dict) -> Dict[str, Any]:
        """Registra un nuevo episodio en la memoria."""
        if len(self._episodios) >= self._max_episodios:
            self._mantenimiento({'forzar': True})
            if len(self._episodios) >= self._max_episodios:
                return {'error': 'Memoria llena', 'exito': False}
        
        try:
            tipo_str = e.get('tipo', 'observacion')
            try:
                tipo = TipoEpisodio(tipo_str)
            except ValueError:
                tipo = TipoEpisodio.PERSONALIZADO
            
            emocion_val = e.get('emocion', 0.0)
            emocion = IntensidadEmocional.NEUTRA
            for ie in IntensidadEmocional:
                if abs(ie.value - emocion_val) < 0.01:
                    emocion = ie
                    break
            
            ep = Episodio(
                timestamp=e.get('timestamp', time.time()),
                tipo=tipo,
                contenido=e.get('contenido', {}),
                resumen=e.get('resumen', str(e.get('contenido', ''))[:200]),
                contexto=e.get('contexto', {}),
                emocion=emocion,
                importancia=float(e.get('importancia', 0.5)),
                etiquetas=e.get('etiquetas', []),
                entidades=e.get('entidades', []),
                relaciones=e.get('relaciones', []),
                embedding=e.get('embedding', None),
                estado=EstadoEpisodio.ACTIVO,
                padre_id=e.get('padre_id', None)
            )
            
            ep.timestamp_str = datetime.fromtimestamp(ep.timestamp).isoformat()
            
            self._episodios[ep.id] = ep
            self._indice.indexar(ep)
            self._estadisticas['total_creados'] += 1
            
            if ep.padre_id and ep.padre_id in self._episodios:
                self._episodios[ep.padre_id].hijos_ids.append(ep.id)
            
            return {
                'exito': True,
                'id': ep.id,
                'timestamp': ep.timestamp_str,
                'tipo': ep.tipo.value,
                'total_episodios': len(self._episodios)
            }
        except Exception as ex:
            return {'error': f'Error registrando: {str(ex)}', 'exito': False}

    def _recuperar(self, e: Dict) -> Dict[str, Any]:
        """Recupera un episodio por ID."""
        eid = e.get('id', '')
        if not eid or eid not in self._episodios:
            return {'error': f'Episodio no encontrado: {eid}', 'exito': False}
        
        ep = self._episodios[eid]
        ep.acceso_count += 1
        ep.ultimo_acceso = time.time()
        self._indice._accesos[eid] = ep.acceso_count
        
        return {
            'exito': True,
            'episodio': {
                'id': ep.id,
                'timestamp': ep.timestamp_str,
                'tipo': ep.tipo.value,
                'contenido': ep.contenido,
                'resumen': ep.resumen,
                'contexto': ep.contexto,
                'emocion': ep.emocion.value,
                'importancia': ep.importancia,
                'etiquetas': ep.etiquetas,
                'entidades': ep.entidades,
                'relaciones': ep.relaciones,
                'estado': ep.estado.value,
                'acceso_count': ep.acceso_count,
                'consolidacion_count': ep.consolidacion_count,
                'olvido_factor': round(ep.olvido_factor, 4),
                'hijos_ids': ep.hijos_ids,
                'padre_id': ep.padre_id
            }
        }

    def _buscar(self, e: Dict) -> Dict[str, Any]:
        """Búsqueda avanzada por múltiples criterios."""
        self._estadisticas['total_busquedas'] += 1
        
        resultado_ids = set(self._episodios.keys())
        
        # Filtrar por tipo
        if 'tipo' in e:
            try:
                tipo = TipoEpisodio(e['tipo'])
                resultado_ids &= set(self._indice._por_tipo.get(tipo, []))
            except ValueError:
                pass
        
        # Filtrar por etiquetas
        if 'etiquetas' in e:
            ets = e['etiquetas'] if isinstance(e['etiquetas'], list) else [e['etiquetas']]
            for et in ets:
                resultado_ids &= set(self._indice._por_etiqueta.get(et, []))
        
        # Filtrar por entidades
        if 'entidades' in e:
            ents = e['entidades'] if isinstance(e['entidades'], list) else [e['entidades']]
            for ent in ents:
                resultado_ids &= set(self._indice._por_entidad.get(ent, []))
        
        # Filtrar por estado
        if 'estado' in e:
            try:
                estado = EstadoEpisodio(e['estado'])
                resultado_ids &= set(self._indice._por_estado.get(estado, []))
            except ValueError:
                pass
        
        # Filtrar por importancia mínima
        if 'importancia_min' in e:
            imp_min = float(e['importancia_min'])
            resultado_ids = {eid for eid in resultado_ids 
                           if eid in self._episodios and self._episodios[eid].importancia >= imp_min}
        
        # Filtrar por ventana temporal
        if 'desde' in e or 'hasta' in e:
            desde = e.get('desde', 0.0)
            hasta = e.get('hasta', time.time())
            if isinstance(desde, str):
                desde = datetime.fromisoformat(desde).timestamp()
            if isinstance(hasta, str):
                hasta = datetime.fromisoformat(hasta).timestamp()
            ids_temporales = set(self._indice.obtener_por_ventana(desde, hasta))
            resultado_ids &= ids_temporales
        
        # Filtrar por texto en resumen o contenido
        if 'texto' in e:
            texto = e['texto'].lower()
            resultado_ids = {eid for eid in resultado_ids if eid in self._episodios and
                           (texto in self._episodios[eid].resumen.lower() or
                            texto in str(self._episodios[eid].contenido).lower())}
        
        # Limitar y ordenar
        limite = e.get('limite', 50)
        orden = e.get('orden', 'reciente')
        
        resultados = list(resultado_ids)
        if orden == 'reciente':
            resultados.sort(key=lambda x: self._episodios[x].timestamp, reverse=True)
        elif orden == 'importante':
            resultados.sort(key=lambda x: self._episodios[x].importancia, reverse=True)
        elif orden == 'accedido':
            resultados.sort(key=lambda x: self._episodios[x].acceso_count, reverse=True)
        
        resultados = resultados[:limite]
        
        return {
            'exito': True,
            'total_encontrados': len(resultado_ids),
            'mostrados': len(resultados),
            'resultados': [self._recuperar({'id': eid})['episodio'] for eid in resultados]
        }

    def _actualizar(self, e: Dict) -> Dict[str, Any]:
        """Actualiza un episodio existente."""
        eid = e.get('id', '')
        if not eid or eid not in self._episodios:
            return {'error': f'Episodio no encontrado: {eid}', 'exito': False}
        
        ep = self._episodios[eid]
        self._indice.desindexar(ep)
        
        if 'contenido' in e:
            ep.contenido = e['contenido']
        if 'resumen' in e:
            ep.resumen = e['resumen']
        if 'contexto' in e:
            ep.contexto = e['contexto']
        if 'importancia' in e:
            ep.importancia = float(e['importancia'])
        if 'etiquetas' in e:
            ep.etiquetas = e['etiquetas']
        if 'entidades' in e:
            ep.entidades = e['entidades']
        if 'relaciones' in e:
            ep.relaciones = e['relaciones']
        if 'estado' in e:
            try:
                ep.estado = EstadoEpisodio(e['estado'])
            except ValueError:
                pass
        if 'embedding' in e:
            ep.embedding = e['embedding']
        
        ep.version += 1
        
        self._indice.indexar(ep)
        return {'exito': True, 'id': eid, 'version': ep.version}

    def _olvidar_episodios(self, e: Dict) -> Dict[str, Any]:
        """Ejecuta el mecanismo de olvido sobre todos los episodios activos."""
        ahora = time.time()
        olvidados = []
        
        for eid, ep in list(self._episodios.items()):
            if ep.estado == EstadoEpisodio.OLVIDADO:
                continue
            if self._olvido.debe_olvidar(ep):
                ep.estado = EstadoEpisodio.OLVIDADO
                self._indice._por_estado[EstadoEpisodio.ACTIVO].remove(eid)
                self._indice._por_estado[EstadoEpisodio.OLVIDADO].append(eid)
                olvidados.append(eid)
                self._estadisticas['total_olvidados'] += 1
                self._olvido._historial_olvidos.append({
                    'id': eid, 'timestamp': ahora, 'factor': ep.olvido_factor,
                    'importancia': ep.importancia, 'accesos': ep.acceso_count
                })
        
        return {'exito': True, 'olvidados': len(olvidados), 'ids': olvidados[:20]}

    def _consolidar(self, e: Dict) -> Dict[str, Any]:
        """Consolida episodios accedidos frecuentemente."""
        eid = e.get('id', '')
        umbral_accesos = e.get('umbral_accesos', 5)
        
        if eid:
            if eid not in self._episodios:
                return {'error': f'Episodio no encontrado: {eid}', 'exito': False}
            ep = self._episodios[eid]
            nueva_imp = self._olvido.consolidar(ep)
            self._estadisticas['total_consolidados'] += 1
            return {'exito': True, 'id': eid, 'nueva_importancia': round(nueva_imp, 4)}
        else:
            consolidados = 0
            for epid, ep in self._episodios.items():
                if ep.acceso_count >= umbral_accesos and ep.estado == EstadoEpisodio.ACTIVO:
                    self._olvido.consolidar(ep)
                    consolidados += 1
            self._estadisticas['total_consolidados'] += consolidados
            return {'exito': True, 'consolidados': consolidados}

    def _encadenar(self, e: Dict) -> Dict[str, Any]:
        """Crea relación padre-hijo entre episodios."""
        padre_id = e.get('padre_id', '')
        hijo_id = e.get('hijo_id', '')
        
        if padre_id not in self._episodios:
            return {'error': f'Padre no encontrado: {padre_id}', 'exito': False}
        if hijo_id not in self._episodios:
            return {'error': f'Hijo no encontrado: {hijo_id}', 'exito': False}
        
        self._episodios[hijo_id].padre_id = padre_id
        self._episodios[padre_id].hijos_ids.append(hijo_id)
        self._indice._por_padre[padre_id].append(hijo_id)
        
        return {'exito': True, 'padre': padre_id, 'hijo': hijo_id}

    def _contexto_crear(self, e: Dict) -> Dict[str, Any]:
        """Crea un contexto compartido para agrupar episodios."""
        if len(self._contextos) >= self._max_contextos:
            return {'error': 'Máximo contextos alcanzado', 'exito': False}
        
        ctx = ContextoEpisodico(
            nombre=e.get('nombre', f'contexto_{len(self._contextos)+1}'),
            metadata=e.get('metadata', {})
        )
        self._contextos[ctx.id] = ctx
        self._estadisticas['total_contextos'] += 1
        return {'exito': True, 'id': ctx.id, 'nombre': ctx.nombre}

    def _contexto_vincular(self, e: Dict) -> Dict[str, Any]:
        """Vincula episodios a un contexto."""
        ctx_id = e.get('contexto_id', '')
        ep_ids = e.get('episodios_ids', [])
        
        if ctx_id not in self._contextos:
            return {'error': f'Contexto no encontrado: {ctx_id}', 'exito': False}
        
        vinculados = 0
        for eid in ep_ids:
            if eid in self._episodios:
                self._contextos[ctx_id].episodios_ids.append(eid)
                self._contextos[ctx_id].timestamp_actualizacion = time.time()
                vinculados += 1
        
        return {'exito': True, 'vinculados': vinculados, 'contexto_id': ctx_id}

    def _similares(self, e: Dict) -> Dict[str, Any]:
        """Encuentra episodios similares a uno dado."""
        eid = e.get('id', '')
        if not eid or eid not in self._episodios:
            return {'error': f'Episodio no encontrado: {eid}', 'exito': False}
        
        ep_base = self._episodios[eid]
        limite = e.get('limite', 10)
        pesos = e.get('pesos', None)
        
        similitudes = []
        for other_id, other_ep in self._episodios.items():
            if other_id == eid:
                continue
            if other_ep.estado == EstadoEpisodio.OLVIDADO:
                continue
            sim = self._similitud.similitud_compuesta(ep_base, other_ep, pesos)
            if sim > 0.1:
                similitudes.append((other_id, sim))
        
        similitudes.sort(key=lambda x: x[1], reverse=True)
        similitudes = similitudes[:limite]
        
        return {
            'exito': True,
            'id': eid,
            'similares': [{'id': sid, 'similitud': round(s, 4),
                          'resumen': self._episodios[sid].resumen[:100]} 
                         for sid, s in similitudes]
        }

    def _estadisticas(self, e: Dict) -> Dict[str, Any]:
        """Retorna estadísticas completas de la memoria."""
        ahora = time.time()
        activos = sum(1 for ep in self._episodios.values() if ep.estado == EstadoEpisodio.ACTIVO)
        archivados = sum(1 for ep in self._episodios.values() if ep.estado == EstadoEpisodio.ARCHIVADO)
        consolidados_count = sum(1 for ep in self._episodios.values() if ep.estado == EstadoEpisodio.CONSOLIDADO)
        olvidados = sum(1 for ep in self._episodios.values() if ep.estado == EstadoEpisodio.OLVIDADO)
        
        importancias = [ep.importancia for ep in self._episodios.values()]
        avg_importancia = sum(importancias) / len(importancias) if importancias else 0.0
        
        if self._estadisticas['ultimo_mantenimiento'] > 0:
            tiempo_desde_mant = ahora - self._estadisticas['ultimo_mantenimiento']
        else:
            tiempo_desde_mant = ahora
        
        return {
            'exito': True,
            'total_episodios': len(self._episodios),
            'activos': activos,
            'archivados': archivados,
            'consolidados': consolidados_count,
            'olvidados': olvidados,
            'contextos': len(self._contextos),
            'importancia_promedio': round(avg_importancia, 4),
            'total_creados': self._estadisticas['total_creados'],
            'total_olvidados': self._estadisticas['total_olvidados'],
            'total_consolidados_ops': self._estadisticas['total_consolidados'],
            'total_accesos': self._estadisticas['total_accesos'],
            'total_busquedas': self._estadisticas['total_busquedas'],
            'tiempo_desde_mantenimiento': round(tiempo_desde_mant / 3600, 2),
            'max_episodios': self._max_episodios,
            'capacidad_porcentaje': round(len(self._episodios) / self._max_episodios * 100, 2)
        }

    def _mantenimiento(self, e: Dict) -> Dict[str, Any]:
        """Ejecuta mantenimiento: olvido, consolidación, limpieza."""
        ahora = time.time()
        
        # Olvido
        resultado_olvido = self._olvidar_episodios({})
        
        # Consolidación de episodios muy accedidos
        resultado_cons = self._consolidar({'umbral_accesos': 3})
        
        # Limpieza de episodios olvidados muy antiguos
        if e.get('forzar', False) or e.get('limpiar', False):
            a_eliminar = []
            for eid, ep in self._episodios.items():
                if ep.estado == EstadoEpisodio.OLVIDADO and ep.olvido_factor < 0.01:
                    a_eliminar.append(eid)
            for eid in a_eliminar[:len(a_eliminar)//2]:
                self._indice.desindexar(self._episodios[eid])
                del self._episodios[eid]
        
        self._estadisticas['ultimo_mantenimiento'] = ahora
        
        return {
            'exito': True,
            'olvidados': resultado_olvido['olvidados'],
            'consolidados': resultado_cons.get('consolidados', 0),
            'total_episodios': len(self._episodios),
            'timestamp': datetime.fromtimestamp(ahora).isoformat()
        }

    def _guardar(self, e: Dict) -> Dict[str, Any]:
        """Persiste toda la memoria episódica a disco."""
        try:
            ruta = e.get('ruta', str(self._dir / 'memoria_episodica'))
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            data = {
                'episodios': {},
                'contextos': {},
                'estadisticas': self._estadisticas,
                'version': '0.0.1-NEBULA',
                'timestamp_guardado': time.time()
            }
            
            # Serializar episodios (convertir dataclasses a dicts)
            for eid, ep in self._episodios.items():
                data['episodios'][eid] = {
                    'id': ep.id,
                    'timestamp': ep.timestamp,
                    'timestamp_str': ep.timestamp_str,
                    'tipo': ep.tipo.value,
                    'contenido': ep.contenido,
                    'resumen': ep.resumen,
                    'contexto': ep.contexto,
                    'emocion': ep.emocion.value,
                    'importancia': ep.importancia,
                    'etiquetas': ep.etiquetas,
                    'entidades': ep.entidades,
                    'relaciones': ep.relaciones,
                    'embedding': ep.embedding,
                    'estado': ep.estado.value,
                    'acceso_count': ep.acceso_count,
                    'ultimo_acceso': ep.ultimo_acceso,
                    'consolidacion_count': ep.consolidacion_count,
                    'olvido_factor': ep.olvido_factor,
                    'version': ep.version,
                    'padre_id': ep.padre_id,
                    'hijos_ids': ep.hijos_ids,
                }
            
            for cid, ctx in self._contextos.items():
                data['contextos'][cid] = {
                    'id': ctx.id,
                    'nombre': ctx.nombre,
                    'episodios_ids': ctx.episodios_ids,
                    'metadata': ctx.metadata,
                    'timestamp_creacion': ctx.timestamp_creacion,
                    'timestamp_actualizacion': ctx.timestamp_actualizacion,
                }
            
            with open(ruta + '.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
            return {'exito': True, 'ruta': ruta + '.pkl', 'episodios': len(data['episodios']),
                   'contextos': len(data['contextos'])}
        except Exception as ex:
            return {'error': f'Error guardando: {str(ex)}', 'exito': False}

    def _cargar(self, e: Dict) -> Dict[str, Any]:
        """Carga la memoria episódica desde disco."""
        try:
            ruta = e.get('ruta', '')
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            if not Path(ruta + '.pkl').exists():
                return {'error': f'Archivo no encontrado: {ruta}.pkl', 'exito': False}
            
            with open(ruta + '.pkl', 'rb') as f:
                data = pickle.load(f)
            
            self._episodios.clear()
            self._contextos.clear()
            self._indice = IndiceEpisodico()
            
            for eid, edict in data.get('episodios', {}).items():
                try:
                    tipo = TipoEpisodio(edict['tipo'])
                except (ValueError, KeyError):
                    tipo = TipoEpisodio.OBSERVACION
                
                emocion_val = edict.get('emocion', 0.0)
                emocion = IntensidadEmocional.NEUTRA
                for ie in IntensidadEmocional:
                    if abs(ie.value - emocion_val) < 0.01:
                        emocion = ie
                        break
                
                try:
                    estado = EstadoEpisodio(edict.get('estado', 'activo'))
                except ValueError:
                    estado = EstadoEpisodio.ACTIVO
                
                ep = Episodio(
                    id=edict['id'],
                    timestamp=edict['timestamp'],
                    timestamp_str=edict.get('timestamp_str', ''),
                    tipo=tipo,
                    contenido=edict.get('contenido', {}),
                    resumen=edict.get('resumen', ''),
                    contexto=edict.get('contexto', {}),
                    emocion=emocion,
                    importancia=edict.get('importancia', 0.5),
                    etiquetas=edict.get('etiquetas', []),
                    entidades=edict.get('entidades', []),
                    relaciones=edict.get('relaciones', []),
                    embedding=edict.get('embedding', None),
                    estado=estado,
                    acceso_count=edict.get('acceso_count', 0),
                    ultimo_acceso=edict.get('ultimo_acceso', edict['timestamp']),
                    consolidacion_count=edict.get('consolidacion_count', 0),
                    olvido_factor=edict.get('olvido_factor', 1.0),
                    version=edict.get('version', 1),
                    padre_id=edict.get('padre_id', None),
                    hijos_ids=edict.get('hijos_ids', [])
                )
                self._episodios[ep.id] = ep
                self._indice.indexar(ep)
            
            for cid, cdict in data.get('contextos', {}).items():
                ctx = ContextoEpisodico(
                    id=cdict['id'],
                    nombre=cdict.get('nombre', ''),
                    episodios_ids=cdict.get('episodios_ids', []),
                    metadata=cdict.get('metadata', {}),
                    timestamp_creacion=cdict.get('timestamp_creacion', time.time()),
                    timestamp_actualizacion=cdict.get('timestamp_actualizacion', time.time())
                )
                self._contextos[ctx.id] = ctx
            
            self._estadisticas = data.get('estadisticas', {
                'total_creados': len(self._episodios),
                'total_olvidados': 0, 'total_consolidados': 0,
                'total_accesos': 0, 'total_busquedas': 0, 'total_contextos': len(self._contextos),
                'memoria_bytes': 0, 'ultimo_mantenimiento': 0.0
            })
            self._indice.ordenar_temporal()
            
            return {'exito': True, 'episodios': len(self._episodios),
                   'contextos': len(self._contextos)}
        except Exception as ex:
            return {'error': f'Error cargando: {str(ex)}', 'exito': False}

    def _info(self, e: Dict) -> Dict[str, Any]:
        """Información general del motor."""
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'episodios_totales': len(self._episodios),
            'contextos_totales': len(self._contextos),
            'max_episodios': self._max_episodios,
            'mecanismo_olvido': 'Ebbinghaus modificado',
            'indices': ['tipo', 'etiqueta', 'entidad', 'emocion', 'estado', 'importancia', 'fecha', 'temporal'],
            'funcionalidades': ['registrar', 'buscar', 'actualizar', 'olvidar', 'consolidar',
                               'encadenar', 'contextos', 'similares', 'persistencia']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR EPISÓDICO — MEMORIA DE EXPERIENCIAS")
    print("=" * 70)
    motor = None
    try:
        print("\n[0] Inicializando...")
        motor = MotorEpisodico()
        motor.inicializar()
        print(f"  ✅ Motor: {motor.nombre} | Estado: {motor.estado}")

        print("\n[1] Registrando episodios...")
        episodios_creados = []
        datos_prueba = [
            {
                'tipo': 'conversacion', 'resumen': 'Usuario preguntó sobre arquitectura ANP',
                'contenido': {'pregunta': '¿Qué es ANP?', 'respuesta': 'Arquitectura Neuronal Profunda'},
                'etiquetas': ['ANP', 'consulta', 'arquitectura'],
                'entidades': ['ANP', 'usuario'],
                'importancia': 0.9,
                'emocion': 0.5
            },
            {
                'tipo': 'aprendizaje', 'resumen': 'Aprendido nuevo patrón de reconocimiento',
                'contenido': {'patron': 'circuito_A', 'precision': 0.95},
                'etiquetas': ['aprendizaje', 'patron', 'reconocimiento'],
                'entidades': ['circuito_A', 'motor_neuronal'],
                'importancia': 0.8,
                'emocion': 0.75
            },
            {
                'tipo': 'error', 'resumen': 'Error de memoria en motor neuronal',
                'contenido': {'error': 'MemoryError', 'ubicacion': 'motor_neuronal.py:234'},
                'etiquetas': ['error', 'memoria', 'critico'],
                'entidades': ['motor_neuronal'],
                'importancia': 0.95,
                'emocion': 0.25
            },
            {
                'tipo': 'logro', 'resumen': 'Motor embebido completado exitosamente',
                'contenido': {'motor': 'embebido', 'estado': 'completado', 'tokens': 208},
                'etiquetas': ['logro', 'motor', 'completado'],
                'entidades': ['motor_embebido'],
                'importancia': 0.9,
                'emocion': 1.0
            },
            {
                'tipo': 'observacion', 'resumen': 'Sistema funcionando estable por 24h',
                'contenido': {'uptime': '24h', 'errores': 0, 'memoria_mb': 450},
                'etiquetas': ['observacion', 'estabilidad', 'sistema'],
                'entidades': ['sistema'],
                'importancia': 0.6,
                'emocion': 0.5
            },
        ]
        
        for datos in datos_prueba:
            r = motor.procesar({'accion': 'registrar', **datos})
            if r.exito and r.datos and r.datos.get('exito'):
                episodios_creados.append(r.datos['id'])
                print(f"  ✅ {datos['tipo']}: {datos['resumen'][:50]}...")
            else:
                err = r.datos.get('error', '?') if r.datos else r.error
                print(f"  ❌ Error: {err}")

        print(f"\n[2] Estadísticas tras registro:")
        r = motor.procesar({'accion': 'estadisticas'})
        if r.exito and r.datos:
            stats = r.datos
            print(f"  Total: {stats['total_episodios']} | Activos: {stats['activos']} | "
                  f"Importancia promedio: {stats['importancia_promedio']}")

        print(f"\n[3] Búsqueda por etiqueta 'motor':")
        r = motor.procesar({'accion': 'buscar', 'etiquetas': ['motor']})
        if r.exito and r.datos:
            for ep in r.datos['resultados']:
                print(f"  📋 {ep['tipo']}: {ep['resumen'][:60]}")

        print(f"\n[4] Búsqueda por entidad 'motor_embebido':")
        r = motor.procesar({'accion': 'buscar', 'entidades': ['motor_embebido']})
        if r.exito and r.datos:
            for ep in r.datos['resultados']:
                print(f"  🎯 {ep['tipo']}: {ep['resumen'][:60]} | Importancia: {ep['importancia']}")

        print(f"\n[5] Similares al primer episodio:")
        if episodios_creados:
            r = motor.procesar({'accion': 'similares', 'id': episodios_creados[0], 'limite': 3})
            if r.exito and r.datos:
                for s in r.datos['similares']:
                    print(f"  🔗 Similitud {s['similitud']}: {s['resumen'][:60]}")

        print(f"\n[6] Encadenamiento padre-hijo:")
        if len(episodios_creados) >= 2:
            r = motor.procesar({'accion': 'encadenar', 'padre_id': episodios_creados[0],
                               'hijo_id': episodios_creados[1]})
            if r.exito and r.datos:
                print(f"  ✅ {r.datos}")

        print(f"\n[7] Consolidación:")
        r = motor.procesar({'accion': 'consolidar', 'id': episodios_creados[0]})
        if r.exito and r.datos:
            print(f"  ✅ Nueva importancia: {r.datos.get('nueva_importancia', 'N/A')}")

        print(f"\n[8] Contexto compartido:")
        r = motor.procesar({'accion': 'contexto_crear', 'nombre': 'Desarrollo ANP'})
        if r.exito and r.datos:
            ctx_id = r.datos['id']
            r2 = motor.procesar({'accion': 'contexto_vincular', 'contexto_id': ctx_id,
                                'episodios_ids': episodios_creados[:3]})
            if r2.exito and r2.datos:
                print(f"  ✅ Vinculados: {r2.datos['vinculados']} episodios al contexto 'Desarrollo ANP'")

        print(f"\n[9] Mecanismo de olvido:")
        r = motor.procesar({'accion': 'olvidar'})
        if r.exito and r.datos:
            print(f"  ✅ Olvidados: {r.datos['olvidados']}")

        ruta = 'almacenamiento/episodica/memoria_test'
        print(f"\n[10] Guardar: {'✅' if motor.procesar({'accion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")
        
        rc = motor.procesar({'accion':'cargar','ruta':ruta})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[11] Cargar: {'✅' if ok else '❌'} "
              f"({rc.datos.get('episodios','?') if ok else ''} episodios)")

        if ok and episodios_creados:
            rv = motor.procesar({'accion':'recuperar','id':episodios_creados[0]})
            if rv.exito and rv.datos:
                ep_rec = rv.datos.get('episodio', {})
                print(f"[12] Verificación post-carga: {ep_rec.get('resumen', 'N/A')[:50]}")
                print(f"     Tipo: {ep_rec.get('tipo')} | Etiquetas: {ep_rec.get('etiquetas')}")

        print(f"\n{'='*70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO | Episodios: {len(episodios_creados)}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'='*70}\n")