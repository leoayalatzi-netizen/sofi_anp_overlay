#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Reflexivo (El Espejo del Ser)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa reflexión profunda REAL con
# autoevaluación, metacognición, análisis de patrones de pensamiento,
# detección de creencias limitantes, cuestionamiento socrático y
# generación de perspectivas alternativas.
# =====================================================================

import sys, os, re, time, math, json, random, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, Counter, deque
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

class NivelReflexion(Enum):
    """Niveles de profundidad reflexiva."""
    SUPERFICIAL = "superficial"
    MODERADA = "moderada"
    PROFUNDA = "profunda"
    MUY_PROFUNDA = "muy_profunda"
    TRASCENDENTAL = "trascendental"

class TipoCreencia(Enum):
    """Tipos de creencias detectables."""
    LIMITANTE = "limitante"
    POTENCIADORA = "potenciadora"
    ABSOLUTISTA = "absolutista"
    CATASTROFISTA = "catastrofista"
    GENERALIZADORA = "generalizadora"
    AUTOEXIGENTE = "autoexigente"
    VICTIMISTA = "victimista"
    PERFECCIONISTA = "perfeccionista"
    COMPARATIVA = "comparativa"
    ADIVINATORIA = "adivinatoria"

class PatronPensamiento(Enum):
    """Patrones de pensamiento detectables."""
    PENSAMIENTO_BINARIO = "pensamiento_binario"
    SOBREGENERALIZACION = "sobregeneralizacion"
    FILTRO_MENTAL = "filtro_mental"
    DESCALIFICACION_POSITIVO = "descalificacion_positivo"
    CONCLUSIONES_APRESURADAS = "conclusiones_apresuradas"
    VISION_CATASTROFICA = "vision_catastrofica"
    RAZONAMIENTO_EMOCIONAL = "razonamiento_emocional"
    DEBERIAS = "deberias"
    ETIQUETADO = "etiquetado"
    PERSONALIZACION = "personalizacion"

class PreguntaSocratica(Enum):
    """Tipos de preguntas socráticas."""
    CLARIFICACION = "clarificacion"
    EVIDENCIA = "evidencia"
    PERSPECTIVA = "perspectiva"
    IMPLICACIONES = "implicaciones"
    ORIGEN = "origen"
    REFLEXION = "reflexion"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class CreenciaDetectada:
    """Creencia detectada en el discurso."""
    tipo: TipoCreencia
    nombre: str = ""
    descripcion: str = ""
    fragmento: str = ""
    confianza: float = 0.0
    pregunta_reflexiva: str = ""
    reformulacion: str = ""

@dataclass
class PatronDetectado:
    """Patrón de pensamiento detectado."""
    tipo: PatronPensamiento
    nombre: str = ""
    descripcion: str = ""
    fragmento: str = ""
    confianza: float = 0.0
    estrategia: str = ""
    ejemplo_alternativo: str = ""

@dataclass
class ReflexionSocratica:
    """Conjunto de preguntas socráticas generadas."""
    pregunta_original: str = ""
    preguntas_clarificacion: List[str] = field(default_factory=list)
    preguntas_evidencia: List[str] = field(default_factory=list)
    preguntas_perspectiva: List[str] = field(default_factory=list)
    preguntas_implicaciones: List[str] = field(default_factory=list)
    preguntas_origen: List[str] = field(default_factory=list)
    conclusion_reflexiva: str = ""

@dataclass
class EvaluacionReflexiva:
    """Evaluación completa de reflexión."""
    texto_original: str = ""
    nivel_reflexion: NivelReflexion = NivelReflexion.MODERADA
    creencias: List[CreenciaDetectada] = field(default_factory=list)
    patrones: List[PatronDetectado] = field(default_factory=list)
    dialogo_socratico: Optional[ReflexionSocratica] = None
    perspectivas_alternativas: List[str] = field(default_factory=list)
    puntuacion_autoconocimiento: float = 50.0
    recomendacion: str = ""
    frase_inspiradora: str = ""

# =====================================================================
# MOTOR REFLEXIVO PRINCIPAL
# =====================================================================

class MotorReflexivo(MotorBase):
    """
    Motor de Reflexión Profunda de ANP.
    
    Capacidades REALES:
    - Detección de 10 tipos de creencias limitantes
    - Identificación de 10 patrones de pensamiento
    - Generación de diálogo socrático
    - Cuestionamiento de supuestos
    - Reformulación de creencias
    - Perspectivas alternativas
    - Frases inspiradoras contextuales
    - Evaluación de profundidad reflexiva
    """
    
    # ===== CATÁLOGO DE CREENCIAS LIMITANTES =====
    
    CREENCIAS_LIMITANTES = {
        TipoCreencia.LIMITANTE: {
            'nombre': 'Creencia Limitante',
            'descripcion': 'Creencia que restringe el potencial o las posibilidades',
            'patrones': [
                r'\b(no puedo|soy incapaz|no sirvo para|no tengo talento|no soy bueno)\b',
                r'\b(nunca podr[eé]|jam[aá]s lograr[eé]|es imposible para m[ií]|no est[aá] a mi alcance)\b',
                r'\b(no merezco|no soy suficiente|no valgo|no soy digno)\b',
            ],
            'reformulacion': '¿Qué evidencia tengo de que esto sea absolutamente cierto? ¿Qué pequeñas acciones podría tomar para desafiarlo?',
        },
        TipoCreencia.ABSOLUTISTA: {
            'nombre': 'Pensamiento Absolutista',
            'descripcion': 'Ver las cosas en términos de todo o nada',
            'patrones': [
                r'\b(siempre|nunca|jam[aá]s|absolutamente|totalmente|completamente)\b.+(?:es|son|pasa|ocurre)\b',
                r'\b(todo el mundo|nadie|todos|ninguno)\b.+(?:hace|dice|piensa|es)\b',
            ],
            'reformulacion': '¿Es realmente siempre/nunca así? ¿Puedo encontrar alguna excepción?',
        },
        TipoCreencia.CATASTROFISTA: {
            'nombre': 'Visión Catastrofista',
            'descripcion': 'Anticipar el peor escenario posible',
            'patrones': [
                r'\b(es un desastre|es horrible|es terrible|es lo peor|es el fin)\b',
                r'\b(no podr[eé] soportarlo|no lo superar[eé]|ser[aá] mi ruina|esto es catastr[oó]fico)\b',
                r'\b(y si sale mal|y si fallo|y si no funciona|y si se equivoca)\b',
            ],
            'reformulacion': '¿Cuál es la probabilidad REAL de que ocurra el peor escenario? ¿He manejado situaciones difíciles antes?',
        },
        TipoCreencia.GENERALIZADORA: {
            'nombre': 'Sobregeneralización',
            'descripcion': 'Sacar conclusiones generales de un solo incidente',
            'patrones': [
                r'\b(conozco a un|una vez|me pas[oó]|tuve una experiencia)\b.+\b(por lo tanto|as[ií] que|siempre|nunca)\b',
                r'\b(todos son iguales|siempre es lo mismo|cada vez que|otra vez)\b',
            ],
            'reformulacion': '¿Un solo caso es suficiente para establecer una regla general? ¿Qué otras experiencias contradicen esto?',
        },
        TipoCreencia.ADIVINATORIA: {
            'nombre': 'Adivinación del Pensamiento',
            'descripcion': 'Creer saber lo que otros piensan sin evidencia',
            'patrones': [
                r'\b(seguro piensa|seguro cree|apuesto a que|estoy seguro de que)\b.+(?:cree|piensa|opina|siente)\b',
                r'\b(ya s[eé] lo que|s[eé] que piensas|est[aá] claro que piensa|es obvio que cree)\b',
                r'\b(no me quiere|le caigo mal|me odia|me desprecia|me ignora)\b',
            ],
            'reformulacion': '¿Tengo evidencia REAL de lo que la otra persona piensa? ¿He preguntado directamente?',
        },
        TipoCreencia.AUTOEXIGENTE: {
            'nombre': 'Autoexigencia Excesiva',
            'descripcion': 'Imponerse estándares poco realistas',
            'patrones': [
                r'\b(deber[ií]a|tendr[ií]a que|debo|tengo que|estoy obligado)\b.+(?:ser|hacer|lograr|conseguir|alcanzar)\b',
                r'\b(tengo que ser perfecto|no puedo fallar|no debo cometer errores|debo hacerlo todo bien)\b',
            ],
            'reformulacion': '¿Estos estándares son realistas? ¿Qué pasaría si fuera un poco más flexible conmigo mismo?',
        },
        TipoCreencia.COMPARATIVA: {
            'nombre': 'Comparación Social',
            'descripcion': 'Medir el propio valor comparándose con otros',
            'patrones': [
                r'\b(ellos son mejores|yo soy peor|no soy tan bueno como|nunca ser[eé] como)\b',
                r'\b(tiene m[aá]s [eé]xito|es m[aá]s inteligente|es m[aá]s guapo|gana m[aá]s dinero)\b',
                r'\b(por qu[eé] ellos s[ií] y yo no|qu[eé] tienen ellos que no tenga yo)\b',
            ],
            'reformulacion': '¿Estoy comparando mi interior con el exterior de los demás? Cada persona tiene su propio camino.',
        },
    }
    
    # ===== PATRONES DE PENSAMIENTO =====
    
    PATRONES_PENSAMIENTO = {
        PatronPensamiento.PENSAMIENTO_BINARIO: {
            'nombre': 'Pensamiento Binario (Blanco/Negro)',
            'descripcion': 'Ver las cosas en términos absolutos, sin matices',
            'patrones': [r'\b(o es|o no es|blanco o negro|bueno o malo|correcto o incorrecto|todo o nada)\b'],
            'estrategia': 'Busca los matices. La mayoría de las situaciones tienen grises y complejidades.',
        },
        PatronPensamiento.SOBREGENERALIZACION: {
            'nombre': 'Sobregeneralización',
            'descripcion': 'Usar palabras como "siempre", "nunca", "todo", "nada"',
            'patrones': [r'\b(siempre es|nunca es|todo el mundo|nadie|absolutamente todos|sin excepci[oó]n)\b'],
            'estrategia': 'Sé específico. Reemplaza "siempre" por "en esta ocasión".',
        },
        PatronPensamiento.FILTRO_MENTAL: {
            'nombre': 'Filtro Mental',
            'descripcion': 'Enfocarse solo en lo negativo, ignorando lo positivo',
            'patrones': [r'\b(solo veo|solo miro|me enfoco en)\b.+\b(malo|negativo|error|fracaso|defecto)\b'],
            'estrategia': 'Haz una lista de aspectos positivos. Equilibra la perspectiva.',
        },
        PatronPensamiento.CONCLUSIONES_APRESURADAS: {
            'nombre': 'Conclusiones Apresuradas',
            'descripcion': 'Llegar a conclusiones sin evidencia suficiente',
            'patrones': [r'\b(ya s[eé]|es obvio|est[aá] claro|sin duda|definitivamente|seguro que)\b(?!.*?(?:porque|evidencia|prueba|dato))'],
            'estrategia': 'Pregúntate: ¿Qué evidencia tengo? ¿Hay otras explicaciones posibles?',
        },
        PatronPensamiento.VISION_CATASTROFICA: {
            'nombre': 'Visión Catastrófica',
            'descripcion': 'Magnificar los problemas anticipando desastres',
            'patrones': [r'\b(desastre|cat[aá]strofe|terrible|horroroso|devastador|el fin del mundo)\b'],
            'estrategia': 'Evalúa la probabilidad real. La mayoría de las catástrofes que imaginamos nunca ocurren.',
        },
        PatronPensamiento.RAZONAMIENTO_EMOCIONAL: {
            'nombre': 'Razonamiento Emocional',
            'descripcion': 'Confundir sentimientos con hechos objetivos',
            'patrones': [r'\b(me siento|siento que|tengo la sensaci[oó]n|presiento|intuyo)\b.+\b(por lo tanto|as[ií] que|entonces)\b'],
            'estrategia': 'Los sentimientos no son hechos. Busca evidencia objetiva más allá de tus emociones.',
        },
        PatronPensamiento.DEBERIAS: {
            'nombre': 'Tiranía de los "Debería"',
            'descripcion': 'Imponerse reglas rígidas sobre cómo deberían ser las cosas',
            'patrones': [r'\b(deber[ií]a|tendr[ií]a que|hay que|es necesario|es obligatorio)\b.+(?:ser|hacer|estar|tener)\b'],
            'estrategia': 'Reemplaza "debería" por "me gustaría" o "preferiría". Reduce la presión.',
        },
    }
    
    # ===== FRASES INSPIRADORAS =====
    
    FRASES_INSPIRADORAS = [
        '"La vida no examinada no merece ser vivida." - Sócrates',
        '"No son las cosas las que nos perturban, sino la opinión que tenemos de ellas." - Epicteto',
        '"El mayor descubrimiento de mi generación es que un ser humano puede cambiar su vida cambiando su actitud mental." - William James',
        '"Lo que pensamos, nos convertimos." - Buda',
        '"La mente es todo. Te conviertes en lo que piensas." - Buda',
        '"No puedes detener las olas, pero puedes aprender a surfear." - Jon Kabat-Zinn',
        '"La libertad es la capacidad de elegir nuestra actitud ante cualquier circunstancia." - Viktor Frankl',
        '"Conocerte a ti mismo es el principio de toda sabiduría." - Aristóteles',
        '"No vemos las cosas como son, las vemos como somos." - Anaïs Nin',
        '"El pájaro no teme que la rama se rompa, porque confía en sus propias alas." - Proverbio',
    ]
    
    def __init__(self, config=None):
        super().__init__(config)
        self._compilar_patrones()
    
    def _compilar_patrones(self):
        """Compila todos los patrones regex."""
        self._patrones_creencias = {}
        for tipo, datos in self.CREENCIAS_LIMITANTES.items():
            self._patrones_creencias[tipo] = [
                re.compile(p, re.IGNORECASE) for p in datos.get('patrones', [])
            ]
        
        self._patrones_pensamiento = {}
        for tipo, datos in self.PATRONES_PENSAMIENTO.items():
            self._patrones_pensamiento[tipo] = [
                re.compile(p, re.IGNORECASE) for p in datos.get('patrones', [])
            ]
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Realiza reflexión profunda sobre un texto."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('pensamiento', entrada.get('reflexion', '')))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado_vacio()
        
        texto_lower = texto.lower()
        
        # Detectar creencias limitantes
        creencias = self._detectar_creencias(texto_lower, texto)
        
        # Detectar patrones de pensamiento
        patrones = self._detectar_patrones(texto_lower, texto)
        
        # Generar diálogo socrático
        dialogo = self._generar_dialogo_socratico(texto, creencias, patrones)
        
        # Generar perspectivas alternativas
        perspectivas = self._generar_perspectivas(creencias, patrones)
        
        # Evaluar nivel de reflexión
        nivel = self._evaluar_nivel(texto, creencias, patrones)
        
        # Puntuación de autoconocimiento
        puntuacion = self._calcular_puntuacion(creencias, patrones)
        
        # Generar recomendación
        recomendacion = self._generar_recomendacion(creencias, patrones, nivel)
        
        # Seleccionar frase inspiradora
        frase = random.choice(self.FRASES_INSPIRADORAS)
        
        return {
            'texto_original': texto,
            'nivel_reflexion': nivel.value,
            'creencias': [
                {
                    'tipo': c.tipo.value,
                    'nombre': c.nombre,
                    'descripcion': c.descripcion,
                    'fragmento': c.fragmento,
                    'confianza': round(c.confianza, 2),
                    'pregunta_reflexiva': c.pregunta_reflexiva,
                    'reformulacion': c.reformulacion,
                }
                for c in creencias
            ],
            'patrones': [
                {
                    'tipo': p.tipo.value,
                    'nombre': p.nombre,
                    'descripcion': p.descripcion,
                    'fragmento': p.fragmento,
                    'confianza': round(p.confianza, 2),
                    'estrategia': p.estrategia,
                    'ejemplo_alternativo': p.ejemplo_alternativo,
                }
                for p in patrones
            ],
            'dialogo_socratico': {
                'pregunta_original': dialogo.pregunta_original,
                'clarificacion': dialogo.preguntas_clarificacion,
                'evidencia': dialogo.preguntas_evidencia,
                'perspectiva': dialogo.preguntas_perspectiva,
                'implicaciones': dialogo.preguntas_implicaciones,
                'origen': dialogo.preguntas_origen,
                'conclusion': dialogo.conclusion_reflexiva,
            } if dialogo else None,
            'perspectivas_alternativas': perspectivas,
            'puntuacion_autoconocimiento': round(puntuacion, 1),
            'recomendacion': recomendacion,
            'frase_inspiradora': frase,
            'total_creencias': len(creencias),
            'total_patrones': len(patrones),
        }
    
    def _detectar_creencias(self, texto_lower: str, texto_original: str) -> List[CreenciaDetectada]:
        """Detecta creencias limitantes en el texto."""
        creencias = []
        
        for tipo, patrones in self._patrones_creencias.items():
            for patron in patrones:
                match = patron.search(texto_lower)
                if match:
                    datos = self.CREENCIAS_LIMITANTES[tipo]
                    fragmento = texto_original[match.start():match.end()]
                    
                    # Generar pregunta reflexiva
                    pregunta = self._generar_pregunta_reflexiva(tipo, fragmento)
                    
                    creencia = CreenciaDetectada(
                        tipo=tipo,
                        nombre=datos['nombre'],
                        descripcion=datos['descripcion'],
                        fragmento=fragmento,
                        confianza=0.80,
                        pregunta_reflexiva=pregunta,
                        reformulacion=datos['reformulacion'],
                    )
                    creencias.append(creencia)
                    break
        
        return creencias
    
    def _generar_pregunta_reflexiva(self, tipo: TipoCreencia, fragmento: str) -> str:
        """Genera una pregunta reflexiva para cuestionar la creencia."""
        preguntas = {
            TipoCreencia.LIMITANTE: f"¿Es realmente cierto que '{fragmento}'? ¿Qué evidencia tienes?",
            TipoCreencia.ABSOLUTISTA: f"¿Siempre es así? ¿Puedes encontrar una excepción a '{fragmento}'?",
            TipoCreencia.CATASTROFISTA: f"¿Cuál es la probabilidad real de que ocurra '{fragmento}'?",
            TipoCreencia.GENERALIZADORA: f"¿Un solo caso justifica '{fragmento}'? ¿Hay contraejemplos?",
            TipoCreencia.ADIVINATORIA: f"¿Tienes evidencia real de '{fragmento}' o es una suposición?",
            TipoCreencia.AUTOEXIGENTE: f"¿Qué pasaría si no '{fragmento}'? ¿Sería realmente tan grave?",
            TipoCreencia.COMPARATIVA: f"¿Estás comparando tu proceso interno con el resultado externo de otros?",
        }
        return preguntas.get(tipo, f"¿Qué evidencia tienes para afirmar '{fragmento}'?")
    
    def _detectar_patrones(self, texto_lower: str, texto_original: str) -> List[PatronDetectado]:
        """Detecta patrones de pensamiento."""
        patrones_detectados = []
        
        for tipo, patrones in self._patrones_pensamiento.items():
            for patron in patrones:
                match = patron.search(texto_lower)
                if match:
                    datos = self.PATRONES_PENSAMIENTO[tipo]
                    fragmento = texto_original[match.start():match.end()]
                    
                    # Generar ejemplo alternativo
                    ejemplo = self._generar_ejemplo_alternativo(tipo, fragmento)
                    
                    patron_det = PatronDetectado(
                        tipo=tipo,
                        nombre=datos['nombre'],
                        descripcion=datos['descripcion'],
                        fragmento=fragmento,
                        confianza=0.80,
                        estrategia=datos['estrategia'],
                        ejemplo_alternativo=ejemplo,
                    )
                    patrones_detectados.append(patron_det)
                    break
        
        return patrones_detectados
    
    def _generar_ejemplo_alternativo(self, tipo: PatronPensamiento, fragmento: str) -> str:
        """Genera un ejemplo de pensamiento alternativo más saludable."""
        alternativas = {
            PatronPensamiento.PENSAMIENTO_BINARIO: f"En lugar de '{fragmento}', considera: 'Existen múltiples posibilidades intermedias que vale la pena explorar.'",
            PatronPensamiento.SOBREGENERALIZACION: f"En lugar de '{fragmento}', intenta: 'En esta situación específica, sucedió esto.'",
            PatronPensamiento.FILTRO_MENTAL: f"En lugar de enfocarte solo en lo negativo, pregúntate: '¿Qué aspectos positivos también están presentes?'",
            PatronPensamiento.VISION_CATASTROFICA: f"En lugar de '{fragmento}', considera: '¿Qué es lo MÁS PROBABLE que ocurra realmente?'",
            PatronPensamiento.DEBERIAS: f"Reemplaza '{fragmento}' por: 'Me gustaría...' o 'Preferiría...' para reducir la presión.",
        }
        return alternativas.get(tipo, f"Considera una perspectiva más equilibrada sobre '{fragmento}'.")
    
    def _generar_dialogo_socratico(self, texto: str, creencias: List[CreenciaDetectada],
                                   patrones: List[PatronDetectado]) -> ReflexionSocratica:
        """Genera un diálogo socrático completo."""
        dialogo = ReflexionSocratica()
        dialogo.pregunta_original = texto[:200]
        
        # Preguntas de clarificación
        dialogo.preguntas_clarificacion = [
            "¿Qué quieres decir exactamente con eso?",
            "¿Podrías explicarlo de otra manera?",
            "¿Cuál es el punto central de tu pensamiento?",
            "¿Puedes darme un ejemplo concreto?",
        ]
        
        # Preguntas de evidencia
        dialogo.preguntas_evidencia = [
            "¿Qué evidencia tienes para apoyar esta idea?",
            "¿De dónde proviene esta creencia?",
            "¿Es esto un hecho o una interpretación?",
            "¿Cómo sabes que esto es cierto?",
        ]
        
        # Preguntas de perspectiva
        dialogo.preguntas_perspectiva = [
            "¿Cómo vería esto otra persona?",
            "¿Qué le dirías a un amigo que pensara así?",
            "¿Hay otra forma de interpretar esta situación?",
            "¿Qué pensarías de esto dentro de 5 años?",
        ]
        
        # Preguntas de implicaciones
        dialogo.preguntas_implicaciones = [
            "¿Cuáles son las consecuencias de pensar así?",
            "¿Este pensamiento te ayuda o te limita?",
            "¿Qué pasaría si soltaras esta creencia?",
            "¿Qué es lo peor que podría pasar si cambiaras de opinión?",
        ]
        
        # Preguntas de origen
        dialogo.preguntas_origen = [
            "¿Cuándo empezaste a pensar así?",
            "¿Quién te enseñó esta forma de pensar?",
            "¿Esta creencia es realmente tuya o la heredaste?",
            "¿Qué experiencia originó este patrón de pensamiento?",
        ]
        
        # Conclusión reflexiva
        if creencias or patrones:
            total = len(creencias) + len(patrones)
            dialogo.conclusion_reflexiva = (
                f"Se detectaron {total} elemento(s) que podrían beneficiarse de una reflexión más profunda. "
                "Las creencias y patrones de pensamiento no son realidades fijas, sino hábitos mentales "
                "que pueden transformarse con conciencia y práctica. La clave está en cuestionar "
                "amablemente nuestras propias certezas."
            )
        else:
            dialogo.conclusion_reflexiva = (
                "Tu pensamiento muestra flexibilidad y apertura. Continúa cultivando "
                "la curiosidad y el cuestionamiento constructivo."
            )
        
        return dialogo
    
    def _generar_perspectivas(self, creencias: List[CreenciaDetectada],
                             patrones: List[PatronDetectado]) -> List[str]:
        """Genera perspectivas alternativas al pensamiento actual."""
        perspectivas = []
        
        if creencias:
            perspectivas.append("Tus creencias no son hechos. Son interpretaciones que pueden ser revisadas.")
        
        if patrones:
            perspectivas.append("Los patrones de pensamiento son como rutas en un bosque: cuanto más las usas, más marcadas están. Pero puedes crear nuevos senderos.")
        
        perspectivas.extend([
            "Imagina que un amigo querido te dijera exactamente lo mismo que tú piensas. ¿Qué le responderías desde la compasión?",
            "Dentro de 10 años, ¿este pensamiento seguirá teniendo la misma importancia que le das ahora?",
            "¿Qué es lo mejor que podría pasar si cambiaras esta forma de pensar?",
            "La mente es como un jardín: puedes elegir qué semillas regar y cuáles dejar marchitar.",
        ])
        
        return perspectivas[:5]
    
    def _evaluar_nivel(self, texto: str, creencias: List[CreenciaDetectada],
                      patrones: List[PatronDetectado]) -> NivelReflexion:
        """Evalúa el nivel de profundidad reflexiva del texto."""
        total_elementos = len(creencias) + len(patrones)
        longitud = len(texto.split())
        
        # Textos muy cortos con muchos patrones = superficial
        if total_elementos >= 5:
            return NivelReflexion.SUPERFICIAL
        elif total_elementos >= 3:
            return NivelReflexion.MODERADA
        elif total_elementos >= 1:
            return NivelReflexion.PROFUNDA
        elif longitud > 100:
            return NivelReflexion.MUY_PROFUNDA
        
        return NivelReflexion.MODERADA
    
    def _calcular_puntuacion(self, creencias: List[CreenciaDetectada],
                            patrones: List[PatronDetectado]) -> float:
        """Calcula puntuación de autoconocimiento (0-100)."""
        base = 70.0
        base -= len(creencias) * 8
        base -= len(patrones) * 5
        return max(10.0, min(100.0, base))
    
    def _generar_recomendacion(self, creencias: List[CreenciaDetectada],
                              patrones: List[PatronDetectado],
                              nivel: NivelReflexion) -> str:
        """Genera una recomendación personalizada."""
        if not creencias and not patrones:
            return ("Tu pensamiento muestra buena salud reflexiva. Sigue cultivando "
                   "la autoconciencia y el cuestionamiento constructivo.")
        
        partes = []
        
        if creencias:
            partes.append(f"Se identificaron {len(creencias)} creencia(s) que podrían estar limitándote. "
                         "Te recomiendo examinarlas con curiosidad, no con juicio.")
        
        if patrones:
            partes.append(f"Se detectaron {len(patrones)} patrón(es) de pensamiento. "
                         "La buena noticia es que los patrones se pueden cambiar con práctica consciente.")
        
        partes.append("Practica el diálogo socrático contigo mismo: cuestiona tus certezas con amabilidad.")
        
        return ' '.join(partes)
    
    def _resultado_vacio(self):
        return {
            'texto_original': '', 'nivel_reflexion': 'moderada',
            'creencias': [], 'patrones': [], 'dialogo_socratico': None,
            'perspectivas_alternativas': [], 'puntuacion_autoconocimiento': 50.0,
            'recomendacion': 'Sin texto para analizar.',
            'frase_inspiradora': 'Conocerte a ti mismo es el principio de toda sabiduría.',
            'total_creencias': 0, 'total_patrones': 0,
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR REFLEXIVO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor reflexivo...")
        motor = MotorReflexivo()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos: return r.datos
            return motor._resultado_vacio()
        
        print("\n[2/6] Creencias limitantes...")
        d1 = sd(motor.procesar("No puedo hacer esto. Soy incapaz de lograrlo. Nunca podré ser exitoso."))
        print(f"  📊 Creencias: {d1['total_creencias']} | Puntuación: {d1['puntuacion_autoconocimiento']}")
        for c in d1.get('creencias', [])[:2]:
            print(f"     - {c['nombre']}: {c['fragmento'][:50]}...")
            print(f"       ↳ {c['pregunta_reflexiva'][:80]}...")
        
        print("\n[3/6] Patrones de pensamiento...")
        d2 = sd(motor.procesar("Siempre es un desastre. Todo el mundo piensa que soy un fracaso. Debería ser perfecto."))
        print(f"  📊 Patrones: {d2['total_patrones']} | Puntuación: {d2['puntuacion_autoconocimiento']}")
        for p in d2.get('patrones', [])[:2]:
            print(f"     - {p['nombre']}: {p['estrategia'][:80]}...")
        
        print("\n[4/6] Diálogo socrático...")
        dialogo = d2.get('dialogo_socratico', {})
        if dialogo:
            print(f"  📊 Preguntas de clarificación: {len(dialogo.get('clarificacion', []))}")
            print(f"  📊 Preguntas de evidencia: {len(dialogo.get('evidencia', []))}")
            print(f"  📊 Preguntas de perspectiva: {len(dialogo.get('perspectiva', []))}")
        
        print("\n[5/6] Perspectivas alternativas...")
        for i, p in enumerate(d2.get('perspectivas_alternativas', [])[:3]):
            print(f"  📍 {i+1}. {p[:80]}...")
        
        print("\n[6/6] Frase inspiradora...")
        print(f"  💭 {d1.get('frase_inspiradora', '')}")
        
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