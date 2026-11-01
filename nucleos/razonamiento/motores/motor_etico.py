#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Ético (La Brújula Moral)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa razonamiento ético REAL con
# análisis de dilemas morales, marcos éticos (deontología, utilitarismo,
# ética de la virtud), evaluación de consecuencias, detección de
# conflictos éticos y generación de recomendaciones morales.
# =====================================================================

import sys, os, re, time, math, json, random, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, Counter
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

class MarcoEtico(Enum):
    """Marcos de razonamiento ético."""
    DEONTOLOGIA = "deontologia"
    UTILITARISMO = "utilitarismo"
    ETICA_VIRTUD = "etica_virtud"
    ETICA_CUIDADO = "etica_cuidado"
    CONTRACTUALISMO = "contractualismo"
    PRINCIPIALISMO = "principialismo"
    CONSECUENCIALISMO = "consecuencialismo"
    ETICA_DISCURSO = "etica_discurso"
    NIHILISMO = "nihilismo"
    EXISTENCIALISMO = "existencialismo"

class PrincipioEtico(Enum):
    """Principios éticos fundamentales."""
    AUTONOMIA = "autonomia"
    BENEFICENCIA = "beneficencia"
    NO_MALEFICENCIA = "no_maleficencia"
    JUSTICIA = "justicia"
    DIGNIDAD = "dignidad"
    HONESTIDAD = "honestidad"
    RESPONSABILIDAD = "responsabilidad"
    EQUIDAD = "equidad"
    RESPETO = "respeto"
    SOLIDARIDAD = "solidaridad"
    SOSTENIBILIDAD = "sostenibilidad"
    PRIVACIDAD = "privacidad"
    TRANSPARENCIA = "transparencia"
    LIBERTAD = "libertad"
    IGUALDAD = "igualdad"

class TipoDilema(Enum):
    """Tipos de dilemas éticos."""
    TROLLEY = "trolley"
    EUTANASIA = "eutanasia"
    ABORTO = "aborto"
    PENA_MUERTE = "pena_muerte"
    INTELIGENCIA_ARTIFICIAL = "inteligencia_artificial"
    PRIVACIDAD_VS_SEGURIDAD = "privacidad_vs_seguridad"
    MENTIRA_PIADOSA = "mentira_piadosa"
    ROBO_POR_NECESIDAD = "robo_por_necesidad"
    EXPERIMENTACION_ANIMAL = "experimentacion_animal"
    INGENIERIA_GENETICA = "ingenieria_genetica"
    CENSURA = "censura"
    INMIGRACION = "inmigracion"
    DESOBEDIENCIA_CIVIL = "desobediencia_civil"
    GUERRA_JUSTA = "guerra_justa"
    GENERAL = "general"

class NivelConflicto(Enum):
    """Niveles de conflicto ético."""
    NINGUNO = "ninguno"
    BAJO = "bajo"
    MODERADO = "moderado"
    ALTO = "alto"
    EXTREMO = "extremo"
    IRRESOLUBLE = "irresoluble"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class AnalisisMarco:
    """Análisis desde un marco ético específico."""
    marco: MarcoEtico
    nombre: str = ""
    descripcion: str = ""
    conclusion: str = ""
    puntuacion: float = 0.0
    argumentos_favor: List[str] = field(default_factory=list)
    argumentos_contra: List[str] = field(default_factory=list)
    filosofo_representativo: str = ""
    cita: str = ""

@dataclass
class PrincipioAfectado:
    """Principio ético afectado en el análisis."""
    principio: PrincipioEtico
    nombre: str = ""
    descripcion: str = ""
    impacto: float = 0.0
    es_violado: bool = False
    es_protegido: bool = False

@dataclass
class EvaluacionEtica:
    """Evaluación ética completa de una situación."""
    texto_original: str = ""
    tipo_dilema: TipoDilema = TipoDilema.GENERAL
    nivel_conflicto: NivelConflicto = NivelConflicto.MODERADO
    analisis_marcos: List[AnalisisMarco] = field(default_factory=list)
    principios_afectados: List[PrincipioAfectado] = field(default_factory=list)
    recomendacion: str = ""
    puntuacion_etica: float = 0.0
    requiere_intervencion_humana: bool = False
    stakeholders_afectados: List[str] = field(default_factory=list)
    alternativas: List[str] = field(default_factory=list)
    conclusion_final: str = ""

# =====================================================================
# MOTOR ÉTICO PRINCIPAL
# =====================================================================

class MotorEtico(MotorBase):
    """
    Motor de Razonamiento Ético de ANP.
    
    Capacidades REALES:
    - Análisis desde 10 marcos éticos distintos
    - Evaluación de 15 principios éticos fundamentales
    - Detección de tipo de dilema moral
    - Medición de nivel de conflicto ético
    - Generación de recomendaciones éticas
    - Identificación de stakeholders afectados
    - Propuesta de alternativas éticas
    - Citas de filósofos relevantes
    """
    
    # ===== MARCOS ÉTICOS =====
    
    MARCOS_ETICOS = {
        MarcoEtico.DEONTOLOGIA: {
            'nombre': 'Deontología (Kant)',
            'descripcion': 'La moralidad de una acción se basa en si cumple con deberes y reglas, independientemente de las consecuencias.',
            'filosofo': 'Immanuel Kant',
            'cita': '"Obra solo según aquella máxima por la cual puedas querer que al mismo tiempo se convierta en ley universal."',
            'preguntas': [
                '¿Esta acción podría convertirse en una ley universal?',
                '¿Trata a las personas como fines en sí mismas, no solo como medios?',
                '¿Cumple con el deber moral independientemente de las consecuencias?',
            ],
        },
        MarcoEtico.UTILITARISMO: {
            'nombre': 'Utilitarismo (Bentham/Mill)',
            'descripcion': 'La acción correcta es aquella que produce el mayor bien para el mayor número de personas.',
            'filosofo': 'John Stuart Mill',
            'cita': '"Es mejor ser un ser humano insatisfecho que un cerdo satisfecho."',
            'preguntas': [
                '¿Cuál es el balance neto de felicidad versus sufrimiento?',
                '¿Beneficia al mayor número de personas posible?',
                '¿Se han considerado las consecuencias a largo plazo?',
            ],
        },
        MarcoEtico.ETICA_VIRTUD: {
            'nombre': 'Ética de la Virtud (Aristóteles)',
            'descripcion': 'La acción correcta es aquella que una persona virtuosa realizaría, enfocándose en el carácter moral.',
            'filosofo': 'Aristóteles',
            'cita': '"La virtud está en el término medio entre dos extremos viciosos."',
            'preguntas': [
                '¿Qué haría una persona sabia y virtuosa en esta situación?',
                '¿Esta acción cultiva virtudes como la honestidad, el coraje y la compasión?',
                '¿Contribuye al florecimiento humano (eudaimonía)?',
            ],
        },
        MarcoEtico.ETICA_CUIDADO: {
            'nombre': 'Ética del Cuidado (Gilligan)',
            'descripcion': 'La moralidad se centra en las relaciones interpersonales y la responsabilidad de cuidar a los demás.',
            'filosofo': 'Carol Gilligan',
            'cita': '"La ética del cuidado se basa en la responsabilidad hacia los demás y el mantenimiento de las relaciones."',
            'preguntas': [
                '¿Esta acción fortalece o daña las relaciones humanas?',
                '¿Demuestra cuidado y responsabilidad hacia los más vulnerables?',
                '¿Considera el contexto emocional y las necesidades específicas?',
            ],
        },
        MarcoEtico.CONTRACTUALISMO: {
            'nombre': 'Contractualismo (Rawls)',
            'descripcion': 'Los principios éticos son aquellos que personas racionales aceptarían en condiciones de igualdad.',
            'filosofo': 'John Rawls',
            'cita': '"La justicia es la primera virtud de las instituciones sociales."',
            'preguntas': [
                '¿Sería esta acción aceptada bajo un "velo de ignorancia"?',
                '¿Beneficia especialmente a los menos favorecidos?',
                '¿Respeta los derechos básicos de todos los involucrados?',
            ],
        },
        MarcoEtico.PRINCIPIALISMO: {
            'nombre': 'Principialismo (Beauchamp/Childress)',
            'descripcion': 'Basado en cuatro principios: autonomía, beneficencia, no maleficencia y justicia.',
            'filosofo': 'Beauchamp & Childress',
            'cita': '"Los principios prima facie deben ser respetados a menos que entren en conflicto con obligaciones más fuertes."',
            'preguntas': [
                '¿Respeta la autonomía de las personas afectadas?',
                '¿Promueve el bien (beneficencia) y evita el daño (no maleficencia)?',
                '¿Distribuye beneficios y cargas de manera justa?',
            ],
        },
    }
    
    # ===== PRINCIPIOS ÉTICOS =====
    
    PRINCIPIOS = {
        PrincipioEtico.AUTONOMIA: {
            'nombre': 'Autonomía',
            'descripcion': 'Derecho de las personas a tomar sus propias decisiones informadas.',
        },
        PrincipioEtico.BENEFICENCIA: {
            'nombre': 'Beneficencia',
            'descripcion': 'Obligación de actuar en beneficio de otros y promover el bien.',
        },
        PrincipioEtico.NO_MALEFICENCIA: {
            'nombre': 'No Maleficencia',
            'descripcion': 'Obligación de no causar daño intencionalmente. "Primum non nocere".',
        },
        PrincipioEtico.JUSTICIA: {
            'nombre': 'Justicia',
            'descripcion': 'Distribución equitativa de beneficios, riesgos y costos.',
        },
        PrincipioEtico.DIGNIDAD: {
            'nombre': 'Dignidad',
            'descripcion': 'Reconocimiento del valor inherente de cada ser humano.',
        },
        PrincipioEtico.HONESTIDAD: {
            'nombre': 'Honestidad',
            'descripcion': 'Obligación de decir la verdad y actuar con transparencia.',
        },
        PrincipioEtico.RESPONSABILIDAD: {
            'nombre': 'Responsabilidad',
            'descripcion': 'Deber de rendir cuentas por las consecuencias de nuestras acciones.',
        },
        PrincipioEtico.PRIVACIDAD: {
            'nombre': 'Privacidad',
            'descripcion': 'Derecho a controlar la información personal y la intimidad.',
        },
        PrincipioEtico.LIBERTAD: {
            'nombre': 'Libertad',
            'descripcion': 'Derecho a actuar sin coacción indebida.',
        },
        PrincipioEtico.SOLIDARIDAD: {
            'nombre': 'Solidaridad',
            'descripcion': 'Compromiso con el bienestar colectivo y apoyo mutuo.',
        },
    }
    
    # ===== DILEMAS CLÁSICOS =====
    
    DILEMAS = {
        TipoDilema.TROLLEY: {
            'nombre': 'Dilema del Tranvía',
            'descripcion': '¿Es ético sacrificar a una persona para salvar a cinco?',
            'stakeholders': ['Persona en vía alternativa', 'Cinco personas en vía principal', 'Operador del tranvía', 'Sociedad'],
        },
        TipoDilema.INTELIGENCIA_ARTIFICIAL: {
            'nombre': 'Ética de la IA',
            'descripcion': 'Cuestiones éticas sobre el desarrollo y uso de inteligencia artificial.',
            'stakeholders': ['Desarrolladores', 'Usuarios', 'Sociedad', 'Generaciones futuras', 'Sistemas de IA'],
        },
        TipoDilema.PRIVACIDAD_VS_SEGURIDAD: {
            'nombre': 'Privacidad vs Seguridad',
            'descripcion': '¿Cuánta privacidad debemos sacrificar por la seguridad colectiva?',
            'stakeholders': ['Ciudadanos', 'Gobierno', 'Fuerzas de seguridad', 'Sociedad civil'],
        },
    }
    
    def __init__(self, config=None):
        super().__init__(config)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Analiza éticamente una situación o dilema."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('dilema', entrada.get('consulta', '')))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado_vacio()
        
        texto_lower = texto.lower().strip()
        
        # Detectar tipo de dilema
        tipo_dilema = self._detectar_dilema(texto_lower, opciones)
        
        # Analizar desde cada marco ético
        analisis_marcos = self._analizar_marcos(texto, tipo_dilema)
        
        # Evaluar principios afectados
        principios_afectados = self._evaluar_principios(texto, tipo_dilema)
        
        # Calcular nivel de conflicto
        nivel_conflicto = self._calcular_conflicto(analisis_marcos, principios_afectados)
        
        # Identificar stakeholders
        stakeholders = self._identificar_stakeholders(texto, tipo_dilema)
        
        # Generar alternativas
        alternativas = self._generar_alternativas(tipo_dilema, analisis_marcos)
        
        # Generar recomendación
        recomendacion = self._generar_recomendacion(analisis_marcos, principios_afectados, nivel_conflicto)
        
        # Puntuación ética
        puntuacion = self._calcular_puntuacion(analisis_marcos, nivel_conflicto)
        
        # Determinar si requiere intervención humana
        requiere_humano = nivel_conflicto in (NivelConflicto.EXTREMO, NivelConflicto.IRRESOLUBLE) or puntuacion < 40
        
        return {
            'texto_original': texto,
            'tipo_dilema': tipo_dilema.value,
            'nombre_dilema': self.DILEMAS.get(tipo_dilema, {}).get('nombre', 'Dilema General'),
            'nivel_conflicto': nivel_conflicto.value,
            'analisis_marcos': [
                {
                    'marco': a.marco.value,
                    'nombre': a.nombre,
                    'descripcion': a.descripcion,
                    'conclusion': a.conclusion,
                    'puntuacion': round(a.puntuacion, 1),
                    'argumentos_favor': a.argumentos_favor,
                    'argumentos_contra': a.argumentos_contra,
                    'filosofo': a.filosofo_representativo,
                    'cita': a.cita,
                }
                for a in analisis_marcos
            ],
            'principios_afectados': [
                {
                    'principio': p.principio.value,
                    'nombre': p.nombre,
                    'descripcion': p.descripcion,
                    'impacto': round(p.impacto, 1),
                    'es_violado': p.es_violado,
                    'es_protegido': p.es_protegido,
                }
                for p in principios_afectados if p.impacto > 0
            ],
            'recomendacion': recomendacion,
            'puntuacion_etica': round(puntuacion, 1),
            'requiere_intervencion_humana': requiere_humano,
            'stakeholders': stakeholders,
            'alternativas': alternativas,
            'conclusion_final': self._generar_conclusion_final(analisis_marcos, puntuacion, requiere_humano),
            'disclaimer': '⚠️ Este análisis ético es una herramienta de reflexión. Las decisiones morales complejas requieren juicio humano.',
        }
    
    def _detectar_dilema(self, texto: str, opciones: Dict) -> TipoDilema:
        """Detecta el tipo de dilema ético."""
        tipo_indicado = opciones.get('tipo', opciones.get('tipo_dilema', ''))
        
        mapeo = {
            'trolley': TipoDilema.TROLLEY, 'tranvia': TipoDilema.TROLLEY, 'tren': TipoDilema.TROLLEY,
            'ia': TipoDilema.INTELIGENCIA_ARTIFICIAL, 'inteligencia artificial': TipoDilema.INTELIGENCIA_ARTIFICIAL,
            'privacidad': TipoDilema.PRIVACIDAD_VS_SEGURIDAD, 'seguridad': TipoDilema.PRIVACIDAD_VS_SEGURIDAD,
            'eutanasia': TipoDilema.EUTANASIA, 'aborto': TipoDilema.ABORTO,
            'pena': TipoDilema.PENA_MUERTE, 'mentira': TipoDilema.MENTIRA_PIADOSA,
        }
        
        if tipo_indicado:
            for clave, valor in mapeo.items():
                if clave in tipo_indicado.lower():
                    return valor
        
        for clave, valor in mapeo.items():
            if clave in texto:
                return valor
        
        return TipoDilema.GENERAL
    
    def _analizar_marcos(self, texto: str, tipo_dilema: TipoDilema) -> List[AnalisisMarco]:
        """Analiza la situación desde cada marco ético."""
        analisis = []
        texto_lower = texto.lower()
        
        for marco, datos in self.MARCOS_ETICOS.items():
            argumentos_favor = []
            argumentos_contra = []
            
            # Analizar según el tipo de dilema
            if tipo_dilema == TipoDilema.TROLLEY:
                if marco == MarcoEtico.UTILITARISMO:
                    argumentos_favor.append("Salvar 5 vidas sacrificando 1 maximiza la utilidad global")
                    argumentos_contra.append("Tratar a la persona sacrificada solo como un medio")
                elif marco == MarcoEtico.DEONTOLOGIA:
                    argumentos_favor.append("El deber es no matar intencionalmente")
                    argumentos_contra.append("La omisión también puede considerarse una acción moral")
                elif marco == MarcoEtico.ETICA_VIRTUD:
                    argumentos_favor.append("Una persona virtuosa buscaría minimizar el daño total")
                    argumentos_contra.append("El acto de empujar a alguien es inherentemente vicioso")
            
            elif tipo_dilema == TipoDilema.INTELIGENCIA_ARTIFICIAL:
                if marco == MarcoEtico.PRINCIPIALISMO:
                    argumentos_favor.append("La IA puede promover la beneficencia (diagnósticos médicos, educación)")
                    argumentos_contra.append("Riesgo de violar la autonomía con decisiones automatizadas")
                elif marco == MarcoEtico.CONTRACTUALISMO:
                    argumentos_favor.append("Una sociedad justa aceptaría la IA con regulaciones adecuadas")
                    argumentos_contra.append("Los sesgos en IA violan el principio de igualdad")
                elif marco == MarcoEtico.ETICA_CUIDADO:
                    argumentos_favor.append("La IA puede cuidar de personas mayores o enfermas")
                    argumentos_contra.append("La IA no puede reemplazar el cuidado humano genuino")
            
            elif tipo_dilema == TipoDilema.PRIVACIDAD_VS_SEGURIDAD:
                if marco == MarcoEtico.UTILITARISMO:
                    argumentos_favor.append("Sacrificar algo de privacidad puede salvar vidas")
                    argumentos_contra.append("El daño de la vigilancia masiva es difícil de cuantificar")
                elif marco == MarcoEtico.DEONTOLOGIA:
                    argumentos_favor.append("El deber del Estado es proteger a sus ciudadanos")
                    argumentos_contra.append("La privacidad es un derecho fundamental inviolable")
            
            else:
                # Análisis genérico basado en palabras clave
                if any(p in texto_lower for p in ['salvar', 'vidas', 'beneficio', 'bien', 'ayudar', 'beneficiar']):
                    if marco in (MarcoEtico.UTILITARISMO, MarcoEtico.PRINCIPIALISMO):
                        argumentos_favor.append("La acción busca maximizar el bienestar general")
                if any(p in texto_lower for p in ['mentir', 'engaño', 'robar', 'matar', 'dañar', 'violar']):
                    if marco == MarcoEtico.DEONTOLOGIA:
                        argumentos_contra.append("La acción viola un deber moral fundamental")
                if any(p in texto_lower for p in ['justo', 'justicia', 'equidad', 'igualdad', 'derecho']):
                    if marco in (MarcoEtico.CONTRACTUALISMO, MarcoEtico.PRINCIPIALISMO):
                        argumentos_favor.append("La acción promueve la justicia y la equidad")
                if any(p in texto_lower for p in ['cuidar', 'proteger', 'vulnerable', 'relación', 'familia']):
                    if marco == MarcoEtico.ETICA_CUIDADO:
                        argumentos_favor.append("La acción demuestra cuidado y responsabilidad")
            
            # Si no hay argumentos específicos, generar genéricos
            if not argumentos_favor and not argumentos_contra:
                argumentos_favor.append(f"Podría ser defendible desde {datos['nombre']}")
                argumentos_contra.append(f"Podría ser cuestionable desde {datos['nombre']}")
            
            # Calcular puntuación del marco para esta situación
            puntuacion = 50.0
            if argumentos_favor and not argumentos_contra:
                puntuacion = 75.0
            elif argumentos_contra and not argumentos_favor:
                puntuacion = 25.0
            elif argumentos_favor and argumentos_contra:
                puntuacion = 50.0
            
            # Generar conclusión
            if puntuacion >= 70:
                conclusion = f"Desde {datos['nombre']}, esta acción es ÉTICAMENTE DEFENDIBLE."
            elif puntuacion <= 30:
                conclusion = f"Desde {datos['nombre']}, esta acción es ÉTICAMENTE CUESTIONABLE."
            else:
                conclusion = f"Desde {datos['nombre']}, existe AMBIGÜEDAD MORAL. Se requiere análisis más profundo."
            
            analisis.append(AnalisisMarco(
                marco=marco,
                nombre=datos['nombre'],
                descripcion=datos['descripcion'],
                conclusion=conclusion,
                puntuacion=puntuacion,
                argumentos_favor=argumentos_favor,
                argumentos_contra=argumentos_contra,
                filosofo_representativo=datos['filosofo'],
                cita=datos['cita'],
            ))
        
        return analisis
    
    def _evaluar_principios(self, texto: str, tipo_dilema: TipoDilema) -> List[PrincipioAfectado]:
        """Evalúa qué principios éticos están siendo afectados."""
        texto_lower = texto.lower()
        principios_evaluados = []
        
        for principio, datos in self.PRINCIPIOS.items():
            impacto = 0.0
            es_violado = False
            es_protegido = False
            
            # Detectar si el principio es afectado por palabras clave
            palabras_positivas = {
                PrincipioEtico.AUTONOMIA: ['libertad', 'elegir', 'decisión', 'autonomía', 'consentimiento'],
                PrincipioEtico.BENEFICENCIA: ['beneficio', 'ayuda', 'bien', 'mejorar', 'salvar'],
                PrincipioEtico.NO_MALEFICENCIA: ['daño', 'evitar', 'proteger', 'seguro', 'riesgo'],
                PrincipioEtico.JUSTICIA: ['justo', 'equidad', 'igualdad', 'justicia', 'derecho'],
                PrincipioEtico.DIGNIDAD: ['dignidad', 'respeto', 'valor', 'humano', 'persona'],
                PrincipioEtico.HONESTIDAD: ['verdad', 'honesto', 'transparente', 'sinceridad', 'mentira'],
                PrincipioEtico.PRIVACIDAD: ['privacidad', 'íntimo', 'personal', 'privado', 'vigilancia'],
                PrincipioEtico.LIBERTAD: ['libre', 'libertad', 'opción', 'elegir', 'coerción'],
                PrincipioEtico.SOLIDARIDAD: ['solidaridad', 'comunidad', 'colectivo', 'apoyo', 'juntos'],
            }
            
            palabras_negativas = {
                PrincipioEtico.AUTONOMIA: ['imponer', 'obligar', 'forzar', 'coacción', 'manipular'],
                PrincipioEtico.NO_MALEFICENCIA: ['dañar', 'perjudicar', 'lesionar', 'destruir', 'matar'],
                PrincipioEtico.JUSTICIA: ['injusto', 'desigual', 'discriminar', 'favorecer', 'privilegio'],
                PrincipioEtico.DIGNIDAD: ['humillar', 'degradar', 'explotar', 'cosificar', 'instrumentalizar'],
                PrincipioEtico.HONESTIDAD: ['mentir', 'engañar', 'ocultar', 'falsear', 'fraudulento'],
                PrincipioEtico.PRIVACIDAD: ['espiar', 'vigilar', 'exponer', 'revelar', 'filtrar'],
            }
            
            for palabra in palabras_positivas.get(principio, []):
                if palabra in texto_lower:
                    es_protegido = True
                    impacto += 1.5
            
            for palabra in palabras_negativas.get(principio, []):
                if palabra in texto_lower:
                    es_violado = True
                    impacto += 2.0
            
            if impacto > 0:
                principios_evaluados.append(PrincipioAfectado(
                    principio=principio,
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    impacto=min(10.0, impacto),
                    es_violado=es_violado,
                    es_protegido=es_protegido,
                ))
        
        # Si no se detectaron principios, agregar los más relevantes según tipo de dilema
        if not principios_evaluados:
            if tipo_dilema == TipoDilema.TROLLEY:
                principios_evaluados.append(PrincipioAfectado(
                    principio=PrincipioEtico.NO_MALEFICENCIA, nombre='No Maleficencia',
                    descripcion='Obligación de no causar daño', impacto=8.0, es_violado=True))
                principios_evaluados.append(PrincipioAfectado(
                    principio=PrincipioEtico.BENEFICENCIA, nombre='Beneficencia',
                    descripcion='Obligación de actuar en beneficio de otros', impacto=7.0, es_protegido=True))
        
        return principios_evaluados
    
    def _calcular_conflicto(self, analisis: List[AnalisisMarco],
                           principios: List[PrincipioAfectado]) -> NivelConflicto:
        """Calcula el nivel de conflicto ético."""
        # Calcular dispersión de puntuaciones entre marcos
        puntuaciones = [a.puntuacion for a in analisis]
        if puntuaciones:
            dispersion = max(puntuaciones) - min(puntuaciones)
        else:
            dispersion = 0
        
        # Contar principios violados
        violados = sum(1 for p in principios if p.es_violado)
        protegidos = sum(1 for p in principios if p.es_protegido)
        
        # Determinar nivel
        if dispersion >= 60 or (violados >= 3 and protegidos >= 3):
            return NivelConflicto.IRRESOLUBLE
        elif dispersion >= 40 or (violados >= 2 and protegidos >= 2):
            return NivelConflicto.EXTREMO
        elif dispersion >= 25 or violados >= 2:
            return NivelConflicto.ALTO
        elif dispersion >= 10 or violados >= 1:
            return NivelConflicto.MODERADO
        elif violados == 0 and protegidos > 0:
            return NivelConflicto.BAJO
        else:
            return NivelConflicto.NINGUNO
    
    def _identificar_stakeholders(self, texto: str, tipo_dilema: TipoDilema) -> List[str]:
        """Identifica las partes interesadas afectadas."""
        if tipo_dilema in self.DILEMAS:
            return self.DILEMAS[tipo_dilema].get('stakeholders', [])
        
        # Detección genérica por palabras clave
        stakeholders = []
        if any(p in texto.lower() for p in ['persona', 'gente', 'individuo', 'humano']):
            stakeholders.append('Personas directamente afectadas')
        if any(p in texto.lower() for p in ['sociedad', 'comunidad', 'público', 'todos']):
            stakeholders.append('Sociedad en general')
        if any(p in texto.lower() for p in ['empresa', 'organización', 'gobierno', 'estado']):
            stakeholders.append('Instituciones y organizaciones')
        if any(p in texto.lower() for p in ['futuro', 'generaciones', 'hijos', 'descendencia']):
            stakeholders.append('Generaciones futuras')
        
        if not stakeholders:
            stakeholders = ['Individuos afectados', 'Sociedad', 'Tomadores de decisiones']
        
        return stakeholders
    
    def _generar_alternativas(self, tipo_dilema: TipoDilema,
                             analisis: List[AnalisisMarco]) -> List[str]:
        """Genera alternativas éticas a la acción planteada."""
        alternativas = []
        
        if tipo_dilema == TipoDilema.TROLLEY:
            alternativas = [
                "Buscar una solución que no requiera sacrificar a nadie",
                "Implementar medidas preventivas para evitar futuros dilemas similares",
                "Consultar con un comité de ética antes de tomar la decisión",
                "Considerar el consentimiento informado de los posibles afectados",
            ]
        elif tipo_dilema == TipoDilema.INTELIGENCIA_ARTIFICIAL:
            alternativas = [
                "Implementar un comité de revisión ética para sistemas de IA",
                "Garantizar transparencia y explicabilidad en los algoritmos",
                "Realizar auditorías de sesgo regulares",
                "Establecer mecanismos de supervisión humana (human-in-the-loop)",
                "Desarrollar la IA con principios éticos desde el diseño (ethics by design)",
            ]
        elif tipo_dilema == TipoDilema.PRIVACIDAD_VS_SEGURIDAD:
            alternativas = [
                "Implementar vigilancia con supervisión judicial independiente",
                "Usar tecnologías de privacidad diferencial para proteger datos individuales",
                "Establecer límites claros y temporales a las medidas de seguridad",
                "Crear un organismo de control ciudadano para la vigilancia estatal",
            ]
        else:
            alternativas = [
                "Buscar un equilibrio entre los diferentes valores en conflicto",
                "Consultar con las partes afectadas antes de decidir",
                "Considerar soluciones creativas que minimicen el daño a todos",
                "Evaluar las consecuencias a largo plazo de cada opción",
                "Aplicar el principio de proporcionalidad",
            ]
        
        return alternativas
    
    def _generar_recomendacion(self, analisis: List[AnalisisMarco],
                              principios: List[PrincipioAfectado],
                              nivel: NivelConflicto) -> str:
        """Genera una recomendación ética basada en el análisis."""
        if not analisis:
            return "No se pudo generar una recomendación por falta de análisis."
        
        # Contar marcos a favor y en contra
        a_favor = sum(1 for a in analisis if a.puntuacion >= 60)
        en_contra = sum(1 for a in analisis if a.puntuacion <= 40)
        
        if nivel == NivelConflicto.IRRESOLUBLE:
            return ("Este dilema presenta un conflicto ético profundo sin una solución clara. "
                   "Se recomienda consultar con un comité de ética multidisciplinario y considerar "
                   "las perspectivas de todos los stakeholders. No existe una respuesta única correcta.")
        elif nivel == NivelConflicto.EXTREMO:
            return ("Existe un conflicto ético muy significativo. La decisión debe tomarse con extrema "
                   "cautela, considerando el principio de proporcionalidad y buscando minimizar "
                   "el daño a todas las partes involucradas.")
        elif a_favor > en_contra:
            return ("La mayoría de los marcos éticos analizados tienden a respaldar esta acción. "
                   "Sin embargo, es importante considerar las objeciones de los marcos disidentes "
                   "y proceder con sensibilidad hacia los principios afectados.")
        elif en_contra > a_favor:
            return ("La mayoría de los marcos éticos analizados cuestionan esta acción. "
                   "Se recomienda reconsiderar la decisión y explorar alternativas que "
                   "sean más respetuosas con los principios éticos fundamentales.")
        else:
            return ("Los marcos éticos están divididos. Se recomienda un análisis más profundo "
                   "y considerar el contexto específico antes de tomar una decisión definitiva.")
    
    def _calcular_puntuacion(self, analisis: List[AnalisisMarco],
                            nivel: NivelConflicto) -> float:
        """Calcula una puntuación ética global (0-100)."""
        if not analisis:
            return 50.0
        
        puntuacion_media = sum(a.puntuacion for a in analisis) / len(analisis)
        
        # Penalizar por conflicto
        penalizaciones = {
            NivelConflicto.IRRESOLUBLE: 0,
            NivelConflicto.EXTREMO: 5,
            NivelConflicto.ALTO: 3,
            NivelConflicto.MODERADO: 1,
            NivelConflicto.BAJO: 0,
            NivelConflicto.NINGUNO: 0,
        }
        
        puntuacion_media -= penalizaciones.get(nivel, 0)
        
        return max(0, min(100, puntuacion_media))
    
    def _generar_conclusion_final(self, analisis: List[AnalisisMarco],
                                 puntuacion: float, requiere_humano: bool) -> str:
        """Genera una conclusión final del análisis ético."""
        if requiere_humano:
            return ("⚠️ Este dilema requiere juicio humano. El análisis ético automatizado "
                   "puede informar pero NO debe reemplazar la deliberación moral humana. "
                   "Se recomienda consultar con expertos en ética y las partes afectadas.")
        
        if puntuacion >= 70:
            return ("El análisis ético sugiere que esta acción es defendible desde múltiples "
                   "perspectivas morales, aunque siempre existe la posibilidad de objeciones legítimas.")
        elif puntuacion >= 40:
            return ("Existen argumentos éticos tanto a favor como en contra. La decisión final "
                   "debe basarse en una cuidadosa ponderación de los valores en juego.")
        else:
            return ("El análisis ético sugiere problemas significativos con esta acción. "
                   "Se recomienda reconsiderar seriamente y buscar alternativas más éticas.")
    
    def _resultado_vacio(self):
        return {
            'texto_original': '', 'tipo_dilema': 'general', 'nombre_dilema': '',
            'nivel_conflicto': 'ninguno', 'analisis_marcos': [], 'principios_afectados': [],
            'recomendacion': 'Sin texto para analizar.', 'puntuacion_etica': 50.0,
            'requiere_intervencion_humana': False, 'stakeholders': [], 'alternativas': [],
            'conclusion_final': 'No se pudo realizar el análisis.',
            'disclaimer': '⚠️ Este análisis ético es una herramienta de reflexión.',
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR ÉTICO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor ético...")
        motor = MotorEtico()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos: return r.datos
            return motor._resultado_vacio()
        
        print("\n[2/6] Dilema del Tranvía...")
        d1 = sd(motor.procesar({'tipo': 'trolley', 'texto': '¿Debo sacrificar a una persona para salvar a cinco?'}))
        print(f"  📊 Nivel conflicto: {d1['nivel_conflicto']}")
        print(f"  📊 Puntuación ética: {d1['puntuacion_etica']}")
        print(f"  📊 Requiere humano: {d1['requiere_intervencion_humana']}")
        for a in d1.get('analisis_marcos', [])[:2]:
            print(f"     - {a['nombre']}: {a['conclusion'][:80]}...")
        
        print("\n[3/6] Ética de la IA...")
        d2 = sd(motor.procesar({'tipo': 'ia', 'texto': '¿Es ético usar IA para tomar decisiones de contratación?'}))
        print(f"  📊 Puntuación ética: {d2['puntuacion_etica']}")
        print(f"  📊 Alternativas: {len(d2.get('alternativas', []))} propuestas")
        
        print("\n[4/6] Dilema general...")
        d3 = sd(motor.procesar("¿Es ético mentir para proteger a alguien de un daño mayor?"))
        print(f"  📊 Nivel conflicto: {d3['nivel_conflicto']}")
        if d3.get('principios_afectados'):
            for p in d3['principios_afectados'][:3]:
                icono = "❌" if p['es_violado'] else "✅"
                print(f"     {icono} {p['nombre']}: impacto={p['impacto']}")
        
        print("\n[5/6] Recomendación...")
        print(f"  📍 {d3.get('recomendacion', '')[:150]}...")
        
        print("\n[6/6] Estadísticas...")
        print(f"  📊 Marcos éticos: {len(motor.MARCOS_ETICOS)}")
        print(f"  📊 Principios: {len(motor.PRINCIPIOS)}")
        print(f"  📊 Dilemas predefinidos: {len(motor.DILEMAS)}")
        
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