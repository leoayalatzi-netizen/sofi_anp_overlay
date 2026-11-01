#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Imaginación — Generación Creativa, Metáforas y Analogías
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Creatividad
# =====================================================================

import sys, time, math, random, traceback, threading, re
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
# BANCO DE CONOCIMIENTO CREATIVO
# =====================================================================

class BancoCreativo:
    """Banco de conceptos, metáforas, patrones poéticos y narrativos."""
    
    CONCEPTOS = {
        'naturaleza': ['mar', 'montaña', 'río', 'bosque', 'desierto', 'cielo', 'estrella', 'luna', 'sol',
                      'tormenta', 'amanecer', 'ocaso', 'viento', 'nieve', 'volcán', 'océano', 'selva', 'pradera',
                      'rayo', 'arcoíris', 'niebla', 'huracán', 'glaciar', 'cascada', 'isla', 'coral'],
        'emociones': ['amor', 'miedo', 'alegría', 'tristeza', 'ira', 'esperanza', 'nostalgia', 'paz',
                     'pasión', 'melancolía', 'euforia', 'ansiedad', 'serenidad', 'gratitud', 'soledad',
                     'ternura', 'desesperación', 'asombro', 'orgullo', 'culpa'],
        'tecnologia': ['algoritmo', 'red', 'código', 'circuito', 'señal', 'pulso', 'nodo', 'enlace',
                      'bit', 'qubit', 'matriz', 'vector', 'kernel', 'buffer', 'stack', 'pixel',
                      'sensor', 'antena', 'láser', 'robot', 'satélite', 'chip'],
        'universo': ['galaxia', 'nebulosa', 'agujero_negro', 'supernova', 'cometa', 'asteroide',
                    'órbita', 'gravedad', 'dimensión', 'singularidad', 'cosmos', 'entropía',
                    'fotón', 'electrón', 'quark', 'antimateria', 'multiverso', 'espacio_tiempo'],
        'abstractos': ['tiempo', 'infinito', 'caos', 'orden', 'silencio', 'eco', 'sombra', 'luz',
                      'destino', 'azar', 'memoria', 'sueño', 'verdad', 'mentira', 'belleza',
                      'eternidad', 'paradoja', 'esencia', 'vacío', 'plenitud'],
        'arte': ['poesía', 'música', 'pintura', 'danza', 'escultura', 'teatro', 'cine',
                'sinfonía', 'melodía', 'ritmo', 'armonía', 'color', 'trazo', 'lienzo',
                'mármol', 'nota', 'acorde', 'verso', 'prosa', 'drama'],
        'cuerpo': ['corazón', 'mente', 'alma', 'sangre', 'hueso', 'piel', 'ojos', 'manos',
                  'voz', 'aliento', 'pulmón', 'cerebro', 'nervio', 'músculo', 'latido'],
        'fuego': ['llama', 'chispa', 'brasas', 'incendio', 'hoguera', 'antorcha', 'ceniza',
                 'calor', 'lava', 'fénix', 'fragua', 'forja', 'fundición', 'crisol'],
    }
    
    PLANTILLAS_METAFORAS = [
        "{A} es un {B} que {accion} en {lugar}",
        "Como un {B} en {lugar}, así {A} {accion}",
        "Si {A} fuera un {B}, sería de {material}",
        "{A} y {B} bailan como {elementos} en {espacio}",
        "En el {lugar} de {A}, crece un {B} de {cualidad}",
        "{A} es el {B} del alma, {accion} sin descanso",
        "Entre {A} y {B} hay un puente de {material}",
        "Las raíces de {A} se hunden en el {B} de {concepto}",
    ]
    
    PLANTILLAS_POEMAS = [
        "En el {lugar} donde {A} encuentra a {B},\n{accion} el {elemento} de la {cualidad}.",
        "{A} susurra al oído de {B}\nmientras {elemento} cubre {lugar}.",
        "He visto {A} desnudarse ante {B}\ny el {lugar} se llenó de {cualidad}.",
        "No preguntes por {A} cuando {B} llora\n{accion} en el {lugar} del {elemento}.",
        "Como {A} que {accion} hacia {B},\nasí mi {elemento} busca tu {cualidad} eterna.",
    ]
    
    INICIOS_HISTORIA = [
        "En un {lugar} donde {A} y {B} coexisten en frágil equilibrio, un evento inesperado cambió todo:",
        "Nunca pensé que {A} pudiera convertirse en {B}. Todo comenzó cuando {accion} en {lugar}:",
        "El último {A} desapareció sin dejar rastro. Solo quedaba {B} y un misterio por resolver:",
        "Dicen que {A} guarda el secreto de {B}. Nadie se atrevía a {accion} hasta que ella llegó:",
        "Cuando {A} despertó aquella mañana en {lugar}, supo que algo era distinto. {B} le esperaba:",
    ]
    
    ADJETIVOS = ['brillante', 'oscuro', 'infinito', 'frágil', 'eterno', 'silencioso', 'profundo',
                'salvaje', 'sereno', 'turbulento', 'cristalino', 'misterioso', 'radiante',
                'sombrío', 'vibrante', 'durmiente', 'fugaz', 'inmenso', 'sutil', 'feroz']
    
    ACCIONES = ['baila', 'susurra', 'emerge', 'despierta', 'teje', 'fluye', 'arde', 'navega',
               'asciende', 'sueña', 'canta', 'forja', 'esculpe', 'derrama', 'abraza', 'persigue',
               'contempla', 'transforma', 'ilumina', 'devora', 'acaricia', 'rompe', 'renace']

# =====================================================================
# GENERADOR DE METÁFORAS
# =====================================================================

class GeneradorMetaforas:
    """Genera metáforas creativas combinando conceptos de dominios distintos."""
    
    def __init__(self, banco: BancoCreativo):
        self._banco = banco
        self._cache: Dict[str, List[str]] = {}
    
    def generar(self, concepto_base: str, cantidad: int = 5,
               estilo: str = 'poetico') -> List[Dict[str, Any]]:
        """Genera metáforas para un concepto base usando dominios lejanos."""
        dominios = list(self._banco.CONCEPTOS.keys())
        resultados = []
        
        for _ in range(cantidad):
            dominio = random.choice([d for d in dominios 
                                    if not any(c in concepto_base.lower() 
                                              for c in self._banco.CONCEPTOS[d])])
            B = random.choice(self._banco.CONCEPTOS[dominio])
            plantilla = random.choice(self._banco.PLANTILLAS_METAFORAS)
            
            metafora = plantilla.format(
                A=concepto_base,
                B=B,
                accion=random.choice(self._banco.ACCIONES),
                lugar=random.choice(self._banco.CONCEPTOS.get('naturaleza', ['universo'])),
                material=random.choice(['cristal', 'seda', 'fuego', 'hielo', 'sombra', 'luz', 
                                       'vapor', 'mármol', 'oro', 'plata']),
                elementos=random.choice(self._banco.CONCEPTOS.get('universo', ['estrellas'])),
                espacio=random.choice(['cosmos', 'abismo', 'horizonte', 'infinito', ' Firmamento']),
                cualidad=random.choice(self._banco.ADJETIVOS),
                concepto=random.choice(self._banco.CONCEPTOS.get('abstractos', ['eternidad'])),
            )
            
            resultados.append({
                'metafora': metafora,
                'dominio_origen': concepto_base,
                'dominio_destino': dominio,
                'elemento_puente': B,
                'estilo': estilo
            })
        
        return resultados
    
    def generar_analogia(self, A: str, B: str, C: str, 
                        cantidad: int = 3) -> List[Dict[str, Any]]:
        """Genera analogías: A es a B como C es a ?"""
        dominios = list(self._banco.CONCEPTOS.keys())
        resultados = []
        
        for _ in range(cantidad):
            dominio = random.choice([d for d in dominios 
                                    if not any(c in (A+B+C).lower() 
                                              for c in self._banco.CONCEPTOS[d])])
            D = random.choice(self._banco.CONCEPTOS[dominio])
            
            plantillas = [
                f"Así como {A} {random.choice(self._banco.ACCIONES)} a {B}, "
                f"{C} {random.choice(self._banco.ACCIONES)} a {D}",
                f"Si {A} es el {B} del alma, entonces {C} es la {D} del pensamiento",
                f"{A} y {B} son como {C} y {D}: dos caras de una misma moneda",
                f"La relación entre {A} y {B} es como la danza entre {C} y {D}",
            ]
            
            resultados.append({
                'analogia': random.choice(plantillas),
                'terminos': (A, B, C, D),
                'dominio_puente': dominio
            })
        
        return resultados

# =====================================================================
# GENERADOR POÉTICO
# =====================================================================

class GeneradorPoetico:
    """Genera poemas y textos literarios con estructuras variables."""
    
    def __init__(self, banco: BancoCreativo):
        self._banco = banco
    
    def poema(self, tema: str, versos: int = 4, 
             estilo: str = 'libre') -> Dict[str, Any]:
        """Genera un poema sobre un tema dado."""
        A = tema
        B = random.choice(sum(self._banco.CONCEPTOS.values(), []))
        
        lineas = []
        for _ in range(versos):
            plantilla = random.choice(self._banco.PLANTILLAS_POEMAS)
            linea = plantilla.format(
                A=A, B=B,
                accion=random.choice(self._banco.ACCIONES),
                lugar=random.choice(self._banco.CONCEPTOS['naturaleza']),
                elemento=random.choice(self._banco.CONCEPTOS['naturaleza'] + 
                                      self._banco.CONCEPTOS['universo']),
                cualidad=random.choice(self._banco.ADJETIVOS),
            )
            lineas.append(linea)
            B = random.choice(sum(self._banco.CONCEPTOS.values(), []))
        
        poema_completo = '\n'.join(lineas)
        
        metrica = {
            'versos': len(lineas),
            'palabras': len(poema_completo.split()),
            'estilo': estilo,
            'tema': tema
        }
        
        return {'poema': poema_completo, 'metrica': metrica}
    
    def micro_historia(self, tema: str, longitud: int = 3) -> Dict[str, Any]:
        """Genera una micro-historia creativa."""
        A = tema
        B = random.choice(sum(self._banco.CONCEPTOS.values(), []))
        inicio = random.choice(self._banco.INICIOS_HISTORIA).format(
            A=A, B=B,
            accion=random.choice(self._banco.ACCIONES),
            lugar=random.choice(self._banco.CONCEPTOS['naturaleza']),
        )
        
        desarrollos = [
            f"Descubrió que {A} guardaba relación con {random.choice(self._banco.CONCEPTOS['abstractos'])}.",
            f"El {B} reveló su verdadera naturaleza: {random.choice(self._banco.ADJETIVOS)} y "
            f"{random.choice(self._banco.ADJETIVOS)}.",
            f"Nadie imaginó que {A} y {B} compartieran el mismo {random.choice(self._banco.CONCEPTOS['abstractos'])}.",
            f"La solución llegó como un {random.choice(self._banco.CONCEPTOS['naturaleza'])}: "
            f"{random.choice(self._banco.ADJETIVOS)} e inesperada.",
        ]
        
        finales = [
            f"Y así, {A} encontró su lugar junto a {B}.",
            f"Desde entonces, {A} nunca volvió a ser lo mismo.",
            f"El misterio de {B} quedó resuelto, pero {A} guardó el secreto para siempre.",
            f"{A} comprendió que {B} era solo el comienzo de algo más {random.choice(self._banco.ADJETIVOS)}.",
        ]
        
        historia = f"{inicio}\n\n{random.choice(desarrollos)}\n\n{random.choice(finales)}"
        
        return {'historia': historia, 'tema': tema, 'palabras': len(historia.split())}

# =====================================================================
# MOTOR DE IMAGINACIÓN
# =====================================================================

class MotorImaginacion(MotorBase):
    """
    Motor de Imaginación ANP — Generación Creativa de Metáforas, Poesía e Historias.
    
    Capacidades:
    - Metáforas: combinación de dominios lejanos con plantillas poéticas
    - Analogías: A es a B como C es a D con salto creativo
    - Poemas: verso libre con imágenes sensoriales
    - Micro-historias: narrativa mínima con estructura inicio-nudo-desenlace
    - Sueños: conceptos surrealistas combinados al azar
    - Visualizaciones: descripciones sensoriales de conceptos abstractos
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._banco = BancoCreativo()
        self._metaforas = GeneradorMetaforas(self._banco)
        self._poetico = GeneradorPoetico(self._banco)
        self._lock = threading.RLock()
        self._estadisticas = {
            'metaforas_generadas': 0,
            'poemas_generados': 0,
            'historias_generadas': 0,
            'analogias_generadas': 0,
        }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'info')
        
        with self._lock:
            metodos = {
                'imaginar': self._imaginar,
                'metafora': self._crear_metafora,
                'analogia': self._crear_analogia,
                'poema': self._crear_poema,
                'historia': self._crear_historia,
                'sonar': self._sonar,
                'info': self._info,
            }
            func = metodos.get(operacion)
            if func:
                return func(entrada)
            return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _imaginar(self, e: Dict) -> Dict[str, Any]:
        """Genera una visualización creativa de un concepto abstracto."""
        concepto = e.get('concepto', 'libertad')
        
        visualizaciones = [
            f"Imagina {concepto} como un {random.choice(self._banco.CONCEPTOS['naturaleza'])} "
            f"que {random.choice(self._banco.ACCIONES)} en el {random.choice(self._banco.CONCEPTOS['universo'])}.",
            
            f"Si pudieras tocar {concepto}, sentirías la textura del "
            f"{random.choice(['cristal', 'seda', 'vapor', 'fuego_líquido', 'mármol_pulido'])} "
            f"mientras {random.choice(self._banco.ACCIONES)} entre tus dedos.",
            
            f"{concepto} tiene el color del {random.choice(['amanecer', 'ocaso', 'mar_profundo', 
            'aurora_boreal', 'eclipse'])}, y suena como {random.choice(['un violín lejano', 
            'el viento entre hojas', 'un latido cósmico', 'silencio absoluto'])}.",
            
            f"El aroma de {concepto} recuerda a {random.choice(['tierra mojada', 'sal marina',
            'flores nocturnas', 'ozono tras la tormenta', 'incienso antiguo'])}.",
        ]
        
        return {
            'exito': True,
            'concepto': concepto,
            'visualizacion': random.choice(visualizaciones),
            'tipo': 'visualizacion_sensorial'
        }
    
    def _crear_metafora(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['metaforas_generadas'] += 1
        concepto = e.get('concepto', 'conocimiento')
        cantidad = min(e.get('cantidad', 3), 10)
        estilo = e.get('estilo', 'poetico')
        
        metaforas = self._metaforas.generar(concepto, cantidad, estilo)
        
        return {
            'exito': True,
            'concepto': concepto,
            'cantidad': len(metaforas),
            'metaforas': [m['metafora'] for m in metaforas],
            'detalle': [{'dominio': m['dominio_destino'], 
                        'puente': m['elemento_puente']} for m in metaforas]
        }
    
    def _crear_analogia(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['analogias_generadas'] += 1
        A = e.get('a', 'conocimiento')
        B = e.get('b', 'luz')
        C = e.get('c', 'ignorancia')
        
        analogias = self._metaforas.generar_analogia(A, B, C, 3)
        
        return {
            'exito': True,
            'estructura': f'{A} : {B} :: {C} : ?',
            'analogias': [a['analogia'] for a in analogias],
            'terminos_puente': [a['terminos'][3] for a in analogias]
        }
    
    def _crear_poema(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['poemas_generados'] += 1
        tema = e.get('tema', 'universo')
        versos = min(e.get('versos', 4), 12)
        estilo = e.get('estilo', 'libre')
        
        resultado = self._poetico.poema(tema, versos, estilo)
        
        return {
            'exito': True,
            'poema': resultado['poema'],
            'metrica': resultado['metrica']
        }
    
    def _crear_historia(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['historias_generadas'] += 1
        tema = e.get('tema', 'descubrimiento')
        
        resultado = self._poetico.micro_historia(tema)
        
        return {
            'exito': True,
            'historia': resultado['historia'],
            'tema': tema,
            'palabras': resultado['palabras']
        }
    
    def _sonar(self, e: Dict) -> Dict[str, Any]:
        """Genera una ensoñación surrealista."""
        elementos = []
        for _ in range(4):
            dominio = random.choice(list(self._banco.CONCEPTOS.keys()))
            elementos.append(random.choice(self._banco.CONCEPTOS[dominio]))
        
        sueno = (
            f"En el {elementos[0]} de {elementos[1]}, "
            f"donde los {elementos[2]} {random.choice(self._banco.ACCIONES)} "
            f"entre {elementos[3]} {random.choice(self._banco.ADJETIVOS)}, "
            f"un {random.choice(self._banco.CONCEPTOS['naturaleza'])} soñó que era "
            f"{random.choice(self._banco.CONCEPTOS['abstractos'])}."
        )
        
        return {'exito': True, 'sueno': sueno, 'elementos': elementos}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'estadisticas': self._estadisticas,
            'banco_creativo': {
                'dominios': len(self._banco.CONCEPTOS),
                'conceptos_totales': sum(len(v) for v in self._banco.CONCEPTOS.values()),
                'plantillas_metaforas': len(self._banco.PLANTILLAS_METAFORAS),
                'plantillas_poemas': len(self._banco.PLANTILLAS_POEMAS),
                'inicios_historia': len(self._banco.INICIOS_HISTORIA),
            },
            'funcionalidades': ['imaginar', 'metafora', 'analogia', 'poema', 'historia', 'sonar']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE IMAGINACIÓN — METÁFORAS + POESÍA")
    print("=" * 70)
    motor = None
    try:
        motor = MotorImaginacion()
        motor.inicializar()
        print(f"\n[0] Motor: {motor.nombre} | Estado: {motor.estado}")
        
        print(f"\n[1] Visualización sensorial de 'libertad':")
        for _ in range(2):
            r = motor.procesar({'operacion': 'imaginar', 'concepto': 'libertad'})
            if r and r.exito and r.datos:
                print(f"  💭 {r.datos['visualizacion'][:100]}...")

        print(f"\n[2] Metáforas sobre 'conocimiento':")
        r = motor.procesar({'operacion': 'metafora', 'concepto': 'conocimiento', 'cantidad': 3})
        if r and r.exito and r.datos:
            for i, m in enumerate(r.datos.get('metaforas', []), 1):
                print(f"  🌟 {i}. {m[:90]}...")

        print(f"\n[3] Analogía: conocimiento : luz :: ignorancia : ?")
        r = motor.procesar({'operacion': 'analogia', 'a': 'conocimiento', 
                           'b': 'luz', 'c': 'ignorancia'})
        if r and r.exito and r.datos:
            for a in r.datos.get('analogias', []):
                print(f"  🔗 {a[:90]}...")

        print(f"\n[4] Poema sobre 'silencio':")
        r = motor.procesar({'operacion': 'poema', 'tema': 'silencio', 'versos': 4})
        if r and r.exito and r.datos:
            print(f"  📝 ")
            for linea in r.datos.get('poema', '').split('\n'):
                print(f"    {linea}")
            m = r.datos.get('metrica', {})
            print(f"  📏 {m.get('versos', 0)} versos | {m.get('palabras', 0)} palabras | "
                  f"Estilo: {m.get('estilo', '?')}")

        print(f"\n[5] Micro-historia sobre 'descubrimiento':")
        r = motor.procesar({'operacion': 'historia', 'tema': 'descubrimiento'})
        if r and r.exito and r.datos:
            for linea in r.datos.get('historia', '').split('\n'):
                if linea.strip():
                    print(f"  📖 {linea.strip()[:100]}")
        
        print(f"\n[6] Ensueño surrealista:")
        r = motor.procesar({'operacion': 'sonar'})
        if r and r.exito and r.datos:
            print(f"  🌙 {r.datos['sueno'][:120]}...")
            print(f"  🧩 Elementos: {r.datos['elementos']}")

        print(f"\n[7] Estadísticas del motor:")
        r = motor.procesar({'operacion': 'info'})
        if r and r.exito and r.datos:
            s = r.datos
            bc = s.get('banco_creativo', {})
            print(f"  📊 Metáforas: {s['estadisticas']['metaforas_generadas']}")
            print(f"  📊 Poemas: {s['estadisticas']['poemas_generados']}")
            print(f"  📊 Historias: {s['estadisticas']['historias_generadas']}")
            print(f"  📊 Dominios: {bc.get('dominios', 0)} | "
                  f"Conceptos: {bc.get('conceptos_totales', 0)} | "
                  f"Plantillas: {bc.get('plantillas_metaforas', 0)}")

        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE IMAGINACIÓN")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")
           