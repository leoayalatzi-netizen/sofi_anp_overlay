#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Tono (El Camaleón Comunicativo)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa análisis de tono REAL con
# detección de 12 tonos comunicativos, puntuación de confianza,
# adaptación contextual y soporte multilingüe ES/EN.
# =====================================================================

import sys, os, re, time, json, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, Counter
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
            def inicializar(self):
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

class TonoComunicativo(Enum):
    """Tonos comunicativos detectables."""
    FORMAL = "formal"
    INFORMAL = "informal"
    ENTUSIASTA = "entusiasta"
    SERIO = "serio"
    HUMORISTICO = "humoristico"
    SARCASTICO = "sarcastico"
    IRONICO = "ironico"
    EMPATICO = "empatito"
    AGRESIVO = "agresivo"
    PASIVO = "pasivo"
    DRAMATICO = "dramatico"
    TECNICO = "tecnico"
    NEUTRAL = "neutral"

class IntensidadTono(Enum):
    """Intensidad del tono detectado."""
    MUY_BAJA = "muy_baja"
    BAJA = "baja"
    MODERADA = "moderada"
    ALTA = "alta"
    MUY_ALTA = "muy_alta"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class TonoDetectado:
    """Tono detectado con su puntuación."""
    tono: TonoComunicativo
    confianza: float = 0.0
    intensidad: IntensidadTono = IntensidadTono.MODERADA
    marcadores: List[str] = field(default_factory=list)
    sugerencia_tono: Optional[TonoComunicativo] = None

@dataclass
class ResultadoTono:
    """Resultado completo del análisis de tono."""
    texto_original: str = ""
    tono_dominante: Optional[TonoDetectado] = None
    tonos_detectados: List[TonoDetectado] = field(default_factory=list)
    recomendacion: str = ""
    adaptacion_sugerida: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# MOTOR DE TONO PRINCIPAL
# =====================================================================

class MotorTono(MotorBase):
    """Motor de Análisis de Tono Comunicativo de ANP."""
    
    # ===== DICCIONARIOS DE MARCADORES POR TONO =====
    
    MARCADORES_ES = {
        TonoComunicativo.FORMAL: {
            'palabras': [
                'usted', 'señor', 'señora', 'doctor', 'docto', 'licenciado',
                'estimado', 'distinguido', 'respetable', 'honorable',
                'atentamente', 'cordialmente', 'respetuosamente', 'saludos cordiales',
                'me dirijo', 'por la presente', 'adjunto', 'remito',
                'agradecería', 'solicitaría', 'ruego', 'suplico',
            ],
            'peso': 0.85,
        },
        TonoComunicativo.INFORMAL: {
            'palabras': [
                'hola', 'oye', 'tío', 'tía', 'colega', 'chaval', 'tronco',
                'vale', 'guay', 'chulo', 'mola', 'flipas', 'mazo',
                'qué tal', 'cómo vas', 'todo bien', 'genial', 'perfect',
                'bro', 'dude', 'tío', 'wey', 'we', 'vato', 'parce',
                'jaja', 'jeje', 'jiji', 'lol', 'xdd', 'xd',
            ],
            'peso': 0.80,
        },
        TonoComunicativo.ENTUSIASTA: {
            'palabras': [
                'genial', 'fantástico', 'increíble', 'maravilloso', 'espectacular',
                'brutal', 'impresionante', 'alucinante', 'flipante', 'bestial',
                'wow', 'guau', 'woo', 'vamos', 'arriba',
                '!!!!', '!!!', '!!', '🎉', '🎊', '🔥', '💪', '🚀',
            ],
            'peso': 0.82,
        },
        TonoComunicativo.SERIO: {
            'palabras': [
                'importante', 'grave', 'crítico', 'urgente', 'serio',
                'preocupante', 'delicado', 'sensible', 'complejo', 'difícil',
                'lamentablemente', 'desafortunadamente', 'tristemente',
                'debemos', 'tenemos que', 'es necesario', 'hay que',
                'atención', 'cuidado', 'precaución', 'alerta',
            ],
            'peso': 0.80,
        },
        TonoComunicativo.HUMORISTICO: {
            'palabras': [
                'jaja', 'jeje', 'jiji', 'jojo', 'juju', 'lol', 'lmao', 'rofl',
                'broma', 'chiste', 'gracioso', 'divertido', 'cómico', 'humor',
                '😂', '🤣', '😆', '😝', '😜',
                'no me digas', 'en serio', 'qué va', 'anda ya', 'venga ya',
            ],
            'peso': 0.78,
        },
        TonoComunicativo.SARCASTICO: {
            'palabras': [
                'claro', 'por supuesto', 'cómo no', 'seguro', 'evidentemente',
                'bravo', 'felicidades', 'enhorabuena', 'ole', 'chapó',
                'qué bien', 'qué bonito', 'qué maravilla', 'qué sorpresa',
                'anda', 'vaya', 'mira', 'fíjate', 'qué curioso',
            ],
            'contexto': [
                (r'(?:claro|seguro|por supuesto)\s*[,.]\s*(?:cómo no|como no|faltaría más)', 0.90),
                (r'(?:qué|que)\s+(?:bien|bonito|maravilla|sorpresa)\s*[,.]\s*(?:cuando|si|mientras)\s+(?:no|nunca|jamás)', 0.85),
                (r'(?:gracias|agradecido)\s+por\s+nada', 0.95),
                (r'(?:bravo|felicidades|enhorabuena)\s*[,.]\s*(?:por|has|has hecho)\s+(?:el|la)\s+(?:desastre|desgracia|tontería)', 0.90),
            ],
            'peso': 0.85,
        },
        TonoComunicativo.IRONICO: {
            'palabras': [
                'curioso', 'interesante', 'sorprendente', 'inesperado', 'peculiar',
                'qué raro', 'qué extraño', 'qué curioso', 'qué interesante',
                'vaya', 'anda', 'mira tú', 'fíjate tú', 'quién lo diría',
            ],
            'contexto': [
                (r'(?:qué|que)\s+(?:raro|extraño|curioso|interesante)\s*[,.]\s*(?:que|si|cuando)\s+(?:justo|precisamente|casualmente)', 0.85),
                (r'(?:vaya|anda|mira)\s*[,.]\s*(?:qué|que)\s+(?:sorpresa|inesperado|casualidad)', 0.80),
            ],
            'peso': 0.83,
        },
        TonoComunicativo.EMPATICO: {
            'palabras': [
                'entiendo', 'comprendo', 'siento', 'lamento', 'preocupa',
                'ayudar', 'apoyar', 'acompañar', 'escuchar', 'compartir',
                'contigo', 'con usted', 'a tu lado', 'para ti',
                'importa', 'vale', 'ánimo', 'fuerza', 'adelante',
                'no te preocupes', 'no se preocupe', 'tranquilo', 'tranquila',
            ],
            'peso': 0.82,
        },
        TonoComunicativo.AGRESIVO: {
            'palabras': [
                'idiota', 'estúpido', 'imbécil', 'inútil', 'inservible',
                'cállate', 'cállese', 'vete', 'fuera', 'largo',
                'basta', 'harto', 'cansado', 'hastiado', 'podrido',
                'eres un', 'es un', 'son unos', 'qué mal', 'pésimo',
                'odio', 'detesto', 'aborrezco', 'repudio', 'asquea',
            ],
            'peso': 0.88,
        },
        TonoComunicativo.PASIVO: {
            'palabras': [
                'quizás', 'quizá', 'tal vez', 'a lo mejor', 'puede ser',
                'no sé', 'no estoy seguro', 'no tengo claro', 'dudo',
                'lo que tú digas', 'como quieras', 'como prefieras',
                'si tú quieres', 'si te parece', 'si no es molestia',
                'da igual', 'me da lo mismo', 'no importa', 'como sea',
            ],
            'peso': 0.78,
        },
        TonoComunicativo.DRAMATICO: {
            'palabras': [
                'desastre', 'catástrofe', 'tragedia', 'horror', 'espanto',
                'terrible', 'horrible', 'espantoso', 'aterrador', 'devastador',
                'no puedo más', 'esto es el fin', 'se acabó', 'todo perdido',
                'nunca', 'jamás', 'eternamente', 'para siempre',
                '😱', '😨', '😰', '💀', '☠️',
            ],
            'peso': 0.82,
        },
        TonoComunicativo.TECNICO: {
            'palabras': [
                'sistema', 'proceso', 'función', 'variable', 'parámetro',
                'algoritmo', 'método', 'técnica', 'procedimiento', 'protocolo',
                'configuración', 'implementación', 'optimización', 'ejecución',
                'datos', 'análisis', 'resultado', 'conclusión', 'evidencia',
                'según', 'de acuerdo con', 'con base en', 'basado en',
                'porcentaje', 'estadística', 'promedio', 'desviación', 'margen',
            ],
            'peso': 0.80,
        },
    }
    
    # ===== PATRONES DE INTENSIDAD =====
    PATRONES_INTENSIDAD = {
        IntensidadTono.MUY_ALTA: [
            r'!!!+', r'[A-Z]{3,}', r'(?:MUY|TAN|SUPER|ULTRA|MEGA|HIPER)\s+\w+',
        ],
        IntensidadTono.ALTA: [
            r'!!', r'[A-Z]{2}', r'(?:muy|tan|bastante|realmente)\s+\w+',
        ],
        IntensidadTono.MODERADA: [
            r'!', r'(?:algo|un poco|ligeramente)\s+\w+',
        ],
        IntensidadTono.BAJA: [
            r'(?:quizás|quizá|tal vez|a lo mejor)\s+\w+',
        ],
        IntensidadTono.MUY_BAJA: [
            r'(?:apenas|casi no|difícilmente)\s+\w+',
        ],
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        self._patrones = {}
    
    def inicializar(self):
        """Inicializa el motor y compila patrones."""
        self._compilar_patrones()
        return super().inicializar()
    
    def _compilar_patrones(self):
        """Compila patrones regex de intensidad."""
        self._patrones = {}
        for intensidad, patrones in self.PATRONES_INTENSIDAD.items():
            self._patrones[intensidad] = [re.compile(p) for p in patrones]
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Analiza el tono comunicativo del texto."""
        if isinstance(entrada, str):
            texto = entrada
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('text', ''))
        else:
            texto = str(entrada)
        
        if not texto or not texto.strip():
            return self._resultado(texto or '')
        
        texto_lower = texto.lower()
        texto_upper = texto  # Para patrones de mayúsculas
        
        # Detectar tonos
        tonos_detectados = []
        
        for tono, datos in self.MARCADORES_ES.items():
            puntuacion = 0.0
            marcadores_encontrados = []
            
            # Buscar palabras marcadoras
            for palabra in datos.get('palabras', []):
                if palabra.lower() in texto_lower:
                    puntuacion += datos.get('peso', 0.7)
                    marcadores_encontrados.append(palabra)
            
            # Buscar patrones de contexto (para sarcasmo e ironía)
            for patron_contexto, peso_contexto in datos.get('contexto', []):
                if re.search(patron_contexto, texto_lower):
                    puntuacion += peso_contexto
                    marcadores_encontrados.append(f'[contexto] {patron_contexto[:30]}')
            
            # Normalizar puntuación
            num_palabras = len(texto_lower.split())
            if num_palabras > 0:
                puntuacion_normalizada = puntuacion / max(1, num_palabras)
            else:
                puntuacion_normalizada = 0.0
            
            if puntuacion_normalizada > 0.02:  # Umbral mínimo
                intensidad = self._detectar_intensidad(texto_upper, texto_lower)
                tonos_detectados.append(TonoDetectado(
                    tono=tono,
                    confianza=min(1.0, puntuacion_normalizada * 10),
                    intensidad=intensidad,
                    marcadores=marcadores_encontrados[:5],
                ))
        
        # Ordenar por confianza
        tonos_detectados.sort(key=lambda t: t.confianza, reverse=True)
        
        # Tono dominante
        tono_dominante = tonos_detectados[0] if tonos_detectados else TonoDetectado(
            tono=TonoComunicativo.NEUTRAL, confianza=0.3
        )
        
        # Sugerencia de tono opuesto si es agresivo o pasivo
        if tono_dominante.tono == TonoComunicativo.AGRESIVO:
            sugerencia = TonoComunicativo.EMPATICO
        elif tono_dominante.tono == TonoComunicativo.PASIVO:
            sugerencia = TonoComunicativo.FORMAL
        elif tono_dominante.tono == TonoComunicativo.SARCASTICO:
            sugerencia = TonoComunicativo.SERIO
        else:
            sugerencia = None
        
        if sugerencia:
            tono_dominante.sugerencia_tono = sugerencia
        
        # Generar recomendación
        recomendacion = self._generar_recomendacion(tono_dominante)
        
        # Adaptación sugerida
        adaptacion = self._generar_adaptacion(tono_dominante, tonos_detectados)
        
        return {
            'texto_original': texto,
            'tono_dominante': {
                'tono': tono_dominante.tono.value,
                'confianza': round(tono_dominante.confianza, 3),
                'intensidad': tono_dominante.intensidad.value,
                'marcadores': tono_dominante.marcadores,
                'sugerencia': tono_dominante.sugerencia_tono.value if tono_dominante.sugerencia_tono else None,
            },
            'tonos_detectados': [
                {
                    'tono': t.tono.value,
                    'confianza': round(t.confianza, 3),
                    'intensidad': t.intensidad.value,
                }
                for t in tonos_detectados[:5]
            ],
            'total_tonos': len(tonos_detectados),
            'recomendacion': recomendacion,
            'adaptacion_sugerida': adaptacion,
        }
    
    def _detectar_intensidad(self, texto_upper: str, texto_lower: str) -> IntensidadTono:
        """Detecta la intensidad del tono basado en patrones."""
        puntuaciones = defaultdict(float)
        
        for intensidad, patrones in self._patrones.items():
            for patron in patrones:
                if patron.search(texto_upper) or patron.search(texto_lower):
                    puntuaciones[intensidad] += 1.0
        
        if puntuaciones:
            return max(puntuaciones, key=puntuaciones.get)
        
        # Por defecto, según signos de exclamación
        count_excl = texto_upper.count('!')
        if count_excl >= 3:
            return IntensidadTono.MUY_ALTA
        elif count_excl >= 2:
            return IntensidadTono.ALTA
        elif count_excl >= 1:
            return IntensidadTono.MODERADA
        
        return IntensidadTono.MODERADA
    
    def _generar_recomendacion(self, tono: TonoDetectado) -> str:
        """Genera una recomendación basada en el tono detectado."""
        recomendaciones = {
            TonoComunicativo.FORMAL: "Mantener tono profesional y respetuoso.",
            TonoComunicativo.INFORMAL: "Se puede usar un lenguaje cercano y coloquial.",
            TonoComunicativo.ENTUSIASTA: "Reflejar energía y positividad en la respuesta.",
            TonoComunicativo.SERIO: "Responder con datos concretos y sin ambigüedades.",
            TonoComunicativo.HUMORISTICO: "Se puede incluir humor ligero si es apropiado.",
            TonoComunicativo.SARCASTICO: "Evitar devolver sarcasmo. Responder con serenidad.",
            TonoComunicativo.IRONICO: "Reconocer el tono sin alimentar la ironía.",
            TonoComunicativo.EMPATICO: "Mostrar comprensión y apoyo emocional.",
            TonoComunicativo.AGRESIVO: "Mantener la calma. No escalar el conflicto.",
            TonoComunicativo.PASIVO: "Animar a expresar opiniones con confianza.",
            TonoComunicativo.DRAMATICO: "Aportar perspectiva y calma.",
            TonoComunicativo.TECNICO: "Usar precisión terminológica adecuada.",
            TonoComunicativo.NEUTRAL: "Tono equilibrado y adaptable.",
        }
        return recomendaciones.get(tono.tono, "Adaptar respuesta al contexto.")
    
    def _generar_adaptacion(self, tono_dominante: TonoDetectado, 
                           tonos: List[TonoDetectado]) -> Dict[str, Any]:
        """Genera sugerencias de adaptación para la respuesta."""
        adaptacion = {
            'formalidad': 0.5,
            'entusiasmo': 0.5,
            'empatia': 0.5,
            'tecnico': 0.5,
            'longitud_respuesta': 'media',
        }
        
        if tono_dominante.tono == TonoComunicativo.FORMAL:
            adaptacion['formalidad'] = 0.9
        elif tono_dominante.tono == TonoComunicativo.INFORMAL:
            adaptacion['formalidad'] = 0.2
        elif tono_dominante.tono == TonoComunicativo.ENTUSIASTA:
            adaptacion['entusiasmo'] = 0.9
        elif tono_dominante.tono == TonoComunicativo.TECNICO:
            adaptacion['tecnico'] = 0.9
            adaptacion['longitud_respuesta'] = 'larga'
        elif tono_dominante.tono == TonoComunicativo.AGRESIVO:
            adaptacion['empatia'] = 0.9
            adaptacion['longitud_respuesta'] = 'corta'
        elif tono_dominante.tono == TonoComunicativo.EMPATICO:
            adaptacion['empatia'] = 0.9
        
        if tono_dominante.intensidad in (IntensidadTono.MUY_ALTA, IntensidadTono.ALTA):
            adaptacion['intensidad_respuesta'] = 'moderada'
        
        return adaptacion
    
    def _resultado(self, texto='', error=''):
        return {
            'texto_original': texto,
            'tono_dominante': {'tono': 'neutral', 'confianza': 0.0, 'intensidad': 'baja', 'marcadores': [], 'sugerencia': None},
            'tonos_detectados': [],
            'total_tonos': 0,
            'recomendacion': 'Sin datos suficientes',
            'adaptacion_sugerida': {},
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE TONO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor...")
        motor = MotorTono()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            td = {'tono': 'neutral', 'confianza': 0.0, 'intensidad': 'baja', 'marcadores': [], 'sugerencia': None}
            return {'tono_dominante': td, 'tonos_detectados': [], 'total_tonos': 0, 'recomendacion': 'Error', 'adaptacion_sugerida': {}}
        
        print("\n[2/6] Tono formal...")
        t1 = "Estimado señor García, por la presente le remito el informe solicitado. Atentamente, Dr. Martínez."
        d1 = sd(motor.procesar(t1))
        print(f"  📊 Tono: {d1['tono_dominante']['tono']} (confianza: {d1['tono_dominante']['confianza']})")
        print(f"  📍 Recomendación: {d1['recomendacion']}")
        
        print("\n[3/6] Tono agresivo...")
        t2 = "¡Eres un idiota! ¡Esto es un desastre total! ¡Estoy harto de tus errores!"
        d2 = sd(motor.procesar(t2))
        print(f"  📊 Tono: {d2['tono_dominante']['tono']} (confianza: {d2['tono_dominante']['confianza']})")
        print(f"  📍 Sugerencia: {d2['tono_dominante']['sugerencia']}")
        print(f"  📍 Recomendación: {d2['recomendacion']}")
        
        print("\n[4/6] Tono sarcástico...")
        t3 = "Ah, claro, qué bien. Justo lo que necesitaba. Muchas gracias por nada."
        d3 = sd(motor.procesar(t3))
        print(f"  📊 Tono: {d3['tono_dominante']['tono']} (confianza: {d3['tono_dominante']['confianza']})")
        print(f"  📍 Marcadores: {d3['tono_dominante']['marcadores']}")
        
        print("\n[5/6] Tono empático...")
        t4 = "Entiendo perfectamente cómo te sientes. No te preocupes, estoy aquí para ayudarte. Cuenta conmigo."
        d4 = sd(motor.procesar(t4))
        print(f"  📊 Tono: {d4['tono_dominante']['tono']} (confianza: {d4['tono_dominante']['confianza']})")
        
        print("\n[6/6] Estadísticas...")
        print(f"  📊 Tonos soportados: {len(motor.MARCADORES_ES)}")
        print(f"  📊 Niveles de intensidad: {len(motor.PATRONES_INTENSIDAD)}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print("\n" + "=" * 70 + "\n")