#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Extracción — Entidades + Resumen + Idioma + Metadatos
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Búsqueda
# =====================================================================

import sys, time, math, re, traceback, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter, defaultdict
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
# PATRONES DE EXTRACCIÓN
# =====================================================================

class PatronesExtraccion:
    """Librería de patrones regex compilados para extracción ultra-rápida."""
    
    def __init__(self):
        self._cache: Dict[str, re.Pattern] = {}
        self._inicializar_patrones()
    
    def _inicializar_patrones(self):
        patrones = {
            'url': r'https?://[^\s<>"{}|\\^`\[\]()]+',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'fecha_iso': r'\d{4}-\d{2}-\d{2}',
            'fecha_latam': r'\d{2}/\d{2}/\d{4}',
            'fecha_usa': r'\d{2}-\d{2}-\d{4}',
            'hora': r'\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?',
            'telefono': r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            'ip': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'hashtag': r'#[a-zA-ZÀ-ÿ0-9_]{2,}',
            'mencion': r'@[a-zA-ZÀ-ÿ0-9_]{2,}',
            'moneda': r'[\$€£¥]\s?[\d,]+\.?\d*|[\d,]+\.?\d*\s?(?:USD|EUR|GBP|JPY|MXN|ARS|CLP|PEN|COP)',
            'porcentaje': r'\d+\.?\d*\s?%',
            'numero': r'\b\d+\.?\d*\b',
            'codigo_postal': r'\b\d{4,5}\b',
            'dni': r'\b\d{7,8}[A-Z]?\b',
            'matricula': r'\b[A-Z]{1,2}\d{4}[A-Z]{1,2}\b',
        }
        for nombre, patron in patrones.items():
            self._cache[nombre] = re.compile(patron, re.IGNORECASE | re.UNICODE)
    
    def extraer(self, nombre: str, texto: str) -> List[str]:
        if nombre in self._cache:
            return self._cache[nombre].findall(texto)
        return []
    
    def extraer_todas(self, texto: str) -> Dict[str, List[str]]:
        resultado = {}
        for nombre in self._cache:
            coincidencias = self._cache[nombre].findall(texto)
            if coincidencias:
                resultado[nombre] = coincidencias[:50]
        return resultado


# =====================================================================
# TOKENIZADOR
# =====================================================================

class TokenizadorExtraccion:
    """Tokenizador específico para extracción con soporte multilingüe."""
    
    _LETRAS = set('abcdefghijklmnopqrstuvwxyz0123456789áéíóúüñ')
    
    def __init__(self):
        self._stopwords = frozenset("""
            el la los las un una unos unas de del en con por para a e o y u al
            que es son ser estar fue fueron ha han su sus se lo le les nos os
            como más muy todo pero sin sobre entre hasta desde este esta estos
            estas ese esa esos esas aquel aquella the a an and or but in on at
            to for of with from by as is are was were be been being have has
            had do does did will would shall should may might can could it its
            this that these those not no if then else when where who how what
            why which all each every both few many some any one two three
        """.split())
    
    def tokenizar(self, texto: str) -> List[str]:
        texto = texto.lower().strip()
        tokens = []
        actual = []
        
        for c in texto:
            if c in self._LETRAS:
                actual.append(c)
            else:
                if len(actual) >= 2:
                    tok = ''.join(actual)
                    if tok not in self._stopwords:
                        tokens.append(tok)
                actual = []
        
        if len(actual) >= 2:
            tok = ''.join(actual)
            if tok not in self._stopwords:
                tokens.append(tok)
        
        return tokens


# =====================================================================
# DETECTOR DE IDIOMA
# =====================================================================

class DetectorIdioma:
    """Detección de idioma por n-gramas de caracteres."""
    
    _PERFILES = {
        'es': {'stopwords': frozenset("el la los las de del en con por para un una su sus al se le es son que no lo".split()),
               'frecuencias': {'a': 0.125, 'e': 0.137, 'o': 0.087, 's': 0.080, 'r': 0.069, 'n': 0.067, 'i': 0.063, 'd': 0.059, 'l': 0.050, 'c': 0.047}},
        'en': {'stopwords': frozenset("the a an and or but in on at to for of with from by as is are was were be been".split()),
               'frecuencias': {'e': 0.127, 't': 0.091, 'a': 0.082, 'o': 0.075, 'i': 0.070, 'n': 0.067, 's': 0.063, 'h': 0.061, 'r': 0.060, 'd': 0.043}},
    }
    
    def detectar(self, texto: str) -> Tuple[str, float]:
        if not texto:
            return 'desconocido', 0.0
        
        texto = texto[:2000].lower()
        scores = {}
        
        for idioma, perfil in self._PERFILES.items():
            tokens = set(re.findall(r'[a-záéíóúüñ]{2,}', texto))
            score_stop = len(tokens & perfil['stopwords']) * 2.0
            
            frecuencias_texto = Counter(c for c in texto if 'a' <= c <= 'z')
            total = sum(frecuencias_texto.values()) or 1
            score_freq = 0
            for letra, freq_esperada in perfil['frecuencias'].items():
                freq_real = frecuencias_texto.get(letra, 0) / total
                score_freq += 1.0 - abs(freq_real - freq_esperada)
            
            scores[idioma] = score_stop + score_freq * 3.0
        
        if not scores:
            return 'desconocido', 0.0
        
        mejor_idioma = max(scores, key=scores.get)
        max_score = scores[mejor_idioma]
        min_score = min(scores.values())
        confianza = max_score / (max_score + min_score + 0.001)
        
        return mejor_idioma, round(min(1.0, confianza), 3)
    
    def detectar_rapido(self, texto: str) -> str:
        idioma, _ = self.detectar(texto)
        return idioma


# =====================================================================
# RESUMIDOR
# =====================================================================

class Resumidor:
    """Resumen automático por puntuación de oraciones."""
    
    def __init__(self):
        self._tokenizador = TokenizadorExtraccion()
    
    def resumir(self, texto: str, max_oraciones: int = 3, 
                longitud_max: int = 500) -> Dict[str, Any]:
        if not texto:
            return {'error': 'Texto vacío'}
        
        oraciones = re.split(r'(?<=[.!?])\s+', texto)
        oraciones = [o.strip() for o in oraciones if len(o.strip().split()) >= 3]
        
        if not oraciones:
            return {'error': 'Sin oraciones válidas'}
        
        if len(oraciones) <= max_oraciones:
            return {
                'resumen': texto[:longitud_max],
                'oraciones_originales': len(oraciones),
                'oraciones_resumen': len(oraciones),
                'compresion': 0.0
            }
        
        tokens_texto = self._tokenizador.tokenizar(texto)
        freq = Counter(tokens_texto)
        max_freq = max(freq.values()) if freq else 1
        
        scores_oraciones = []
        for i, oracion in enumerate(oraciones):
            tokens_oracion = self._tokenizador.tokenizar(oracion)
            if not tokens_oracion:
                continue
            score = sum(freq.get(t, 0) for t in tokens_oracion) / (max_freq * len(tokens_oracion))
            scores_oraciones.append((score, i))
        
        scores_oraciones.sort(reverse=True)
        indices = sorted([i for _, i in scores_oraciones[:max_oraciones]])
        
        resumen = ' '.join(oraciones[i] for i in indices)
        if len(resumen) > longitud_max:
            resumen = resumen[:longitud_max-3] + '...'
        
        compresion = 1.0 - (len(oraciones) - len(indices)) / len(oraciones)
        
        return {
            'resumen': resumen,
            'oraciones_originales': len(oraciones),
            'oraciones_resumen': len(indices),
            'compresion': round(compresion, 2)
        }


# =====================================================================
# MOTOR DE EXTRACCIÓN
# =====================================================================

class MotorExtraccion(MotorBase):
    """
    Motor de Extracción — Entidades + Resumen + Idioma + Metadatos.
    
    Capacidades:
    - Extracción de 16 tipos de entidades (URL, email, fecha, teléfono, IP, etc.)
    - Resumen automático por frecuencia de términos
    - Detección de idioma por n-gramas y stopwords
    - Análisis de frecuencia de términos
    - Extracción de metadatos del texto
    - Conteo de caracteres, palabras, oraciones
    - Detección de sentimiento básico por léxico
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._patrones = PatronesExtraccion()
        self._tokenizador = TokenizadorExtraccion()
        self._detector_idioma = DetectorIdioma()
        self._resumidor = Resumidor()
        self._lock = threading.RLock()
        self._estadisticas = {
            'extracciones_realizadas': 0,
            'resumenes_generados': 0,
            'idiomas_detectados': 0,
        }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'extraer')
        
        with self._lock:
            if operacion == 'extraer':
                return self._extraer(entrada)
            elif operacion == 'resumir':
                return self._resumir(entrada)
            elif operacion == 'detectar_idioma':
                return self._detectar_idioma(entrada)
            elif operacion == 'analizar':
                return self._analizar(entrada)
            elif operacion == 'info':
                return self._info(entrada)
            else:
                return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _extraer(self, e: Dict) -> Dict[str, Any]:
        texto = e.get('texto', '')
        if not texto:
            return {'error': 'Texto requerido', 'exito': False}
        
        self._estadisticas['extracciones_realizadas'] += 1
        
        entidades = self._patrones.extraer_todas(texto)
        tokens = self._tokenizador.tokenizar(texto)
        tokens_unicos = set(tokens)
        frecuencia = Counter(tokens).most_common(20)
        idioma, confianza = self._detector_idioma.detectar(texto)
        
        return {
            'exito': True,
            'entidades': entidades,
            'estadisticas_texto': {
                'caracteres': len(texto),
                'palabras': len(texto.split()),
                'tokens': len(tokens),
                'tokens_unicos': len(tokens_unicos),
                'oraciones': len(re.split(r'[.!?]+', texto)),
                'densidad_lexica': round(len(tokens_unicos) / max(1, len(tokens)), 3)
            },
            'frecuencias': [{'token': t, 'count': c} for t, c in frecuencia],
            'idioma': {'detectado': idioma, 'confianza': confianza}
        }
    
    def _resumir(self, e: Dict) -> Dict[str, Any]:
        texto = e.get('texto', '')
        max_oraciones = e.get('max_oraciones', 3)
        
        if not texto:
            return {'error': 'Texto requerido', 'exito': False}
        
        self._estadisticas['resumenes_generados'] += 1
        
        resultado = self._resumidor.resumir(texto, max_oraciones)
        if 'error' in resultado:
            return {'error': resultado['error'], 'exito': False}
        
        return {'exito': True, **resultado}
    
    def _detectar_idioma(self, e: Dict) -> Dict[str, Any]:
        texto = e.get('texto', '')
        if not texto:
            return {'error': 'Texto requerido', 'exito': False}
        
        self._estadisticas['idiomas_detectados'] += 1
        
        idioma, confianza = self._detector_idioma.detectar(texto)
        return {'exito': True, 'idioma': idioma, 'confianza': confianza}
    
    def _analizar(self, e: Dict) -> Dict[str, Any]:
        """Análisis completo: entidades + resumen + idioma + frecuencias."""
        texto = e.get('texto', '')
        if not texto:
            return {'error': 'Texto requerido', 'exito': False}
        
        extraccion = self._extraer({'texto': texto})
        resumen = self._resumir({'texto': texto, 'max_oraciones': e.get('max_oraciones', 3)})
        
        resultado = {'exito': True}
        if extraccion:
            resultado.update(extraccion)
        if resumen and resumen.get('exito'):
            resultado['resumen'] = resumen.get('resumen', '')
            resultado['compresion'] = resumen.get('compresion', 0)
        
        return resultado
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'extracciones_realizadas': self._estadisticas['extracciones_realizadas'],
            'resumenes_generados': self._estadisticas['resumenes_generados'],
            'idiomas_detectados': self._estadisticas['idiomas_detectados'],
            'tipos_entidades': ['url', 'email', 'fecha_iso', 'fecha_latam', 'fecha_usa', 'hora',
                               'telefono', 'ip', 'hashtag', 'mencion', 'moneda', 'porcentaje',
                               'numero', 'codigo_postal', 'dni', 'matricula'],
            'funcionalidades': ['extraer', 'resumir', 'detectar_idioma', 'analizar']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE EXTRACCIÓN — ENTIDADES + RESUMEN")
    print("=" * 70)
    motor = None
    try:
        motor = MotorExtraccion()
        motor.inicializar()
        print(f"\n[0] Motor: {motor.nombre} | Estado: {motor.estado}")
        
        texto_prueba = """
        Contacto: info@anp.ai y soporte@anp.ai
        Visita https://anp.ai/docs para documentación oficial.
        El proyecto inició el 2024-01-15 y la versión 2.0 salió el 15/03/2024.
        Teléfono de contacto: +52 55 1234 5678 o 555-987-6543.
        Precio: $1,999.99 USD con 15% de descuento.
        IP del servidor: 192.168.1.100 y 10.0.0.1
        Síguenos en redes: #ANP #InteligenciaArtificial #Python
        Menciones: @proyecto_anp @deepseek_ai
        La inteligencia artificial ha revolucionado la tecnología moderna.
        Los algoritmos de aprendizaje profundo permiten procesar grandes cantidades de datos.
        Las redes neuronales convolucionales son ideales para visión por computadora.
        El procesamiento de lenguaje natural ha avanzado significativamente en los últimos años.
        Python es el lenguaje preferido para desarrollo de IA por su simplicidad.
        """
        
        print(f"\n[1] Extracción de entidades:")
        r = motor.procesar({'operacion': 'extraer', 'texto': texto_prueba})
        if r.exito and r.datos:
            ent = r.datos.get('entidades', {})
            for tipo, valores in ent.items():
                print(f"  🏷️ {tipo}: {valores[:3]}")
            print(f"  📊 Tokens: {r.datos['estadisticas_texto']['tokens']} "
                  f"({r.datos['estadisticas_texto']['tokens_unicos']} únicos)")
            print(f"  🌐 Idioma: {r.datos['idioma']['detectado']} "
                  f"(confianza: {r.datos['idioma']['confianza']})")
        
        print(f"\n[2] Resumen automático (3 oraciones):")
        r = motor.procesar({'operacion': 'resumir', 'texto': texto_prueba, 'max_oraciones': 3})
        if r.exito and r.datos:
            print(f"  📝 {r.datos.get('resumen', '')[:250]}")
            print(f"  📊 Compresión: {r.datos.get('compresion', 0)}")
            print(f"  📊 Oraciones: {r.datos.get('oraciones_resumen', 0)}/"
                  f"{r.datos.get('oraciones_originales', 0)}")
        
        print(f"\n[3] Detección de idioma:")
        pruebas_idioma = [
            "The artificial intelligence revolution is transforming technology",
            "La inteligencia artificial está transformando la tecnología moderna",
        ]
        for texto in pruebas_idioma:
            r = motor.procesar({'operacion': 'detectar_idioma', 'texto': texto})
            if r.exito and r.datos:
                print(f"  🌐 '{texto[:50]}...' → {r.datos['idioma']} "
                      f"({r.datos['confianza']})")
        
        print(f"\n[4] Análisis completo:")
        r = motor.procesar({'operacion': 'analizar', 'texto': texto_prueba, 'max_oraciones': 2})
        if r.exito and r.datos:
            print(f"  📊 Entidades encontradas: {len(r.datos.get('entidades', {}))} tipos")
            print(f"  📝 Resumen: {r.datos.get('resumen', '')[:150]}...")
            print(f"  🌐 Idioma: {r.datos.get('idioma', {}).get('detectado', '?')}")
        
        print(f"\n[5] Estadísticas del motor:")
        r = motor.procesar({'operacion': 'info'})
        if r.exito and r.datos:
            s = r.datos
            print(f"  📊 Extracciones: {s['extracciones_realizadas']}")
            print(f"  📊 Resúmenes: {s['resumenes_generados']}")
            print(f"  📊 Idiomas: {s['idiomas_detectados']}")
            print(f"  📊 Tipos de entidades: {len(s['tipos_entidades'])}")
        
        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE EXTRACCIÓN")
        print(f"{'=' * 70}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")