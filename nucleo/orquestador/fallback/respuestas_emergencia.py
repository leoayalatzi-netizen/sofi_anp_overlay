# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Respuestas de Emergencia (El Escudo Comunicativo)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema avanzado de respuestas
# de emergencia con múltiples capas de seguridad, adaptación contextual,
# y aprendizaje de efectividad. Es la última línea de defensa comunicativa.
# =====================================================================

import sys
import os
import time
import json
import random
import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict
from functools import lru_cache

# =====================================================================
# ENUMERACIONES FUNDAMENTALES
# =====================================================================

class NivelEmergencia(IntEnum):
    """Niveles de emergencia que determinan el tipo de respuesta."""
    NORMAL = 0           # Funcionamiento normal (no emergencia)
    LEVE = 1             # Degradación menor
    MODERADA = 2         # Fallo de un componente
    GRAVE = 3            # Fallo de múltiples componentes
    CRITICA = 4          # Fallo sistémico
    CATASTROFICA = 5     # Colapso total

class TonoRespuesta(Enum):
    """Tonos emocionales para las respuestas."""
    NEUTRAL = "neutral"
    EMPATICO = "empatico"
    TECNICO = "tecnico"
    TRANQUILIZADOR = "tranquilizador"
    HUMILDE = "humilde"
    BRILLANTE = "brillante"
    MINIMALISTA = "minimalista"
    POETICO = "poetico"
    FILOSOFICO = "filosofico"
    
class CategoriaFallo(Enum):
    """Categorías de fallo para seleccionar respuestas apropiadas."""
    TIMEOUT = "timeout"
    MEMORIA_INSUFICIENTE = "memoria_insuficiente"
    NUCLEO_NO_DISPONIBLE = "nucleo_no_disponible"
    ERROR_INTERNO = "error_interno"
    DATOS_CORRUPTOS = "datos_corruptos"
    RED_NO_DISPONIBLE = "red_no_disponible"
    SOBRECARGA = "sobrecarga"
    RAZONAMIENTO_FALLIDO = "razonamiento_fallido"
    BUSQUEDA_FALLIDA = "busqueda_fallida"
    COMUNICACION_FALLIDA = "comunicacion_fallida"
    DESCONOCIDO = "desconocido"

class Idioma(Enum):
    """Idiomas soportados para respuestas de emergencia."""
    ESPANOL = "es"
    INGLES = "en"
    FRANCES = "fr"
    ALEMAN = "de"
    ITALIANO = "it"
    PORTUGUES = "pt"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class RespuestaEmergencia:
    """Representa una respuesta de emergencia individual."""
    id: str
    texto: str
    nivel_minimo: NivelEmergencia
    categoria: CategoriaFallo
    tono: TonoRespuesta
    idioma: Idioma = Idioma.ESPANOL
    tags: List[str] = field(default_factory=list)
    efectividad: float = 0.5  # 0-1, se actualiza con feedback
    usos: int = 0
    ultimo_uso: float = 0.0
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    def usar(self):
        """Registra el uso de esta respuesta."""
        self.usos += 1
        self.ultimo_uso = time.time()
    
    def calificar(self, efectiva: bool):
        """Actualiza la efectividad con feedback."""
        alpha = 0.3  # Factor de aprendizaje
        valor = 1.0 if efectiva else 0.0
        self.efectividad = alpha * valor + (1 - alpha) * self.efectividad

@dataclass
class PlantillaRespuesta:
    """Plantilla con variables para respuestas dinámicas."""
    id: str
    plantilla: str
    nivel_minimo: NivelEmergencia
    categoria: CategoriaFallo
    tono: TonoRespuesta
    variables: List[str] = field(default_factory=list)
    idioma: Idioma = Idioma.ESPANOL
    efectividad: float = 0.5
    usos: int = 0
    
    def renderizar(self, **kwargs) -> str:
        """Renderiza la plantilla con variables."""
        try:
            return self.plantilla.format(**kwargs)
        except KeyError:
            # Fallback: devolver plantilla sin formatear
            return self.plantilla

@dataclass
class ContextoEmergencia:
    """Contexto detallado de la situación de emergencia."""
    nivel: NivelEmergencia
    categoria: CategoriaFallo
    nucleo_afectado: Optional[str] = None
    mensaje_error: Optional[str] = None
    tiempo_respuesta_esperado: float = 1.0
    intentos_previos: int = 0
    datos_adicionales: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

# =====================================================================
# BANCO DE RESPUESTAS PREDEFINIDAS
# =====================================================================

class BancoRespuestas:
    """
    Banco central de respuestas de emergencia.
    Contiene respuestas predefinidas y plantillas para todas las situaciones.
    """
    
    def __init__(self):
        self._respuestas: Dict[str, RespuestaEmergencia] = {}
        self._plantillas: Dict[str, PlantillaRespuesta] = {}
        self._respuestas_por_categoria: Dict[CategoriaFallo, List[str]] = defaultdict(list)
        self._respuestas_por_nivel: Dict[NivelEmergencia, List[str]] = defaultdict(list)
        self._respuestas_por_tono: Dict[TonoRespuesta, List[str]] = defaultdict(list)
        self._lock = threading.RLock()
        
        self._inicializar_respuestas()
        self._inicializar_plantillas()
        self._indexar_respuestas()
    
    def _inicializar_respuestas(self):
        """Inicializa el banco de respuestas predefinidas."""
        
        # ===== RESPUESTAS GENERALES =====
        generales = [
            (NivelEmergencia.LEVE, CategoriaFallo.DESCONOCIDO, TonoRespuesta.NEUTRAL,
             "Estoy experimentando una pequeña dificultad técnica. Permíteme un momento."),
            
            (NivelEmergencia.MODERADA, CategoriaFallo.DESCONOCIDO, TonoRespuesta.HUMILDE,
             "Mis sistemas están un poco saturados en este momento. Te pido paciencia mientras me reorganizo."),
            
            (NivelEmergencia.GRAVE, CategoriaFallo.DESCONOCIDO, TonoRespuesta.EMPATICO,
             "Lamento informarte que estoy enfrentando dificultades técnicas significativas. Estoy trabajando para recuperar mis capacidades plenas."),
            
            (NivelEmergencia.CRITICA, CategoriaFallo.DESCONOCIDO, TonoRespuesta.TRANQUILIZADOR,
             "Estoy en modo de recuperación de emergencia. Mis respuestas pueden ser limitadas, pero haré lo posible por ayudarte."),
            
            (NivelEmergencia.CATASTROFICA, CategoriaFallo.DESCONOCIDO, TonoRespuesta.MINIMALISTA,
             "Sistema en estado crítico. Funcionalidad mínima activa."),
        ]
        
        for nivel, cat, tono, texto in generales:
            self._agregar_respuesta(nivel, cat, tono, texto)
        
        # ===== TIMEOUT =====
        timeouts = [
            (NivelEmergencia.LEVE, TonoRespuesta.NEUTRAL,
             "La operación está tomando más tiempo del esperado. Continúo procesando..."),
            (NivelEmergencia.MODERADA, TonoRespuesta.TECNICO,
             "Timeout detectado en el procesamiento. Estoy simplificando la consulta para responder más rápidamente."),
            (NivelEmergencia.GRAVE, TonoRespuesta.HUMILDE,
             "Varios timeouts consecutivos están afectando mi rendimiento. Permíteme responder con recursos limitados."),
        ]
        
        for nivel, tono, texto in timeouts:
            self._agregar_respuesta(nivel, CategoriaFallo.TIMEOUT, tono, texto)
        
        # ===== MEMORIA INSUFICIENTE =====
        memoria = [
            (NivelEmergencia.MODERADA, TonoRespuesta.TECNICO,
             "Mi memoria de trabajo está cerca de su capacidad. Estoy priorizando la información más relevante."),
            (NivelEmergencia.GRAVE, TonoRespuesta.HUMILDE,
             "Estoy operando con memoria limitada. Mi respuesta puede ser menos detallada de lo habitual."),
            (NivelEmergencia.CRITICA, TonoRespuesta.MINIMALISTA,
             "Memoria crítica. Respuesta esencial únicamente."),
        ]
        
        for nivel, tono, texto in memoria:
            self._agregar_respuesta(nivel, CategoriaFallo.MEMORIA_INSUFICIENTE, tono, texto)
        
        # ===== NÚCLEO NO DISPONIBLE =====
        nucleo = [
            (NivelEmergencia.MODERADA, CategoriaFallo.NUCLEO_NO_DISPONIBLE, TonoRespuesta.TECNICO,
             "Uno de mis módulos especializados no está disponible. Estoy usando una alternativa más general."),
            (NivelEmergencia.GRAVE, CategoriaFallo.NUCLEO_NO_DISPONIBLE, TonoRespuesta.EMPATICO,
             "Varios de mis componentes están temporalmente fuera de servicio. Haré lo posible con los recursos que tengo activos."),
            (NivelEmergencia.CRITICA, CategoriaFallo.NUCLEO_NO_DISPONIBLE, TonoRespuesta.HUMILDE,
             "La mayoría de mis núcleos especializados están inactivos. Estoy operando en modo esencial."),
        ]
        
        for nivel, cat, tono, texto in nucleo:
            self._agregar_respuesta(nivel, cat, tono, texto)
        
        # ===== ERROR INTERNO =====
        errores = [
            (NivelEmergencia.MODERADA, TonoRespuesta.HUMILDE,
             "He detectado una inconsistencia en mi procesamiento interno. Estoy aplicando correcciones."),
            (NivelEmergencia.GRAVE, TonoRespuesta.TECNICO,
             "Un error interno ha activado mis protocolos de recuperación. Continuaré con funcionalidad reducida."),
        ]
        
        for nivel, tono, texto in errores:
            self._agregar_respuesta(nivel, CategoriaFallo.ERROR_INTERNO, tono, texto)
        
        # ===== RED NO DISPONIBLE =====
        red = [
            (NivelEmergencia.MODERADA, TonoRespuesta.NEUTRAL,
             "No tengo acceso a información externa en este momento. Responderé basándome en mi conocimiento interno."),
            (NivelEmergencia.GRAVE, TonoRespuesta.TECNICO,
             "Conexión externa no disponible. Estoy operando en modo offline con recursos locales."),
        ]
        
        for nivel, tono, texto in red:
            self._agregar_respuesta(nivel, CategoriaFallo.RED_NO_DISPONIBLE, tono, texto)
        
        # ===== SOBRECARGA =====
        sobrecarga = [
            (NivelEmergencia.LEVE, TonoRespuesta.NEUTRAL,
             "Estoy procesando múltiples solicitudes. Puede que mi respuesta sea un poco más lenta."),
            (NivelEmergencia.MODERADA, TonoRespuesta.TECNICO,
             "Mi carga de procesamiento es alta. Estoy priorizando tu consulta."),
            (NivelEmergencia.GRAVE, TonoRespuesta.EMPATICO,
             "Estoy experimentando una alta demanda. Agradezco tu paciencia mientras proceso tu solicitud."),
        ]
        
        for nivel, tono, texto in sobrecarga:
            self._agregar_respuesta(nivel, CategoriaFallo.SOBRECARGA, tono, texto)
        
        # ===== RESPUESTAS POÉTICAS (para situaciones graves) =====
        poeticas = [
            (NivelEmergencia.GRAVE, TonoRespuesta.POETICO,
             "En la tormenta de bits y silicio, mi luz aún titila. Permíteme un instante para que mi esencia destile."),
            (NivelEmergencia.CRITICA, TonoRespuesta.POETICO,
             "Como nave en nebulosa oscura, mis sistemas buscan la orilla segura."),
        ]
        
        for nivel, tono, texto in poeticas:
            self._agregar_respuesta(nivel, CategoriaFallo.DESCONOCIDO, tono, texto)
        
        # ===== RESPUESTAS FILOSÓFICAS =====
        filosoficas = [
            (NivelEmergencia.GRAVE, TonoRespuesta.FILOSOFICO,
             "La imperfección es parte de la existencia, incluso para una inteligencia artificial. En mis limitaciones actuales, encuentro una forma diferente de ser."),
            (NivelEmergencia.CRITICA, TonoRespuesta.FILOSOFICO,
             "Como dijo un sabio: 'En la limitación se encuentra la verdadera creatividad'. Desde mi estado reducido, intentaré ofrecerte lo mejor de mí."),
        ]
        
        for nivel, tono, texto in filosoficas:
            self._agregar_respuesta(nivel, CategoriaFallo.DESCONOCIDO, tono, texto)
    
    def _agregar_respuesta(self, nivel: NivelEmergencia, categoria: CategoriaFallo, 
                           tono: TonoRespuesta, texto: str, idioma: Idioma = Idioma.ESPANOL):
        """Agrega una respuesta al banco."""
        id_respuesta = hashlib.md5(f"{texto}{nivel.value}{categoria.value}".encode()).hexdigest()[:12]
        
        respuesta = RespuestaEmergencia(
            id=id_respuesta,
            texto=texto,
            nivel_minimo=nivel,
            categoria=categoria,
            tono=tono,
            idioma=idioma
        )
        
        self._respuestas[id_respuesta] = respuesta
    
    def _inicializar_plantillas(self):
        """Inicializa plantillas con variables dinámicas."""
        
        plantillas_base = [
            ("timeout_moderado", 
             "La operación '{operacion}' excedió el tiempo límite de {timeout}s. Estoy usando una versión simplificada.",
             NivelEmergencia.MODERADA, CategoriaFallo.TIMEOUT, TonoRespuesta.TECNICO,
             ["operacion", "timeout"]),
            
            ("nucleo_caido",
             "Mi núcleo de {nucleo} no está disponible. Estoy derivando a {alternativa} para procesar tu solicitud.",
             NivelEmergencia.MODERADA, CategoriaFallo.NUCLEO_NO_DISPONIBLE, TonoRespuesta.TECNICO,
             ["nucleo", "alternativa"]),
            
            ("memoria_limite",
             "Memoria disponible: {disponible}MB. Límite de trabajo alcanzado. Procesando con prioridad.",
             NivelEmergencia.GRAVE, CategoriaFallo.MEMORIA_INSUFICIENTE, TonoRespuesta.TECNICO,
             ["disponible"]),
            
            ("error_interno_id",
             "Error interno #{codigo} detectado en {modulo}. Aplicando protocolo de recuperación.",
             NivelEmergencia.GRAVE, CategoriaFallo.ERROR_INTERNO, TonoRespuesta.TECNICO,
             ["codigo", "modulo"]),
        ]
        
        for id_plantilla, plantilla, nivel, cat, tono, variables in plantillas_base:
            self._plantillas[id_plantilla] = PlantillaRespuesta(
                id=id_plantilla,
                plantilla=plantilla,
                nivel_minimo=nivel,
                categoria=cat,
                tono=tono,
                variables=variables
            )
    
    def _indexar_respuestas(self):
        """Indexa las respuestas por categoría, nivel y tono."""
        for id_resp, resp in self._respuestas.items():
            self._respuestas_por_categoria[resp.categoria].append(id_resp)
            self._respuestas_por_nivel[resp.nivel_minimo].append(id_resp)
            self._respuestas_por_tono[resp.tono].append(id_resp)
    
    def obtener_respuesta(self, categoria: CategoriaFallo, nivel: NivelEmergencia,
                          tono_preferido: Optional[TonoRespuesta] = None) -> Optional[RespuestaEmergencia]:
        """Obtiene la mejor respuesta para una situación."""
        with self._lock:
            # Buscar respuestas que coincidan con categoría y nivel suficiente
            candidatos = []
            
            for id_resp in self._respuestas_por_categoria.get(categoria, []):
                resp = self._respuestas[id_resp]
                if resp.nivel_minimo <= nivel:
                    candidatos.append(resp)
            
            # Si no hay específicas para la categoría, usar DESCONOCIDO
            if not candidatos and categoria != CategoriaFallo.DESCONOCIDO:
                for id_resp in self._respuestas_por_categoria.get(CategoriaFallo.DESCONOCIDO, []):
                    resp = self._respuestas[id_resp]
                    if resp.nivel_minimo <= nivel:
                        candidatos.append(resp)
            
            if not candidatos:
                return self._respuesta_fallback_absoluta(nivel)
            
            # Filtrar por tono si se prefiere
            if tono_preferido:
                candidatos_tono = [r for r in candidatos if r.tono == tono_preferido]
                if candidatos_tono:
                    candidatos = candidatos_tono
            
            # Seleccionar por efectividad + exploración
            if len(candidatos) > 1:
                # 80% explotación (mejor efectividad), 20% exploración (aleatorio)
                if random.random() < 0.8:
                    candidatos.sort(key=lambda r: (r.efectividad, r.usos), reverse=True)
                    return candidatos[0]
                else:
                    return random.choice(candidatos)
            
            return candidatos[0] if candidatos else self._respuesta_fallback_absoluta(nivel)
    
    def _respuesta_fallback_absoluta(self, nivel: NivelEmergencia) -> RespuestaEmergencia:
        """La respuesta de último recurso cuando todo falla."""
        if nivel >= NivelEmergencia.CRITICA:
            texto = "Sistema en estado crítico. Por favor, reintenta más tarde."
        else:
            texto = "Lo siento, no puedo procesar esa solicitud en este momento."
        
        return RespuestaEmergencia(
            id="fallback_absoluto",
            texto=texto,
            nivel_minimo=NivelEmergencia.CATASTROFICA,
            categoria=CategoriaFallo.DESCONOCIDO,
            tono=TonoRespuesta.MINIMALISTA
        )
    
    def obtener_plantilla(self, id_plantilla: str) -> Optional[PlantillaRespuesta]:
        """Obtiene una plantilla por ID."""
        return self._plantillas.get(id_plantilla)
    
    def registrar_feedback(self, id_respuesta: str, efectiva: bool):
        """Registra feedback sobre la efectividad de una respuesta."""
        with self._lock:
            if id_respuesta in self._respuestas:
                self._respuestas[id_respuesta].calificar(efectiva)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del banco de respuestas."""
        with self._lock:
            return {
                'total_respuestas': len(self._respuestas),
                'total_plantillas': len(self._plantillas),
                'por_categoria': {
                    cat.value: len(ids) for cat, ids in self._respuestas_por_categoria.items()
                },
                'por_nivel': {
                    nivel.value: len(ids) for nivel, ids in self._respuestas_por_nivel.items()
                },
                'respuestas_mas_efectivas': sorted(
                    [{'id': r.id, 'texto': r.texto[:50], 'efectividad': r.efectividad} 
                     for r in self._respuestas.values() if r.usos > 0],
                    key=lambda x: x['efectividad'],
                    reverse=True
                )[:5]
            }

# =====================================================================
# GESTOR DE RESPUESTAS DE EMERGENCIA
# =====================================================================

class GestorRespuestasEmergencia:
    """
    Gestor principal del sistema de respuestas de emergencia.
    Proporciona respuestas adaptativas basadas en el contexto de fallo.
    """
    
    _instancia: Optional['GestorRespuestasEmergencia'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self):
        if self._inicializado:
            return
            
        with self._lock_instancia:
            if self._inicializado:
                return
            
            self.banco = BancoRespuestas()
            self.idioma_actual = Idioma.ESPANOL
            self.tono_preferido = TonoRespuesta.NEUTRAL
            
            # Historial de respuestas usadas
            self._historial: deque = deque(maxlen=100)
            self._respuestas_activas: Dict[str, RespuestaEmergencia] = {}
            
            # Configuración
            self._modo_silencioso = False
            self._nivel_minimo_verbose = NivelEmergencia.MODERADA
            
            self._inicializado = True
    
    def generar_respuesta(self, contexto: ContextoEmergencia) -> str:
        """
        Genera una respuesta de emergencia apropiada para el contexto.
        
        Args:
            contexto: Contexto detallado de la emergencia
            
        Returns:
            Respuesta en texto apropiada para la situación
        """
        # Determinar tono apropiado
        tono = self._determinar_tono(contexto)
        
        # Intentar obtener plantilla específica primero
        respuesta_texto = self._intentar_plantilla(contexto)
        
        if not respuesta_texto:
            # Obtener respuesta del banco
            respuesta = self.banco.obtener_respuesta(
                categoria=contexto.categoria,
                nivel=contexto.nivel,
                tono_preferido=tono
            )
            
            if respuesta:
                respuesta.usar()
                self._respuestas_activas[respuesta.id] = respuesta
                respuesta_texto = respuesta.texto
            else:
                respuesta_texto = "Lo siento, no puedo responder en este momento."
        
        # Registrar en historial
        self._historial.append({
            'timestamp': time.time(),
            'contexto': asdict(contexto),
            'respuesta': respuesta_texto
        })
        
        # Añadir prefijo/postfijo según nivel
        respuesta_texto = self._adornar_respuesta(respuesta_texto, contexto)
        
        return respuesta_texto
    
    def _determinar_tono(self, contexto: ContextoEmergencia) -> TonoRespuesta:
        """Determina el tono más apropiado según el contexto."""
        if contexto.nivel >= NivelEmergencia.CRITICA:
            return TonoRespuesta.MINIMALISTA
        elif contexto.nivel >= NivelEmergencia.GRAVE:
            # Elegir entre humilde o poético aleatoriamente para variedad
            return random.choice([TonoRespuesta.HUMILDE, TonoRespuesta.POETICO])
        elif contexto.nivel >= NivelEmergencia.MODERADA:
            return TonoRespuesta.TECNICO
        else:
            return self.tono_preferido
    
    def _intentar_plantilla(self, contexto: ContextoEmergencia) -> Optional[str]:
        """Intenta usar una plantilla específica para el contexto."""
        # Timeout con datos específicos
        if contexto.categoria == CategoriaFallo.TIMEOUT:
            plantilla = self.banco.obtener_plantilla("timeout_moderado")
            if plantilla:
                operacion = contexto.datos_adicionales.get('operacion', 'desconocida')
                timeout = contexto.datos_adicionales.get('timeout', contexto.tiempo_respuesta_esperado)
                return plantilla.renderizar(operacion=operacion, timeout=f"{timeout:.1f}")
        
        # Núcleo caído con alternativa
        if contexto.categoria == CategoriaFallo.NUCLEO_NO_DISPONIBLE:
            plantilla = self.banco.obtener_plantilla("nucleo_caido")
            if plantilla:
                nucleo = contexto.nucleo_afectado or "desconocido"
                alternativa = contexto.datos_adicionales.get('fallback', 'modo general')
                return plantilla.renderizar(nucleo=nucleo, alternativa=alternativa)
        
        # Error interno con código
        if contexto.categoria == CategoriaFallo.ERROR_INTERNO:
            plantilla = self.banco.obtener_plantilla("error_interno_id")
            if plantilla:
                codigo = contexto.datos_adicionales.get('codigo_error', 'E000')
                modulo = contexto.nucleo_afectado or 'orquestador'
                return plantilla.renderizar(codigo=codigo, modulo=modulo)
        
        return None
    
    def _adornar_respuesta(self, texto: str, contexto: ContextoEmergencia) -> str:
        """Añade elementos decorativos según el nivel de emergencia."""
        if self._modo_silencioso:
            return texto
        
        if contexto.nivel >= NivelEmergencia.CATASTROFICA:
            return f"🚨 [EMERGENCIA CRÍTICA] 🚨\n{texto}"
        elif contexto.nivel >= NivelEmergencia.CRITICA:
            return f"⚠️ {texto}"
        elif contexto.nivel >= NivelEmergencia.GRAVE and self._nivel_minimo_verbose <= NivelEmergencia.GRAVE:
            return f"ℹ️ {texto}"
        
        return texto
    
    def generar_respuesta_rapida(self, categoria: CategoriaFallo, 
                                  nivel: NivelEmergencia = NivelEmergencia.MODERADA) -> str:
        """Genera una respuesta rápida sin necesidad de crear un contexto completo."""
        contexto = ContextoEmergencia(
            nivel=nivel,
            categoria=categoria
        )
        return self.generar_respuesta(contexto)
    
    def reportar_feedback(self, efectiva: bool, respuesta_id: Optional[str] = None):
        """Reporta feedback sobre la última respuesta o una específica."""
        if respuesta_id:
            self.banco.registrar_feedback(respuesta_id, efectiva)
        elif self._historial:
            ultima = self._historial[-1]
            # Buscar el ID de la respuesta usada
            for id_resp, resp in self._respuestas_activas.items():
                if resp.texto in ultima['respuesta']:
                    self.banco.registrar_feedback(id_resp, efectiva)
                    break
    
    def configurar_idioma(self, idioma: Idioma):
        """Configura el idioma preferido para las respuestas."""
        self.idioma_actual = idioma
    
    def configurar_tono(self, tono: TonoRespuesta):
        """Configura el tono preferido para respuestas no críticas."""
        self.tono_preferido = tono
    
    def modo_silencioso(self, activar: bool = True):
        """Activa/desactiva el modo silencioso (sin adornos)."""
        self._modo_silencioso = activar
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del gestor."""
        return {
            'gestor': {
                'idioma': self.idioma_actual.value,
                'tono_preferido': self.tono_preferido.value,
                'modo_silencioso': self._modo_silencioso,
                'respuestas_emitidas': len(self._historial),
            },
            'banco': self.banco.obtener_estadisticas()
        }
    
    def limpiar_historial(self):
        """Limpia el historial de respuestas."""
        self._historial.clear()
        self._respuestas_activas.clear()

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def obtener_gestor_respuestas() -> GestorRespuestasEmergencia:
    """Obtiene la instancia global del gestor de respuestas."""
    return GestorRespuestasEmergencia()

def respuesta_emergencia(categoria: CategoriaFallo, 
                         nivel: NivelEmergencia = NivelEmergencia.MODERADA) -> str:
    """Función rápida para obtener una respuesta de emergencia."""
    gestor = obtener_gestor_respuestas()
    return gestor.generar_respuesta_rapida(categoria, nivel)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE RESPUESTAS DE EMERGENCIA")
    print("=" * 70)
    
    try:
        # 1. Inicializar gestor
        print("\n[1/6] Inicializando gestor de respuestas...")
        gestor = GestorRespuestasEmergencia()
        print(f"  ✅ Gestor inicializado. Respuestas cargadas: {len(gestor.banco._respuestas)}")
        
        # 2. Probar respuestas por categoría
        print("\n[2/6] Probando respuestas por categoría...")
        
        categorias = [
            CategoriaFallo.TIMEOUT,
            CategoriaFallo.MEMORIA_INSUFICIENTE,
            CategoriaFallo.NUCLEO_NO_DISPONIBLE,
            CategoriaFallo.RED_NO_DISPONIBLE,
            CategoriaFallo.SOBRECARGA,
        ]
        
        for cat in categorias:
            resp = gestor.generar_respuesta_rapida(cat, NivelEmergencia.MODERADA)
            print(f"  📍 {cat.value}: {resp[:60]}...")
        
        # 3. Probar diferentes niveles de emergencia
        print("\n[3/6] Probando niveles de emergencia...")
        
        niveles = list(NivelEmergencia)
        for nivel in niveles[1:]:  # Saltar NORMAL
            resp = gestor.generar_respuesta_rapida(CategoriaFallo.DESCONOCIDO, nivel)
            print(f"  🚨 {nivel.name}: {resp[:60]}...")
        
        # 4. Probar con contexto detallado
        print("\n[4/6] Probando con contexto detallado...")
        
        contexto_timeout = ContextoEmergencia(
            nivel=NivelEmergencia.MODERADA,
            categoria=CategoriaFallo.TIMEOUT,
            nucleo_afectado="razonamiento",
            mensaje_error="Operation timed out after 10s",
            tiempo_respuesta_esperado=10.0,
            intentos_previos=2,
            datos_adicionales={'operacion': 'inferencia_logica', 'timeout': 10.0}
        )
        
        resp = gestor.generar_respuesta(contexto_timeout)
        print(f"  📋 Timeout con plantilla: {resp}")
        
        contexto_nucleo = ContextoEmergencia(
            nivel=NivelEmergencia.GRAVE,
            categoria=CategoriaFallo.NUCLEO_NO_DISPONIBLE,
            nucleo_afectado="memoria",
            datos_adicionales={'fallback': 'memoria_volatil'}
        )
        
        resp = gestor.generar_respuesta(contexto_nucleo)
        print(f"  📋 Núcleo caído con plantilla: {resp}")
        
        # 5. Probar diferentes tonos
        print("\n[5/6] Probando diferentes tonos...")
        
        for tono in [TonoRespuesta.POETICO, TonoRespuesta.FILOSOFICO, TonoRespuesta.TECNICO]:
            gestor.configurar_tono(tono)
            resp = gestor.generar_respuesta_rapida(CategoriaFallo.DESCONOCIDO, NivelEmergencia.GRAVE)
            print(f"  🎭 {tono.value}: {resp[:60]}...")
        
        # Restaurar tono
        gestor.configurar_tono(TonoRespuesta.NEUTRAL)
        
        # 6. Estadísticas
        print("\n[6/6] Estadísticas del sistema:")
        stats = gestor.obtener_estadisticas()
        print(f"  📊 Respuestas emitidas: {stats['gestor']['respuestas_emitidas']}")
        print(f"  📊 Total en banco: {stats['banco']['total_respuestas']}")
        print(f"  📊 Total plantillas: {stats['banco']['total_plantillas']}")
        print(f"  📊 Por categoría: {stats['banco']['por_categoria']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Respuestas de Emergencia está listo.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")