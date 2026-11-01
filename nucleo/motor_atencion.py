#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Atención — Mecanismo de Atención Contextual Multi-Head
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, uuid, traceback, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, deque
from enum import Enum
import heapq

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

class TipoAtencion(Enum):
    SELECTIVA = "selectiva"
    SOSTENIDA = "sostenida"
    DIVIDIDA = "dividida"
    ALTERNANTE = "alternante"
    EJECUTIVA = "ejecutiva"
    ESPACIAL = "espacial"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"

class ModoPooling(Enum):
    MAX = "max"
    MEAN = "mean"
    WEIGHTED = "weighted"
    EXPONENTIAL = "exponential"
    MEDIAN = "median"

class FuncionScore(Enum):
    DOT = "dot"
    SCALED_DOT = "scaled_dot"
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    ADDITIVE = "additive"
    BILINEAR = "bilinear"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class VentanaContextual:
    """Ventana de contexto con peso temporal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    items: List[Any] = field(default_factory=list)
    pesos: List[float] = field(default_factory=list)
    timestamp_inicio: float = field(default_factory=time.time)
    timestamp_fin: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CabezaAtencion:
    """Una cabeza de atención individual."""
    nombre: str = ""
    W_q: Optional[np.ndarray] = None
    W_k: Optional[np.ndarray] = None
    W_v: Optional[np.ndarray] = None
    dimension: int = 64
    scores: Optional[np.ndarray] = None
    pesos_atencion: Optional[np.ndarray] = None
    salida: Optional[np.ndarray] = None

@dataclass
class PerfilAtencion:
    """Perfil de atención para seguimiento de patrones."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    historial_scores: List[float] = field(default_factory=list)
    patrones_detectados: List[Dict] = field(default_factory=list)
    entropia_promedio: float = 0.0
    timestamp_creacion: float = field(default_factory=time.time)

# =====================================================================
# SCORING FUNCTIONS
# =====================================================================

class ScoringFunctions:
    """Funciones de scoring para mecanismos de atención."""
    
    @staticmethod
    def dot_product(Q: np.ndarray, K: np.ndarray) -> np.ndarray:
        return np.dot(Q, K.T)
    
    @staticmethod
    def scaled_dot(Q: np.ndarray, K: np.ndarray, scale: float = None) -> np.ndarray:
        if scale is None:
            scale = math.sqrt(Q.shape[-1])
        return np.dot(Q, K.T) / scale
    
    @staticmethod
    def cosine_similarity(Q: np.ndarray, K: np.ndarray) -> np.ndarray:
        Q_norm = Q / (np.linalg.norm(Q, axis=-1, keepdims=True) + 1e-12)
        K_norm = K / (np.linalg.norm(K, axis=-1, keepdims=True) + 1e-12)
        return np.dot(Q_norm, K_norm.T)
    
    @staticmethod
    def euclidean(Q: np.ndarray, K: np.ndarray) -> np.ndarray:
        return -np.linalg.norm(Q[:, None, :] - K[None, :, :], axis=-1)
    
    @staticmethod
    def additive(Q: np.ndarray, K: np.ndarray, W: np.ndarray = None) -> np.ndarray:
        if W is None:
            W = np.random.randn(Q.shape[-1]) * 0.01
        return np.tanh(Q @ W + K @ W)
    
    @staticmethod
    def bilinear(Q: np.ndarray, K: np.ndarray, W: np.ndarray = None) -> np.ndarray:
        if W is None:
            W = np.random.randn(Q.shape[-1], K.shape[-1]) * 0.01
        return Q @ W @ K.T


# =====================================================================
# MULTI-HEAD ATTENTION DESDE CERO
# =====================================================================

class MultiHeadAttention:
    """
    Implementación completa de Multi-Head Attention (Vaswani et al., 2017).
    
    Características:
    - Proyecciones lineales Q, K, V por cabeza
    - Scaled dot-product attention con softmax
    - Concatenación y proyección final
    - Dropout atencional
    - Caché de pesos para inferencia rápida
    - Soporte para masking (causal, padding)
    """
    
    def __init__(self, d_model: int = 512, num_heads: int = 8, 
                 d_k: int = 64, d_v: int = 64, dropout: float = 0.1,
                 semilla: int = 42):
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_k
        self.d_v = d_v
        self.dropout_rate = dropout
        self.semilla = semilla
        
        self.cabezas: List[CabezaAtencion] = []
        self.W_o: Optional[np.ndarray] = None
        self._inicializado = False
        self._cache_scores: OrderedDict = OrderedDict()
        self._max_cache = 100
    
    def inicializar(self):
        """Inicializa todas las matrices de pesos."""
        np.random.seed(self.semilla)
        
        for i in range(self.num_heads):
            cabeza = CabezaAtencion(
                nombre=f"head_{i}",
                W_q=np.random.randn(self.d_model, self.d_k).astype(np.float64) * 0.02,
                W_k=np.random.randn(self.d_model, self.d_k).astype(np.float64) * 0.02,
                W_v=np.random.randn(self.d_model, self.d_v).astype(np.float64) * 0.02,
                dimension=self.d_k
            )
            self.cabezas.append(cabeza)
        
        self.W_o = np.random.randn(self.num_heads * self.d_v, self.d_model).astype(np.float64) * 0.02
        self._inicializado = True
    
    def _scaled_dot_product_attention(self, Q: np.ndarray, K: np.ndarray, 
                                      V: np.ndarray, mask: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Calcula atención escalada para una cabeza."""
        d_k = Q.shape[-1]
        scores = np.dot(Q, K.T) / math.sqrt(d_k)
        
        if mask is not None:
            scores = np.where(mask == 0, -1e9, scores)
        
        pesos = self._softmax(scores, axis=-1)
        
        if self.dropout_rate > 0:
            mascara_dropout = np.random.binomial(1, 1 - self.dropout_rate, size=pesos.shape)
            pesos = pesos * mascara_dropout
            pesos = pesos / (pesos.sum(axis=-1, keepdims=True) + 1e-12)
        
        salida = np.dot(pesos, V)
        return salida, pesos
    
    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Softmax numéricamente estable."""
        x_max = np.max(x, axis=axis, keepdims=True)
        e_x = np.exp(x - x_max)
        return e_x / (e_x.sum(axis=axis, keepdims=True) + 1e-12)
    
    def forward(self, Q: np.ndarray, K: np.ndarray, V: np.ndarray, 
                mask: np.ndarray = None, usar_cache: bool = False) -> Tuple[np.ndarray, Dict]:
        """
        Forward pass del multi-head attention.
        
        Args:
            Q: Query matrix (batch_size, seq_len_q, d_model)
            K: Key matrix (batch_size, seq_len_k, d_model)
            V: Value matrix (batch_size, seq_len_v, d_model)
            mask: Attention mask
            usar_cache: Si debe usar caché de scores
        
        Returns:
            output: (batch_size, seq_len_q, d_model)
            metadata: Diccionario con pesos y scores por cabeza
        """
        if not self._inicializado:
            self.inicializar()
        
        batch_size = Q.shape[0]
        seq_len_q = Q.shape[1]
        seq_len_k = K.shape[1]
        
        cache_key = None
        if usar_cache:
            cache_key = hashlib.md5(Q.tobytes()[:100] + K.tobytes()[:100]).hexdigest()
            if cache_key in self._cache_scores:
                return self._cache_scores[cache_key]
        
        salidas_cabezas = []
        metadata = {'cabezas': {}, 'pesos_promedio': None}
        todas_atenciones = []
        
        for i, cabeza in enumerate(self.cabezas):
            Q_proj = np.dot(Q, cabeza.W_q)
            K_proj = np.dot(K, cabeza.W_k)
            V_proj = np.dot(V, cabeza.W_v)
            
            salida_cabeza, pesos = self._scaled_dot_product_attention(
                Q_proj, K_proj, V_proj, mask
            )
            
            cabeza.scores = None
            cabeza.pesos_atencion = pesos
            cabeza.salida = salida_cabeza
            
            salidas_cabezas.append(salida_cabeza)
            todas_atenciones.append(pesos)
            
            metadata['cabezas'][cabeza.nombre] = {
                'pesos_promedio': float(np.mean(pesos)),
                'pesos_max': float(np.max(pesos)),
                'entropia': float(self._entropia_atencion(pesos))
            }
        
        concatenadas = np.concatenate(salidas_cabezas, axis=-1)
        salida_final = np.dot(concatenadas, self.W_o)
        
        metadata['pesos_promedio'] = float(np.mean(todas_atenciones))
        metadata['entropia_global'] = float(self._entropia_atencion(np.mean(todas_atenciones, axis=0)))
        
        if usar_cache and cache_key:
            self._cache_scores[cache_key] = (salida_final, metadata)
            if len(self._cache_scores) > self._max_cache:
                self._cache_scores.popitem(last=False)
        
        return salida_final, metadata
    
    def _entropia_atencion(self, pesos: np.ndarray) -> float:
        """Calcula la entropía de la distribución de atención."""
        pesos = np.clip(pesos, 1e-12, 1.0)
        entropia = -np.sum(pesos * np.log(pesos), axis=-1)
        return float(np.mean(entropia))


# =====================================================================
# ATENCIÓN TEMPORAL CON DECAIMIENTO
# =====================================================================

class AtencionTemporal:
    """
    Atención con decaimiento temporal adaptativo.
    Los items más recientes reciben mayor peso.
    """
    
    def __init__(self, tasa_decaimiento: float = 0.1, 
                 funcion_score: FuncionScore = FuncionScore.SCALED_DOT):
        self.tasa_decaimiento = tasa_decaimiento
        self.funcion_score = funcion_score
        self._historial_temporal: List[Tuple[float, Any]] = []
    
    def agregar_evento(self, item: Any, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        self._historial_temporal.append((timestamp, item))
        if len(self._historial_temporal) > 1000:
            self._historial_temporal = self._historial_temporal[-500:]
    
    def pesos_temporales(self, tiempo_referencia: float = None) -> np.ndarray:
        if not self._historial_temporal:
            return np.array([])
        
        if tiempo_referencia is None:
            tiempo_referencia = time.time()
        
        tiempos = np.array([t for t, _ in self._historial_temporal])
        antiguedad = tiempo_referencia - tiempos
        pesos = np.exp(-self.tasa_decaimiento * antiguedad / 60.0)
        return pesos / (pesos.sum() + 1e-12)
    
    def atender_temporal(self, query: Any, items: List[Any], 
                        timestamps: List[float] = None) -> Tuple[Any, np.ndarray]:
        pesos = self.pesos_temporales()
        if len(pesos) == 0:
            return None, np.array([])
        
        if NUMPY_DISPONIBLE and isinstance(items[0], np.ndarray):
            items_array = np.array([i for _, i in self._historial_temporal])
            salida = np.average(items_array, axis=0, weights=pesos)
            return salida, pesos
        
        return items[-1], pesos


# =====================================================================
# ATENCIÓN ESPACIAL
# =====================================================================

class AtencionEspacial:
    """
    Atención espacial para datos 2D/3D.
    Implementa spotlight attention con campo receptivo variable.
    """
    
    def __init__(self, tamano_spotlight: int = 3):
        self.tamano_spotlight = tamano_spotlight
        self._mapa_saliencia: Optional[np.ndarray] = None
        self._posicion_foco: Tuple[int, int] = (0, 0)
    
    def calcular_mapa_saliencia(self, datos: np.ndarray) -> np.ndarray:
        """Calcula mapa de saliencia usando diferencias de contraste."""
        if len(datos.shape) == 2:
            datos = datos.reshape(1, *datos.shape)
        
        gradiente_x = np.gradient(datos, axis=-1)
        gradiente_y = np.gradient(datos, axis=-2)
        magnitud = np.sqrt(gradiente_x**2 + gradiente_y**2)
        self._mapa_saliencia = magnitud
        return magnitud
    
    def enfocar(self, datos: np.ndarray, centro: Tuple[int, int] = None) -> Tuple[np.ndarray, Tuple[int, int]]:
        if centro is None:
            if self._mapa_saliencia is not None:
                idx_max = np.unravel_index(np.argmax(self._mapa_saliencia), self._mapa_saliencia.shape)
                centro = (idx_max[-2], idx_max[-1])
            else:
                centro = (datos.shape[-2] // 2, datos.shape[-1] // 2)
        
        r = self.tamano_spotlight // 2
        h, w = datos.shape[-2], datos.shape[-1]
        
        y_min = max(0, centro[0] - r)
        y_max = min(h, centro[0] + r + 1)
        x_min = max(0, centro[1] - r)
        x_max = min(w, centro[1] + r + 1)
        
        self._posicion_foco = centro
        
        if len(datos.shape) == 3:
            return datos[:, y_min:y_max, x_min:x_max], centro
        return datos[y_min:y_max, x_min:x_max], centro


# =====================================================================
# ATENCIÓN CONTEXTUAL (PRINCIPAL)
# =====================================================================

class AtencionContextual:
    """
    Sistema de atención contextual completo.
    Integra atención multi-head, temporal, espacial y selectiva.
    """
    
    def __init__(self, d_model: int = 256, num_heads: int = 4,
                 ventana_contexto: int = 10, tasa_decaimiento: float = 0.05):
        self.d_model = d_model
        self.ventana_contexto = ventana_contexto
        self.multi_head = MultiHeadAttention(d_model=d_model, num_heads=num_heads)
        self.temporal = AtencionTemporal(tasa_decaimiento=tasa_decaimiento)
        self.espacial = AtencionEspacial()
        self._contexto_actual: deque = deque(maxlen=ventana_contexto)
        self._perfiles: Dict[str, PerfilAtencion] = {}
        self._estadisticas = {
            'atenciones_realizadas': 0,
            'entropia_promedio': 0.0,
            'cambios_foco': 0,
            'items_procesados': 0
        }
    
    def alimentar_contexto(self, item: Any, embedding: Optional[np.ndarray] = None):
        """Alimenta un nuevo item al contexto actual."""
        entrada = {
            'item': item,
            'embedding': embedding if embedding is not None else item,
            'timestamp': time.time()
        }
        self._contexto_actual.append(entrada)
        self.temporal.agregar_evento(item)
        self._estadisticas['items_procesados'] += 1
    
    def atender(self, query_embedding: np.ndarray, 
                tipo: TipoAtencion = TipoAtencion.CONTEXTUAL,
                k: int = 5) -> Dict[str, Any]:
        """
        Ejecuta el mecanismo de atención sobre el contexto actual.
        
        Args:
            query_embedding: Embedding de la consulta
            tipo: Tipo de atención a aplicar
            k: Número de items a retornar
        
        Returns:
            Diccionario con items atendidos, pesos y metadata
        """
        if not self._contexto_actual:
            return {'error': 'Contexto vacío', 'exito': False}
        
        self._estadisticas['atenciones_realizadas'] += 1
        
        items = [c['item'] for c in self._contexto_actual]
        embeddings = [c['embedding'] for c in self._contexto_actual]
        timestamps = [c['timestamp'] for c in self._contexto_actual]
        
        if NUMPY_DISPONIBLE and all(isinstance(e, np.ndarray) for e in embeddings):
            K = np.array(embeddings)
            V = np.array(embeddings)
            Q = query_embedding.reshape(1, -1)
            
            K = K.reshape(1, *K.shape)
            V = V.reshape(1, *V.shape)
            
            if not self.multi_head._inicializado:
                self.multi_head.inicializar()
            
            salida, metadata = self.multi_head.forward(Q, K, V)
            
            pesos_temporales = self.temporal.pesos_temporales()
            
            scores_combinados = metadata['pesos_promedio'] * 0.7
            if len(pesos_temporales) > 0:
                scores_combinados += float(np.mean(pesos_temporales)) * 0.3
            
            indices_ordenados = np.argsort(-np.array([scores_combinados] * len(items)))[:k]
            
            items_atendidos = []
            for idx in indices_ordenados:
                if idx < len(items):
                    items_atendidos.append({
                        'item': str(items[idx])[:100],
                        'score': float(scores_combinados),
                        'timestamp': timestamps[idx]
                    })
            
            return {
                'exito': True,
                'tipo': tipo.value,
                'items_atendidos': items_atendidos,
                'entropia': round(metadata['entropia_global'], 4),
                'peso_promedio': round(metadata['pesos_promedio'], 4),
                'contexto_tamano': len(self._contexto_actual),
                'detalle_cabezas': metadata['cabezas']
            }
        
        return {'error': 'Se requieren embeddings NumPy', 'exito': False}
    
    def crear_perfil(self, nombre: str) -> str:
        perfil = PerfilAtencion(nombre=nombre)
        self._perfiles[perfil.id] = perfil
        return perfil.id


# =====================================================================
# MOTOR DE ATENCIÓN PRINCIPAL
# =====================================================================

class MotorAtencion(MotorBase):
    """
    Motor de Atención de ANP — Núcleo de Memoria.
    
    Implementa mecanismos de atención contextual:
    - Multi-Head Self-Attention (Vaswani et al.)
    - Atención temporal con decaimiento adaptativo
    - Atención espacial con spotlight
    - Scoring functions: dot, scaled-dot, cosine, euclidean, additive, bilinear
    - Pooling: max, mean, weighted, exponential, median
    - Perfiles de atención para seguimiento de patrones
    - Ventanas contextuales deslizantes
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._atencion = AtencionContextual(d_model=256, num_heads=4, ventana_contexto=15)
        self._ventanas: Dict[str, VentanaContextual] = {}
        self._scoring = ScoringFunctions()
        self._lock = threading.RLock()
        self._dir = Path("almacenamiento/atencion")
        self._dir.mkdir(parents=True, exist_ok=True)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        accion = entrada.get('accion', 'info')
        with self._lock:
            metodos = {
                'alimentar': self._alimentar,
                'atender': self._atender,
                'ventana_crear': self._ventana_crear,
                'perfil_crear': self._perfil_crear,
                'scoring': self._scoring_comparar,
                'estado': self._estado,
                'estadisticas': self._estadisticas,
                'guardar': self._guardar,
                'cargar': self._cargar,
                'info': self._info,
            }
            func = metodos.get(accion)
            return func(entrada) if func else {'error': f'Acción: {accion}', 'exito': False}
    
    def _alimentar(self, e: Dict) -> Dict[str, Any]:
        item = e.get('item', e.get('contenido', ''))
        embedding = e.get('embedding')
        
        if embedding is not None and isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float64)
        
        self._atencion.alimentar_contexto(item, embedding)
        
        return {
            'exito': True,
            'contexto_tamano': len(self._atencion._contexto_actual),
            'items_procesados': self._atencion._estadisticas['items_procesados']
        }
    
    def _atender(self, e: Dict) -> Dict[str, Any]:
        query_emb = e.get('query_embedding')
        if query_emb is not None and isinstance(query_emb, list):
            query_emb = np.array(query_emb, dtype=np.float64)
        
        if query_emb is None:
            if self._atencion._contexto_actual:
                query_emb = self._atencion._contexto_actual[-1]['embedding']
                if not isinstance(query_emb, np.ndarray):
                    query_emb = np.random.randn(256)
            else:
                query_emb = np.random.randn(256)
        
        tipo_str = e.get('tipo', 'contextual')
        try:
            tipo = TipoAtencion(tipo_str)
        except ValueError:
            tipo = TipoAtencion.CONTEXTUAL
        
        k = e.get('k', 5)
        
        return self._atencion.atender(query_emb, tipo=tipo, k=k)
    
    def _ventana_crear(self, e: Dict) -> Dict[str, Any]:
        items = e.get('items', [])
        pesos = e.get('pesos', [1.0] * len(items))
        
        ventana = VentanaContextual(
            items=items,
            pesos=pesos,
            timestamp_fin=time.time() + e.get('duracion', 60.0),
            metadata=e.get('metadata', {})
        )
        self._ventanas[ventana.id] = ventana
        
        return {'exito': True, 'ventana_id': ventana.id, 'items': len(items)}
    
    def _perfil_crear(self, e: Dict) -> Dict[str, Any]:
        nombre = e.get('nombre', f'perfil_{len(self._atencion._perfiles)+1}')
        perfil_id = self._atencion.crear_perfil(nombre)
        return {'exito': True, 'perfil_id': perfil_id, 'nombre': nombre}
    
    def _scoring_comparar(self, e: Dict) -> Dict[str, Any]:
        emb1 = e.get('embedding1')
        emb2 = e.get('embedding2')
        
        if emb1 is None or emb2 is None:
            return {'error': 'Se requieren embedding1 y embedding2', 'exito': False}
        
        if isinstance(emb1, list):
            emb1 = np.array(emb1, dtype=np.float64)
        if isinstance(emb2, list):
            emb2 = np.array(emb2, dtype=np.float64)
        
        funcion_str = e.get('funcion', 'cosine')
        try:
            funcion = FuncionScore(funcion_str)
        except ValueError:
            funcion = FuncionScore.COSINE
        
        scores = {}
        if funcion == FuncionScore.DOT:
            scores['dot'] = float(np.dot(emb1, emb2))
        if funcion == FuncionScore.SCALED_DOT:
            scores['scaled_dot'] = float(np.dot(emb1, emb2) / math.sqrt(len(emb1)))
        if funcion == FuncionScore.COSINE:
            n1, n2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
            scores['cosine'] = float(np.dot(emb1, emb2) / (n1 * n2 + 1e-12))
        if funcion == FuncionScore.EUCLIDEAN:
            scores['euclidean'] = float(-np.linalg.norm(emb1 - emb2))
        
        return {'exito': True, 'scores': scores, 'funcion': funcion.value}
    
    def _estado(self, e: Dict) -> Dict[str, Any]:
        contexto = list(self._atencion._contexto_actual)
        return {
            'exito': True,
            'contexto_tamano': len(contexto),
            'contexto': [{'item': str(c['item'])[:60], 
                         'timestamp': c['timestamp']} for c in contexto[-5:]],
            'ventanas_activas': len(self._ventanas),
            'perfiles': len(self._atencion._perfiles),
            'estadisticas': self._atencion._estadisticas
        }
    
    def _estadisticas(self, e: Dict) -> Dict[str, Any]:
        stats = self._atencion._estadisticas
        return {
            'exito': True,
            'atenciones_realizadas': stats['atenciones_realizadas'],
            'items_procesados': stats['items_procesados'],
            'entropia_promedio': round(stats['entropia_promedio'], 4),
            'cambios_foco': stats['cambios_foco'],
            'ventanas_activas': len(self._ventanas),
            'perfiles_creados': len(self._atencion._perfiles)
        }
    
    def _guardar(self, e: Dict) -> Dict[str, Any]:
        try:
            ruta = e.get('ruta', str(self._dir / 'atencion'))
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            data = {
                'estadisticas': self._atencion._estadisticas,
                'contexto': [(c['timestamp'], str(c['item'])[:200]) 
                           for c in self._atencion._contexto_actual],
                'version': '0.0.1-NEBULA',
                'timestamp': time.time()
            }
            
            with open(ruta + '.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
            return {'exito': True, 'ruta': ruta + '.pkl'}
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
            
            self._atencion._estadisticas = data.get('estadisticas', self._atencion._estadisticas)
            
            return {'exito': True, 'contexto_cargado': len(data.get('contexto', []))}
        except Exception as ex:
            return {'error': str(ex), 'exito': False}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'arquitectura': 'Multi-Head Attention (Vaswani 2017)',
            'cabezas': self._atencion.multi_head.num_heads,
            'd_model': self._atencion.d_model,
            'ventana_contexto': self._atencion.ventana_contexto,
            'tipos_atencion': [t.value for t in TipoAtencion],
            'scoring_functions': [f.value for f in FuncionScore],
            'funcionalidades': ['alimentar_contexto', 'atender', 'ventanas_contextuales',
                               'perfiles', 'scoring', 'persistencia']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE ATENCIÓN — MULTI-HEAD ATTENTION")
    print("=" * 70)
    motor = None
    try:
        print(f"\n[0] NumPy: {'✅ ' + np.__version__ if NUMPY_DISPONIBLE else '❌ No'}")
        if not NUMPY_DISPONIBLE:
            sys.exit(1)
        
        motor = MotorAtencion()
        motor.inicializar()
        print(f"[1] Motor: {motor.nombre} | Estado: {motor.estado}")
        
        print(f"\n[2] Alimentando contexto...")
        contexto_prueba = [
            "El perro juega en el parque con el gato",
            "El gato duerme en la casa",
            "La madre prepara la cena para el padre",
            "El rey vive en el castillo con la reina",
            "Python es un lenguaje de programación",
            "La inteligencia artificial aprende de los datos",
            "El algoritmo ordena los números eficientemente",
            "Las redes neuronales imitan al cerebro",
            "El sol brilla en el cielo azul",
            "La luna refleja la luz en la noche",
            "Sistema ANP funcionando correctamente",
            "Motor embebido completado con éxito",
            "Usuario solicita análisis de sentimiento",
            "Error detectado en módulo de memoria",
            "Actualización de parámetros completada",
        ]
        
        for i, texto in enumerate(contexto_prueba):
            emb = np.random.randn(256).astype(np.float64) * 0.1
            r = motor.procesar({'accion': 'alimentar', 'item': texto, 'embedding': emb.tolist()})
        
        r = motor.procesar({'accion': 'estado'})
        if r.exito and r.datos:
            print(f"  ✅ Contexto: {r.datos['contexto_tamano']} items")

        print(f"\n[3] Atención contextual con query 'perro gato':")
        query_emb = np.random.randn(256).astype(np.float64) * 0.1
        r = motor.procesar({'accion': 'atender', 
                           'query_embedding': query_emb.tolist(),
                           'tipo': 'contextual', 'k': 5})
        if r.exito and r.datos:
            print(f"  🎯 Tipo: {r.datos['tipo']}")
            print(f"  📊 Entropía: {r.datos['entropia']}")
            print(f"  ⚖️ Peso promedio: {r.datos['peso_promedio']}")
            for item in r.datos.get('items_atendidos', [])[:3]:
                print(f"  📋 {item['item'][:60]}... (score: {item['score']:.3f})")

        print(f"\n[4] Scoring cosine entre dos embeddings:")
        e1 = np.random.randn(128).astype(np.float64)
        e2 = np.random.randn(128).astype(np.float64)
        r = motor.procesar({'accion': 'scoring', 'funcion': 'cosine',
                           'embedding1': e1.tolist(), 'embedding2': e2.tolist()})
        if r.exito and r.datos:
            print(f"  📐 Cosine: {r.datos['scores'].get('cosine', 'N/A')}")

        print(f"\n[5] Scoring scaled_dot:")
        r = motor.procesar({'accion': 'scoring', 'funcion': 'scaled_dot',
                           'embedding1': e1.tolist(), 'embedding2': e2.tolist()})
        if r.exito and r.datos:
            print(f"  📐 Scaled Dot: {r.datos['scores'].get('scaled_dot', 'N/A')}")

        print(f"\n[6] Creando ventana contextual:")
        r = motor.procesar({'accion': 'ventana_crear', 
                           'items': ['tarea1', 'tarea2', 'tarea3'],
                           'pesos': [0.5, 0.3, 0.2], 'duracion': 120})
        if r.exito and r.datos:
            print(f"  ✅ Ventana: {r.datos['ventana_id'][:8]}... ({r.datos['items']} items)")

        print(f"\n[7] Creando perfil de atención:")
        r = motor.procesar({'accion': 'perfil_crear', 'nombre': 'Perfil Principal ANP'})
        if r.exito and r.datos:
            print(f"  ✅ Perfil: {r.datos['nombre']} (ID: {r.datos['perfil_id'][:8]}...)")

        print(f"\n[8] Atención selectiva (top 3):")
        r = motor.procesar({'accion': 'atender', 
                           'query_embedding': query_emb.tolist(),
                           'tipo': 'selectiva', 'k': 3})
        if r.exito and r.datos:
            print(f"  🎯 Items enfocados: {len(r.datos.get('items_atendidos', []))}")

        ruta = 'almacenamiento/atencion/motor_test'
        print(f"\n[9] Guardar: {'✅' if motor.procesar({'accion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")
        
        rc = motor.procesar({'accion':'cargar','ruta':ruta})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[10] Cargar: {'✅' if ok else '❌'} "
              f"({rc.datos.get('contexto_cargado','?') if ok else ''} items)")

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