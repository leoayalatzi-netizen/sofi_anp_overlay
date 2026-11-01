#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Búsqueda Web — Indexación Invertida + TF-IDF + Fuzzy
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Búsqueda
# =====================================================================

import sys, time, math, re, hashlib, threading, traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter, OrderedDict
from dataclasses import dataclass, field
from enum import Enum

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
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class DocumentoIndexado:
    """Documento almacenado en el índice."""
    id: str
    titulo: str = ""
    texto: str = ""
    url: str = ""
    tokens: List[str] = field(default_factory=list)
    tokens_unicos: int = 0
    tokens_total: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    calidad: float = 0.5

@dataclass
class EntradaIndice:
    """Entrada del índice invertido para un término."""
    termino: str
    documentos: Dict[str, List[int]] = field(default_factory=dict)
    frecuencia_documentos: int = 0
    idf: float = 0.0

# =====================================================================
# TOKENIZADOR MULTILINGÜE
# =====================================================================

class Tokenizador:
    """Tokenizador ultrarrápido con soporte multilenguaje."""
    
    __slots__ = ('_stopwords', '_cache', '_cache_max')
    
    _STOPWORDS = frozenset("""
        el la los las un una unos unas de del en con por para a e o y al
        que es son ser estar fue fueron ha han su sus se lo le les nos
        como más muy todo pero sin sobre entre hasta desde este esta
        estos estas ese esa esos esas aquel aquella the a an and or but
        in on at to for of with from by as is are was were be been being
        have has had do does did will would shall should may might can
        could it its this that these those not no if then else when
    """.split())
    
    _LETRAS_VALIDAS = set('abcdefghijklmnopqrstuvwxyz0123456789áéíóúüñ')
    
    def __init__(self):
        self._cache = {}
        self._cache_max = 5000
    
    def tokenizar(self, texto: str) -> List[str]:
        texto = texto.lower().strip()
        
        if texto in self._cache:
            return self._cache[texto]
        
        tokens = []
        actual = []
        
        for c in texto:
            if c in self._LETRAS_VALIDAS:
                actual.append(c)
            else:
                if len(actual) >= 2:
                    tok = ''.join(actual)
                    if tok not in self._STOPWORDS:
                        tokens.append(tok)
                actual = []
        
        if len(actual) >= 2:
            tok = ''.join(actual)
            if tok not in self._STOPWORDS:
                tokens.append(tok)
        
        if len(self._cache) < self._cache_max:
            self._cache[texto] = tokens
        
        return tokens


# =====================================================================
# ÍNDICE INVERTIDO CON CACHÉ TF-IDF
# =====================================================================

class IndiceInvertido:
    """Índice invertido con scoring TF-IDF y caché de frecuencias."""
    
    __slots__ = ('_entradas', '_documentos', '_total_docs', '_tf_cache', '_idf_cache')
    
    def __init__(self):
        self._entradas: Dict[str, EntradaIndice] = {}
        self._documentos: Dict[str, DocumentoIndexado] = {}
        self._total_docs = 0
        self._tf_cache: Dict[Tuple[str, str], float] = {}
        self._idf_cache: Dict[str, float] = {}
    
    def indexar(self, doc: DocumentoIndexado):
        if doc.id in self._documentos:
            self.desindexar(doc.id)
        
        self._documentos[doc.id] = doc
        self._total_docs = len(self._documentos)
        
        contador_posiciones = defaultdict(list)
        for pos, token in enumerate(doc.tokens):
            contador_posiciones[token].append(pos)
        
        for token, posiciones in contador_posiciones.items():
            if token not in self._entradas:
                self._entradas[token] = EntradaIndice(termino=token)
            
            entrada = self._entradas[token]
            entrada.documentos[doc.id] = posiciones
            entrada.frecuencia_documentos = len(entrada.documentos)
        
        self._idf_cache.clear()
        self._tf_cache.clear()
    
    def desindexar(self, doc_id: str):
        if doc_id not in self._documentos:
            return
        
        doc = self._documentos[doc_id]
        for token in doc.tokens:
            if token in self._entradas:
                self._entradas[token].documentos.pop(doc_id, None)
                self._entradas[token].frecuencia_documentos = len(self._entradas[token].documentos)
                if not self._entradas[token].documentos:
                    del self._entradas[token]
        
        del self._documentos[doc_id]
        self._total_docs = len(self._documentos)
        self._idf_cache.clear()
        self._tf_cache.clear()
    
    def tf(self, termino: str, doc_id: str) -> float:
        clave = (termino, doc_id)
        if clave in self._tf_cache:
            return self._tf_cache[clave]
        
        if termino not in self._entradas or doc_id not in self._entradas[termino].documentos:
            return 0.0
        
        doc = self._documentos.get(doc_id)
        if not doc:
            return 0.0
        
        tf = len(self._entradas[termino].documentos[doc_id]) / max(1, doc.tokens_total)
        self._tf_cache[clave] = tf
        return tf
    
    def idf(self, termino: str) -> float:
        if termino in self._idf_cache:
            return self._idf_cache[termino]
        
        if termino not in self._entradas:
            return 0.0
        
        df = self._entradas[termino].frecuencia_documentos
        idf = math.log((self._total_docs + 1) / (df + 1)) + 1
        self._idf_cache[termino] = idf
        self._entradas[termino].idf = idf
        return idf
    
    def tfidf(self, termino: str, doc_id: str) -> float:
        tf = self.tf(termino, doc_id)
        if tf == 0.0:
            return 0.0
        return tf * self.idf(termino)
    
    def buscar_termino(self, termino: str) -> Set[str]:
        if termino in self._entradas:
            return set(self._entradas[termino].documentos.keys())
        return set()
    
    @property
    def total_documentos(self) -> int:
        return self._total_docs
    
    @property
    def total_terminos(self) -> int:
        return len(self._entradas)


# =====================================================================
# BUSCADOR FUZZY
# =====================================================================

class BuscadorFuzzy:
    """Búsqueda difusa con distancia de Levenshtein optimizada."""
    
    __slots__ = ('_cache_distancias',)
    
    def __init__(self):
        self._cache_distancias: Dict[Tuple[str, str], int] = {}
    
    def distancia(self, s1: str, s2: str, max_dist: int = 5) -> int:
        if s1 == s2:
            return 0
        if abs(len(s1) - len(s2)) > max_dist:
            return max_dist + 1
        
        clave = (s1, s2) if s1 <= s2 else (s2, s1)
        if clave in self._cache_distancias:
            return self._cache_distancias[clave]
        
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        len_s2 = len(s2)
        prev = list(range(len_s2 + 1))
        
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            min_curr = i + 1
            for j, c2 in enumerate(s2):
                if c1 == c2:
                    curr.append(prev[j])
                else:
                    curr.append(1 + min(prev[j], prev[j+1], curr[j]))
                min_curr = min(min_curr, curr[-1])
            
            if min_curr > max_dist:
                self._cache_distancias[clave] = max_dist + 1
                return max_dist + 1
            
            prev = curr
        
        self._cache_distancias[clave] = prev[-1]
        return prev[-1]
    
    def similitud(self, s1: str, s2: str) -> float:
        d = self.distancia(s1, s2)
        return 1.0 - d / max(len(s1), len(s2), 1)
    
    def expandir_termino(self, termino: str, vocabulario: Set[str], 
                         umbral: float = 0.7) -> List[Tuple[str, float]]:
        resultados = []
        for palabra in vocabulario:
            sim = self.similitud(termino, palabra)
            if sim >= umbral:
                resultados.append((palabra, sim))
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[:5]


# =====================================================================
# MOTOR DE BÚSQUEDA WEB
# =====================================================================

class MotorBusquedaWeb(MotorBase):
    """
    Motor de Búsqueda Web — Indexación Invertida + TF-IDF + Fuzzy Search.
    
    Capacidades:
    - Indexación de documentos con posición de términos
    - Búsqueda textual con ranking TF-IDF
    - Operadores booleanos: AND, OR, NOT
    - Búsqueda difusa con distancia Levenshtein
    - Paginación de resultados
    - Filtros por metadata, fecha, calidad
    - Ordenamiento por relevancia, fecha, titulo
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._indice = IndiceInvertido()
        self._tokenizador = Tokenizador()
        self._fuzzy = BuscadorFuzzy()
        self._lock = threading.RLock()
        self._estadisticas = {
            'documentos_indexados': 0,
            'busquedas_realizadas': 0,
            'terminos_unicos': 0,
            'cache_hits': 0,
        }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'buscar')
        
        with self._lock:
            if operacion == 'indexar':
                return self._indexar(entrada)
            elif operacion == 'buscar':
                return self._buscar(entrada)
            elif operacion == 'desindexar':
                return self._desindexar(entrada)
            elif operacion == 'info':
                return self._info(entrada)
            else:
                return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _indexar(self, e: Dict) -> Dict[str, Any]:
        doc_id = e.get('id', '')
        texto = e.get('texto', '')
        titulo = e.get('titulo', '')
        url = e.get('url', '')
        metadata = e.get('metadata', {})
        calidad = float(e.get('calidad', 0.5))
        
        if not doc_id:
            return {'error': 'ID de documento requerido', 'exito': False}
        if not texto:
            return {'error': 'Texto requerido', 'exito': False}
        
        tokens = self._tokenizador.tokenizar(texto)
        if not tokens:
            return {'error': 'Sin tokens válidos', 'exito': False}
        
        doc = DocumentoIndexado(
            id=doc_id,
            titulo=titulo,
            texto=texto,
            url=url,
            tokens=tokens,
            tokens_unicos=len(set(tokens)),
            tokens_total=len(tokens),
            metadata=metadata,
            calidad=calidad
        )
        
        self._indice.indexar(doc)
        self._estadisticas['documentos_indexados'] = self._indice.total_documentos
        self._estadisticas['terminos_unicos'] = self._indice.total_terminos
        
        return {
            'exito': True,
            'id': doc_id,
            'tokens': len(tokens),
            'tokens_unicos': doc.tokens_unicos,
            'total_docs': self._indice.total_documentos,
            'total_terminos': self._indice.total_terminos
        }
    
    def _buscar(self, e: Dict) -> Dict[str, Any]:
        consulta = e.get('consulta', '')
        limite = int(e.get('limite', 10))
        pagina = int(e.get('pagina', 1))
        fuzzy = bool(e.get('fuzzy', False))
        umbral_fuzzy = float(e.get('umbral_fuzzy', 0.7))
        orden = e.get('orden', 'relevancia')
        filtro_calidad = e.get('calidad_min', 0.0)
        
        if not consulta:
            return {'error': 'Consulta requerida', 'exito': False}
        
        self._estadisticas['busquedas_realizadas'] += 1
        
        tokens_consulta = self._tokenizador.tokenizar(consulta)
        if not tokens_consulta:
            return {'exito': True, 'total': 0, 'resultados': [], 'consulta': consulta}
        
        # Detectar operadores
        usar_or = any(t in ('or', 'o') for t in tokens_consulta)
        usar_not = any(t in ('not', 'no') for t in tokens_consulta)
        tokens_busqueda = [t for t in tokens_consulta if t not in ('and', 'or', 'not', 'y', 'o', 'no')]
        
        if not tokens_busqueda:
            return {'exito': True, 'total': 0, 'resultados': [], 'consulta': consulta}
        
        # Expandir con fuzzy
        todos_terminos = set(self._indice._entradas.keys())
        terminos_expandidos = {}
        
        for token in tokens_busqueda:
            if token in todos_terminos:
                terminos_expandidos[token] = 1.0
            elif fuzzy:
                sugerencias = self._fuzzy.expandir_termino(token, todos_terminos, umbral_fuzzy)
                for sug, sim in sugerencias:
                    terminos_expandidos[sug] = sim
        
        if not terminos_expandidos:
            return {'exito': True, 'total': 0, 'resultados': [], 'consulta': consulta,
                   'sugerencia': 'Sin resultados. Active fuzzy para búsqueda difusa.'}
        
        # Scoring
        scores = defaultdict(float)
        docs_validos = None if usar_or else None
        
        for termino, peso in terminos_expandidos.items():
            docs_termino = self._indice.buscar_termino(termino)
            
            if usar_or:
                docs_validos = (docs_validos or set()) | docs_termino
            elif docs_validos is None:
                docs_validos = docs_termino.copy()
            else:
                docs_validos &= docs_termino
            
            for doc_id in docs_termino:
                tfidf = self._indice.tfidf(termino, doc_id)
                scores[doc_id] += tfidf * peso
        
        if docs_validos is None:
            docs_validos = set()
        
        # Aplicar NOT
        if usar_not:
            for token in tokens_busqueda:
                if token in self._indice._entradas:
                    docs_validos -= self._indice.buscar_termino(token)
        
        # Construir resultados
        resultados = []
        for doc_id in docs_validos:
            if doc_id not in self._indice._documentos:
                continue
            
            doc = self._indice._documentos[doc_id]
            
            if doc.calidad < filtro_calidad:
                continue
            
            score = scores.get(doc_id, 0.0)
            
            resultados.append({
                'id': doc_id,
                'score': round(score, 4),
                'titulo': doc.titulo[:100] if doc.titulo else doc.texto[:100],
                'url': doc.url,
                'fragmento': self._generar_fragmento(doc, tokens_busqueda),
                'tokens': doc.tokens_total,
                'calidad': doc.calidad,
                'timestamp': doc.timestamp
            })
        
        # Ordenar
        if orden == 'relevancia':
            resultados.sort(key=lambda x: x['score'], reverse=True)
        elif orden == 'fecha':
            resultados.sort(key=lambda x: x['timestamp'], reverse=True)
        elif orden == 'titulo':
            resultados.sort(key=lambda x: x['titulo'])
        
        # Paginar
        total = len(resultados)
        inicio = (pagina - 1) * limite
        fin = inicio + limite
        pagina_resultados = resultados[inicio:fin]
        
        return {
            'exito': True,
            'consulta': consulta,
            'total': total,
            'pagina': pagina,
            'limite': limite,
            'mostrados': len(pagina_resultados),
            'fuzzy_activo': fuzzy,
            'terminos_expandidos': list(terminos_expandidos.keys()),
            'resultados': pagina_resultados
        }
    
    def _generar_fragmento(self, doc: DocumentoIndexado, 
                          terminos: List[str], longitud: int = 200) -> str:
        """Genera un fragmento contextual relevante a los términos de búsqueda."""
        texto = doc.texto
        texto_lower = texto.lower()
        
        mejor_pos = -1
        mejor_score = 0
        
        for termino in terminos:
            pos = texto_lower.find(termino)
            if pos != -1:
                score = self._indice.tfidf(termino, doc.id)
                if score > mejor_score:
                    mejor_score = score
                    mejor_pos = pos
        
        if mejor_pos == -1:
            return texto[:longitud]
        
        inicio = max(0, mejor_pos - longitud // 2)
        fin = min(len(texto), inicio + longitud)
        fragmento = texto[inicio:fin]
        
        if inicio > 0:
            fragmento = '...' + fragmento
        if fin < len(texto):
            fragmento = fragmento + '...'
        
        return fragmento
    
    def _desindexar(self, e: Dict) -> Dict[str, Any]:
        doc_id = e.get('id', '')
        if not doc_id:
            return {'error': 'ID requerido', 'exito': False}
        
        self._indice.desindexar(doc_id)
        self._estadisticas['documentos_indexados'] = self._indice.total_documentos
        self._estadisticas['terminos_unicos'] = self._indice.total_terminos
        
        return {'exito': True, 'id': doc_id, 'total_docs': self._indice.total_documentos}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'documentos_indexados': self._indice.total_documentos,
            'terminos_unicos': self._indice.total_terminos,
            'busquedas_realizadas': self._estadisticas['busquedas_realizadas'],
            'funcionalidades': ['indexar', 'buscar', 'desindexar', 'fuzzy', 'tfidf']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE BÚSQUEDA WEB — TF-IDF + FUZZY")
    print("=" * 70)
    motor = None
    try:
        print(f"\n[0] NumPy: {'✅ ' + np.__version__ if NUMPY_DISPONIBLE else '❌ No (no requerido)'}")
        
        motor = MotorBusquedaWeb()
        motor.inicializar()
        print(f"[1] Motor: {motor.nombre} | Estado: {motor.estado}")
        
        print(f"\n[2] Indexando documentos...")
        documentos = [
            "Inteligencia artificial y aprendizaje automático con Python para redes neuronales",
            "Redes neuronales profundas para procesamiento de lenguaje natural con transformers",
            "Algoritmos de búsqueda y optimización en grafos con inteligencia artificial",
            "Machine learning aplicado a visión por computadora con deep learning",
            "Sistemas distribuidos y arquitectura de microservicios en la nube",
            "Bases de datos NoSQL y almacenamiento en la nube con MongoDB",
            "Desarrollo web con frameworks modernos de JavaScript y Python",
            "Ciberseguridad y protección de datos empresariales con machine learning",
            "Internet de las cosas y dispositivos conectados con sensores inteligentes",
            "Blockchain y criptomonedas descentralizadas con contratos inteligentes",
        ]
        
        for i, texto in enumerate(documentos, 1):
            r = motor.procesar({
                'operacion': 'indexar',
                'id': f'doc_{i}',
                'texto': texto,
                'titulo': f'Documento {i}: {texto[:40]}...',
                'url': f'https://ejemplo.com/doc_{i}',
                'calidad': 0.5 + (i * 0.05),
                'metadata': {'categoria': 'tecnologia', 'idioma': 'es'}
            })
            if r.exito and r.datos:
                print(f"  ✅ doc_{i}: {r.datos['tokens']} tokens | {r.datos['tokens_unicos']} únicos")
        
        print(f"\n[3] Buscando 'inteligencia artificial':")
        r = motor.procesar({'operacion': 'buscar', 'consulta': 'inteligencia artificial', 'limite': 5})
        if r.exito and r.datos:
            print(f"  📊 {r.datos['total']} resultados (mostrando {r.datos['mostrados']}):")
            for res in r.datos['resultados']:
                print(f"  📋 [{res['score']:.4f}] {res['titulo'][:55]}...")
        
        print(f"\n[4] Buscando con AND implícito 'redes neuronales':")
        r = motor.procesar({'operacion': 'buscar', 'consulta': 'redes neuronales', 'limite': 3})
        if r.exito and r.datos:
            for res in r.datos['resultados']:
                print(f"  📋 [{res['score']:.4f}] {res['fragmento'][:80]}...")
        
        print(f"\n[5] Buscando con OR 'python or javascript':")
        r = motor.procesar({'operacion': 'buscar', 'consulta': 'python or javascript', 'limite': 5})
        if r.exito and r.datos:
            print(f"  📊 {r.datos['total']} resultados:")
            for res in r.datos['resultados']:
                print(f"  📋 [{res['score']:.4f}] {res['titulo'][:55]}...")
        
        print(f"\n[6] Búsqueda fuzzy 'inteligensia':")
        r = motor.procesar({'operacion': 'buscar', 'consulta': 'inteligensia', 'fuzzy': True, 'limite': 3})
        if r.exito and r.datos:
            print(f"  📊 {r.datos['total']} resultados (términos: {r.datos['terminos_expandidos']})")
            for res in r.datos['resultados']:
                print(f"  📋 [{res['score']:.4f}] {res['titulo'][:55]}...")
        
        print(f"\n[7] Búsqueda con paginación:")
        r = motor.procesar({'operacion': 'buscar', 'consulta': 'datos', 'limite': 2, 'pagina': 1})
        if r.exito and r.datos:
            print(f"  📄 Página 1: {r.datos['mostrados']} de {r.datos['total']}")
            r2 = motor.procesar({'operacion': 'buscar', 'consulta': 'datos', 'limite': 2, 'pagina': 2})
            if r2.exito and r2.datos:
                print(f"  📄 Página 2: {r2.datos['mostrados']} de {r2.datos['total']}")
        
        print(f"\n[8] Desindexando doc_10:")
        r = motor.procesar({'operacion': 'desindexar', 'id': 'doc_10'})
        if r.exito and r.datos:
            print(f"  ✅ {r.datos['id']} eliminado. {r.datos['total_docs']} docs restantes")
        
        print(f"\n[9] Estadísticas del motor:")
        r = motor.procesar({'operacion': 'info'})
        if r.exito and r.datos:
            s = r.datos
            print(f"  📊 Documentos: {s['documentos_indexados']}")
            print(f"  📊 Términos únicos: {s['terminos_unicos']}")
            print(f"  📊 Búsquedas: {s['busquedas_realizadas']}")
        
        print(f"\n{'='*70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE BÚSQUEDA WEB")
        print(f"   Docs: {r.datos['documentos_indexados']} | "
              f"Términos: {r.datos['terminos_unicos']} | "
              f"Búsquedas: {r.datos['busquedas_realizadas']}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'='*70}\n")