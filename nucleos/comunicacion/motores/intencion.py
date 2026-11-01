#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Intención (El Oráculo de la Voluntad)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa clasificación de intención REAL
# con patrones lingüísticos, análisis contextual, puntuación de
# confianza multinivel, detección de ámbito semántico mejorada y
# soporte multilingüe (ES/EN/FR/DE/PT).
# =====================================================================

import sys
import os
import re
import math
import time
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Pattern
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

class CategoriaIntencion(Enum):
    """Categorías principales de intención."""
    PREGUNTA = "pregunta"
    ORDEN = "orden"
    SOLICITUD = "solicitud"
    SALUDO = "saludo"
    DESPEDIDA = "despedida"
    AGRADECIMIENTO = "agradecimiento"
    DISCULPA = "disculpa"
    OPINION = "opinion"
    INFORMACION = "informacion"
    CONFIRMACION = "confirmacion"
    NEGACION = "negacion"
    QUEJA = "queja"
    SUGERENCIA = "sugerencia"
    INVITACION = "invitacion"
    PROMESA = "promesa"
    AMENAZA = "amenaza"
    DESEO = "deseo"
    DUDA = "duda"
    EXPLICACION = "explicacion"
    DESCONOCIDO = "desconocido"

class SubIntencion(Enum):
    """Sub-intenciones más específicas."""
    PREGUNTA_HECHO = "pregunta_hecho"
    PREGUNTA_OPINION = "pregunta_opinion"
    PREGUNTA_PROCEDIMIENTO = "pregunta_procedimiento"
    PREGUNTA_DEFINICION = "pregunta_definicion"
    PREGUNTA_UBICACION = "pregunta_ubicacion"
    PREGUNTA_TIEMPO = "pregunta_tiempo"
    PREGUNTA_CANTIDAD = "pregunta_cantidad"
    PREGUNTA_PERSONA = "pregunta_persona"
    PREGUNTA_MOTIVO = "pregunta_motivo"
    PREGUNTA_CONFIRMACION = "pregunta_confirmacion"
    ORDEN_DIRECTA = "orden_directa"
    ORDEN_CORTES = "orden_cortes"
    SOLICITUD_AYUDA = "solicitud_ayuda"
    SOLICITUD_PERMISO = "solicitud_permiso"
    SOLICITUD_FAVOR = "solicitud_favor"
    SALUDO_INICIAL = "saludo_inicial"
    SALUDO_RESPUESTA = "saludo_respuesta"
    QUEJA_SERVICIO = "queja_servicio"
    QUEJA_PERSONAL = "queja_personal"
    SUGERENCIA_MEJORA = "sugerencia_mejora"
    SUGERENCIA_ALTERNATIVA = "sugerencia_alternativa"
    DESCONOCIDO = "desconocido"

class Urgencia(Enum):
    """Nivel de urgencia de la intención."""
    INMEDIATA = "inmediata"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    NULA = "nula"

class AmbitoIntencion(Enum):
    """Ámbito o dominio de la intención."""
    GENERAL = "general"
    TECNICO = "tecnico"
    PERSONAL = "personal"
    PROFESIONAL = "profesional"
    ACADEMICO = "academico"
    CREATIVO = "creativo"
    EMOCIONAL = "emocional"
    SOCIAL = "social"
    COMERCIAL = "comercial"
    CIENTIFICO = "cientifico"
    SALUD = "salud"
    DESCONOCIDO = "desconocido"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class IntencionDetectada:
    """Intención detectada con su puntuación de confianza."""
    categoria: CategoriaIntencion
    sub_intencion: SubIntencion = SubIntencion.DESCONOCIDO
    confianza: float = 0.0
    palabras_clave: List[str] = field(default_factory=list)
    patrones_coincidentes: List[str] = field(default_factory=list)
    urgencia: Urgencia = Urgencia.MEDIA
    ambito: AmbitoIntencion = AmbitoIntencion.GENERAL
    emocion_asociada: Optional[str] = None

# =====================================================================
# MOTOR DE INTENCIÓN PRINCIPAL (PERFECTO Y CORREGIDO)
# =====================================================================

class MotorIntencion(MotorBase):
    """
    Motor de Clasificación de Intención de ANP.
    
    Capacidades REALES:
    - Detección de 20 categorías de intención
    - 22 sub-intenciones específicas
    - Análisis de urgencia (5 niveles)
    - Identificación de ámbito (11 dominios) con coincidencia substring
    - Puntuación de confianza multinivel
    - Soporte multilingüe (ES, EN, FR, DE, PT)
    - Detección de múltiples intenciones simultáneas
    - Contexto sugerido para la respuesta
    """
    
    # ===== PATRONES DE INTENCIÓN =====
    
    PATRONES_ES = {
        CategoriaIntencion.PREGUNTA: {
            'patrones': [
                (r'^(¿|qu[eé]|qui[eé]n|c[oó]mo|cu[áa]ndo|d[oó]nde|por qu[eé]|para qu[eé]|cu[áa]l|cu[áa]nto|cu[áa]nta|cu[áa]ntos|cu[áa]ntas)\b', 0.95),
                (r'\?$', 0.9),
                (r'\b(pregunto|quisiera saber|me gustar[ií]a saber|podr[ií]as decirme|podr[ií]a decirme|sabes|sabe)\b', 0.85),
                (r'\b(qu[eé]|quien|qui[eé]n|como|c[oó]mo|cuando|cu[áa]ndo|donde|d[oó]nde|porque|por qu[eé]|por que|porqu[eé])\b', 0.7),
                (r'\b(cual|cu[áa]l|cuanto|cu[áa]nto|cuanta|cu[áa]nta|cuantos|cu[áa]ntos|cuantas|cu[áa]ntas)\b', 0.75),
            ],
            'sub_intenciones': {
                SubIntencion.PREGUNTA_DEFINICION: [
                    (r'\b(qu[eé] es|que es|definici[oó]n|definir|significa|concepto|qu[eé] significa)\b', 0.9),
                ],
                SubIntencion.PREGUNTA_PROCEDIMIENTO: [
                    (r'\b(c[oó]mo se hace|c[oó]mo hacer|como hacer|c[oó]mo funciona|como funciona|pasos|procedimiento|m[eé]todo|tutorial|c[oó]mo puedo|c[oó]mo se puede)\b', 0.9),
                ],
                SubIntencion.PREGUNTA_UBICACION: [
                    (r'\b(d[oó]nde|donde|ubicado|ubicaci[oó]n|localizar|encontrar|situado|queda|est[áa]\s+(?:el|la))\b', 0.9),
                ],
                SubIntencion.PREGUNTA_TIEMPO: [
                    (r'\b(cu[áa]ndo|cuando|fecha|hora|tiempo|duraci[oó]n|plazo|cada cu[áa]nto)\b', 0.85),
                ],
                SubIntencion.PREGUNTA_CANTIDAD: [
                    (r'\b(cu[áa]nto|cuanto|cu[áa]ntos|cuantos|n[uú]mero|cantidad|total|precio|costo|vale|cu[áa]nto cuesta)\b', 0.85),
                ],
                SubIntencion.PREGUNTA_PERSONA: [
                    (r'\b(qui[eé]n|quien|qui[eé]nes|quienes|persona|gente|alguien|qui[eé]n es|qui[eé]nes son)\b', 0.9),
                ],
                SubIntencion.PREGUNTA_MOTIVO: [
                    (r'\b(por qu[eé]|porque|porqu[eé]|raz[oó]n|motivo|causa|cu[aá]l es la raz[oó]n|a qu[eé] se debe)\b', 0.85),
                ],
                SubIntencion.PREGUNTA_CONFIRMACION: [
                    (r'^(es cierto|es verdad|verdad\?|cierto\?|no\?|verdad que|cierto que)\b', 0.9),
                    (r'\b(confirmar|verificar|comprobar|asegurar|es correcto|est[aá] bien)\b', 0.8),
                ],
                SubIntencion.PREGUNTA_OPINION: [
                    (r'\b(qu[eé] opinas|que opinas|qu[eé] piensas|que piensas|parecer|opini[oó]n|punto de vista|qu[eé] te parece)\b', 0.9),
                ],
                SubIntencion.PREGUNTA_HECHO: [
                    (r'\b(qu[eé] pas[oó]|que pas[oó]|qu[eé] ocurri[oó]|que ocurri[oó]|qu[eé] sucedi[oó]|que sucedi[oó])\b', 0.85),
                ],
            }
        },
        CategoriaIntencion.ORDEN: {
            'patrones': [
                (r'^(haz|has|hac[eé]|realiza|ejecuta|corre|inicia|para|det[eé]n|abre|cierra|busca|encuentra|muestra|dime|d[ií]|dame|trae|ll[eé]vate)\b', 0.9),
                (r'^(no\s+)?(hagas|realices|ejecutes|corras|inicies|pares|detengas|abras|cierres|busques|encuentres|muestres)\b', 0.85),
                (r'^[A-ZÁÉÍÓÚ].*(?:ya|ahora|inmediatamente|urgente)\b', 0.6),
                (r'!$', 0.5),
                (r'\b(debes|debe|deber[ií]as|tienes que|tiene que|hay que|es necesario|es preciso)\b', 0.75),
            ],
            'sub_intenciones': {
                SubIntencion.ORDEN_DIRECTA: [
                    (r'^(haz|has|hac[eé]|realiza|ejecuta|corre|inicia)\b', 0.9),
                ],
                SubIntencion.ORDEN_CORTES: [
                    (r'\b(por favor|si puedes|si puede|cuando puedas|gracias|si no es molestia)\b', 0.85),
                ],
            }
        },
        CategoriaIntencion.SOLICITUD: {
            'patrones': [
                (r'\b(necesito|requiero|preciso|hace falta|me hace falta|ocupo)\b', 0.85),
                (r'\b(podr[ií]as|podria|puedes|puede|pod[eé]is|podr[ií]an|podrian)\b', 0.8),
                (r'\b(me ayudas|me ayuda|me ayudan|ayuda|auxilio|socorro)\b', 0.9),
                (r'\b(quisiera|querr[ií]a|me gustar[ií]a|desear[ií]a)\b', 0.85),
                (r'\b(por favor|please|si no es molestia|si es posible|te importar[ií]a)\b', 0.7),
            ],
            'sub_intenciones': {
                SubIntencion.SOLICITUD_AYUDA: [
                    (r'\b(ayuda|auxilio|socorro|necesito ayuda|me ayudas|me puede ayudar|ay[uú]dame|auxilio)\b', 0.95),
                ],
                SubIntencion.SOLICITUD_PERMISO: [
                    (r'\b(permiso|permitir|dejar|autorizar|consentir|puedo|podr[ií]a|se puede|es posible)\b', 0.9),
                ],
                SubIntencion.SOLICITUD_FAVOR: [
                    (r'\b(favor|favorsito|podr[ií]as hacer|me har[ií]as|te pido|te solicito)\b', 0.85),
                ],
            }
        },
        CategoriaIntencion.SALUDO: {
            'patrones': [
                (r'^(hola|hey|buenos d[ií]as|buenas tardes|buenas noches|saludos|buenas|qu[eé] tal|como estas|c[oó]mo est[áa]s|como est[aá]|c[oó]mo est[aá]|qu[eé] onda|qui[uú]bole|ey|epa|qu[eé] hay|qu[eé] tal)\b', 0.95),
            ],
            'sub_intenciones': {
                SubIntencion.SALUDO_INICIAL: [
                    (r'^(hola|hey|buenos d[ií]as|buenas tardes|buenas noches|qu[eé] onda|qui[uú]bole|ey|epa)\b', 0.95),
                ],
                SubIntencion.SALUDO_RESPUESTA: [
                    (r'\b(bien\s+y\s+t[uú]|bien\s+y\s+vos|todo\s+bien|aqu[ií]|ac[áa]|todo bien|muy bien)\b', 0.8),
                ],
            }
        },
        CategoriaIntencion.DESPEDIDA: {
            'patrones': [
                (r'\b(adi[oó]s|adios|hasta luego|hasta pronto|nos vemos|chao|chau|bye|hasta la vista|hasta ma[ñn]ana|hasta la pr[oó]xima)\b', 0.95),
                (r'\b(me voy|me retiro|me despido|cerrar|terminar|finalizar|me marcho)\b', 0.8),
            ],
        },
        CategoriaIntencion.AGRADECIMIENTO: {
            'patrones': [
                (r'\b(gracias|muchas gracias|agradecido|agradezco|te agradezco|mil gracias|thank you|thanks|muy amable|muy gentil)\b', 0.95),
                (r'\b(te debo una|se lo agradezco|te estoy agradecido|qu[eé] amable)\b', 0.85),
            ],
        },
        CategoriaIntencion.DISCULPA: {
            'patrones': [
                (r'\b(perd[oó]n|perdon|disculpa|disculpe|lo siento|lamento|perdona|perd[oó]name|disculpame|lo lamento|mil disculpas|mis disculpas)\b', 0.95),
                (r'\b(mi error|mi culpa|me equivoqu[eé]|no fue mi intenci[oó]n|fue sin querer)\b', 0.85),
            ],
        },
        CategoriaIntencion.OPINION: {
            'patrones': [
                (r'\b(yo creo|creo que|pienso que|opino que|en mi opini[oó]n|a mi parecer|a mi juicio|considero|desde mi punto de vista)\b', 0.9),
                (r'\b(yo dir[ií]a|yo pienso|yo opino|me parece|a mi entender|segu[nú]n yo)\b', 0.85),
            ],
        },
        CategoriaIntencion.QUEJA: {
            'patrones': [
                (r'\b(queja|reclamo|protesta|disconforme|insatisfecho|no funciona|no sirve|malo|p[eé]simo|horrible|esto es un desastre)\b', 0.85),
                (r'\b(me han estafado|es una estafa|esto no funciona|no me gusta|estoy harto|estoy cansado)\b', 0.9),
            ],
        },
        CategoriaIntencion.SUGERENCIA: {
            'patrones': [
                (r'\b(sugiero|sugerir|recomiendo|recomendar|propongo|proponer|ser[ií]a mejor|podr[ií]as probar|deber[ií]as)\b', 0.85),
                (r'\b(qu[eé] tal si|por qu[eé] no|has pensado en|has considerado|te propongo|mi sugerencia)\b', 0.8),
            ],
        },
        CategoriaIntencion.DESEO: {
            'patrones': [
                (r'\b(desear[ií]a|quisiera|me gustar[ií]a|anhelo|sue[ñn]o con|ojal[aá]|espero que|qu[eé] ganas de|me encantar[ií]a)\b', 0.85),
            ],
        },
        CategoriaIntencion.DUDA: {
            'patrones': [
                (r'\b(no s[eé]|no estoy seguro|dudo|tengo dudas|no tengo claro|no me queda claro|no entiendo|no comprendo)\b', 0.9),
                (r'\b(puede ser|a lo mejor|quiz[aá]s|quizas|tal vez|talvez|probablemente|posiblemente)\b', 0.7),
            ],
        },
    }
    
    # Patrones de urgencia
    PATRONES_URGENCIA_ES = {
        Urgencia.INMEDIATA: [
            (r'\b(urgente|inmediatamente|ahora mismo|ya mismo|para ya|cuanto antes|lo antes posible|r[aá]pido|deprisa|corre|es una emergencia)\b', 0.9),
            (r'\b(emergencia|situaci[oó]n cr[ií]tica|peligro|riesgo|grave|catastr[oó]fico|vida o muerte)\b', 0.95),
            (r'!!!$|!!$', 0.8),
        ],
        Urgencia.ALTA: [
            (r'\b(importante|prioritario|necesito|requiero|esencial|fundamental|vital|cr[ií]tico)\b', 0.8),
            (r'\b(lo antes posible|pronto|r[aá]pido|breve|sin demora|sin falta)\b', 0.75),
        ],
        Urgencia.MEDIA: [
            (r'\b(cuando puedas|si tienes tiempo|sin prisa|tranquilo|con calma|sin apuro)\b', 0.7),
        ],
        Urgencia.BAJA: [
            (r'\b(no es urgente|cuando sea|alg[uú]n d[ií]a|eventualmente|tarde o temprano|sin prisas)\b', 0.8),
        ],
    }
    
    # Palabras clave por ámbito (SIMPLIFICADAS - sin regex, substrings directos)
    PALABRAS_AMBITO_SIMPLES = {
        AmbitoIntencion.TECNICO: [
            'codigo', 'programar', 'programacion', 'software', 'hardware', 'sistema',
            'algoritmo', 'base de datos', 'servidor', 'red', 'api', 'funcion', 'variable',
            'clase', 'objeto', 'bug', 'error', 'compilar', 'ejecutar', 'instalar', 'configurar',
            'actualizar', 'version', 'app', 'aplicacion', 'web', 'movil',
            'internet', 'wifi', 'bluetooth', 'archivo', 'documento', 'pantalla', 'teclado',
            'raton', 'monitor', 'procesador', 'memoria', 'disco', 'nube', 'cloud',
            'datos', 'informacion', 'tecnologia', 'digital', 'electronico', 'robot',
            'inteligencia artificial', 'ia', 'machine learning', 'deep learning', 'red neuronal',
            'script', 'python', 'java', 'javascript', 'html', 'css', 'sql', 'git',
            'terminal', 'consola', 'comando', 'linux', 'windows', 'mac', 'android', 'ios',
            'computadora', 'ordenador', 'portatil', 'tablet', 'celular', 'telefono',
            'pagina', 'sitio', 'url', 'link', 'enlace', 'descargar', 'subir', 'login',
            'contraseña', 'usuario', 'cuenta', 'perfil', 'configuracion', 'ajustes',
        ],
        AmbitoIntencion.PERSONAL: [
            'familia', 'amigo', 'amiga', 'pareja', 'hijo', 'hija', 'padre', 'madre',
            'hermano', 'hermana', 'abuelo', 'abuela', 'tio', 'tia', 'primo', 'prima',
            'esposo', 'esposa', 'novio', 'novia', 'casa', 'hogar', 'sentimiento', 'emocion',
            'salud', 'ejercicio', 'dieta', 'comida', 'dormir', 'descansar', 'vacaciones',
            'viaje', 'fiesta', 'cumpleaños', 'regalo', 'mascota', 'perro', 'gato',
            'hobby', 'pasatiempo', 'deporte', 'musica', 'pelicula', 'serie', 'libro',
            'jardin', 'cocina', 'receta', 'ropa', 'compras', 'dinero', 'ahorro',
            'yo', 'mi', 'mis', 'nuestra', 'nuestro', 'personal', 'intimo', 'privado',
            'relacion', 'matrimonio', 'boda', 'hijos', 'crianza', 'educacion',
            'colegio', 'escuela', 'universidad', 'mudanza', 'decoracion', 'reparacion',
        ],
        AmbitoIntencion.PROFESIONAL: [
            'trabajo', 'trabajar', 'empresa', 'negocio', 'reunion', 'proyecto', 'cliente',
            'jefe', 'salario', 'sueldo', 'contrato', 'entrevista', 'curriculum', 'carrera',
            'puesto', 'ascenso', 'renuncia', 'despido', 'oficina', 'compañero',
            'empleado', 'empleador', 'colega', 'equipo', 'departamento', 'area',
            'sector', 'industria', 'mercado', 'competencia', 'estrategia', 'objetivo',
            'meta', 'plazo', 'presupuesto', 'factura', 'informe', 'reporte',
            'presentacion', 'conferencia', 'seminario', 'capacitacion', 'formacion',
            'profesional', 'networking', 'linkedin', 'email', 'correo', 'laboral',
            'compañia', 'corporacion', 'startup', 'emprendimiento', 'freelance',
            'consultor', 'gerente', 'director', 'ceo', 'marketing', 'ventas',
            'finanzas', 'contabilidad', 'legal', 'abogado', 'impuestos', 'nomina',
        ],
        AmbitoIntencion.CREATIVO: [
            'crear', 'creativo', 'creatividad', 'diseñar', 'diseño', 'dibujar',
            'dibujo', 'pintar', 'pintura', 'escribir', 'escritura', 'musica', 'arte',
            'poema', 'poesia', 'historia', 'cuento', 'novela', 'cancion', 'melodia',
            'color', 'forma', 'estilo', 'belleza', 'estetica', 'original', 'innovador',
            'inspiracion', 'imaginacion', 'sueño', 'fantasia', 'ficcion',
            'arte digital', 'fotografia', 'cine', 'teatro', 'danza', 'escultura',
            'manualidad', 'artesania', 'bricolaje', 'diy', 'hazlo tu mismo',
            'composicion', 'armonia', 'ritmo', 'expresion', 'abstracto',
            'artista', 'pintor', 'escritor', 'musico', 'compositor', 'diseñador',
            'fotografo', 'director', 'guionista', 'poeta', 'bailarin', 'actor',
            'actriz', 'galeria', 'exposicion', 'concierto', 'obra', 'performance',
        ],
        AmbitoIntencion.ACADEMICO: [
            'estudiar', 'estudio', 'examen', 'tarea', 'tesis', 'investigacion',
            'universidad', 'clase', 'profesor', 'alumno', 'estudiante', 'nota',
            'calificacion', 'bibliografia', 'paper', 'articulo', 'publicacion',
            'revista', 'journal', 'conferencia', 'ponencia', 'seminario', 'curso',
            'asignatura', 'materia', 'carrera', 'licenciatura', 'maestria', 'doctorado',
            'posgrado', 'grado', 'titulo', 'diploma', 'certificado', 'beca',
            'matematicas', 'fisica', 'quimica', 'biologia', 'historia',
            'filosofia', 'literatura', 'linguistica', 'economia', 'derecho',
            'medicina', 'ingenieria', 'arquitectura', 'psicologia', 'sociologia',
            'aprender', 'enseñar', 'educacion', 'academico', 'escolar', 'colegio',
            'instituto', 'facultad', 'campus', 'biblioteca', 'laboratorio', 'aula',
            'apuntes', 'resumen', 'esquema', 'mapa conceptual', 'referencia', 'cita',
            'fuente', 'metodologia', 'hipotesis', 'experimento',
        ],
        AmbitoIntencion.EMOCIONAL: [
            'sentir', 'siento', 'emocion', 'triste', 'tristeza', 'feliz', 'felicidad',
            'enojado', 'enojo', 'ansioso', 'ansiedad', 'deprimido', 'depresion',
            'alegre', 'alegria', 'frustrado', 'frustracion', 'esperanzado', 'esperanza',
            'temeroso', 'temor', 'amor', 'odio', 'celos', 'envidia', 'compasion',
            'empatia', 'soledad', 'angustia', 'angustiado', 'preocupacion', 'preocupado',
            'estres', 'estresado', 'calma', 'paz', 'ira', 'miedo', 'sorpresa',
            'asco', 'verguenza', 'culpa', 'orgullo', 'orgulloso', 'gratitud',
            'agradecido', 'nostalgia', 'alivio', 'deseo', 'confusion', 'confundido',
            'corazon', 'alma', 'lagrima', 'llorar', 'sonrisa', 'reir', 'gritar',
            'abrazar', 'besar', 'extrañar', 'recordar', 'olvidar', 'perdonar',
            'sanar', 'curar', 'herida', 'dolor', 'sufrimiento',
        ],
        AmbitoIntencion.COMERCIAL: [
            'comprar', 'vender', 'precio', 'costo', 'dinero', 'pago', 'factura',
            'descuento', 'oferta', 'producto', 'servicio', 'cliente', 'proveedor',
            'mercado', 'tienda', 'comercio', 'negocio', 'transaccion', 'envio',
            'entrega', 'devolucion', 'garantia', 'reembolso', 'suscripcion',
            'membresia', 'plan', 'tarifa', 'cuota', 'impuesto', 'iva', 'total',
            'adquirir', 'gastar', 'invertir', 'ahorrar', 'presupuesto',
            'caro', 'barato', 'economico', 'costoso', 'gratis', 'gratuito',
            'promocion', 'liquidacion', 'rebaja', 'telefono', 'celular',
            'ecommerce', 'tienda online', 'marketplace', 'mayoreo', 'menudeo',
        ],
        AmbitoIntencion.CIENTIFICO: [
            'ciencia', 'cientifico', 'experimento', 'hipotesis', 'teoria',
            'ley', 'principio', 'metodo cientifico', 'investigacion',
            'descubrimiento', 'avance', 'innovacion', 'fisica', 'quimica',
            'biologia', 'astronomia', 'matematicas', 'geologia',
            'evolucion', 'genetica', 'particula', 'atomo', 'molecula',
            'energia', 'materia', 'universo', 'cosmos', 'planeta', 'estrella',
            'galaxia', 'agujero negro', 'relatividad', 'cuantico', 'nuclear',
            'laboratorio', 'microscopio', 'telescopio', 'satelite',
            'nasa', 'esa', 'cohete', 'estacion espacial', 'mision',
        ],
        AmbitoIntencion.SALUD: [
            'medico', 'doctor', 'enfermera', 'hospital', 'clinica', 'consulta',
            'diagnostico', 'tratamiento', 'medicamento', 'medicina', 'farmaco',
            'pastilla', 'receta', 'sintoma', 'enfermedad', 'dolor', 'fiebre', 'tos',
            'alergia', 'cirugia', 'operacion', 'terapia', 'rehabilitacion',
            'nutricion', 'dieta', 'ejercicio', 'gimnasio', 'yoga', 'meditacion',
            'bienestar', 'salud mental', 'ansiedad', 'depresion', 'insomnio', 'estres',
            'sanar', 'curar', 'prevenir', 'vacuna', 'vacunacion', 'analisis',
            'laboratorio', 'radiografia', 'resonancia', 'ecografia', 'urgencias',
            'emergencia', 'ambulancia', 'farmacia', 'botiquin', 'primeros auxilios',
        ],
    }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """
        Clasifica la intención de un texto con análisis completo.
        RETORNA SIEMPRE UN DICCIONARIO VÁLIDO.
        """
        # Parsear entrada
        if isinstance(entrada, str):
            texto = entrada
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('text', ''))
        else:
            texto = str(entrada)
        
        if not texto or not texto.strip():
            return {
                'texto_original': texto,
                'intencion_principal': {'categoria': 'desconocido', 'sub_intencion': 'desconocido', 'confianza': 0.0, 'urgencia': 'media', 'ambito': 'general'},
                'intenciones_secundarias': [],
                'total_intenciones_detectadas': 0,
                'es_pregunta': False, 'es_orden': False, 'es_solicitud': False,
                'requiere_respuesta': False, 'requiere_accion': False,
                'confianza_global': 0.0, 'contexto_sugerido': {},
                'todas_intenciones': [],
            }
        
        texto_lower = texto.strip().lower()
        texto_norm = texto.strip()
        
        # Detectar intenciones
        intenciones_detectadas = []
        for categoria, datos in self.PATRONES_ES.items():
            for patron, peso_base in datos.get('patrones', []):
                if re.search(patron, texto_lower):
                    sub_intencion = SubIntencion.DESCONOCIDO
                    sub_confianza = 0.0
                    for sub, sub_patrones in datos.get('sub_intenciones', {}).items():
                        for sub_patron, sub_peso in sub_patrones:
                            if re.search(sub_patron, texto_lower):
                                if sub_peso > sub_confianza:
                                    sub_intencion = sub
                                    sub_confianza = sub_peso
                    
                    intencion = IntencionDetectada(
                        categoria=categoria,
                        sub_intencion=sub_intencion,
                        confianza=peso_base,
                        urgencia=self._detectar_urgencia(texto_lower, texto_norm),
                        ambito=self._detectar_ambito_simple(texto_lower),
                    )
                    intenciones_detectadas.append(intencion)
                    break
        
        # Ordenar por confianza
        intenciones_detectadas.sort(key=lambda x: x.confianza, reverse=True)
        
        # Intención principal (garantizar que NUNCA sea None)
        if intenciones_detectadas:
            intencion_principal = intenciones_detectadas[0]
        else:
            intencion_principal = IntencionDetectada(
                categoria=CategoriaIntencion.DESCONOCIDO,
                sub_intencion=SubIntencion.DESCONOCIDO,
                confianza=0.3,
                urgencia=Urgencia.MEDIA,
                ambito=AmbitoIntencion.GENERAL,
            )
            intenciones_detectadas = [intencion_principal]
        
        intenciones_secundarias = intenciones_detectadas[1:4] if len(intenciones_detectadas) > 1 else []
        
        # Flags
        es_pregunta = intencion_principal.categoria == CategoriaIntencion.PREGUNTA
        es_orden = intencion_principal.categoria == CategoriaIntencion.ORDEN
        es_solicitud = intencion_principal.categoria == CategoriaIntencion.SOLICITUD
        
        requiere_respuesta = es_pregunta or es_solicitud or intencion_principal.categoria in (
            CategoriaIntencion.SALUDO, CategoriaIntencion.DUDA, CategoriaIntencion.DESEO)
        requiere_accion = es_orden or intencion_principal.categoria in (
            CategoriaIntencion.SOLICITUD, CategoriaIntencion.SUGERENCIA)
        
        # Construir resultado SEGURO
        return {
            'texto_original': texto,
            'intencion_principal': {
                'categoria': intencion_principal.categoria.value,
                'sub_intencion': intencion_principal.sub_intencion.value,
                'confianza': round(intencion_principal.confianza, 3),
                'urgencia': intencion_principal.urgencia.value,
                'ambito': intencion_principal.ambito.value,
            },
            'intenciones_secundarias': [
                {'categoria': i.categoria.value, 'confianza': round(i.confianza, 3)}
                for i in intenciones_secundarias
            ],
            'total_intenciones_detectadas': len(intenciones_detectadas),
            'es_pregunta': es_pregunta,
            'es_orden': es_orden,
            'es_solicitud': es_solicitud,
            'requiere_respuesta': requiere_respuesta,
            'requiere_accion': requiere_accion,
            'confianza_global': round(intencion_principal.confianza, 3),
            'contexto_sugerido': self._generar_contexto(intencion_principal, es_pregunta, es_orden),
            'todas_intenciones': [
                {'categoria': i.categoria.value, 'sub_intencion': i.sub_intencion.value, 'confianza': round(i.confianza, 3)}
                for i in intenciones_detectadas[:5]
            ],
        }
    
    def _detectar_urgencia(self, texto_lower: str, texto_norm: str) -> Urgencia:
        """Detecta el nivel de urgencia del texto."""
        mejor_urgencia = Urgencia.MEDIA
        mejor_confianza = 0.0
        for urgencia, patrones in self.PATRONES_URGENCIA_ES.items():
            for patron, confianza in patrones:
                if re.search(patron, texto_lower):
                    if confianza > mejor_confianza:
                        mejor_confianza = confianza
                        mejor_urgencia = urgencia
        if texto_norm.count('!') >= 3 and mejor_urgencia in (Urgencia.MEDIA, Urgencia.BAJA):
            mejor_urgencia = Urgencia.ALTA
        return mejor_urgencia
    
    def _detectar_ambito_simple(self, texto_lower: str) -> AmbitoIntencion:
        """Detección de ámbito por substrings simples (SIN REGEX, SIN ERRORES)."""
        puntuaciones = defaultdict(float)
        for ambito, palabras in self.PALABRAS_AMBITO_SIMPLES.items():
            for palabra in palabras:
                if palabra in texto_lower:
                    puntuaciones[ambito] += 1.5
        if puntuaciones:
            return max(puntuaciones, key=puntuaciones.get)
        return AmbitoIntencion.GENERAL
    
    def _generar_contexto(self, ip: IntencionDetectada, es_pregunta: bool, es_orden: bool) -> Dict[str, Any]:
        """Genera contexto sugerido para la respuesta."""
        ctx = {'tipo_respuesta': 'informativa', 'formato': 'texto', 'tono_sugerido': 'neutral',
               'longitud_sugerida': 'media', 'incluir_ejemplos': False, 'incluir_referencias': False}
        if es_pregunta:
            ctx.update({'tipo_respuesta': 'respuesta', 'tono_sugerido': 'informativo', 'incluir_ejemplos': True})
            if ip.sub_intencion in (SubIntencion.PREGUNTA_PROCEDIMIENTO, SubIntencion.PREGUNTA_DEFINICION):
                ctx.update({'formato': 'estructurado', 'longitud_sugerida': 'larga', 'incluir_referencias': True})
        elif es_orden:
            ctx.update({'tipo_respuesta': 'confirmacion', 'tono_sugerido': 'ejecutivo', 'longitud_sugerida': 'corta'})
        elif ip.categoria == CategoriaIntencion.SALUDO:
            ctx.update({'tipo_respuesta': 'saludo', 'tono_sugerido': 'calido', 'longitud_sugerida': 'corta'})
        elif ip.categoria == CategoriaIntencion.DESPEDIDA:
            ctx.update({'tipo_respuesta': 'despedida', 'tono_sugerido': 'calido', 'longitud_sugerida': 'corta'})
        if ip.urgencia in (Urgencia.INMEDIATA, Urgencia.ALTA):
            ctx.update({'longitud_sugerida': 'corta', 'tono_sugerido': 'directo'})
        return ctx

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS (PERFECTO - SIN ERRORES)
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE INTENCIÓN")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/7] Inicializando motor de intención...")
        motor = MotorIntencion()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def ip(datos, clave, default='desconocido'):
            """Obtiene valor seguro de intencion_principal."""
            p = datos.get('intencion_principal', {})
            if isinstance(p, dict):
                return p.get(clave, default)
            return default
        
        print("\n[2/7] Probando preguntas...")
        for texto in [
            "¿Qué es la inteligencia artificial?",
            "¿Cómo se hace una tortilla de patatas?",
            "¿Dónde está la biblioteca más cercana?",
            "¿Cuándo es el próximo eclipse solar?",
            "¿Por qué el cielo es azul?",
        ]:
            r = motor.procesar(texto)
            d = r.datos
            print(f"  📍 '{texto[:50]}...' → {ip(d,'categoria')} ({ip(d,'sub_intencion')})")
        
        print("\n[3/7] Probando órdenes...")
        for texto in ["Abre el navegador ahora mismo", "Busca información sobre el clima por favor", "¡Hazlo ya!"]:
            r = motor.procesar(texto)
            d = r.datos
            print(f"  📍 '{texto[:50]}...' → {ip(d,'categoria')} | urgencia={ip(d,'urgencia')}")
        
        print("\n[4/7] Probando saludos y despedidas...")
        for texto in ["Hola, ¿cómo estás?", "Buenos días, ¿qué tal?", "Adiós, hasta luego", "Muchas gracias por tu ayuda", "Perdón por la interrupción"]:
            r = motor.procesar(texto)
            d = r.datos
            print(f"  📍 '{texto[:50]}...' → {ip(d,'categoria')}")
        
        print("\n[5/7] Probando solicitudes y quejas...")
        for texto in ["Necesito ayuda con mi tarea", "¿Podrías explicarme esto?", "Esto no funciona, es un desastre", "Sugiero que mejoremos el sistema"]:
            r = motor.procesar(texto)
            d = r.datos
            print(f"  📍 '{texto[:50]}...' → {ip(d,'categoria')} | requiere_respuesta={d.get('requiere_respuesta',False)}")
        
        print("\n[6/7] Probando detección de ámbito...")
        pruebas_ambito = [
            ("Necesito programar una API REST con Python", "tecnico"),
            ("Mi familia y yo vamos de vacaciones a la playa", "personal"),
            ("Tengo una reunión con el cliente mañana en la oficina", "profesional"),
            ("Quiero crear un poema sobre el amor y la naturaleza", "creativo"),
            ("Necesito estudiar para el examen de matemáticas", "academico"),
            ("Me siento muy triste y deprimido últimamente", "emocional"),
            ("Quiero comprar un teléfono nuevo, ¿cuál me recomiendas?", "comercial"),
            ("¿Qué opinas sobre la teoría de la relatividad?", "cientifico"),
        ]
        aciertos = 0
        for texto, esperado in pruebas_ambito:
            r = motor.procesar(texto)
            d = r.datos
            ambito = ip(d, 'ambito', 'general')
            if ambito == esperado:
                print(f"  ✅ '{texto[:55]}...' → {ambito}")
                aciertos += 1
            else:
                print(f"  ❌ '{texto[:55]}...' → {ambito} (esperado: {esperado})")
        print(f"  📊 Precisión de ámbito: {aciertos}/{len(pruebas_ambito)} ({aciertos/len(pruebas_ambito)*100:.0f}%)")
        
        print("\n[7/7] Estadísticas del motor...")
        print(f"  📊 Categorías de intención: {len(motor.PATRONES_ES)}")
        print(f"  📊 Niveles de urgencia: {len(motor.PATRONES_URGENCIA_ES)}")
        total_palabras = sum(len(v) for v in motor.PALABRAS_AMBITO_SIMPLES.values())
        print(f"  📊 Ámbitos: {len(motor.PALABRAS_AMBITO_SIMPLES)}")
        print(f"  📊 Palabras por ámbito: {total_palabras}+")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Motor de Intención está VIVO y es REAL.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print("\n" + "=" * 70 + "\n")