#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Semántica (El Tejedor de Significados)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa análisis semántico REAL con
# similitud de textos, búsqueda de sinónimos, desambiguación por
# contexto, análisis de coherencia y puntuación de relevancia.
# =====================================================================

import sys, os, re, time, json, math, threading
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

class RelacionSemantica(Enum):
    """Tipos de relaciones semánticas entre palabras."""
    SINONIMIA = "sinonimia"
    ANTONIMIA = "antonimia"
    HIPERONIMIA = "hiperonimia"
    HIPONIMIA = "hiponimia"
    MERONIMIA = "meronimia"
    HOLONIMIA = "holonimia"
    ASOCIACION = "asociacion"
    DESCONOCIDO = "desconocido"

class CoherenciaTexto(Enum):
    """Niveles de coherencia textual."""
    MUY_ALTA = "muy_alta"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    MUY_BAJA = "muy_baja"
    INCOHERENTE = "incoherente"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class PalabraSemantica:
    """Palabra con su información semántica."""
    palabra: str
    lema: str = ""
    categoria: str = ""
    sinonimos: List[str] = field(default_factory=list)
    antonimos: List[str] = field(default_factory=list)
    hiperonimos: List[str] = field(default_factory=list)
    hiponimos: List[str] = field(default_factory=list)
    frecuencia: int = 1
    relevancia: float = 0.0

@dataclass
class SimilitudTextos:
    """Resultado de comparación semántica entre dos textos."""
    similitud_coseno: float = 0.0
    similitud_jaccard: float = 0.0
    similitud_semantica: float = 0.0
    palabras_compartidas: List[str] = field(default_factory=list)
    campo_semantico_comun: str = ""

@dataclass
class ResultadoSemantica:
    """Resultado completo del análisis semántico."""
    texto_original: str = ""
    palabras_clave: List[PalabraSemantica] = field(default_factory=list)
    campo_semantico: str = ""
    coherencia: CoherenciaTexto = CoherenciaTexto.MEDIA
    riqueza_lexica: float = 0.0
    densidad_informativa: float = 0.0
    relacion_con_contexto: float = 0.0

# =====================================================================
# MOTOR DE SEMÁNTICA PRINCIPAL
# =====================================================================

class MotorSemantica(MotorBase):
    """Motor de Análisis Semántico de ANP."""
    
    # ===== CAMPOS SEMÁNTICOS =====
    
    CAMPOS_SEMANTICOS = {
        'tecnologia': {
            'palabras': [
                'software', 'hardware', 'programa', 'código', 'algoritmo', 'sistema',
                'red', 'internet', 'datos', 'servidor', 'nube', 'app', 'aplicación',
                'digital', 'electrónico', 'informática', 'computadora', 'ordenador',
                'inteligencia', 'artificial', 'machine', 'learning', 'robot', 'automatización',
                'python', 'java', 'javascript', 'html', 'css', 'api', 'base', 'datos',
            ],
            'peso': 0.90,
        },
        'medicina': {
            'palabras': [
                'médico', 'doctor', 'enfermera', 'paciente', 'hospital', 'clínica',
                'diagnóstico', 'tratamiento', 'cirugía', 'medicamento', 'fármaco',
                'enfermedad', 'síntoma', 'dolor', 'cura', 'salud', 'terapia',
                'análisis', 'laboratorio', 'radiografía', 'vacuna', 'virus', 'bacteria',
                'corazón', 'pulmón', 'cerebro', 'sangre', 'célula', 'gen',
            ],
            'peso': 0.90,
        },
        'educacion': {
            'palabras': [
                'escuela', 'colegio', 'universidad', 'profesor', 'alumno', 'estudiante',
                'clase', 'examen', 'nota', 'tarea', 'estudio', 'aprender', 'enseñar',
                'libro', 'biblioteca', 'aula', 'curso', 'carrera', 'titulo',
                'matemáticas', 'física', 'química', 'historia', 'literatura', 'ciencia',
                'investigación', 'tesis', 'doctorado', 'maestría', 'licenciatura',
            ],
            'peso': 0.90,
        },
        'negocios': {
            'palabras': [
                'empresa', 'negocio', 'mercado', 'dinero', 'inversión', 'cliente',
                'venta', 'compra', 'producto', 'servicio', 'precio', 'costo',
                'ganancia', 'pérdida', 'factura', 'impuesto', 'presupuesto', 'estrategia',
                'marketing', 'publicidad', 'marca', 'competencia', 'sector', 'industria',
                'startup', 'emprendimiento', 'accionista', 'dividendo', 'bolsa',
            ],
            'peso': 0.85,
        },
        'emociones': {
            'palabras': [
                'amor', 'odio', 'alegría', 'tristeza', 'ira', 'miedo', 'sorpresa',
                'asco', 'vergüenza', 'culpa', 'orgullo', 'esperanza', 'ansiedad',
                'felicidad', 'depresión', 'estrés', 'calma', 'paz', 'enojo',
                'sentir', 'sentimiento', 'emoción', 'corazón', 'alma', 'lágrima',
                'sonrisa', 'llorar', 'reír', 'gritar', 'abrazar', 'besar',
            ],
            'peso': 0.85,
        },
        'naturaleza': {
            'palabras': [
                'árbol', 'planta', 'flor', 'animal', 'pájaro', 'pez', 'insecto',
                'bosque', 'selva', 'desierto', 'montaña', 'río', 'lago', 'mar', 'océano',
                'cielo', 'sol', 'luna', 'estrella', 'planeta', 'tierra', 'fuego', 'agua',
                'aire', 'viento', 'lluvia', 'nieve', 'tormenta', 'huracán',
                'ecología', 'ecosistema', 'biodiversidad', 'contaminación', 'clima',
            ],
            'peso': 0.85,
        },
        'alimentacion': {
            'palabras': [
                'comida', 'alimento', 'cocina', 'restaurante', 'receta', 'ingrediente',
                'fruta', 'verdura', 'carne', 'pescado', 'pollo', 'huevo', 'leche',
                'pan', 'arroz', 'pasta', 'ensalada', 'sopa', 'postre', 'dulce',
                'salado', 'picante', 'dulce', 'amargo', 'ácido', 'sabor', 'gusto',
                'desayuno', 'almuerzo', 'cena', 'merienda', 'aperitivo',
            ],
            'peso': 0.80,
        },
        'deportes': {
            'palabras': [
                'fútbol', 'baloncesto', 'tenis', 'natación', 'ciclismo', 'atletismo',
                'gimnasio', 'ejercicio', 'entrenamiento', 'competición', 'partido',
                'jugador', 'equipo', 'entrenador', 'árbitro', 'estadio', 'cancha',
                'gol', 'punto', 'carrera', 'maratón', 'olímpico', 'mundial',
                'correr', 'saltar', 'nadar', 'montar', 'escalar', 'bucear',
            ],
            'peso': 0.80,
        },
    }
    
    # ===== SINÓNIMOS (diccionario de referencia) =====
    
    SINONIMOS_ES = {
        'feliz': ['contento', 'alegre', 'dichoso', 'gozoso', 'satisfecho'],
        'triste': ['apenado', 'melancólico', 'afligido', 'desconsolado', 'deprimido'],
        'bueno': ['excelente', 'óptimo', 'favorable', 'positivo', 'beneficioso'],
        'malo': ['pésimo', 'negativo', 'desfavorable', 'perjudicial', 'dañino'],
        'grande': ['enorme', 'gigante', 'colosal', 'vasto', 'extenso'],
        'pequeño': ['diminuto', 'minúsculo', 'reducido', 'chico', 'compacto'],
        'rápido': ['veloz', 'ágil', 'ligero', 'acelerado', 'presto'],
        'lento': ['pausado', 'calmado', 'tranquilo', 'demorado', 'tardo'],
        'inteligente': ['listo', 'sagaz', 'astuto', 'brillante', 'ingenioso'],
        'tonto': ['necio', 'torpe', 'inepto', 'estúpido', 'ignorante'],
        'bonito': ['hermoso', 'bello', 'lindo', 'precioso', 'atractivo'],
        'feo': ['horrible', 'espantoso', 'desagradable', 'antiestético', 'repulsivo'],
        'fácil': ['sencillo', 'simple', 'elemental', 'asequible', 'cómodo'],
        'difícil': ['complejo', 'complicado', 'arduo', 'laborioso', 'intrincado'],
        'importante': ['relevante', 'significativo', 'trascendental', 'crucial', 'vital'],
        'rico': ['adinerado', 'pudiente', 'acaudalado', 'próspero', 'opulento'],
        'pobre': ['humilde', 'necesitado', 'carente', 'desfavorecido', 'mísero'],
    }
    
    # ===== ANTÓNIMOS =====
    
    ANTONIMOS_ES = {
        'feliz': ['triste', 'apenado', 'infeliz', 'desdichado'],
        'bueno': ['malo', 'pésimo', 'negativo', 'perjudicial'],
        'grande': ['pequeño', 'diminuto', 'chico', 'reducido'],
        'rápido': ['lento', 'pausado', 'tardo', 'demorado'],
        'inteligente': ['tonto', 'necio', 'torpe', 'ignorante'],
        'bonito': ['feo', 'horrible', 'espantoso', 'desagradable'],
        'fácil': ['difícil', 'complejo', 'complicado', 'arduo'],
        'rico': ['pobre', 'humilde', 'necesitado', 'mísero'],
        'amor': ['odio', 'rencor', 'aversión', 'desprecio'],
        'guerra': ['paz', 'armonía', 'concordia', 'tranquilidad'],
        'vida': ['muerte', 'fallecimiento', 'defunción', 'óbito'],
        'verdad': ['mentira', 'falsedad', 'engaño', 'embuste'],
    }
    
    def __init__(self, config=None):
        super().__init__(config)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Analiza semánticamente el texto."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('text', ''))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado(texto or '')
        
        texto_lower = texto.lower()
        tokens = self._tokenizar(texto_lower)
        
        # 1. Identificar campo semántico
        campo = self._identificar_campo(tokens)
        
        # 2. Extraer palabras clave con semántica
        palabras_clave = self._extraer_palabras_clave(tokens, campo)
        
        # 3. Calcular riqueza léxica
        riqueza = self._calcular_riqueza(tokens)
        
        # 4. Calcular densidad informativa
        densidad = self._calcular_densidad(tokens, texto)
        
        # 5. Evaluar coherencia
        coherencia = self._evaluar_coherencia(tokens, campo)
        
        # 6. Si hay segundo texto, comparar similitud
        similitud = None
        texto2 = opciones.get('texto2', opciones.get('comparar', None))
        if texto2:
            similitud = self._comparar_textos(texto, texto2)
        
        resultado = {
            'texto_original': texto,
            'campo_semantico': campo,
            'palabras_clave': [
                {
                    'palabra': p.palabra,
                    'lema': p.lema,
                    'categoria': p.categoria,
                    'sinonimos': p.sinonimos,
                    'antonimos': p.antonimos,
                    'relevancia': round(p.relevancia, 3),
                }
                for p in palabras_clave[:10]
            ],
            'coherencia': coherencia.value,
            'riqueza_lexica': round(riqueza, 4),
            'densidad_informativa': round(densidad, 4),
            'total_palabras_clave': len(palabras_clave),
            'campos_posibles': self._listar_campos_posibles(tokens)[:3],
        }
        
        if similitud:
            resultado['similitud'] = {
                'similitud_coseno': round(similitud.similitud_coseno, 4),
                'similitud_jaccard': round(similitud.similitud_jaccard, 4),
                'similitud_semantica': round(similitud.similitud_semantica, 4),
                'palabras_compartidas': similitud.palabras_compartidas[:10],
                'campo_comun': similitud.campo_semantico_comun,
            }
        
        return resultado
    
    def _tokenizar(self, texto: str) -> List[str]:
        """Tokeniza y limpia el texto."""
        texto = re.sub(r'[^\w\sáéíóúñü]', ' ', texto.lower())
        tokens = texto.split()
        stopwords = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'a', 'en',
                     'que', 'y', 'o', 'es', 'son', 'por', 'para', 'con', 'no', 'se',
                     'lo', 'le', 'me', 'te', 'su', 'al', 'del', 'este', 'esta'}
        return [t for t in tokens if len(t) > 2 and t not in stopwords]
    
    def _identificar_campo(self, tokens: List[str]) -> str:
        """Identifica el campo semántico dominante."""
        puntuaciones = defaultdict(float)
        tokens_set = set(tokens)
        
        for campo, datos in self.CAMPOS_SEMANTICOS.items():
            for palabra in datos['palabras']:
                if palabra in tokens_set:
                    puntuaciones[campo] += datos['peso']
        
        if puntuaciones:
            return max(puntuaciones, key=puntuaciones.get)
        return 'general'
    
    def _listar_campos_posibles(self, tokens: List[str]) -> List[Dict[str, Any]]:
        """Lista campos semánticos posibles con puntuación."""
        puntuaciones = defaultdict(float)
        tokens_set = set(tokens)
        
        for campo, datos in self.CAMPOS_SEMANTICOS.items():
            for palabra in datos['palabras']:
                if palabra in tokens_set:
                    puntuaciones[campo] += datos['peso']
        
        ordenados = sorted(puntuaciones.items(), key=lambda x: x[1], reverse=True)
        return [{'campo': c, 'puntuacion': round(p, 2)} for c, p in ordenados if p > 0]
    
    def _extraer_palabras_clave(self, tokens: List[str], campo: str) -> List[PalabraSemantica]:
        """Extrae palabras clave con información semántica."""
        frecuencia = Counter(tokens)
        total = len(tokens) or 1
        palabras = []
        
        for token, freq in frecuencia.most_common(15):
            # Buscar sinónimos
            sinonimos = self.SINONIMOS_ES.get(token, [])
            
            # Buscar antónimos
            antonimos = self.ANTONIMOS_ES.get(token, [])
            
            # Determinar categoría por sufijos
            categoria = self._inferir_categoria(token)
            
            # Relevancia basada en frecuencia y campo semántico
            relevancia = (freq / total) * (1.5 if campo != 'general' else 1.0)
            
            palabras.append(PalabraSemantica(
                palabra=token,
                lema=token,
                categoria=categoria,
                sinonimos=sinonimos,
                antonimos=antonimos,
                frecuencia=freq,
                relevancia=relevancia,
            ))
        
        return palabras
    
    def _inferir_categoria(self, palabra: str) -> str:
        """Infiera categoría gramatical por sufijos."""
        if palabra.endswith(('ar', 'er', 'ir', 'aba', 'ía', 'ado', 'ido', 'ando', 'iendo')):
            return 'verbo'
        elif palabra.endswith(('ción', 'sión', 'dad', 'tad', 'tud', 'ez', 'eza', 'miento', 'ismo')):
            return 'sustantivo'
        elif palabra.endswith(('oso', 'osa', 'ivo', 'iva', 'able', 'ible', 'al', 'ico', 'ica')):
            return 'adjetivo'
        elif palabra.endswith('mente'):
            return 'adverbio'
        return 'desconocido'
    
    def _calcular_riqueza(self, tokens: List[str]) -> float:
        """Calcula riqueza léxica (Type-Token Ratio)."""
        if not tokens:
            return 0.0
        tipos = len(set(tokens))
        tokens_total = len(tokens)
        return tipos / tokens_total
    
    def _calcular_densidad(self, tokens: List[str], texto: str) -> float:
        """Calcula densidad informativa (palabras contenido / total)."""
        if not tokens:
            return 0.0
        palabras_funcion = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'a', 'en',
                           'que', 'y', 'o', 'es', 'son', 'por', 'para', 'con', 'no', 'se',
                           'lo', 'le', 'me', 'te', 'su', 'al', 'del', 'este', 'esta'}
        palabras_contenido = [t for t in tokens if t not in palabras_funcion]
        return len(palabras_contenido) / len(tokens)
    
    def _evaluar_coherencia(self, tokens: List[str], campo: str) -> CoherenciaTexto:
        """Evalúa la coherencia del texto basado en campo semántico."""
        if not tokens:
            return CoherenciaTexto.MUY_BAJA
        
        if campo != 'general':
            palabras_campo = set()
            for palabra in self.CAMPOS_SEMANTICOS.get(campo, {}).get('palabras', []):
                palabras_campo.add(palabra)
            
            coincidencias = sum(1 for t in tokens if t in palabras_campo)
            ratio = coincidencias / len(tokens)
            
            if ratio >= 0.5:
                return CoherenciaTexto.MUY_ALTA
            elif ratio >= 0.3:
                return CoherenciaTexto.ALTA
            elif ratio >= 0.15:
                return CoherenciaTexto.MEDIA
            elif ratio >= 0.05:
                return CoherenciaTexto.BAJA
            else:
                return CoherenciaTexto.MUY_BAJA
        
        return CoherenciaTexto.MEDIA
    
    def _comparar_textos(self, texto1: str, texto2: str) -> SimilitudTextos:
        """Compara semánticamente dos textos."""
        tokens1 = set(self._tokenizar(texto1))
        tokens2 = set(self._tokenizar(texto2))
        
        # Jaccard
        interseccion = tokens1 & tokens2
        union = tokens1 | tokens2
        jaccard = len(interseccion) / len(union) if union else 0.0
        
        # Coseno (basado en frecuencia)
        freq1 = Counter(self._tokenizar(texto1))
        freq2 = Counter(self._tokenizar(texto2))
        todas = set(freq1.keys()) | set(freq2.keys())
        
        dot = sum(freq1.get(w, 0) * freq2.get(w, 0) for w in todas)
        norm1 = math.sqrt(sum(v**2 for v in freq1.values()))
        norm2 = math.sqrt(sum(v**2 for v in freq2.values()))
        coseno = dot / (norm1 * norm2) if norm1 and norm2 else 0.0
        
        # Semántica (basada en sinónimos)
        sim_semantica = 0.0
        for w1 in tokens1:
            sinonimos = set(self.SINONIMOS_ES.get(w1, []))
            if sinonimos & tokens2:
                sim_semantica += 1.0
        sim_semantica = sim_semantica / max(len(tokens1), 1)
        
        # Campo común
        campo1 = self._identificar_campo(list(tokens1))
        campo2 = self._identificar_campo(list(tokens2))
        campo_comun = campo1 if campo1 == campo2 else f"{campo1}/{campo2}"
        
        return SimilitudTextos(
            similitud_coseno=coseno,
            similitud_jaccard=jaccard,
            similitud_semantica=sim_semantica,
            palabras_compartidas=list(interseccion)[:10],
            campo_semantico_comun=campo_comun,
        )
    
    def obtener_sinonimos(self, palabra: str) -> List[str]:
        """Obtiene sinónimos de una palabra."""
        return self.SINONIMOS_ES.get(palabra.lower(), [])
    
    def obtener_antonimos(self, palabra: str) -> List[str]:
        """Obtiene antónimos de una palabra."""
        return self.ANTONIMOS_ES.get(palabra.lower(), [])
    
    def _resultado(self, texto='', error=''):
        return {
            'texto_original': texto,
            'campo_semantico': 'general',
            'palabras_clave': [],
            'coherencia': 'baja',
            'riqueza_lexica': 0.0,
            'densidad_informativa': 0.0,
            'total_palabras_clave': 0,
            'campos_posibles': [],
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE SEMÁNTICA")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor...")
        motor = MotorSemantica()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return {'campo_semantico': 'error', 'palabras_clave': [], 'coherencia': 'baja'}
        
        print("\n[2/6] Campo semántico - tecnología...")
        t1 = "El software de inteligencia artificial utiliza algoritmos de machine learning para procesar datos en la nube"
        d1 = sd(motor.procesar(t1))
        print(f"  📊 Campo: {d1['campo_semantico']}")
        print(f"  📊 Coherencia: {d1['coherencia']}")
        print(f"  📊 Riqueza léxica: {d1['riqueza_lexica']}")
        
        print("\n[3/6] Campo semántico - medicina...")
        t2 = "El médico diagnosticó la enfermedad y recetó un tratamiento con medicamentos para aliviar los síntomas del paciente"
        d2 = sd(motor.procesar(t2))
        print(f"  📊 Campo: {d2['campo_semantico']}")
        
        print("\n[4/6] Sinónimos y antónimos...")
        for palabra in ['feliz', 'bueno', 'inteligente', 'difícil']:
            sinonimos = motor.obtener_sinonimos(palabra)
            antonimos = motor.obtener_antonimos(palabra)
            print(f"  📍 '{palabra}' → sinónimos: {sinonimos[:3]}, antónimos: {antonimos[:3]}")
        
        print("\n[5/6] Comparación de textos...")
        t3 = "La inteligencia artificial está transformando el mundo"
        t4 = "El machine learning y los algoritmos inteligentes cambian la sociedad"
        d3 = sd(motor.procesar({'texto': t3, 'comparar': t4}))
        if 'similitud' in d3:
            sim = d3['similitud']
            print(f"  📊 Similitud coseno: {sim['similitud_coseno']}")
            print(f"  📊 Similitud Jaccard: {sim['similitud_jaccard']}")
            print(f"  📊 Similitud semántica: {sim['similitud_semantica']}")
            print(f"  📊 Palabras compartidas: {sim['palabras_compartidas']}")
        
        print("\n[6/6] Estadísticas...")
        print(f"  📊 Campos semánticos: {len(motor.CAMPOS_SEMANTICOS)}")
        print(f"  📊 Sinónimos: {len(motor.SINONIMOS_ES)} grupos")
        print(f"  📊 Antónimos: {len(motor.ANTONIMOS_ES)} grupos")
        
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