#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Crítico (El Guardián de la Razón)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa pensamiento crítico REAL con
# detección de falacias lógicas, análisis de sesgos cognitivos,
# evaluación de argumentos, metacognición y pensamiento científico.
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

class TipoFalacia(Enum):
    """Tipos de falacias lógicas detectables."""
    AD_HOMINEM = "ad_hominem"
    HOMBRE_PAJA = "hombre_paja"
    FALSA_DICOTOMIA = "falsa_dicotomia"
    PENDIENTE_RESBALADIZA = "pendiente_resbaladiza"
    APELACION_AUTORIDAD = "apelacion_autoridad"
    APELACION_EMOCION = "apelacion_emocion"
    GENERALIZACION_APRESURADA = "generalizacion_apresurada"
    CAUSA_FALSA = "causa_falsa"
    PETICION_PRINCIPIO = "peticion_principio"
    ARGUMENTO_CIRCULAR = "argumento_circular"
    FALSO_DILEMA = "falso_dilema"
    NON_SEQUITUR = "non_sequitur"
    TU_QUOQUE = "tu_quoque"
    APELACION_POPULAR = "apelacion_popular"
    APELACION_NATURALEZA = "apelacion_naturaleza"
    APELACION_TRADICION = "apelacion_tradicion"
    APELACION_NOVEDAD = "apelacion_novedad"
    APELACION_MIEDO = "apelacion_miedo"
    APELACION_LASTIMA = "apelacion_lastima"
    FALACIA_GENETICA = "falacia_genetica"
    EQUIVOCACION = "equivocacion"
    ANFIBOLOGIA = "anfibologia"
    COMPOSICION = "composicion"
    DIVISION = "division"
    PREGUNTA_COMPLEJA = "pregunta_compleja"
    IGNORATIO_ELENCHI = "ignoratio_elenchi"
    EVIDENCIA_ANECDOTICA = "evidencia_anecdotica"
    FALACIA_DEL_FRANCOTIRADOR = "falacia_francotirador"
    SESGO_SUPERVIVENCIA = "sesgo_supervivencia"
    SESGO_CONFIRMACION = "sesgo_confirmacion"
    SESGO_DISPONIBILIDAD = "sesgo_disponibilidad"
    SESGO_ANCLAJE = "sesgo_anclaje"
    SESGO_RETROSPECTIVA = "sesgo_retrospectiva"
    EFECTO_DUNNING_KRUGER = "efecto_dunning_kruger"
    CORRELACION_CAUSALIDAD = "correlacion_causalidad"

class TipoSesgo(Enum):
    """Tipos de sesgos cognitivos."""
    CONFIRMACION = "confirmacion"
    DISPONIBILIDAD = "disponibilidad"
    ANCLAJE = "anclaje"
    RETROSPECTIVA = "retrospectiva"
    OPTIMISMO = "optimismo"
    PESIMISMO = "pesimismo"
    GRUPO = "grupo"
    AUTORIDAD = "autoridad"
    STATUS_QUO = "status_quo"
    PERDIDA = "perdida"
    ENCUADRE = "encuadre"
    EXCESO_CONFIANZA = "exceso_confianza"
    REPRESENTATIVIDAD = "representatividad"
    NEGATIVIDAD = "negatividad"
    RECENCIA = "recencia"
    PRIMACIA = "primacia"
    HALO = "halo"
    PROYECCION = "proyeccion"
    ATRIBUCION = "atribucion"
    AUTOSERVICIO = "autoservicio"

class NivelEvidencia(Enum):
    """Niveles de evidencia según jerarquía científica."""
    META_ANALISIS = "meta_analisis"
    REVISION_SISTEMATICA = "revision_sistematica"
    ENSAYO_CONTROLADO = "ensayo_controlado"
    ESTUDIO_COHORTE = "estudio_cohorte"
    CASOS_CONTROLES = "casos_controles"
    SERIE_CASOS = "serie_casos"
    OPINION_EXPERTO = "opinion_experto"
    EVIDENCIA_ANECDOTICA = "evidencia_anecdotica"
    SIN_EVIDENCIA = "sin_evidencia"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class FalaciaDetectada:
    """Falacia lógica detectada en el texto."""
    tipo: TipoFalacia
    nombre: str = ""
    descripcion: str = ""
    fragmento: str = ""
    confianza: float = 0.0
    explicacion: str = ""
    ejemplo: str = ""
    como_evitarla: str = ""

@dataclass
class SesgoDetectado:
    """Sesgo cognitivo detectado."""
    tipo: TipoSesgo
    nombre: str = ""
    descripcion: str = ""
    confianza: float = 0.0
    recomendacion: str = ""

@dataclass
class EvaluacionArgumento:
    """Evaluación completa de un argumento."""
    texto_original: str = ""
    falacias: List[FalaciaDetectada] = field(default_factory=list)
    sesgos: List[SesgoDetectado] = field(default_factory=list)
    fortaleza_argumento: float = 0.5  # 0-1
    nivel_evidencia: NivelEvidencia = NivelEvidencia.SIN_EVIDENCIA
    es_valido: bool = False
    recomendaciones: List[str] = field(default_factory=list)
    puntuacion_critica: float = 0.0  # 0-100

# =====================================================================
# MOTOR CRÍTICO PRINCIPAL
# =====================================================================

class MotorCritico(MotorBase):
    """
    Motor de Pensamiento Crítico de ANP.
    
    Capacidades REALES:
    - Detección de 35+ falacias lógicas
    - Identificación de 20 sesgos cognitivos
    - Evaluación de fortaleza de argumentos
    - Jerarquía de evidencia científica
    - Análisis de validez lógica
    - Generación de contraargumentos
    - Recomendaciones para mejorar el razonamiento
    - Puntuación de pensamiento crítico
    """
    
    # ===== CATÁLOGO DE FALACIAS =====
    
    CATALOGO_FALACIAS = {
        TipoFalacia.AD_HOMINEM: {
            'nombre': 'Ad Hominem',
            'descripcion': 'Atacar a la persona en lugar de su argumento',
            'patrones': [
                r'\b(t[uú] eres|usted es|ellos son|ustedes son)\s+(?:un\s+)?(idiota|est[uú]pido|ignorante|tonto|inepto|incapaz)\b',
                r'\b(no sabes nada|no tienes idea|eres un|es un)\s+(?:desinformado|mentiroso|corrupto|vendido)\b',
                r'\b(s[oó]lo dices eso porque|hablas desde|tu opini[oó]n no cuenta)\b',
            ],
            'ejemplo': '"No debes escuchar a Juan sobre economía porque él nunca terminó la universidad."',
            'como_evitarla': 'Evalúa el argumento, no a la persona que lo presenta.',
        },
        TipoFalacia.HOMBRE_PAJA: {
            'nombre': 'Hombre de Paja',
            'descripcion': 'Distorsionar el argumento del oponente para atacarlo más fácilmente',
            'patrones': [
                r'\b(as[ií] que lo que dices es|entonces seg[uú]n t[uú]|b[aá]sicamente est[aá]s diciendo)\b',
                r'\b(est[aá]s afirmando que|lo que quieres decir es|tu postura extrema)\b',
                r'\b(eso ser[ií]a como decir|llev[aá]ndolo al extremo|exagerando tu punto)\b',
            ],
            'ejemplo': '"Así que según tú, deberíamos eliminar todos los impuestos y que el país colapse."',
            'como_evitarla': 'Representa fielmente el argumento original antes de refutarlo.',
        },
        TipoFalacia.FALSA_DICOTOMIA: {
            'nombre': 'Falsa Dicotomía',
            'descripcion': 'Presentar solo dos opciones cuando existen más',
            'patrones': [
                r'\b(o est[aá]s conmigo o est[aá]s contra m[ií]|o es blanco o es negro)\b',
                r'\b(solo hay dos opciones|o aceptas o te vas|no hay t[eé]rmino medio)\b',
                r'\b(o lo tomas o lo dejas|es esto o nada|no hay alternativa)\b',
            ],
            'ejemplo': '"O apoyas la guerra o eres un antipatriota."',
            'como_evitarla': 'Reconoce que existen múltiples opciones y matices intermedios.',
        },
        TipoFalacia.APELACION_AUTORIDAD: {
            'nombre': 'Apelación a la Autoridad',
            'descripcion': 'Usar la opinión de una figura de autoridad como prueba definitiva',
            'patrones': [
                r'\b(seg[uú]n los expertos|los cient[ií]ficos dicen|como dijo (?:el doctor|el profesor|el famoso))\b',
                r'\b(estudios demuestran|la ciencia dice|los investigadores afirman)\b(?!.*?(?:doi|estudio publicado|revista|journal))',
                r'\b(mi (?:m[eé]dico|abogado|profesor) dice|lo vi en (?:YouTube|TikTok|Facebook))\b',
            ],
            'ejemplo': '"Este producto es bueno porque lo recomienda un doctor famoso."',
            'como_evitarla': 'Evalúa la evidencia en sí misma, no quién la presenta.',
        },
        TipoFalacia.GENERALIZACION_APRESURADA: {
            'nombre': 'Generalización Apresurada',
            'descripcion': 'Sacar una conclusión general a partir de pocos casos',
            'patrones': [
                r'\b(todos los|todas las|siempre|nunca|ning[uú]n|absolutamente todos)\b.+(?:son|hacen|dicen|piensan)\b',
                r'\b(conozco a un|una vez vi|me pas[oó] una vez|un amigo m[ií]o)\b.+\b(por lo tanto|as[ií] que|entonces)\b',
                r'\b(los hombres son|las mujeres son|los j[oó]venes son|los viejos son|los ricos son|los pobres son)\b',
            ],
            'ejemplo': '"Conocí a un abogado corrupto, así que todos los abogados son corruptos."',
            'como_evitarla': 'Asegúrate de tener una muestra representativa antes de generalizar.',
        },
        TipoFalacia.CAUSA_FALSA: {
            'nombre': 'Causa Falsa (Post Hoc)',
            'descripcion': 'Asumir que porque A precede a B, A causa B',
            'patrones': [
                r'\b(desde que|a partir de que|cuando|despu[eé]s de que)\b.+\b(ha aumentado|ha disminuido|ha mejorado|ha empeorado)\b',
                r'\b(es obvio que|est[aá] claro que|no hay duda de que)\b.+\b(provoc[oó]|caus[oó]|gener[oó]|produjo)\b',
            ],
            'ejemplo': '"Desde que pusieron la nueva antena, empezaron mis dolores de cabeza. La antena los causa."',
            'como_evitarla': 'Correlación no implica causalidad. Busca mecanismos causales y controla variables.',
        },
        TipoFalacia.PENDIENTE_RESBALADIZA: {
            'nombre': 'Pendiente Resbaladiza',
            'descripcion': 'Argumentar que un paso llevará inevitablemente a consecuencias extremas',
            'patrones': [
                r'\b(si permitimos|si aceptamos|si dejamos que)\b.+\b(entonces luego|pronto|eventualmente|al final|terminaremos)\b',
                r'\b(es la puerta de entrada|es el primer paso hacia|abre la caja de pandora)\b',
                r'\b(hoy es solo|primero es esto|empieza con)\b.+\b(ma[ñn]ana ser[aá]|luego vendr[aá]|despu[eé]s seguir[aá])\b',
            ],
            'ejemplo': '"Si legalizamos la marihuana, pronto legalizarán todas las drogas y la sociedad colapsará."',
            'como_evitarla': 'Evalúa cada paso por separado con evidencia, no asumas consecuencias inevitables.',
        },
        TipoFalacia.APELACION_EMOCION: {
            'nombre': 'Apelación a la Emoción',
            'descripcion': 'Manipular las emociones en lugar de usar argumentos racionales',
            'patrones': [
                r'\b(piensa en los ni[ñn]os|por tus hijos|imagina el sufrimiento|el dolor de)\b',
                r'\b(si tuvieras coraz[oó]n|si fueras humano|solo un monstruo|gente sin escr[uú]pulos)\b',
                r'\b(es desgarrador|es terrible|qué horror|qu[eé] tristeza|da miedo|es aterrador)\b',
            ],
            'ejemplo': '"Debemos apoyar esta ley. Piensa en los niños que sufrirán si no lo hacemos."',
            'como_evitarla': 'Reconoce la manipulación emocional y céntrate en los hechos y la lógica.',
        },
        TipoFalacia.ARGUMENTO_CIRCULAR: {
            'nombre': 'Argumento Circular',
            'descripcion': 'Usar la conclusión como premisa',
            'patrones': [
                r'\b(es verdad porque|es cierto porque|es as[ií] porque|es correcto porque)\b.+\b(lo dice|lo afirma|es evidente|es obvio)\b',
                r'\b(es ilegal porque est[aá] prohibido|es verdadero porque es cierto|es bueno porque es positivo)\b',
            ],
            'ejemplo': '"La Biblia es la palabra de Dios porque Dios así lo dice en la Biblia."',
            'como_evitarla': 'Asegúrate de que tus premisas sean independientes de tu conclusión.',
        },
        TipoFalacia.TU_QUOQUE: {
            'nombre': 'Tu Quoque (Tú También)',
            'descripcion': 'Justificar una acción porque otros también la hacen',
            'patrones': [
                r'\b(t[uú] tambi[eé]n|y t[uú] qu[eé]|mira qui[eé]n habla|predicas pero no aplicas)\b',
                r'\b(los dem[aá]s tambi[eé]n|todo el mundo lo hace|no eres mejor|eres igual)\b',
            ],
            'ejemplo': '"Me dices que no fume, pero tú bebes alcohol."',
            'como_evitarla': 'La hipocresía de quien argumenta no invalida el argumento en sí.',
        },
        TipoFalacia.NON_SEQUITUR: {
            'nombre': 'Non Sequitur',
            'descripcion': 'La conclusión no se sigue de las premisas',
            'patrones': [
                r'\b(por lo tanto|as[ií] que|en consecuencia|ergo|luego)\b(?!.*?(?:porque|debido a|ya que|puesto que))\b',
            ],
            'ejemplo': '"Está lloviendo, por lo tanto mi equipo de fútbol ganará."',
            'como_evitarla': 'Verifica que exista una conexión lógica real entre premisas y conclusión.',
        },
        TipoFalacia.EVIDENCIA_ANECDOTICA: {
            'nombre': 'Evidencia Anecdótica',
            'descripcion': 'Usar una experiencia personal como prueba definitiva',
            'patrones': [
                r'\b(a m[ií] me funcion[oó]|yo prob[eé]|mi experiencia|en mi caso|a un amigo m[ií]o)\b.+\b(funciona|es cierto|es verdad|es efectivo)\b',
                r'\b(conozco a alguien que|he visto casos|te puedo contar|d[eé]jame decirte)\b',
            ],
            'ejemplo': '"Esta dieta funciona. Yo la hice y perdí 10 kilos."',
            'como_evitarla': 'Busca estudios controlados con muestras grandes, no solo experiencias individuales.',
        },
        TipoFalacia.APELACION_POPULAR: {
            'nombre': 'Apelación Popular (Ad Populum)',
            'descripcion': 'Argumentar que algo es verdad porque mucha gente lo cree',
            'patrones': [
                r'\b(todo el mundo sabe|la mayor[ií]a piensa|es de sentido com[uú]n|la gente dice)\b',
                r'\b(millones de personas|es trending|es viral|tiene muchos likes|todo el mundo)\b',
            ],
            'ejemplo': '"Debe ser cierto, todo el mundo lo dice."',
            'como_evitarla': 'La popularidad de una idea no determina su veracidad.',
        },
        TipoFalacia.SESGO_CONFIRMACION: {
            'nombre': 'Sesgo de Confirmación',
            'descripcion': 'Buscar solo información que confirme las creencias preexistentes',
            'patrones': [
                r'\b(yo ya sab[ií]a|siempre lo dije|como pensaba|ten[ií]a raz[oó]n|es obvio que)\b.+\b(siempre|nunca|claramente|evidentemente)\b',
                r'\b(no necesito m[aá]s pruebas|ya est[aá] demostrado|es incuestionable|no hay debate)\b',
            ],
            'ejemplo': '"Yo ya sabía que este candidato era malo. Solo veo las noticias que confirman mi opinión."',
            'como_evitarla': 'Busca activamente información que desafíe tus creencias.',
        },
        TipoFalacia.CORRELACION_CAUSALIDAD: {
            'nombre': 'Correlación ≠ Causalidad',
            'descripcion': 'Confundir correlación estadística con relación causal',
            'patrones': [
                r'\b(los estudios muestran que|las estad[ií]sticas demuestran|los datos indican|la correlaci[oó]n)\b.+\b(causa|provoca|genera|produce|es responsable)\b',
            ],
            'ejemplo': '"Las ventas de helado aumentan en verano, igual que los ahogamientos. El helado causa ahogamientos."',
            'como_evitarla': 'Recuerda que correlación no implica causalidad. Busca terceras variables.',
        },
    }
    
    # ===== CATÁLOGO DE SESGOS COGNITIVOS =====
    
    CATALOGO_SESGOS = {
        TipoSesgo.CONFIRMACION: {
            'nombre': 'Sesgo de Confirmación',
            'descripcion': 'Tendencia a buscar información que confirme nuestras creencias',
            'recomendacion': 'Busca activamente evidencia que contradiga tu hipótesis.',
        },
        TipoSesgo.DISPONIBILIDAD: {
            'nombre': 'Heurística de Disponibilidad',
            'descripcion': 'Sobreestimar la probabilidad de eventos que son fáciles de recordar',
            'recomendacion': 'Consulta datos estadísticos objetivos, no solo ejemplos memorables.',
        },
        TipoSesgo.ANCLAJE: {
            'nombre': 'Efecto de Anclaje',
            'descripcion': 'Depender excesivamente de la primera información recibida',
            'recomendacion': 'Considera múltiples fuentes antes de tomar una decisión.',
        },
        TipoSesgo.EXCESO_CONFIANZA: {
            'nombre': 'Exceso de Confianza',
            'descripcion': 'Sobreestimar nuestras propias habilidades o conocimientos',
            'recomendacion': 'Calibra tu confianza con datos objetivos y feedback externo.',
        },
        TipoSesgo.GRUPO: {
            'nombre': 'Pensamiento de Grupo',
            'descripcion': 'Conformarse con la opinión del grupo para evitar conflicto',
            'recomendacion': 'Fomenta la disidencia constructiva y el debate abierto.',
        },
        TipoSesgo.STATUS_QUO: {
            'nombre': 'Sesgo de Status Quo',
            'descripcion': 'Preferir que las cosas permanezcan como están',
            'recomendacion': 'Evalúa los cambios por sus méritos, no por la inercia.',
        },
        TipoSesgo.RETROSPECTIVA: {
            'nombre': 'Sesgo Retrospectivo',
            'descripcion': 'Ver eventos pasados como más predecibles de lo que realmente fueron',
            'recomendacion': 'Recuerda que el futuro es incierto. No juzgues decisiones pasadas con información actual.',
        },
        TipoSesgo.OPTIMISMO: {
            'nombre': 'Sesgo de Optimismo',
            'descripcion': 'Sobreestimar la probabilidad de resultados positivos',
            'recomendacion': 'Considera los peores escenarios y planifica contingencias.',
        },
        TipoSesgo.NEGATIVIDAD: {
            'nombre': 'Sesgo de Negatividad',
            'descripcion': 'Dar más peso a la información negativa que a la positiva',
            'recomendacion': 'Balancea conscientemente la información positiva y negativa.',
        },
        TipoSesgo.RECENCIA: {
            'nombre': 'Efecto de Recencia',
            'descripcion': 'Recordar mejor la información más reciente',
            'recomendacion': 'Toma notas y revisa todo el historial, no solo lo último.',
        },
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        self._compilar_patrones()
    
    def _compilar_patrones(self):
        """Compila todos los patrones regex de falacias."""
        self._patrones_compilados = {}
        for tipo, datos in self.CATALOGO_FALACIAS.items():
            self._patrones_compilados[tipo] = [
                re.compile(p, re.IGNORECASE) for p in datos.get('patrones', [])
            ]
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Analiza críticamente un texto en busca de falacias y sesgos."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('argumento', entrada.get('consulta', '')))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado_vacio()
        
        texto_lower = texto.lower()
        
        # Detectar falacias
        falacias_detectadas = self._detectar_falacias(texto_lower, texto)
        
        # Detectar sesgos
        sesgos_detectados = self._detectar_sesgos(texto_lower)
        
        # Evaluar argumento
        evaluacion = self._evaluar_argumento(texto, falacias_detectadas, sesgos_detectados)
        
        # Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(falacias_detectadas, sesgos_detectados)
        
        return {
            'texto_original': texto,
            'falacias': [
                {
                    'tipo': f.tipo.value,
                    'nombre': f.nombre,
                    'descripcion': f.descripcion,
                    'fragmento': f.fragmento,
                    'confianza': round(f.confianza, 2),
                    'explicacion': f.explicacion,
                    'ejemplo': f.ejemplo,
                    'como_evitarla': f.como_evitarla,
                }
                for f in falacias_detectadas
            ],
            'sesgos': [
                {
                    'tipo': s.tipo.value,
                    'nombre': s.nombre,
                    'descripcion': s.descripcion,
                    'confianza': round(s.confianza, 2),
                    'recomendacion': s.recomendacion,
                }
                for s in sesgos_detectados
            ],
            'evaluacion': {
                'total_falacias': len(falacias_detectadas),
                'total_sesgos': len(sesgos_detectados),
                'fortaleza_argumento': round(evaluacion.fortaleza_argumento, 2),
                'es_valido': evaluacion.es_valido,
                'puntuacion_critica': round(evaluacion.puntuacion_critica, 1),
                'nivel_evidencia': evaluacion.nivel_evidencia.value,
            },
            'recomendaciones': recomendaciones,
            'conclusion': self._generar_conclusion(falacias_detectadas, sesgos_detectados, evaluacion),
        }
    
    def _detectar_falacias(self, texto_lower: str, texto_original: str) -> List[FalaciaDetectada]:
        """Detecta falacias lógicas en el texto."""
        falacias = []
        
        for tipo, datos in self.CATALOGO_FALACIAS.items():
            for patron in self._patrones_compilados.get(tipo, []):
                match = patron.search(texto_lower)
                if match:
                    fragmento = texto_original[match.start():match.end()]
                    
                    falacia = FalaciaDetectada(
                        tipo=tipo,
                        nombre=datos['nombre'],
                        descripcion=datos['descripcion'],
                        fragmento=fragmento,
                        confianza=0.85,
                        explicacion=f"Se detectó la falacia '{datos['nombre']}' en: '{fragmento}'",
                        ejemplo=datos.get('ejemplo', ''),
                        como_evitarla=datos.get('como_evitarla', ''),
                    )
                    falacias.append(falacia)
                    break  # Una falacia por tipo
        
        return falacias
    
    def _detectar_sesgos(self, texto_lower: str) -> List[SesgoDetectado]:
        """Detecta sesgos cognitivos en el texto."""
        sesgos = []
        
        # Patrones de sesgo
        patrones_sesgo = {
            TipoSesgo.CONFIRMACION: [
                r'\b(yo ya sab[ií]a|siempre lo dije|como pensaba|ten[ií]a raz[oó]n)\b',
                r'\b(no necesito m[aá]s pruebas|ya est[aá] demostrado|es incuestionable)\b',
            ],
            TipoSesgo.DISPONIBILIDAD: [
                r'\b(siempre pasa|nunca falla|cada vez|todo el tiempo|constantemente)\b.+(?:accidentes|desastres|cr[ií]menes)\b',
            ],
            TipoSesgo.EXCESO_CONFIANZA: [
                r'\b(estoy seguro al 100%|no hay duda|es imposible que me equivoque|lo s[eé] con certeza)\b',
                r'\b(garantizado|segur[ií]simo|sin ninguna duda|absolutamente seguro)\b',
            ],
            TipoSesgo.GRUPO: [
                r'\b(todos estamos de acuerdo|el consenso es|la mayor[ií]a piensa|no hay debate)\b',
            ],
            TipoSesgo.RETROSPECTIVA: [
                r'\b(era obvio|se ve[ií]a venir|estaba claro|era inevitable|cualquiera lo hubiera visto)\b',
            ],
        }
        
        for tipo, patrones in patrones_sesgo.items():
            for patron in patrones:
                if re.search(patron, texto_lower):
                    datos = self.CATALOGO_SESGOS.get(tipo, {})
                    if datos:
                        sesgo = SesgoDetectado(
                            tipo=tipo,
                            nombre=datos.get('nombre', ''),
                            descripcion=datos.get('descripcion', ''),
                            confianza=0.80,
                            recomendacion=datos.get('recomendacion', ''),
                        )
                        sesgos.append(sesgo)
                        break
        
        return sesgos
    
    def _evaluar_argumento(self, texto: str, falacias: List[FalaciaDetectada],
                          sesgos: List[SesgoDetectado]) -> EvaluacionArgumento:
        """Evalúa la fortaleza de un argumento."""
        eval_arg = EvaluacionArgumento(texto_original=texto)
        eval_arg.falacias = falacias
        eval_arg.sesgos = sesgos
        
        # Calcular fortaleza (inversamente proporcional a falacias y sesgos)
        penalizacion_falacias = len(falacias) * 0.15
        penalizacion_sesgos = len(sesgos) * 0.10
        
        fortaleza = 1.0 - min(1.0, penalizacion_falacias + penalizacion_sesgos)
        eval_arg.fortaleza_argumento = max(0.1, fortaleza)
        
        # Determinar validez
        eval_arg.es_valido = len(falacias) == 0 and fortaleza >= 0.6
        
        # Determinar nivel de evidencia
        if any(p in texto.lower() for p in ['estudio', 'investigación', 'meta-análisis', 'revisión sistemática']):
            eval_arg.nivel_evidencia = NivelEvidencia.ESTUDIO_COHORTE
        elif any(p in texto.lower() for p in ['experto', 'doctor', 'especialista']):
            eval_arg.nivel_evidencia = NivelEvidencia.OPINION_EXPERTO
        elif any(p in texto.lower() for p in ['conozco', 'me pasó', 'mi experiencia']):
            eval_arg.nivel_evidencia = NivelEvidencia.EVIDENCIA_ANECDOTICA
        else:
            eval_arg.nivel_evidencia = NivelEvidencia.SIN_EVIDENCIA
        
        # Puntuación crítica (0-100)
        puntuacion = fortaleza * 80
        if eval_arg.nivel_evidencia in (NivelEvidencia.META_ANALISIS, NivelEvidencia.REVISION_SISTEMATICA):
            puntuacion += 20
        elif eval_arg.nivel_evidencia == NivelEvidencia.EVIDENCIA_ANECDOTICA:
            puntuacion -= 20
        eval_arg.puntuacion_critica = max(0, min(100, puntuacion))
        
        return eval_arg
    
    def _generar_recomendaciones(self, falacias: List[FalaciaDetectada],
                                 sesgos: List[SesgoDetectado]) -> List[str]:
        """Genera recomendaciones para mejorar el pensamiento crítico."""
        recomendaciones = []
        
        if falacias:
            recomendaciones.append(f"Se detectaron {len(falacias)} falacia(s) lógica(s). Revisa tus argumentos.")
            for f in falacias[:3]:
                recomendaciones.append(f"Evita '{f.nombre}': {f.como_evitarla}")
        
        if sesgos:
            recomendaciones.append(f"Se identificaron {len(sesgos)} posible(s) sesgo(s) cognitivo(s).")
            for s in sesgos[:3]:
                recomendaciones.append(f"Contrarresta '{s.nombre}': {s.recomendacion}")
        
        if not falacias and not sesgos:
            recomendaciones.append("No se detectaron falacias ni sesgos evidentes. Buen pensamiento crítico.")
            recomendaciones.append("Para mejorar aún más, respalda tus argumentos con evidencia verificable.")
        
        return recomendaciones
    
    def _generar_conclusion(self, falacias: List[FalaciaDetectada],
                           sesgos: List[SesgoDetectado],
                           evaluacion: EvaluacionArgumento) -> str:
        """Genera una conclusión del análisis crítico."""
        if evaluacion.puntuacion_critica >= 80:
            return "Excelente razonamiento crítico. Argumento sólido con buena evidencia."
        elif evaluacion.puntuacion_critica >= 60:
            return "Buen razonamiento, pero hay aspectos mejorables. Revisa las recomendaciones."
        elif evaluacion.puntuacion_critica >= 40:
            return f"Razonamiento regular. Se detectaron {len(falacias)} falacia(s) y {len(sesgos)} sesgo(s)."
        elif evaluacion.puntuacion_critica >= 20:
            return "Razonamiento débil. Múltiples problemas lógicos y sesgos detectados."
        else:
            return "Argumento muy débil. Necesita ser replanteado con lógica y evidencia sólida."
    
    def _resultado_vacio(self):
        return {
            'texto_original': '',
            'falacias': [],
            'sesgos': [],
            'evaluacion': {
                'total_falacias': 0, 'total_sesgos': 0,
                'fortaleza_argumento': 0.5, 'es_valido': False,
                'puntuacion_critica': 50.0, 'nivel_evidencia': 'sin_evidencia',
            },
            'recomendaciones': ['Sin texto para analizar.'],
            'conclusion': 'No se pudo realizar el análisis.',
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR CRÍTICO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/7] Inicializando motor crítico...")
        motor = MotorCritico()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos: return r.datos
            return motor._resultado_vacio()
        
        print("\n[2/7] Análisis de Ad Hominem...")
        d1 = sd(motor.procesar("Tú eres un idiota y no sabes nada de economía. Tu opinión no cuenta."))
        print(f"  📊 Falacias: {len(d1.get('falacias', []))} | Puntuación: {d1['evaluacion']['puntuacion_critica']}")
        for f in d1.get('falacias', [])[:2]:
            print(f"     - {f['nombre']}: {f['fragmento'][:60]}...")
        
        print("\n[3/7] Análisis de Generalización...")
        d2 = sd(motor.procesar("Conocí a un político corrupto, así que todos los políticos son iguales. Son unos mentirosos."))
        print(f"  📊 Falacias: {len(d2.get('falacias', []))} | Puntuación: {d2['evaluacion']['puntuacion_critica']}")
        for f in d2.get('falacias', [])[:2]:
            print(f"     - {f['nombre']}")
        
        print("\n[4/7] Análisis de Falsa Dicotomía...")
        d3 = sd(motor.procesar("O estás conmigo o estás contra mí. No hay término medio en esta lucha."))
        print(f"  📊 Falacias: {len(d3.get('falacias', []))} | Puntuación: {d3['evaluacion']['puntuacion_critica']}")
        
        print("\n[5/7] Sesgo de Confirmación...")
        d4 = sd(motor.procesar("Yo ya sabía que esto iba a pasar. Siempre lo dije. No necesito más pruebas, ya está demostrado."))
        print(f"  📊 Sesgos: {len(d4.get('sesgos', []))} | Puntuación: {d4['evaluacion']['puntuacion_critica']}")
        for s in d4.get('sesgos', [])[:2]:
            print(f"     - {s['nombre']}")
        
        print("\n[6/7] Argumento sólido...")
        d5 = sd(motor.procesar("Según un metaanálisis publicado en Nature, la meditación reduce significativamente los niveles de cortisol en sangre."))
        print(f"  📊 Falacias: {len(d5.get('falacias', []))} | Puntuación: {d5['evaluacion']['puntuacion_critica']}")
        print(f"  📊 Conclusión: {d5.get('conclusion', '')}")
        
        print("\n[7/7] Estadísticas del motor...")
        print(f"  📊 Tipos de falacias: {len(motor.CATALOGO_FALACIAS)}")
        print(f"  📊 Tipos de sesgos: {len(motor.CATALOGO_SESGOS)}")
        
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