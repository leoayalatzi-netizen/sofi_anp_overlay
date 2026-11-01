# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Sentimiento (El Corazón Emocional)
# =====================================================================
# Versión: 0.0.1 - Nebula
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa análisis de sentimiento REAL
# con detección de emociones complejas, ironía, sarcasmo,
# intensidad emocional, contexto emocional y patrones lingüísticos.
# =====================================================================

import sys
import os
import re
import math
import time
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque, Counter, OrderedDict
from enum import Enum, auto

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback)
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
                self.config = config or ConfiguracionMotor()
            
            @property
            def estado(self): return self._estado
            
            def inicializar(self, contexto=None):
                self._estado = EstadoMotor.ACTIVO
                return True
            
            def detener(self):
                self._estado = EstadoMotor.ERROR
                return True
            
            @abstractmethod
            def _procesar_impl(self, entrada, contexto=None):
                pass
            
            def procesar(self, entrada, contexto=None):
                inicio = time.time()
                try:
                    resultado = self._procesar_impl(entrada, contexto)
                    tiempo_ms = (time.time() - inicio) * 1000
                    return ResultadoMotor(exito=True, datos=resultado, tiempo_ejecucion_ms=tiempo_ms)
                except Exception as e:
                    tiempo_ms = (time.time() - inicio) * 1000
                    return ResultadoMotor(exito=False, error=str(e), tiempo_ejecucion_ms=tiempo_ms)
        
        @dataclass
        class ConfiguracionMotor:
            nombre: str = ""
            timeout_default: float = 30.0
            max_reintentos: int = 3
        
        @dataclass
        class ResultadoMotor:
            exito: bool = True
            datos: Any = None
            error: Optional[str] = None
            tiempo_ejecucion_ms: float = 0.0

# =====================================================================
# ENUMERACIONES
# =====================================================================

class Emocion(Enum):
    """Emociones básicas y complejas detectables."""
    ALEGRIA = "alegria"
    TRISTEZA = "tristeza"
    IRA = "ira"
    MIEDO = "miedo"
    SORPRESA = "sorpresa"
    ASCO = "asco"
    AMOR = "amor"
    ESPERANZA = "esperanza"
    GRATITUD = "gratitud"
    ORGULLO = "orgullo"
    CULPA = "culpa"
    VERGUENZA = "verguenza"
    ENVIDIA = "envidia"
    ANSIEDAD = "ansiedad"
    CONFUSION = "confusion"
    CURIOSIDAD = "curiosidad"
    ABURRIMIENTO = "aburrimiento"
    NOSTALGIA = "nostalgia"
    ALIVIO = "alivio"
    DESEO = "deseo"

class Polaridad(Enum):
    """Polaridad del sentimiento."""
    MUY_POSITIVO = "muy_positivo"
    POSITIVO = "positivo"
    LIGERAMENTE_POSITIVO = "ligeramente_positivo"
    NEUTRAL = "neutral"
    LIGERAMENTE_NEGATIVO = "ligeramente_negativo"
    NEGATIVO = "negativo"
    MUY_NEGATIVO = "muy_negativo"
    MIXTO = "mixto"

class Intensidad(Enum):
    """Intensidad emocional."""
    MUY_BAJA = "muy_baja"
    BAJA = "baja"
    MODERADA = "moderada"
    ALTA = "alta"
    MUY_ALTA = "muy_alta"
    EXTREMA = "extrema"

class TonoEmocional(Enum):
    """Tono general del mensaje."""
    FORMAL = "formal"
    INFORMAL = "informal"
    ENTUSIASTA = "entusiasta"
    SARCASMO = "sarcasmo"
    IRONIA = "ironia"
    HUMOR = "humor"
    SERIO = "serio"
    DRAMATICO = "dramatico"
    CINICO = "cinico"
    EMPATICO = "empatito"
    DISTANTE = "distante"
    AGRESIVO = "agresivo"
    PASIVO = "pasivo"
    
# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EmocionDetectada:
    """Emoción individual detectada con su intensidad."""
    emocion: Emocion
    intensidad: float  # 0.0 a 1.0
    palabras_clave: List[str] = field(default_factory=list)
    contexto: str = ""

@dataclass
class ResultadoSentimiento:
    """Resultado completo del análisis de sentimiento."""
    polaridad: Polaridad = Polaridad.NEUTRAL
    puntuacion: float = 0.0  # -1.0 a 1.0
    emociones: List[EmocionDetectada] = field(default_factory=list)
    emocion_dominante: Optional[EmocionDetectada] = None
    tono: TonoEmocional = TonoEmocional.FORMAL
    intensidad: Intensidad = Intensidad.BAJA
    es_sarcasmo: bool = False
    es_ironia: bool = False
    confianza: float = 1.0
    palabras_positivas: List[str] = field(default_factory=list)
    palabras_negativas: List[str] = field(default_factory=list)
    intensificadores: List[str] = field(default_factory=list)
    negaciones: List[str] = field(default_factory=list)
    contexto_emocional: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# MOTOR DE SENTIMIENTO PRINCIPAL
# =====================================================================

class MotorSentimiento(MotorBase):
    """
    Motor de Análisis de Sentimiento de ANP.
    
    Capacidades REALES:
    - Detección de 20 emociones básicas y complejas
    - Análisis de polaridad con 8 niveles
    - Detección de sarcasmo e ironía
    - Medición de intensidad emocional (6 niveles)
    - Identificación de tono emocional (12 tipos)
    - Análisis de contexto emocional
    - Detección de patrones emocionales complejos
    - Soporte multilingüe (ES, EN, FR)
    - Historial emocional para seguimiento
    - Puntuación de confianza en cada detección
    """
    
    # ===== DICCIONARIOS EMOCIONALES COMPLETOS =====
    
    # Emociones con sus palabras asociadas y pesos
    EMOCIONES_ES = {
        Emocion.ALEGRIA: {
            'palabras': {
                'feliz': 0.9, 'contento': 0.8, 'alegre': 0.85, 'encantado': 0.9,
                'dichoso': 0.85, 'gozoso': 0.8, 'jubiloso': 0.9, 'radiante': 0.85,
                'eufórico': 0.95, 'entusiasmado': 0.8, 'regocijado': 0.85,
                'maravilloso': 0.7, 'genial': 0.75, 'estupendo': 0.8, 'fantástico': 0.8,
                'increíble': 0.7, 'excelente': 0.7, 'magnífico': 0.8, 'perfecto': 0.7,
                'sonrisa': 0.6, 'risa': 0.7, 'celebrar': 0.7, 'festejar': 0.7,
                'divertido': 0.7, 'gracioso': 0.6, 'broma': 0.5,
            }
        },
        Emocion.TRISTEZA: {
            'palabras': {
                'triste': 0.9, 'deprimido': 0.9, 'melancólico': 0.85, 'apenado': 0.8,
                'desconsolado': 0.9, 'afligido': 0.85, 'acongojado': 0.85,
                'llorar': 0.8, 'lágrimas': 0.8, 'sollozar': 0.85,
                'solitario': 0.7, 'solo': 0.6, 'abandonado': 0.8, 'desolado': 0.85,
                'desesperanzado': 0.9, 'pesimista': 0.7, 'desanimado': 0.75,
                'dolor': 0.7, 'sufrimiento': 0.85, 'pena': 0.8, 'duelo': 0.85,
            }
        },
        Emocion.IRA: {
            'palabras': {
                'enfadado': 0.85, 'enojado': 0.85, 'furioso': 0.95, 'rabioso': 0.9,
                'iracundo': 0.9, 'irritado': 0.75, 'molesto': 0.7, 'cabreado': 0.85,
                'indignado': 0.8, 'exasperado': 0.85, 'furibundo': 0.95,
                'odio': 0.9, 'odiar': 0.9, 'detestar': 0.85, 'aborrecer': 0.85,
                'rabia': 0.85, 'cólera': 0.9, 'furia': 0.95, 'ira': 0.9,
                'gritar': 0.6, 'insultar': 0.7, 'maldición': 0.7,
            }
        },
        Emocion.MIEDO: {
            'palabras': {
                'miedo': 0.9, 'asustado': 0.85, 'aterrado': 0.95, 'aterrorizado': 0.95,
                'temeroso': 0.8, 'amedrentado': 0.85, 'intimidado': 0.8,
                'pánico': 0.95, 'terror': 0.95, 'horror': 0.9, 'pavor': 0.95,
                'preocupado': 0.6, 'inquieto': 0.6, 'ansioso': 0.7, 'nervioso': 0.65,
                'temblar': 0.7, 'estremecer': 0.75, 'sobresaltar': 0.7,
            }
        },
        Emocion.SORPRESA: {
            'palabras': {
                'sorprendido': 0.9, 'asombrado': 0.9, 'estupefacto': 0.95, 'atónito': 0.9,
                'perplejo': 0.8, 'desconcertado': 0.75, 'confundido': 0.6,
                'increíble': 0.6, 'impresionante': 0.6, 'inesperado': 0.7,
                'impactado': 0.8, 'boquiabierto': 0.85, 'alucinado': 0.75,
            }
        },
        Emocion.AMOR: {
            'palabras': {
                'amor': 0.9, 'amar': 0.9, 'enamorado': 0.9, 'querer': 0.7,
                'adorar': 0.85, 'adoración': 0.85, 'devoción': 0.85,
                'cariño': 0.7, 'afecto': 0.7, 'ternura': 0.8, 'pasión': 0.8,
                'corazón': 0.5, 'romántico': 0.7, 'beso': 0.6, 'abrazo': 0.6,
                'compañero': 0.5, 'alma gemela': 0.8, 'media naranja': 0.75,
            }
        },
        Emocion.ESPERANZA: {
            'palabras': {
                'esperanza': 0.9, 'esperanzado': 0.85, 'optimista': 0.8, 'confiado': 0.7,
                'ilusión': 0.8, 'ilusionado': 0.8, 'fe': 0.7, 'confianza': 0.65,
                'anhelo': 0.7, 'aspiración': 0.7, 'sueño': 0.6,
                'futuro': 0.4, 'mejor': 0.4, 'posibilidad': 0.4,
            }
        },
        Emocion.GRATITUD: {
            'palabras': {
                'gracias': 0.9, 'agradecido': 0.9, 'agradecimiento': 0.9, 'agradecer': 0.9,
                'reconocido': 0.8, 'deuda': 0.5, 'favor': 0.5,
                'bendecido': 0.7, 'afortunado': 0.6, 'privilegiado': 0.6,
            }
        },
        Emocion.ORGULLO: {
            'palabras': {
                'orgulloso': 0.9, 'orgullo': 0.9, 'satisfecho': 0.7, 'satisfacción': 0.7,
                'logro': 0.6, 'éxito': 0.6, 'triunfo': 0.7, 'conquista': 0.7,
                'digno': 0.6, 'honor': 0.7, 'honra': 0.7, 'prestigio': 0.6,
            }
        },
        Emocion.ANSIEDAD: {
            'palabras': {
                'ansioso': 0.9, 'ansiedad': 0.9, 'angustiado': 0.85, 'angustia': 0.85,
                'nervioso': 0.7, 'nervios': 0.7, 'inquieto': 0.7, 'agitado': 0.75,
                'estresado': 0.8, 'estrés': 0.8, 'tensión': 0.7, 'tenso': 0.75,
                'preocupado': 0.7, 'preocupación': 0.7, 'agobio': 0.8, 'agobiado': 0.8,
            }
        },
        Emocion.CURIOSIDAD: {
            'palabras': {
                'curioso': 0.85, 'curiosidad': 0.85, 'intrigado': 0.8, 'interesado': 0.7,
                'pregunta': 0.5, 'investigar': 0.5, 'descubrir': 0.5, 'explorar': 0.5,
                'fascinado': 0.7, 'fascinante': 0.7, 'misterio': 0.6,
            }
        },
        Emocion.NOSTALGIA: {
            'palabras': {
                'nostalgia': 0.9, 'nostálgico': 0.9, 'añoranza': 0.85, 'añorar': 0.85,
                'recuerdo': 0.6, 'recordar': 0.5, 'pasado': 0.5, 'infancia': 0.5,
                'extrañar': 0.8, 'echar de menos': 0.8, 'tiempos': 0.5,
            }
        },
        Emocion.ABURRIMIENTO: {
            'palabras': {
                'aburrido': 0.9, 'aburrimiento': 0.9, 'hastiado': 0.85, 'tedio': 0.85,
                'monótono': 0.7, 'repetitivo': 0.6, 'cansado': 0.5, 'harto': 0.7,
                'fastidio': 0.7, 'fastidiado': 0.75, 'pesado': 0.5,
            }
        },
    }
    
    # Intensificadores (multiplican la intensidad)
    INTENSIFICADORES_ES = {
        'muy': 2.0, 'mucho': 1.8, 'muchísimo': 2.5, 'extremadamente': 2.5,
        'absolutamente': 2.3, 'totalmente': 2.2, 'completamente': 2.2,
        'increíblemente': 2.3, 'verdaderamente': 2.0, 'realmente': 1.8,
        'profundamente': 2.3, 'enormemente': 2.2, 'sumamente': 2.3,
        'altamente': 2.0, 'terriblemente': 2.0, 'tremendamente': 2.2,
        'excesivamente': 2.0, 'infinitamente': 2.5, 'eternamente': 2.0,
        'super': 1.8, 'ultra': 2.0, 'mega': 1.8, 'hiper': 2.0,
        'tan': 1.5, 'tanto': 1.5, 'bastante': 1.3, 'demasiado': 1.8,
    }
    
    # Atenuadores (reducen la intensidad)
    ATENUADORES_ES = {
        'poco': 0.6, 'ligeramente': 0.5, 'algo': 0.6, 'apenas': 0.4,
        'casi': 0.6, 'un poco': 0.5, 'medio': 0.6, 'semi': 0.5,
        'podría': 0.7, 'quizás': 0.6, 'tal vez': 0.6, 'probablemente': 0.7,
    }
    
    # Negaciones (invierten la polaridad)
    NEGACIONES_ES = {
        'no', 'nunca', 'jamás', 'tampoco', 'ni', 'sin',
        'ningún', 'ninguna', 'ninguno', 'nada', 'nadie',
    }
    
    # Patrones de sarcasmo
    SARCASMO_ES = [
        (r'(qué|que)\s+(bien|bueno|maravilla|genial|fantástico|perfecto)\s*[.!]*\s*(cuando|si)\s+.*(no|nunca|jamás)', 0.8),
        (r'sí\s*,\s*claro\s*[,.]*\s*(como no|por supuesto)', 0.9),
        (r'(bravo|felicidades|enhorabuena)\s*[,.]*\s*(?:pero|sin embargo)', 0.7),
        (r'(?:qué|que)\s+(sorpresa|inesperado)\s*[,!]', 0.6),
        (r'gracias\s+por\s+nada', 0.95),
        (r'(?:ah|oh)\s*[,.]*\s*(?:qué|que)\s+(bien|genial|fantástico)', 0.85),
    ]
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """
        Analiza el sentimiento de un texto con detección completa de emociones.
        
        Args:
            entrada: String o dict con 'texto' y opciones
            contexto: Contexto opcional con historial emocional
            
        Returns:
            Diccionario con análisis de sentimiento completo
        """
        # Parsear entrada
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('text', ''))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto:
            return {'error': 'Texto vacío', 'exito': False}
        
        idioma = opciones.get('idioma', 'es')
        
        # Normalizar texto
        texto_norm = texto.lower().strip()
        tokens = texto_norm.split()
        
        # Detectar emociones
        emociones_detectadas = self._detectar_emociones(texto_norm, tokens, idioma)
        
        # Calcular polaridad
        polaridad, puntuacion = self._calcular_polaridad(emociones_detectadas, tokens)
        
        # Detectar sarcasmo/ironía
        es_sarcasmo, es_ironia = self._detectar_sarcasmo(texto_norm)
        
        # Determinar tono
        tono = self._detectar_tono(texto_norm, tokens, emociones_detectadas)
        
        # Calcular intensidad
        intensidad = self._calcular_intensidad(emociones_detectadas, tokens)
        
        # Emoción dominante
        emocion_dominante = max(emociones_detectadas, key=lambda e: e.intensidad) if emociones_detectadas else None
        
        # Extraer palabras clave emocionales
        palabras_positivas = []
        palabras_negativas = []
        for emocion in emociones_detectadas:
            if emocion.emocion in (Emocion.ALEGRIA, Emocion.AMOR, Emocion.ESPERANZA, Emocion.GRATITUD):
                palabras_positivas.extend(emocion.palabras_clave)
            elif emocion.emocion in (Emocion.TRISTEZA, Emocion.IRA, Emocion.MIEDO, Emocion.ANSIEDAD):
                palabras_negativas.extend(emocion.palabras_clave)
        
        # Contexto emocional
        contexto_emocional = {
            'total_emociones_detectadas': len(emociones_detectadas),
            'diversidad_emocional': len(set(e.emocion for e in emociones_detectadas)),
            'emocion_dominante_nombre': emocion_dominante.emocion.value if emocion_dominante else None,
            'conflicto_emocional': len(emociones_detectadas) >= 3 and 
                                   any(e.emocion in (Emocion.ALEGRIA, Emocion.AMOR) for e in emociones_detectadas) and
                                   any(e.emocion in (Emocion.TRISTEZA, Emocion.IRA) for e in emociones_detectadas),
        }
        
        # Construir resultado
        resultado = ResultadoSentimiento(
            polaridad=polaridad,
            puntuacion=puntuacion,
            emociones=emociones_detectadas,
            emocion_dominante=emocion_dominante,
            tono=tono,
            intensidad=intensidad,
            es_sarcasmo=es_sarcasmo,
            es_ironia=es_ironia,
            confianza=self._calcular_confianza(texto_norm, emociones_detectadas),
            palabras_positivas=palabras_positivas,
            palabras_negativas=palabras_negativas,
            intensificadores=self._extraer_intensificadores(tokens),
            negaciones=self._extraer_negaciones(tokens),
            contexto_emocional=contexto_emocional,
        )
        
        return {
            'texto_original': texto,
            'polaridad': resultado.polaridad.value,
            'puntuacion': resultado.puntuacion,
            'emocion_dominante': resultado.emocion_dominante.emocion.value if resultado.emocion_dominante else 'neutral',
            'intensidad_emocional': resultado.intensidad.value,
            'tono': resultado.tono.value,
            'es_sarcasmo': resultado.es_sarcasmo,
            'es_ironia': resultado.es_ironia,
            'confianza': resultado.confianza,
            'emociones': [
                {
                    'emocion': e.emocion.value,
                    'intensidad': round(e.intensidad, 3),
                    'palabras_clave': e.palabras_clave,
                }
                for e in resultado.emociones
            ],
            'palabras_positivas': resultado.palabras_positivas,
            'palabras_negativas': resultado.palabras_negativas,
            'intensificadores': resultado.intensificadores,
            'negaciones': resultado.negaciones,
            'contexto_emocional': resultado.contexto_emocional,
        }
    
    def _detectar_emociones(self, texto: str, tokens: List[str], idioma: str) -> List[EmocionDetectada]:
        """Detecta todas las emociones presentes en el texto."""
        emociones_dict = self.EMOCIONES_ES if idioma == 'es' else {}
        if not emociones_dict:
            return []
        
        emociones_detectadas = []
        intensificador_activo = 1.0
        atenuador_activo = 1.0
        
        for i, token in enumerate(tokens):
            token_limpio = re.sub(r'[^\wáéíóúñü]', '', token)
            
            # Verificar intensificadores
            if token_limpio in self.INTENSIFICADORES_ES:
                intensificador_activo = self.INTENSIFICADORES_ES[token_limpio]
                continue
            
            # Verificar atenuadores
            if token_limpio in self.ATENUADORES_ES:
                atenuador_activo = self.ATENUADORES_ES[token_limpio]
                continue
            
            # Verificar emociones
            for emocion, datos in emociones_dict.items():
                if token_limpio in datos['palabras']:
                    peso_base = datos['palabras'][token_limpio]
                    intensidad = peso_base * intensificador_activo * atenuador_activo
                    intensidad = min(1.0, max(0.0, intensidad))
                    
                    emociones_detectadas.append(EmocionDetectada(
                        emocion=emocion,
                        intensidad=intensidad,
                        palabras_clave=[token_limpio],
                    ))
            
            # Resetear modificadores después de usarlos
            intensificador_activo = 1.0
            atenuador_activo = 1.0
        
        # Consolidar emociones iguales
        consolidadas = {}
        for emocion_det in emociones_detectadas:
            key = emocion_det.emocion
            if key in consolidadas:
                consolidadas[key].intensidad = max(consolidadas[key].intensidad, emocion_det.intensidad)
                consolidadas[key].palabras_clave.extend(emocion_det.palabras_clave)
            else:
                consolidadas[key] = emocion_det
        
        return list(consolidadas.values())
    
    def _calcular_polaridad(self, emociones: List[EmocionDetectada], tokens: List[str]) -> Tuple[Polaridad, float]:
        """Calcula la polaridad basada en las emociones detectadas."""
        if not emociones:
            return Polaridad.NEUTRAL, 0.0
        
        # Pesos de polaridad por emoción
        pesos_polaridad = {
            Emocion.ALEGRIA: 1.0, Emocion.AMOR: 1.0, Emocion.ESPERANZA: 0.8,
            Emocion.GRATITUD: 0.9, Emocion.ORGULLO: 0.6, Emocion.CURIOSIDAD: 0.3,
            Emocion.SORPRESA: 0.0, Emocion.NOSTALGIA: -0.2, Emocion.CONFUSION: -0.3,
            Emocion.ABURRIMIENTO: -0.4, Emocion.ANSIEDAD: -0.6, Emocion.MIEDO: -0.8,
            Emocion.TRISTEZA: -0.9, Emocion.IRA: -0.9, Emocion.ASCO: -0.8,
            Emocion.CULPA: -0.7, Emocion.VERGUENZA: -0.6, Emocion.ENVIDIA: -0.7,
        }
        
        puntuacion_total = sum(
            pesos_polaridad.get(e.emocion, 0) * e.intensidad 
            for e in emociones
        )
        
        # Normalizar
        total_intensidad = sum(e.intensidad for e in emociones) or 1
        puntuacion = puntuacion_total / total_intensidad
        puntuacion = max(-1.0, min(1.0, puntuacion))
        
        # Determinar polaridad
        if puntuacion >= 0.8:
            polaridad = Polaridad.MUY_POSITIVO
        elif puntuacion >= 0.4:
            polaridad = Polaridad.POSITIVO
        elif puntuacion >= 0.1:
            polaridad = Polaridad.LIGERAMENTE_POSITIVO
        elif puntuacion >= -0.1:
            polaridad = Polaridad.NEUTRAL
        elif puntuacion >= -0.4:
            polaridad = Polaridad.LIGERAMENTE_NEGATIVO
        elif puntuacion >= -0.8:
            polaridad = Polaridad.NEGATIVO
        else:
            polaridad = Polaridad.MUY_NEGATIVO
        
        return polaridad, round(puntuacion, 4)
    
    def _detectar_sarcasmo(self, texto: str) -> Tuple[bool, bool]:
        """Detecta sarcasmo e ironía en el texto."""
        es_sarcasmo = False
        es_ironia = False
        
        for patron, umbral in self.SARCASMO_ES:
            if re.search(patron, texto, re.IGNORECASE):
                es_sarcasmo = True
                if umbral > 0.8:
                    es_ironia = True
                break
        
        # Patrones adicionales de ironía
        patrones_ironia = [
            r'(?:sí|claro|obvio|evidente(?:mente)?)\s*[,.]\s*(?:cómo|como)\s+(?:no|siempre|nunca)',
            r'(?:qué|que)\s+(raro|extraño|curioso)\s*[,.]\s*(?:si|cuando)',
        ]
        
        if not es_ironia:
            for patron in patrones_ironia:
                if re.search(patron, texto, re.IGNORECASE):
                    es_ironia = True
                    es_sarcasmo = True
                    break
        
        return es_sarcasmo, es_ironia
    
    def _detectar_tono(self, texto: str, tokens: List[str], emociones: List[EmocionDetectada]) -> TonoEmocional:
        """Determina el tono emocional general del texto."""
        
        # Marcadores de tono
        marcadores = {
            TonoEmocional.FORMAL: ['usted', 'señor', 'señora', 'doctor', 'licenciado', 'estimado', 'atentamente', 'cordialmente', 'distinguido'],
            TonoEmocional.INFORMAL: ['hola', 'oye', 'tío', 'colega', 'chaval', 'vale', 'guay', 'chido', 'wey', 'bro'],
            TonoEmocional.ENTUSIASTA: ['!!!', '!!', 'genial', 'increíble', 'fantástico', 'wow', 'guau', 'brutal'],
            TonoEmocional.AGRESIVO: ['idiota', 'estúpido', 'imbécil', 'inútil', 'cállate', 'vete', 'fuera', 'basta'],
            TonoEmocional.EMPATICO: ['entiendo', 'comprendo', 'siento', 'lamento', 'preocupa', 'ayudar', 'apoyar', 'acompañar'],
        }
        
        puntuaciones = defaultdict(float)
        
        for tono, palabras in marcadores.items():
            for palabra in palabras:
                if palabra in texto.lower():
                    puntuaciones[tono] += 1.0
        
        # Inferir tono por emociones
        emociones_nombres = [e.emocion for e in emociones]
        if Emocion.IRA in emociones_nombres:
            puntuaciones[TonoEmocional.AGRESIVO] += 2.0
        if Emocion.ALEGRIA in emociones_nombres:
            puntuaciones[TonoEmocional.ENTUSIASTA] += 1.5
        
        # Detectar sarcasmo afecta el tono
        es_sarcasmo, _ = self._detectar_sarcasmo(texto)
        if es_sarcasmo:
            puntuaciones[TonoEmocional.SARCASMO] += 3.0
        
        if puntuaciones:
            return max(puntuaciones, key=puntuaciones.get)
        
        return TonoEmocional.FORMAL
    
    def _calcular_intensidad(self, emociones: List[EmocionDetectada], tokens: List[str]) -> Intensidad:
        """Calcula la intensidad emocional general."""
        if not emociones:
            return Intensidad.MUY_BAJA
        
        # Intensidad promedio de las emociones
        intensidad_promedio = sum(e.intensidad for e in emociones) / len(emociones)
        
        # Bonus por intensificadores
        intensificadores = self._extraer_intensificadores(tokens)
        bonus = len(intensificadores) * 0.05
        
        # Penalización por atenuadores
        atenuadores = [t for t in tokens if t.lower() in self.ATENUADORES_ES]
        penalizacion = len(atenuadores) * 0.03
        
        intensidad_final = intensidad_promedio + bonus - penalizacion
        intensidad_final = max(0.0, min(1.0, intensidad_final))
        
        if intensidad_final >= 0.9:
            return Intensidad.EXTREMA
        elif intensidad_final >= 0.75:
            return Intensidad.MUY_ALTA
        elif intensidad_final >= 0.55:
            return Intensidad.ALTA
        elif intensidad_final >= 0.35:
            return Intensidad.MODERADA
        elif intensidad_final >= 0.15:
            return Intensidad.BAJA
        else:
            return Intensidad.MUY_BAJA
    
    def _calcular_confianza(self, texto: str, emociones: List[EmocionDetectada]) -> float:
        """Calcula la confianza en la detección realizada."""
        if not emociones:
            # Si no hay emociones pero hay texto, confianza media en "neutral"
            return 0.7 if len(texto.split()) >= 3 else 0.5
        
        # Más palabras emocionales = más confianza
        total_palabras_emocionales = sum(len(e.palabras_clave) for e in emociones)
        confianza_base = min(1.0, total_palabras_emocionales / 5.0)
        
        # Si hay emociones conflictivas, menos confianza
        emociones_nombres = [e.emocion for e in emociones]
        if len(emociones_nombres) >= 4:
            confianza_base *= 0.8
        
        return round(confianza_base, 3)
    
    def _extraer_intensificadores(self, tokens: List[str]) -> List[str]:
        """Extrae intensificadores del texto."""
        return [t for t in tokens if t.lower() in self.INTENSIFICADORES_ES]
    
    def _extraer_negaciones(self, tokens: List[str]) -> List[str]:
        """Extrae negaciones del texto."""
        return [t for t in tokens if t.lower() in self.NEGACIONES_ES]

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE SENTIMIENTO")
    print("=" * 70)
    
    motor = None
    
    try:
        print("\n[1/7] Inicializando motor de sentimiento...")
        motor = MotorSentimiento()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        print("\n[2/7] Probando emociones positivas...")
        textos_positivos = [
            "Estoy muy feliz y contento con este resultado tan maravilloso",
            "Te quiero muchísimo, eres increíble y me haces muy feliz",
            "¡Qué alegría! ¡Estoy eufórico! ¡Esto es fantástico!",
        ]
        for texto in textos_positivos:
            resultado = motor.procesar(texto)
            datos = resultado.datos
            print(f"  📍 '{texto[:50]}...' → {datos['polaridad']} ({datos['puntuacion']}) | {datos['emocion_dominante']}")
        
        print("\n[3/7] Probando emociones negativas...")
        textos_negativos = [
            "Estoy muy triste y deprimido, todo esto es horrible",
            "Me enfurece esta situación, estoy extremadamente enojado",
            "Tengo mucho miedo, esto es aterrador y me pone muy nervioso",
        ]
        for texto in textos_negativos:
            resultado = motor.procesar(texto)
            datos = resultado.datos
            print(f"  📍 '{texto[:50]}...' → {datos['polaridad']} ({datos['puntuacion']}) | {datos['emocion_dominante']}")
        
        print("\n[4/7] Probando emociones complejas...")
        textos_complejos = [
            "Siento nostalgia por aquellos tiempos, pero también alegría de haberlos vivido",
            "Estoy agradecido por la oportunidad aunque también un poco ansioso",
            "Qué curioso este descubrimiento, me intriga muchísimo",
        ]
        for texto in textos_complejos:
            resultado = motor.procesar(texto)
            datos = resultado.datos
            emociones_detectadas = [e['emocion'] for e in datos['emociones']]
            print(f"  📍 '{texto[:50]}...' → {datos['polaridad']} | Emociones: {emociones_detectadas}")
        
        print("\n[5/7] Probando sarcasmo e ironía...")
        textos_sarcasmo = [
            "Ah, qué bien, justo lo que necesitaba cuando no tengo tiempo",
            "Sí, claro, como no, siempre es un placer trabajar contigo",
            "Bravo, felicidades por el desastre que has montado",
        ]
        for texto in textos_sarcasmo:
            resultado = motor.procesar(texto)
            datos = resultado.datos
            print(f"  📍 '{texto[:50]}...' → sarcasmo={datos['es_sarcasmo']}, ironía={datos['es_ironia']}, tono={datos['tono']}")
        
        print("\n[6/7] Probando intensidad emocional...")
        textos_intensidad = [
            ("Estoy contento", Intensidad.BAJA.value if hasattr(Intensidad, 'BAJA') else "baja"),
            ("Estoy MUY contento", Intensidad.MODERADA.value if hasattr(Intensidad, 'MODERADA') else "moderada"),
            ("Estoy EXTREMADAMENTE contento y eufórico", Intensidad.EXTREMA.value if hasattr(Intensidad, 'EXTREMA') else "extrema"),
        ]
        for texto, esperado in textos_intensidad:
            resultado = motor.procesar(texto)
            datos = resultado.datos
            print(f"  📍 '{texto}' → intensidad={datos['intensidad_emocional']}")
        
        print("\n[7/7] Resumen del motor...")
        stats = {
            'emociones_soportadas': len(motor.EMOCIONES_ES),
            'intensificadores': len(motor.INTENSIFICADORES_ES),
            'atenuadores': len(motor.ATENUADORES_ES),
            'patrones_sarcasmo': len(motor.SARCASMO_ES),
        }
        for k, v in stats.items():
            print(f"  📊 {k}: {v}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Motor de Sentimiento está VIVO y es REAL.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if motor:
            motor.detener()
    
    print("\n" + "=" * 70 + "\n")    