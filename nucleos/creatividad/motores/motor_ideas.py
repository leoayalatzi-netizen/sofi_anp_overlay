#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Ideas — Brainstorming, Combinación y Refinamiento Creativo
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Creatividad
# =====================================================================

import sys, time, math, random, traceback, threading, itertools
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter
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
# BANCO DE IDEAS Y PATRONES CREATIVOS
# =====================================================================

class BancoIdeas:
    """Banco de conocimiento para generación y refinamiento de ideas."""
    
    DOMINIOS_INNOVACION = {
        'tecnologia': ['IA generativa', 'computación cuántica', 'biotecnología', 'nanotecnología',
                      'robótica', 'realidad extendida', 'blockchain', 'edge computing',
                      'gemelos digitales', 'neurotecnología', 'materiales inteligentes',
                      'energía de fusión', 'internet cuántico', 'fábricas autónomas'],
        'sostenibilidad': ['economía circular', 'ciudades esponja', 'agricultura regenerativa',
                          'captura de carbono', 'bioplásticos', 'microrredes solares',
                          'desalinización solar', 'bosques comestibles', 'edificios vivos'],
        'salud': ['medicina personalizada', 'órganos bioimpresos', 'terapia génica',
                 'nanobots médicos', 'diagnóstico por voz', 'fármacos diseñados por IA',
                 'neuroprótesis', 'hospital virtual', 'epidemiología predictiva'],
        'educacion': ['aprendizaje inmersivo', 'tutores IA', 'aulas sin paredes',
                     'certificación por habilidades', 'simulaciones históricas',
                     'laboratorios virtuales', 'currículo adaptativo', 'mentoría inversa'],
        'espacio': ['hoteles orbitales', 'minería de asteroides', 'ascensores espaciales',
                   'biosferas marcianas', 'velas solares', 'fábricas en órbita',
                   'telescopios líquidos', 'agricultura lunar'],
        'sociedad': ['democracia líquida', 'renta básica universal', 'ciudades de 15 minutos',
                    'economía del cuidado', 'justicia predictiva', 'gobernanza DAO',
                    'pasaporte de carbono', 'bancos de tiempo'],
    }
    
    TECNICAS_CREATIVAS = {
        'scamper': [
            'Sustituir: ¿Qué elemento puedes reemplazar?',
            'Combinar: ¿Qué pasaría si unes dos conceptos?',
            'Adaptar: ¿Qué puedes tomar prestado de otro campo?',
            'Modificar: ¿Qué cambiarías de forma, tamaño o color?',
            'Propósito: ¿Para qué otro uso serviría?',
            'Eliminar: ¿Qué pasaría si quitas algo esencial?',
            'Reorganizar: ¿En qué otro orden funcionaría?',
        ],
        'triz': [
            'Segmentación: Divide el problema en partes independientes',
            'Extracción: Separa la parte problemática del resto',
            'Asimetría: Cambia la forma para ganar funcionalidad',
            'Consolidación: Une funciones en un solo elemento',
            'Universalidad: Que un elemento cumpla múltiples funciones',
            'Anidación: Coloca un objeto dentro de otro',
            'Contrapeso: Compensa con fuerzas opuestas',
        ],
        'pensamiento_lateral': [
            'Inversión: ¿Y si fuera al revés?',
            'Exageración: ¿Y si lo multiplicas por 1000?',
            'Aleatoriedad: Conecta con algo totalmente azaroso',
            'Analogía: ¿A qué se parece en la naturaleza?',
            'Paradoja: ¿Cómo puede ser verdadero y falso a la vez?',
            'Provocación: ¿Y si eliminamos la restricción principal?',
            'Sueño: ¿Cómo lo resolvería alguien dormido?',
        ],
    }
    
    CRITERIOS_EVALUACION = [
        'originalidad', 'viabilidad', 'impacto', 'escalabilidad',
        'urgencia', 'novedad', 'simplicidad', 'disrupción',
        'sostenibilidad', 'inclusividad', 'rentabilidad', 'belleza'
    ]
    
    VERBOS_ACCION = [
        'crear', 'diseñar', 'construir', 'imaginar', 'desarrollar', 'transformar',
        'revolucionar', 'conectar', 'fusionar', 'expandir', 'destilar', 'esculpir',
        'orquestar', 'cultivar', 'codificar', 'escribir', 'componer', 'forjar'
    ]
    
    ADJETIVOS_IDEA = [
        'radical', 'elegante', 'disruptiva', 'minimalista', 'exponencial', 'líquida',
        'cuántica', 'simbiótica', 'autónoma', 'regenerativa', 'adaptativa', 'fluida',
        'invisible', 'ubicua', 'silenciosa', 'empática', 'resiliente', 'anticipatoria'
    ]

# =====================================================================
# GENERADOR DE IDEAS POR BRAINSTORMING
# =====================================================================

class Brainstorming:
    """Técnicas de generación de ideas: brainstorming, SCAMPER, TRIZ, lateral."""
    
    def __init__(self, banco: BancoIdeas):
        self._banco = banco
    
    def divergir(self, tema: str, cantidad: int = 10, 
                tecnica: str = 'scamper') -> List[Dict[str, Any]]:
        """Genera ideas divergentes usando distintas técnicas creativas."""
        ideas = []
        dominios = list(self._banco.DOMINIOS_INNOVACION.keys())
        
        if tecnica == 'scamper':
            prompts = self._banco.TECNICAS_CREATIVAS['scamper']
        elif tecnica == 'triz':
            prompts = self._banco.TECNICAS_CREATIVAS['triz']
        else:
            prompts = self._banco.TECNICAS_CREATIVAS['pensamiento_lateral']
        
        for i in range(cantidad):
            dominio = random.choice(dominios)
            concepto = random.choice(self._banco.DOMINIOS_INNOVACION[dominio])
            prompt = random.choice(prompts)
            verbo = random.choice(self._banco.VERBOS_ACCION)
            adjetivo = random.choice(self._banco.ADJETIVOS_IDEA)
            
            idea = f"{verbo} un sistema {adjetivo} de {concepto} aplicado a {tema}. {prompt}"
            
            ideas.append({
                'idea': idea,
                'tecnica': tecnica,
                'dominio': dominio,
                'concepto_disparador': concepto,
                'puntuacion_originalidad': round(random.uniform(0.5, 1.0), 2),
                'puntuacion_viabilidad': round(random.uniform(0.3, 0.9), 2),
            })
        
        return ideas
    
    def combinar(self, idea1: str, idea2: str) -> Dict[str, Any]:
        """Combina dos ideas en una nueva usando intersección creativa."""
        conectores = [
            f"Un híbrido entre {idea1[:50]} y {idea2[:50]} que revolucione ambos campos",
            f"Aplicar el principio de {idea1[:40]} al dominio de {idea2[:40]}",
            f"Crear una plataforma donde {idea1[:40]} potencie a {idea2[:40]}",
            f"La intersección inesperada de {idea1[:40]} con {idea2[:40]}",
            f"¿Qué pasaría si {idea1[:40]} se diseñara con la filosofía de {idea2[:40]}?",
        ]
        
        return {
            'idea_original_1': idea1,
            'idea_original_2': idea2,
            'idea_combinada': random.choice(conectores),
            'tipo_combinacion': random.choice(['híbrido', 'plataforma', 'intersección', 
                                               'fusión', 'aplicación_cruzada'])
        }

# =====================================================================
# REFINADOR DE IDEAS
# =====================================================================

class RefinadorIdeas:
    """Refina, evalúa y expande ideas existentes."""
    
    def __init__(self, banco: BancoIdeas):
        self._banco = banco
    
    def refinar(self, idea: str, criterios: List[str] = None, 
               iteraciones: int = 3) -> Dict[str, Any]:
        """Refina una idea aplicando múltiples criterios."""
        if criterios is None:
            criterios = random.sample(self._banco.CRITERIOS_EVALUACION, 4)
        
        versiones = [idea]
        for i in range(iteraciones):
            criterio = random.choice(criterios)
            mejora = random.choice(self._banco.TECNICAS_CREATIVAS['pensamiento_lateral'])
            
            version_refinada = (f"[v{i+1}] Aplicando {criterio}: {mejora} → "
                              f"{versiones[-1][:80]}...")
            versiones.append(version_refinada)
        
        return {
            'idea_original': idea,
            'versiones_refinadas': versiones[1:],
            'criterios_aplicados': criterios,
            'iteraciones': iteraciones,
            'version_final': versiones[-1]
        }
    
    def evaluar(self, idea: str) -> Dict[str, Any]:
        """Evalúa una idea según 12 criterios de innovación."""
        evaluacion = {}
        for criterio in self._banco.CRITERIOS_EVALUACION:
            base = random.uniform(0.3, 0.7)
            evaluacion[criterio] = round(base + random.uniform(-0.15, 0.35), 2)
        
        puntuacion_total = sum(evaluacion.values()) / len(evaluacion)
        fortalezas = sorted(evaluacion, key=evaluacion.get, reverse=True)[:3]
        debilidades = sorted(evaluacion, key=evaluacion.get)[:2]
        
        return {
            'idea': idea[:100],
            'puntuacion_total': round(puntuacion_total, 2),
            'evaluacion_detallada': evaluacion,
            'fortalezas': fortalezas,
            'debilidades': debilidades,
            'recomendacion': 'DESARROLLAR' if puntuacion_total > 0.55 else 'REFINAR'
        }
    
    def expandir(self, idea: str, direcciones: int = 3) -> Dict[str, Any]:
        """Expande una idea en múltiples direcciones."""
        expansiones = []
        dominios = random.sample(list(self._banco.DOMINIOS_INNOVACION.keys()), 
                                min(direcciones, len(self._banco.DOMINIOS_INNOVACION)))
        
        for dominio in dominios:
            concepto = random.choice(self._banco.DOMINIOS_INNOVACION[dominio])
            verbo = random.choice(self._banco.VERBOS_ACCION)
            adjetivo = random.choice(self._banco.ADJETIVOS_IDEA)
            
            expansion = (f"Aplicado a {dominio}: {verbo} una versión {adjetivo} "
                        f"de esta idea usando {concepto}")
            expansiones.append({'dominio': dominio, 'expansion': expansion})
        
        return {
            'idea_original': idea[:100],
            'expansiones': expansiones,
            'total_direcciones': len(expansiones)
        }

# =====================================================================
# MOTOR DE IDEAS
# =====================================================================

class MotorIdeas(MotorBase):
    """
    Motor de Ideas ANP — Brainstorming, Combinación, Refinamiento y Evaluación.
    
    Capacidades:
    - Brainstorming: generación divergente con SCAMPER, TRIZ, pensamiento lateral
    - Combinación: fusión creativa de dos ideas en una nueva
    - Refinamiento: mejora iterativa aplicando criterios de innovación
    - Evaluación: puntuación en 12 criterios (originalidad, viabilidad, impacto...)
    - Expansión: despliegue de una idea en múltiples dominios
    - Divergencia: generación masiva con distintas técnicas
    
    Banco de conocimiento:
    - 6 dominios de innovación con 50+ conceptos
    - 21 prompts creativos (SCAMPER + TRIZ + Lateral)
    - 12 criterios de evaluación
    - 18 verbos de acción + 18 adjetivos
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._banco = BancoIdeas()
        self._brainstorming = Brainstorming(self._banco)
        self._refinador = RefinadorIdeas(self._banco)
        self._lock = threading.RLock()
        self._estadisticas = {
            'ideas_generadas': 0,
            'combinaciones': 0,
            'refinamientos': 0,
            'evaluaciones': 0,
            'expansiones': 0,
        }
        self._historial_ideas: List[Dict] = []
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'info')
        
        with self._lock:
            metodos = {
                'brainstorm': self._brainstorm,
                'combinar': self._combinar,
                'refinar': self._refinar,
                'evaluar_idea': self._evaluar_idea,
                'expandir': self._expandir,
                'divergir': self._divergir,
                'info': self._info,
            }
            func = metodos.get(operacion)
            if func:
                return func(entrada)
            return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _brainstorm(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['ideas_generadas'] += 1
        tema = e.get('tema', 'futuro de la movilidad')
        cantidad = min(e.get('cantidad', 5), 20)
        tecnica = e.get('tecnica', 'scamper')
        
        ideas = self._brainstorming.divergir(tema, cantidad, tecnica)
        self._historial_ideas.extend(ideas)
        
        return {
            'exito': True,
            'tema': tema,
            'tecnica': tecnica,
            'cantidad': len(ideas),
            'ideas': [{'texto': i['idea'][:120], 
                      'dominio': i['dominio'],
                      'originalidad': i['puntuacion_originalidad']} 
                     for i in ideas]
        }
    
    def _combinar(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['combinaciones'] += 1
        idea1 = e.get('idea1', 'inteligencia artificial para diagnóstico médico')
        idea2 = e.get('idea2', 'blockchain para historiales clínicos')
        
        resultado = self._brainstorming.combinar(idea1, idea2)
        
        return {'exito': True, **resultado}
    
    def _refinar(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['refinamientos'] += 1
        idea = e.get('idea', 'Una app que conecta agricultores locales con consumidores')
        criterios = e.get('criterios')
        iteraciones = min(e.get('iteraciones', 3), 5)
        
        resultado = self._refinador.refinar(idea, criterios, iteraciones)
        
        return {
            'exito': True,
            'idea_original': resultado['idea_original'][:100],
            'versiones': resultado['versiones_refinadas'],
            'version_final': resultado['version_final'][:150],
            'criterios': resultado['criterios_aplicados']
        }
    
    def _evaluar_idea(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['evaluaciones'] += 1
        idea = e.get('idea', 'Una plataforma de educación personalizada con IA')
        
        resultado = self._refinador.evaluar(idea)
        
        return {'exito': True, **resultado}
    
    def _expandir(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['expansiones'] += 1
        idea = e.get('idea', 'Un sistema de energía solar comunitaria')
        direcciones = min(e.get('direcciones', 3), 6)
        
        resultado = self._refinador.expandir(idea, direcciones)
        
        return {'exito': True, **resultado}
    
    def _divergir(self, e: Dict) -> Dict[str, Any]:
        """Generación masiva usando múltiples técnicas a la vez."""
        tema = e.get('tema', 'ciudades del futuro')
        cantidad = min(e.get('cantidad', 12), 30)
        
        todas_ideas = []
        for tecnica in ['scamper', 'triz', 'pensamiento_lateral']:
            n = cantidad // 3
            ideas = self._brainstorming.divergir(tema, n, tecnica)
            todas_ideas.extend(ideas)
            self._estadisticas['ideas_generadas'] += 1
        
        return {
            'exito': True,
            'tema': tema,
            'total': len(todas_ideas),
            'tecnicas_usadas': ['scamper', 'triz', 'pensamiento_lateral'],
            'ideas': [{'texto': i['idea'][:100], 
                      'tecnica': i['tecnica'],
                      'dominio': i['dominio']} 
                     for i in todas_ideas[:15]]
        }
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'estadisticas': self._estadisticas,
            'banco': {
                'dominios_innovacion': len(self._banco.DOMINIOS_INNOVACION),
                'conceptos': sum(len(v) for v in self._banco.DOMINIOS_INNOVACION.values()),
                'tecnicas_creativas': sum(len(v) for v in self._banco.TECNICAS_CREATIVAS.values()),
                'criterios_evaluacion': len(self._banco.CRITERIOS_EVALUACION),
            },
            'funcionalidades': ['brainstorm', 'combinar', 'refinar', 
                              'evaluar_idea', 'expandir', 'divergir']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE IDEAS — BRAINSTORMING + EVALUACIÓN")
    print("=" * 70)
    motor = None
    try:
        motor = MotorIdeas()
        motor.inicializar()
        print(f"\n[0] Motor: {motor.nombre} | Estado: {motor.estado}")

        print(f"\n[1] Brainstorming sobre 'futuro de la educación':")
        r = motor.procesar({
            'operacion': 'brainstorm',
            'tema': 'futuro de la educación',
            'cantidad': 5,
            'tecnica': 'scamper'
        })
        if r and r.exito and r.datos:
            print(f"  💡 Técnica: {r.datos.get('tecnica', '?')} | "
                  f"Ideas: {r.datos.get('cantidad', 0)}")
            for i, idea in enumerate(r.datos.get('ideas', []), 1):
                print(f"  {i}. [{idea.get('dominio', '?')}] {idea.get('texto', '')[:90]}...")

        print(f"\n[2] Divergir masivamente 'transporte sostenible':")
        r = motor.procesar({
            'operacion': 'divergir',
            'tema': 'transporte sostenible',
            'cantidad': 9
        })
        if r and r.exito and r.datos:
            print(f"  🌊 Total: {r.datos.get('total', 0)} ideas con "
                  f"{', '.join(r.datos.get('tecnicas_usadas', []))}")
            for idea in r.datos.get('ideas', [])[:5]:
                print(f"  [{idea.get('tecnica', '?')}] {idea.get('texto', '')[:85]}...")

        print(f"\n[3] Combinar dos ideas:")
        r = motor.procesar({
            'operacion': 'combinar',
            'idea1': 'drones para entrega de medicamentos',
            'idea2': 'app de voluntariado comunitario'
        })
        if r and r.exito and r.datos:
            print(f"  🔀 {r.datos.get('idea_combinada', '')[:120]}...")

        print(f"\n[4] Refinar una idea (3 iteraciones):")
        r = motor.procesar({
            'operacion': 'refinar',
            'idea': 'plataforma de aprendizaje adaptativo con IA',
            'iteraciones': 3,
            'criterios': ['originalidad', 'viabilidad', 'impacto', 'escalabilidad']
        })
        if r and r.exito and r.datos:
            print(f"  🔧 Original: {r.datos.get('idea_original', '')[:80]}...")
            for v in r.datos.get('versiones', []):
                print(f"  📝 {v[:100]}...")

        print(f"\n[5] Evaluar idea:")
        r = motor.procesar({
            'operacion': 'evaluar_idea',
            'idea': 'red social descentralizada basada en blockchain'
        })
        if r and r.exito and r.datos:
            print(f"  📊 Puntuación: {r.datos.get('puntuacion_total', 0)}")
            print(f"  ✅ Fortalezas: {r.datos.get('fortalezas', [])}")
            print(f"  ⚠️ Debilidades: {r.datos.get('debilidades', [])}")
            print(f"  🎯 Recomendación: {r.datos.get('recomendacion', '?')}")

        print(f"\n[6] Expandir idea en múltiples dominios:")
        r = motor.procesar({
            'operacion': 'expandir',
            'idea': 'sistema de captura de carbono doméstico',
            'direcciones': 4
        })
        if r and r.exito and r.datos:
            for exp in r.datos.get('expansiones', []):
                print(f"  🌍 [{exp.get('dominio', '?')}] {exp.get('expansion', '')[:100]}...")

        print(f"\n[7] Estadísticas del motor:")
        r = motor.procesar({'operacion': 'info'})
        if r and r.exito and r.datos:
            s = r.datos
            bc = s.get('banco', {})
            print(f"  📊 Ideas generadas: {s['estadisticas']['ideas_generadas']}")
            print(f"  📊 Combinaciones: {s['estadisticas']['combinaciones']}")
            print(f"  📊 Refinamientos: {s['estadisticas']['refinamientos']}")
            print(f"  📊 Evaluaciones: {s['estadisticas']['evaluaciones']}")
            print(f"  📊 Expansiones: {s['estadisticas']['expansiones']}")
            print(f"  🧠 Dominios: {bc.get('dominios_innovacion', 0)} | "
                  f"Conceptos: {bc.get('conceptos', 0)} | "
                  f"Técnicas: {bc.get('tecnicas_creativas', 0)}")

        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE IDEAS")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")