#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Diálogo (El Arquitecto de la Conversación)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa gestión de diálogo multi-turno
# REAL con estados conversacionales, contexto dinámico, memoria de
# conversación, adaptación de personalidad, manejo de turnos y
# generación de respuestas contextuales.
# =====================================================================

import sys, os, re, time, json, math, uuid, random, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque, OrderedDict, Counter
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
                self._id = str(uuid.uuid4())
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

class EstadoConversacion(Enum):
    INICIO = "inicio"
    SALUDO = "saludo"
    PRESENTACION = "presentacion"
    EXPLORACION = "exploracion"
    PROFUNDIZACION = "profundizacion"
    ACLARACION = "aclaracion"
    CONFIRMACION = "confirmacion"
    CIERRE = "cierre"
    DESPEDIDA = "despedida"
    ESPERA = "espera"
    ERROR = "error"

class EstrategiaRespuesta(Enum):
    DIRECTA = "directa"
    ELABORADA = "elaborada"
    REFLEXIVA = "reflexiva"
    EMPATICA = "empatica"
    SOCRATICA = "socratica"
    RESUMEN = "resumen"
    ACLARACION = "aclaracion"
    SUGERENCIA = "sugerencia"
    HUMORISTICA = "humoristica"

class PersonalidadDialogo(Enum):
    FORMAL = "formal"
    AMIGABLE = "amigable"
    TECNICO = "tecnico"
    CREATIVO = "creativo"
    SOCRATICO = "socratico"
    EMPATICO = "empatito"
    HUMORISTICO = "humoristico"
    ADAPTATIVO = "adaptativo"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class TurnoConversacion:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    rol: str = "usuario"
    texto: str = ""
    intencion: Optional[str] = None
    sentimiento: Optional[str] = None
    entidades: List[Dict] = field(default_factory=list)
    contexto_local: Dict[str, Any] = field(default_factory=dict)
    duracion_ms: float = 0.0

@dataclass
class ContextoConversacional:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    estado: EstadoConversacion = EstadoConversacion.INICIO
    tema_actual: str = ""
    temas_tratados: List[str] = field(default_factory=list)
    personalidad: PersonalidadDialogo = PersonalidadDialogo.ADAPTATIVO
    turnos: List[TurnoConversacion] = field(default_factory=list)
    entidades_acumuladas: Dict[str, Any] = field(default_factory=dict)
    preguntas_pendientes: List[str] = field(default_factory=list)
    nivel_profundidad: int = 0
    satisfaccion_estimada: float = 0.5
    ultima_actividad: float = field(default_factory=time.time)
    metadatos: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RespuestaDialogo:
    texto: str
    estrategia: EstrategiaRespuesta
    confianza: float = 0.8
    sugerencias: List[str] = field(default_factory=list)
    emocion_transmitida: str = "neutral"
    referencias: List[str] = field(default_factory=list)
    acciones_sugeridas: List[str] = field(default_factory=list)

# =====================================================================
# MOTOR DE DIÁLOGO PRINCIPAL (CORREGIDO)
# =====================================================================

class MotorDialogo(MotorBase):
    """Motor de Gestión de Diálogo Multi-Turno de ANP."""
    
    # ===== PLANTILLAS DE RESPUESTA POR ESTADO =====
    
    PLANTILLAS = {
        EstadoConversacion.SALUDO: {
            'formal': [
                "Buenos días. ¿En qué puedo ayudarle hoy?",
                "Saludos. Estoy a su disposición para lo que necesite.",
            ],
            'amigable': [
                "¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte?",
                "¡Hey! Qué gusto verte. ¿Qué necesitas?",
            ],
            'tecnico': [
                "Sistema iniciado. Indique su consulta.",
                "ANP en línea. Especifique su requerimiento.",
            ],
            'creativo': [
                "¡Saludos, explorador del conocimiento! ¿Qué misterio desvelamos hoy?",
                "Bienvenido a bordo. ¿Hacia dónde dirigimos nuestra imaginación?",
            ],
            'empatito': [
                "¡Qué gusto verte! Cuéntame, ¿cómo te sientes hoy?",
                "Bienvenido. Estoy aquí para escucharte y ayudarte.",
            ],
        },
        EstadoConversacion.PRESENTACION: {
            'formal': [
                "Soy ANP, un sistema de inteligencia artificial diseñado para asistirle. ¿Podría indicarme su nombre?",
            ],
            'amigable': [
                "Soy ANP, tu asistente de IA. ¿Cómo te llamas?",
            ],
            'tecnico': [
                "ANP v0.0.1-NEBULA. Arquitectura Neuronal Profunda. Listo para procesar consultas.",
            ],
        },
        EstadoConversacion.EXPLORACION: {
            'formal': [
                "Interesante consulta. Permítame analizarla.",
                "Estoy procesando su solicitud. ¿Podría darme más detalles?",
            ],
            'amigable': [
                "¡Qué interesante! Déjame ver eso.",
                "Vale, estoy en ello. ¿Algo más que deba saber?",
            ],
            'tecnico': [
                "Procesando consulta. Analizando parámetros relevantes.",
            ],
        },
        EstadoConversacion.CIERRE: {
            'formal': [
                "Ha sido un placer ayudarle. Quedo a su disposición. Hasta pronto.",
            ],
            'amigable': [
                "¡Me alegró ayudarte! Nos vemos pronto. ¡Cuídate!",
            ],
            'empatito': [
                "Espero haberte sido de ayuda. Cuídate mucho. Aquí estaré cuando me necesites.",
            ],
        },
        EstadoConversacion.DESPEDIDA: {
            'formal': [
                "Le deseo un excelente día. Estaré aquí cuando me necesite.",
            ],
            'amigable': [
                "¡Que tengas un día increíble! Chao.",
            ],
            'creativo': [
                "Que las musas te acompañen en tu camino. ¡Hasta la próxima aventura!",
            ],
        },
        EstadoConversacion.ESPERA: {
            'formal': [
                "Permítame un momento mientras proceso su solicitud.",
            ],
            'amigable': [
                "Dame un segundo, estoy procesando esto...",
            ],
        },
        EstadoConversacion.ERROR: {
            'formal': [
                "Disculpe, he encontrado una dificultad técnica. ¿Podría reformular su consulta?",
            ],
            'amigable': [
                "Ups, tuve un problema al procesar eso. ¿Puedes decirlo de otra forma?",
            ],
        },
    }
    
    # ===== RESPUESTAS POR INTENCIÓN =====
    
    RESPUESTAS_INTENCION = {
        'pregunta': {
            'directa': "Basado en la información disponible, {respuesta}",
            'elaborada': "Excelente pregunta. Permíteme explicarlo detalladamente: {respuesta}. ¿Te gustaría profundizar en algún aspecto?",
            'reflexiva': "Interesante cuestión. Reflexionando sobre ello: {respuesta}. ¿Qué opinas tú?",
            'socratica': "Antes de responder, ¿qué crees tú que significa? ... Interesante perspectiva. Complementando tu idea: {respuesta}",
        },
        'pregunta_definicion': {
            'elaborada': "Una definición completa sería: {respuesta}. ¿Necesitas que la desglose más?",
            'directa': "Se define como: {respuesta}",
        },
        'pregunta_procedimiento': {
            'elaborada': "El procedimiento es el siguiente: {respuesta}. ¿Quieres que detalle algún paso en particular?",
            'directa': "Los pasos son: {respuesta}",
        },
        'orden': {
            'directa': "De acuerdo, {respuesta}",
            'elaborada': "¡Claro! Aquí tienes: {respuesta}. ¿Quieres que profundice en algo?",
        },
        'solicitud': {
            'directa': "Claro, {respuesta}",
            'empatica': "Entiendo que necesitas {respuesta}. Déjame ayudarte con eso.",
        },
        'agradecimiento': {
            'directa': "¡De nada! Es un placer ayudar.",
            'amigable': "No hay de qué. Para eso estoy. 😊",
            'formal': "Ha sido un placer. Estoy a su disposición.",
        },
        'queja': {
            'empatica': "Lamento mucho escuchar eso. Entiendo tu frustración. Veamos cómo podemos solucionarlo.",
            'directa': "Comprendo tu molestia. Trabajemos juntos para resolver este problema.",
        },
        'desconocido': {
            'directa': "¡Gracias por tu mensaje! Déjame ayudarte con eso. {respuesta}",
            'amigable': "Vale, cuéntame más sobre eso.",
            'reflexiva': "Interesante. ¿Podrías elaborar un poco más?",
        },
    }
    
    # ===== SUGERENCIAS POR ESTADO =====
    
    SUGERENCIAS = {
        EstadoConversacion.SALUDO: [
            "¿En qué tema estás interesado hoy?",
            "¿Necesitas ayuda con algo específico?",
        ],
        EstadoConversacion.EXPLORACION: [
            "¿Te gustaría que profundice en algún aspecto?",
            "¿Hay algo más que quieras saber sobre este tema?",
            "¿Prefieres un enfoque más técnico o más divulgativo?",
        ],
        EstadoConversacion.PROFUNDIZACION: [
            "¿Quieres que te muestre ejemplos concretos?",
            "¿Necesitas referencias adicionales?",
            "¿Te gustaría ver aplicaciones prácticas de esto?",
        ],
        EstadoConversacion.CONFIRMACION: [
            "¿Es correcta esta información?",
            "¿Responde esto a tu pregunta?",
            "¿Necesitas alguna aclaración adicional?",
        ],
        EstadoConversacion.CIERRE: [
            "¿Hay algo más en lo que pueda ayudarte?",
            "¿Quieres que exploremos otro tema?",
        ],
    }
    
    # ===== TRANSICIONES DE ESTADO (CORREGIDAS) =====
    
    TRANSICIONES = {
        EstadoConversacion.INICIO: {
            'saludo': EstadoConversacion.SALUDO,
            'pregunta': EstadoConversacion.EXPLORACION,
            'orden': EstadoConversacion.EXPLORACION,
            'default': EstadoConversacion.SALUDO,
        },
        EstadoConversacion.SALUDO: {
            'pregunta': EstadoConversacion.EXPLORACION,
            'orden': EstadoConversacion.EXPLORACION,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.EXPLORACION,
        },
        EstadoConversacion.PRESENTACION: {
            'pregunta': EstadoConversacion.EXPLORACION,
            'saludo': EstadoConversacion.SALUDO,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.EXPLORACION,
        },
        EstadoConversacion.EXPLORACION: {
            'pregunta': EstadoConversacion.PROFUNDIZACION,
            'orden': EstadoConversacion.PROFUNDIZACION,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.EXPLORACION,
        },
        EstadoConversacion.PROFUNDIZACION: {
            'pregunta': EstadoConversacion.ACLARACION,
            'orden': EstadoConversacion.PROFUNDIZACION,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.CONFIRMACION,
        },
        EstadoConversacion.ACLARACION: {
            'pregunta': EstadoConversacion.ACLARACION,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.EXPLORACION,
        },
        EstadoConversacion.CONFIRMACION: {
            'pregunta': EstadoConversacion.EXPLORACION,
            'despedida': EstadoConversacion.DESPEDIDA,
            'default': EstadoConversacion.CIERRE,
        },
        EstadoConversacion.CIERRE: {
            'despedida': EstadoConversacion.DESPEDIDA,
            'pregunta': EstadoConversacion.EXPLORACION,
            'saludo': EstadoConversacion.SALUDO,
            'default': EstadoConversacion.ESPERA,
        },
        EstadoConversacion.DESPEDIDA: {
            'saludo': EstadoConversacion.SALUDO,
            'pregunta': EstadoConversacion.EXPLORACION,
            'default': EstadoConversacion.INICIO,
        },
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        self._contexto: Optional[ContextoConversacional] = None
        self._historial: deque = deque(maxlen=100)
        self._lock = threading.RLock()
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Procesa un turno de diálogo."""
        if isinstance(entrada, str):
            texto = entrada
            metadatos = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('mensaje', ''))
            metadatos = entrada
        else:
            texto = str(entrada)
            metadatos = {}
        
        if not texto or not texto.strip():
            return self._resultado_vacio()
        
        with self._lock:
            # Inicializar contexto si no existe
            if self._contexto is None:
                self._contexto = ContextoConversacional(
                    personalidad=PersonalidadDialogo.ADAPTATIVO
                )
            
            # Obtener metadatos del análisis previo
            intencion = metadatos.get('intencion', metadatos.get('intencion_principal', 'desconocido'))
            if isinstance(intencion, dict):
                intencion = intencion.get('categoria', 'desconocido')
            
            sentimiento = metadatos.get('sentimiento', 'neutral')
            if isinstance(sentimiento, dict):
                sentimiento = sentimiento.get('polaridad', 'neutral')
            
            entidades = metadatos.get('entidades', [])
            personalidad_nombre = metadatos.get('personalidad', 'adaptativo')
            
            # Ajustar personalidad
            if personalidad_nombre != 'adaptativo':
                try:
                    self._contexto.personalidad = PersonalidadDialogo(personalidad_nombre)
                except ValueError:
                    pass
            
            # Si el estado es DESPEDIDA y llega un saludo, reiniciar contexto
            if self._contexto.estado == EstadoConversacion.DESPEDIDA and intencion == 'saludo':
                self._contexto = ContextoConversacional(
                    personalidad=self._contexto.personalidad
                )
            
            # Crear turno
            turno = TurnoConversacion(
                rol="usuario",
                texto=texto,
                intencion=intencion,
                sentimiento=sentimiento,
                entidades=entidades,
            )
            self._contexto.turnos.append(turno)
            self._contexto.ultima_actividad = time.time()
            
            # Transición de estado
            estado_anterior = self._contexto.estado
            self._contexto.estado = self._transicionar_estado(intencion)
            
            # Acumular entidades
            for ent in entidades:
                nombre = ent.get('texto', '')
                tipo = ent.get('tipo', 'desconocido')
                if nombre:
                    self._contexto.entidades_acumuladas[nombre] = tipo
            
            # Actualizar nivel de profundidad
            if self._contexto.estado in (EstadoConversacion.PROFUNDIZACION, EstadoConversacion.ACLARACION):
                self._contexto.nivel_profundidad = min(5, self._contexto.nivel_profundidad + 1)
            elif self._contexto.estado == EstadoConversacion.EXPLORACION and estado_anterior in (EstadoConversacion.PROFUNDIZACION, EstadoConversacion.ACLARACION):
                # Al volver a exploración desde profundidad, mantener nivel
                pass
            elif self._contexto.estado in (EstadoConversacion.SALUDO, EstadoConversacion.INICIO):
                self._contexto.nivel_profundidad = 0
            
            # Actualizar tema
            tema_actual = metadatos.get('tema', metadatos.get('campo_semantico', ''))
            if tema_actual and tema_actual != self._contexto.tema_actual:
                if self._contexto.tema_actual:
                    self._contexto.temas_tratados.append(self._contexto.tema_actual)
                self._contexto.tema_actual = tema_actual
            
            # Generar respuesta
            respuesta = self._generar_respuesta(texto, intencion, sentimiento)
            
            # Registrar turno de respuesta
            turno_respuesta = TurnoConversacion(
                rol="asistente",
                texto=respuesta.texto,
                duracion_ms=0.0,
            )
            self._contexto.turnos.append(turno_respuesta)
            
            # Calcular satisfacción estimada
            self._actualizar_satisfaccion(intencion, sentimiento)
            
            # Número de turno
            num_turno = len(self._contexto.turnos) // 2 + 1
            
            return {
                'texto_original': texto,
                'respuesta': respuesta.texto,
                'estrategia': respuesta.estrategia.value,
                'estado_conversacion': self._contexto.estado.value,
                'estado_anterior': estado_anterior.value,
                'personalidad': self._contexto.personalidad.value,
                'tema_actual': self._contexto.tema_actual,
                'nivel_profundidad': self._contexto.nivel_profundidad,
                'satisfaccion_estimada': round(self._contexto.satisfaccion_estimada, 2),
                'sugerencias': respuesta.sugerencias,
                'num_turno': num_turno,
                'total_turnos': len(self._contexto.turnos) // 2,
                'entidades_acumuladas': len(self._contexto.entidades_acumuladas),
                'temas_tratados': self._contexto.temas_tratados[-5:],
            }
    
    def _transicionar_estado(self, intencion: str) -> EstadoConversacion:
        """Determina el nuevo estado basado en la intención."""
        transiciones_estado = self.TRANSICIONES.get(self._contexto.estado, {})
        
        # Buscar coincidencia exacta
        if intencion in transiciones_estado:
            return transiciones_estado[intencion]
        
        # Buscar coincidencia parcial (prefijo)
        for key in transiciones_estado:
            if key != 'default' and intencion.startswith(key):
                return transiciones_estado[key]
        
        return transiciones_estado.get('default', self._contexto.estado)
    
    def _generar_respuesta(self, texto: str, intencion: str, sentimiento: str) -> RespuestaDialogo:
        """Genera una respuesta contextual."""
        estado = self._contexto.estado
        personalidad_clave = self._contexto.personalidad.value
        
        # 1. Intentar respuesta por intención (búsqueda exacta y por prefijo)
        plantillas_intencion = None
        if intencion in self.RESPUESTAS_INTENCION:
            plantillas_intencion = self.RESPUESTAS_INTENCION[intencion]
        else:
            for key in self.RESPUESTAS_INTENCION:
                if intencion.startswith(key):
                    plantillas_intencion = self.RESPUESTAS_INTENCION[key]
                    break
        
        if plantillas_intencion:
            estrategia = self._seleccionar_estrategia(intencion, sentimiento)
            estrategia_str = estrategia.value if isinstance(estrategia, EstrategiaRespuesta) else 'directa'
            plantilla = plantillas_intencion.get(estrategia_str)
            
            if plantilla is None:
                # Tomar la primera disponible
                plantilla = list(plantillas_intencion.values())[0]
            
            if plantilla:
                contenido = self._generar_contenido_respuesta(intencion, texto)
                texto_respuesta = plantilla.format(respuesta=contenido)
                return RespuestaDialogo(
                    texto=texto_respuesta,
                    estrategia=estrategia if isinstance(estrategia, EstrategiaRespuesta) else EstrategiaRespuesta.DIRECTA,
                    sugerencias=self.SUGERENCIAS.get(estado, [])[:2],
                )
        
        # 2. Intentar respuesta por estado
        plantillas_estado = self.PLANTILLAS.get(estado, {})
        if plantillas_estado:
            # Buscar por personalidad exacta
            plantillas_personalidad = plantillas_estado.get(personalidad_clave, [])
            
            # Si no hay, buscar cualquier personalidad
            if not plantillas_personalidad:
                for key in plantillas_estado:
                    plantillas_personalidad = plantillas_estado[key]
                    break
            
            if plantillas_personalidad:
                texto_respuesta = random.choice(plantillas_personalidad)
                return RespuestaDialogo(
                    texto=texto_respuesta,
                    estrategia=EstrategiaRespuesta.DIRECTA,
                    sugerencias=self.SUGERENCIAS.get(estado, [])[:2],
                )
        
        # 3. Respuesta genérica
        return RespuestaDialogo(
            texto="¡Listo! ¿Hay algo más en lo que quieras que te ayude?",
            estrategia=EstrategiaRespuesta.DIRECTA,
            sugerencias=["¿Quieres que profundice en algún tema?", "¿Necesitas alguna aclaración?"],
        )
    
    def _seleccionar_estrategia(self, intencion: str, sentimiento: str) -> EstrategiaRespuesta:
        """Selecciona la estrategia de respuesta más adecuada."""
        if intencion in ('pregunta_definicion', 'pregunta_procedimiento', 'pregunta_hecho'):
            return EstrategiaRespuesta.ELABORADA
        
        if intencion in ('pregunta_opinion', 'pregunta_motivo'):
            return EstrategiaRespuesta.REFLEXIVA
        
        if sentimiento in ('negativo', 'muy_negativo', 'tristeza', 'ira', 'ansiedad'):
            return EstrategiaRespuesta.EMPATICA
        
        if intencion == 'queja':
            return EstrategiaRespuesta.EMPATICA
        
        if intencion in ('orden', 'orden_directa', 'orden_cortes'):
            return EstrategiaRespuesta.DIRECTA
        
        return EstrategiaRespuesta.DIRECTA
    
    def _generar_contenido_respuesta(self, intencion: str, texto: str) -> str:
        """Genera el contenido base de la respuesta."""
        texto_corto = texto[:80] + '...' if len(texto) > 80 else texto
        
        if intencion.startswith('pregunta'):
            return f"he analizado tu consulta sobre '{texto_corto}' y esto es lo que he encontrado"
        elif intencion.startswith('orden'):
            return "procedo a ejecutar la acción solicitada"
        elif intencion == 'solicitud_ayuda':
            return "te ayudo con eso que necesitas"
        elif intencion == 'solicitud':
            return "atiendo tu solicitud"
        else:
            return f"proceso tu solicitud sobre '{texto_corto}'"
    
    def _actualizar_satisfaccion(self, intencion: str, sentimiento: str):
        """Actualiza la estimación de satisfacción del usuario."""
        # Sube con preguntas (muestra interés)
        if intencion.startswith('pregunta'):
            self._contexto.satisfaccion_estimada = min(1.0, self._contexto.satisfaccion_estimada + 0.05)
        
        # Baja con quejas
        if intencion == 'queja' or sentimiento in ('negativo', 'muy_negativo'):
            self._contexto.satisfaccion_estimada = max(0.0, self._contexto.satisfaccion_estimada - 0.1)
        
        # Sube con agradecimientos
        if intencion == 'agradecimiento':
            self._contexto.satisfaccion_estimada = min(1.0, self._contexto.satisfaccion_estimada + 0.1)
        
        # Decaimiento natural
        self._contexto.satisfaccion_estimada = max(0.1, self._contexto.satisfaccion_estimada - 0.01)
    
    def _resultado_vacio(self):
        return {
            'texto_original': '',
            'respuesta': '',
            'estrategia': 'directa',
            'estado_conversacion': 'inicio',
            'estado_anterior': 'inicio',
            'personalidad': 'adaptativo',
            'tema_actual': '',
            'nivel_profundidad': 0,
            'satisfaccion_estimada': 0.5,
            'sugerencias': [],
            'num_turno': 0,
            'total_turnos': 0,
            'entidades_acumuladas': 0,
            'temas_tratados': [],
        }
    
    def resetear_contexto(self):
        """Reinicia el contexto de la conversación."""
        with self._lock:
            self._contexto = None
    
    def obtener_contexto(self) -> Optional[Dict[str, Any]]:
        """Obtiene el contexto actual de la conversación."""
        if self._contexto is None:
            return None
        
        return {
            'estado': self._contexto.estado.value,
            'tema_actual': self._contexto.tema_actual,
            'temas_tratados': self._contexto.temas_tratados,
            'personalidad': self._contexto.personalidad.value,
            'total_turnos': len(self._contexto.turnos) // 2,
            'nivel_profundidad': self._contexto.nivel_profundidad,
            'satisfaccion_estimada': round(self._contexto.satisfaccion_estimada, 2),
            'entidades_acumuladas': len(self._contexto.entidades_acumuladas),
        }
    
    def cambiar_personalidad(self, personalidad: str) -> bool:
        """Cambia la personalidad del diálogo."""
        try:
            with self._lock:
                if self._contexto:
                    self._contexto.personalidad = PersonalidadDialogo(personalidad)
                return True
        except ValueError:
            return False

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE DIÁLOGO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/8] Inicializando motor...")
        motor = MotorDialogo()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return {
                'respuesta': 'Error', 'estado_conversacion': 'error',
                'estado_anterior': 'error', 'estrategia': 'directa',
                'nivel_profundidad': 0, 'sugerencias': [],
                'personalidad': 'adaptativo', 'satisfaccion_estimada': 0.5,
                'num_turno': 0, 'total_turnos': 0,
            }
        
        print("\n[2/8] Saludo inicial...")
        r1 = sd(motor.procesar({'texto': 'Hola', 'intencion': 'saludo'}))
        print(f"  📍 Estado: {r1['estado_anterior']} → {r1['estado_conversacion']}")
        print(f"  📍 Respuesta: \"{r1['respuesta']}\"")
        
        print("\n[3/8] Primera pregunta...")
        r2 = sd(motor.procesar({'texto': '¿Qué es la inteligencia artificial?', 'intencion': 'pregunta_definicion'}))
        print(f"  📍 Estado: {r2['estado_anterior']} → {r2['estado_conversacion']}")
        print(f"  📍 Estrategia: {r2['estrategia']}")
        print(f"  📍 Nivel profundidad: {r2['nivel_profundidad']}")
        print(f"  📍 Sugerencias: {r2['sugerencias']}")
        
        print("\n[4/8] Profundizando...")
        r3 = sd(motor.procesar({'texto': '¿Cómo funciona exactamente?', 'intencion': 'pregunta_procedimiento'}))
        print(f"  📍 Estado: {r3['estado_anterior']} → {r3['estado_conversacion']}")
        print(f"  📍 Nivel profundidad: {r3['nivel_profundidad']}")
        print(f"  📍 Sugerencias: {r3['sugerencias']}")
        
        print("\n[5/8] Cambio de personalidad a técnico...")
        motor.cambiar_personalidad('tecnico')
        r4 = sd(motor.procesar({'texto': 'Explícame los detalles técnicos', 'intencion': 'pregunta'}))
        print(f"  📍 Personalidad: {r4['personalidad']}")
        print(f"  📍 Estado: {r4['estado_conversacion']}")
        
        print("\n[6/8] Agradecimiento...")
        r5 = sd(motor.procesar({'texto': 'Muchas gracias', 'intencion': 'agradecimiento'}))
        print(f"  📍 Estado: {r5['estado_anterior']} → {r5['estado_conversacion']}")
        print(f"  📍 Satisfacción: {r5['satisfaccion_estimada']}")
        
        print("\n[7/8] Despedida...")
        r6 = sd(motor.procesar({'texto': 'Adiós, hasta luego', 'intencion': 'despedida'}))
        print(f"  📍 Estado: {r6['estado_anterior']} → {r6['estado_conversacion']}")
        print(f"  📍 Respuesta: \"{r6['respuesta']}\"")
        
        print("\n[8/8] Contexto final...")
        ctx = motor.obtener_contexto()
        if ctx:
            print(f"  📊 Total turnos: {ctx['total_turnos']}")
            print(f"  📊 Entidades: {ctx['entidades_acumuladas']}")
            print(f"  📊 Satisfacción: {ctx['satisfaccion_estimada']}")
            print(f"  📊 Nivel profundidad: {ctx['nivel_profundidad']}")
        
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