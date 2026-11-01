#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Física — Mecánica, Termodinámica, Electromagnetismo y más
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Resolución
# =====================================================================

import sys, time, math, traceback, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import defaultdict
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
# CONSTANTES FÍSICAS (CODATA 2018)
# =====================================================================

class ConstantesFisicas:
    """Constantes físicas fundamentales CODATA 2018."""
    G = 6.67430e-11          # Constante gravitacional (N·m²/kg²)
    c = 299792458.0           # Velocidad de la luz (m/s)
    h = 6.62607015e-34        # Constante de Planck (J·s)
    h_bar = 1.054571817e-34   # Constante de Planck reducida (J·s)
    e_carga = 1.602176634e-19 # Carga elemental (C)
    k_B = 1.380649e-23        # Constante de Boltzmann (J/K)
    N_A = 6.02214076e23       # Número de Avogadro (mol⁻¹)
    epsilon_0 = 8.8541878128e-12  # Permitividad del vacío (F/m)
    mu_0 = 1.25663706212e-6       # Permeabilidad del vacío (N/A²)
    R_gas = 8.314462618        # Constante universal de gases (J/(mol·K))
    sigma_SB = 5.670374419e-8  # Constante Stefan-Boltzmann (W/(m²·K⁴))
    m_e = 9.1093837015e-31     # Masa del electrón (kg)
    m_p = 1.67262192369e-27    # Masa del protón (kg)
    m_n = 1.67492749804e-27    # Masa del neutrón (kg)
    g_tierra = 9.80665          # Aceleración gravitatoria estándar (m/s²)
    R_tierra = 6371000.0        # Radio medio terrestre (m)
    M_tierra = 5.9722e24        # Masa de la Tierra (kg)
    M_sol = 1.98847e30          # Masa del Sol (kg)
    UA = 1.495978707e11         # Unidad Astronómica (m)
    pc = 3.085677581e16         # Pársec (m)
    ly = 9.4607304725808e15     # Año luz (m)

# =====================================================================
# CINEMÁTICA
# =====================================================================

class Cinematica:
    """Cinemática: MRU, MRUV, tiro parabólico, movimiento circular."""
    
    @staticmethod
    def mru(posicion_inicial: float, velocidad: float, tiempo: float) -> Dict[str, float]:
        pos_final = posicion_inicial + velocidad * tiempo
        return {'posicion_final': pos_final, 'distancia_recorrida': abs(velocidad * tiempo),
                'velocidad': velocidad, 'tiempo': tiempo}
    
    @staticmethod
    def mruv(x0: float, v0: float, a: float, t: float) -> Dict[str, float]:
        vf = v0 + a * t
        xf = x0 + v0 * t + 0.5 * a * t**2
        return {'posicion_final': xf, 'velocidad_final': vf, 
                'aceleracion': a, 'tiempo': t,
                'velocidad_media': (v0 + vf) / 2}
    
    @staticmethod
    def tiro_parabolico(v0: float, angulo_grados: float, 
                        y0: float = 0.0, g: float = 9.80665) -> Dict[str, float]:
        ang_rad = math.radians(abs(angulo_grados))
        v0x = v0 * math.cos(ang_rad)
        v0y = v0 * math.sin(ang_rad)
        t_vuelo = (v0y + math.sqrt(v0y**2 + 2*g*y0)) / g
        alcance = v0x * t_vuelo
        altura_max = y0 + v0y**2 / (2*g)
        return {'alcance': alcance, 'altura_maxima': altura_max, 
                'tiempo_vuelo': t_vuelo, 'v0x': v0x, 'v0y': v0y}
    
    @staticmethod
    def movimiento_circular(radio: float, frecuencia: float = None,
                           periodo: float = None) -> Dict[str, float]:
        if frecuencia:
            T = 1.0 / frecuencia if frecuencia > 0 else float('inf')
        elif periodo and periodo > 0:
            T = periodo
        else:
            return {'error': 'Se requiere frecuencia o periodo'}
        omega = 2 * math.pi / T
        v = omega * radio
        ac = omega**2 * radio
        return {'radio': radio, 'periodo': T, 'frecuencia': 1/T,
                'velocidad_angular': omega, 'velocidad_tangencial': v,
                'aceleracion_centripeta': ac}

# =====================================================================
# DINÁMICA Y MECÁNICA
# =====================================================================

class Dinamica:
    """Dinámica: leyes de Newton, trabajo, energía, momento."""
    
    @staticmethod
    def fuerza(masa: float, aceleracion: float) -> Dict[str, float]:
        F = masa * aceleracion
        return {'fuerza': F, 'masa': masa, 'aceleracion': aceleracion}
    
    @staticmethod
    def trabajo(fuerza: float, distancia: float, angulo_grados: float = 0.0) -> float:
        ang = math.radians(angulo_grados)
        return fuerza * distancia * math.cos(ang)
    
    @staticmethod
    def energia_cinetica(masa: float, velocidad: float) -> float:
        return 0.5 * masa * velocidad**2
    
    @staticmethod
    def energia_potencial_gravitatoria(masa: float, altura: float, 
                                       g: float = 9.80665) -> float:
        return masa * g * altura
    
    @staticmethod
    def momento_lineal(masa: float, velocidad: float) -> float:
        return masa * velocidad
    
    @staticmethod
    def colision_elastica(m1: float, v1i: float, m2: float, v2i: float) -> Dict[str, float]:
        v1f = (m1 - m2) / (m1 + m2) * v1i + (2*m2) / (m1 + m2) * v2i
        v2f = (2*m1) / (m1 + m2) * v1i + (m2 - m1) / (m1 + m2) * v2i
        return {'velocidad_final_1': v1f, 'velocidad_final_2': v2f,
                'momento_inicial': m1*v1i + m2*v2i,
                'momento_final': m1*v1f + m2*v2f}
    
    @staticmethod
    def fuerza_gravitatoria(m1: float, m2: float, distancia: float) -> float:
        return ConstantesFisicas.G * m1 * m2 / distancia**2
    
    @staticmethod
    def velocidad_escape(masa_cuerpo: float, radio_cuerpo: float) -> float:
        return math.sqrt(2 * ConstantesFisicas.G * masa_cuerpo / radio_cuerpo)
    
    @staticmethod
    def pendulo_simple(longitud: float, g: float = 9.80665, 
                       amplitud_rad: float = 0.1) -> Dict[str, float]:
        T = 2 * math.pi * math.sqrt(longitud / g)
        T_exacto = T * (1 + (1/16)*amplitud_rad**2 + (11/3072)*amplitud_rad**4)
        return {'periodo_aproximado': T, 'periodo_exacto': T_exacto,
                'frecuencia': 1/T_exacto}

# =====================================================================
# TERMODINÁMICA
# =====================================================================

class Termodinamica:
    """Termodinámica: gases ideales, calor, entropía, ciclos."""
    
    @staticmethod
    def gas_ideal(presion: float = None, volumen: float = None, 
                  n_moles: float = None, temperatura: float = None) -> Dict[str, float]:
        R = ConstantesFisicas.R_gas
        if presion is None and volumen and n_moles and temperatura:
            P = n_moles * R * temperatura / volumen
            return {'presion': P, 'volumen': volumen, 'n_moles': n_moles, 'temperatura': temperatura}
        elif volumen is None and presion and n_moles and temperatura:
            V = n_moles * R * temperatura / presion
            return {'presion': presion, 'volumen': V, 'n_moles': n_moles, 'temperatura': temperatura}
        elif temperatura is None and presion and volumen and n_moles:
            T = presion * volumen / (n_moles * R)
            return {'presion': presion, 'volumen': volumen, 'n_moles': n_moles, 'temperatura': T}
        return {'error': 'Proporcione 3 de 4 variables'}
    
    @staticmethod
    def calorimetria(masa: float, calor_especifico: float, delta_T: float) -> float:
        return masa * calor_especifico * delta_T
    
    @staticmethod
    def eficiencia_carnot(T_caliente: float, T_fria: float) -> float:
        return 1.0 - T_fria / T_caliente
    
    @staticmethod
    def expansion_adiabatica(V1: float, P1: float, V2: float, 
                            gamma: float = 1.4) -> Dict[str, float]:
        P2 = P1 * (V1 / V2)**gamma
        T2_T1 = (V1 / V2)**(gamma - 1)
        trabajo = (P1*V1 - P2*V2) / (gamma - 1)
        return {'presion_final': P2, 'relacion_temperaturas': T2_T1, 'trabajo': trabajo}
    
    @staticmethod
    def ley_stefan_boltzmann(temperatura: float, emisividad: float = 1.0) -> float:
        return emisividad * ConstantesFisicas.sigma_SB * temperatura**4

# =====================================================================
# ELECTROMAGNETISMO
# =====================================================================

class Electromagnetismo:
    """Electromagnetismo: Coulomb, campo eléctrico, circuitos, ondas."""
    
    @staticmethod
    def ley_coulomb(q1: float, q2: float, distancia: float) -> Dict[str, float]:
        k = 1.0 / (4 * math.pi * ConstantesFisicas.epsilon_0)
        F = k * abs(q1 * q2) / distancia**2
        return {'fuerza': F, 'constante_k': k, 'atractiva': q1*q2 < 0}
    
    @staticmethod
    def campo_electrico(carga: float, distancia: float) -> float:
        k = 1.0 / (4 * math.pi * ConstantesFisicas.epsilon_0)
        return k * abs(carga) / distancia**2
    
    @staticmethod
    def potencial_electrico(carga: float, distancia: float) -> float:
        k = 1.0 / (4 * math.pi * ConstantesFisicas.epsilon_0)
        return k * carga / distancia
    
    @staticmethod
    def ley_ohm(voltaje: float = None, corriente: float = None, 
               resistencia: float = None) -> Dict[str, float]:
        if voltaje is None:
            V = corriente * resistencia
        elif corriente is None:
            I = voltaje / resistencia if resistencia != 0 else float('inf')
        else:
            R = voltaje / corriente if corriente != 0 else float('inf')
        return {'voltaje': voltaje if voltaje else V, 
                'corriente': corriente if corriente else I,
                'resistencia': resistencia if resistencia else R}
    
    @staticmethod
    def potencia_electrica(voltaje: float, corriente: float) -> Dict[str, float]:
        return {'potencia': voltaje * corriente, 'voltaje': voltaje, 'corriente': corriente}
    
    @staticmethod
    def resistencias_serie(*resistencias: float) -> float:
        return sum(resistencias)
    
    @staticmethod
    def resistencias_paralelo(*resistencias: float) -> float:
        if 0 in resistencias:
            return 0.0
        return 1.0 / sum(1.0/r for r in resistencias if r != 0)
    
    @staticmethod
    def fuerza_lorentz(q: float, v: float, B: float, 
                       angulo_grados: float = 90.0) -> float:
        return abs(q) * v * B * math.sin(math.radians(angulo_grados))
    
    @staticmethod
    def frecuencia_ciclotron(q: float, B: float, masa: float) -> float:
        return abs(q) * B / (2 * math.pi * masa)

# =====================================================================
# ÓPTICA Y ONDAS
# =====================================================================

class OpticaOndas:
    """Óptica y ondas: refracción, difracción, efecto Doppler."""
    
    @staticmethod
    def ley_snell(n1: float, n2: float, angulo1_grados: float) -> Dict[str, float]:
        a1 = math.radians(angulo1_grados)
        sin_a2 = n1 * math.sin(a1) / n2
        if abs(sin_a2) > 1:
            return {'reflexion_total': True, 'angulo_critico': 
                   math.degrees(math.asin(n2/n1)) if n1 > n2 else 0}
        a2 = math.asin(sin_a2)
        return {'angulo_2_grados': math.degrees(a2), 'reflexion_total': False}
    
    @staticmethod
    def ecuacion_onda(amplitud: float, frecuencia: float, 
                     longitud_onda: float = None, 
                     velocidad: float = None) -> Dict[str, float]:
        if velocidad is None and longitud_onda:
            v = frecuencia * longitud_onda
        elif longitud_onda is None and velocidad:
            l = velocidad / frecuencia
        return {'amplitud': amplitud, 'frecuencia': frecuencia,
                'longitud_onda': longitud_onda if longitud_onda else l,
                'velocidad': velocidad if velocidad else v,
                'periodo': 1.0/frecuencia}
    
    @staticmethod
    def efecto_doppler(f_emisor: float, v_emisor: float, v_receptor: float,
                      v_sonido: float = 343.0) -> float:
        return f_emisor * (v_sonido + v_receptor) / (v_sonido + v_emisor)
    
    @staticmethod
    def intensidad_sonido(potencia: float, distancia: float) -> float:
        return potencia / (4 * math.pi * distancia**2)
    
    @staticmethod
    def nivel_sonoro(intensidad: float, 
                    I0: float = 1e-12) -> float:
        return 10 * math.log10(intensidad / I0) if intensidad > 0 else 0

# =====================================================================
# MOTOR DE FÍSICA
# =====================================================================

class MotorFisica(MotorBase):
    """
    Motor de Física ANP — Mecánica, Termodinámica, Electromagnetismo, Óptica.
    
    Capacidades:
    - Cinemática: MRU, MRUV, tiro parabólico, movimiento circular
    - Dinámica: Leyes de Newton, trabajo, energía, colisiones, gravitación
    - Termodinámica: Gases ideales, calor, ciclos, radiación
    - Electromagnetismo: Coulomb, Ohm, circuitos, Lorentz
    - Óptica y Ondas: Snell, Doppler, sonido, ecuación de onda
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._cinematica = Cinematica()
        self._dinamica = Dinamica()
        self._termodinamica = Termodinamica()
        self._electromagnetismo = Electromagnetismo()
        self._optica = OpticaOndas()
        self._constantes = ConstantesFisicas()
        self._lock = threading.RLock()
        self._estadisticas = {
            'calculos_realizados': 0,
            'cinematica': 0, 'dinamica': 0,
            'termodinamica': 0, 'electromagnetismo': 0, 'optica': 0,
        }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'info')
        
        with self._lock:
            metodos = {
                'cinematica': self._calc_cinematica,
                'dinamica': self._calc_dinamica,
                'termodinamica': self._calc_termodinamica,
                'electromagnetismo': self._calc_electromagnetismo,
                'optica': self._calc_optica,
                'constantes': self._constantes_fisicas,
                'info': self._info,
            }
            func = metodos.get(operacion)
            if func:
                self._estadisticas['calculos_realizados'] += 1
                return func(entrada)
            return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _calc_cinematica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['cinematica'] += 1
        subop = e.get('suboperacion', 'mru')
        if subop == 'mru':
            return {'exito': True, **self._cinematica.mru(
                e.get('x0', 0), e.get('v', 1), e.get('t', 1))}
        elif subop == 'mruv':
            return {'exito': True, **self._cinematica.mruv(
                e.get('x0', 0), e.get('v0', 0), e.get('a', 1), e.get('t', 1))}
        elif subop == 'parabolico':
            return {'exito': True, **self._cinematica.tiro_parabolico(
                e.get('v0', 10), e.get('angulo', 45), e.get('y0', 0), e.get('g', 9.80665))}
        elif subop == 'circular':
            return {'exito': True, **self._cinematica.movimiento_circular(
                e.get('radio', 1), e.get('frecuencia'), e.get('periodo'))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_dinamica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['dinamica'] += 1
        subop = e.get('suboperacion', 'fuerza')
        if subop == 'fuerza':
            return {'exito': True, **self._dinamica.fuerza(
                e.get('masa', 1), e.get('aceleracion', 1))}
        elif subop == 'trabajo':
            return {'exito': True, 'trabajo': self._dinamica.trabajo(
                e.get('fuerza', 1), e.get('distancia', 1), e.get('angulo', 0))}
        elif subop == 'energia_cinetica':
            return {'exito': True, 'energia_cinetica': self._dinamica.energia_cinetica(
                e.get('masa', 1), e.get('velocidad', 1))}
        elif subop == 'energia_potencial':
            return {'exito': True, 'energia_potencial': self._dinamica.energia_potencial_gravitatoria(
                e.get('masa', 1), e.get('altura', 1), e.get('g', 9.80665))}
        elif subop == 'colision':
            return {'exito': True, **self._dinamica.colision_elastica(
                e.get('m1', 1), e.get('v1i', 1), e.get('m2', 1), e.get('v2i', 0))}
        elif subop == 'gravitacion':
            return {'exito': True, 'fuerza': self._dinamica.fuerza_gravitatoria(
                e.get('m1', 1), e.get('m2', 1), e.get('distancia', 1))}
        elif subop == 'velocidad_escape':
            return {'exito': True, 'velocidad_escape': self._dinamica.velocidad_escape(
                e.get('masa', 5.972e24), e.get('radio', 6371000))}
        elif subop == 'pendulo':
            return {'exito': True, **self._dinamica.pendulo_simple(
                e.get('longitud', 1), e.get('g', 9.80665), e.get('amplitud', 0.1))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_termodinamica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['termodinamica'] += 1
        subop = e.get('suboperacion', 'gas_ideal')
        if subop == 'gas_ideal':
            return {'exito': True, **self._termodinamica.gas_ideal(
                e.get('presion'), e.get('volumen'), e.get('n_moles'), e.get('temperatura'))}
        elif subop == 'calor':
            return {'exito': True, 'calor': self._termodinamica.calorimetria(
                e.get('masa', 1), e.get('calor_especifico', 4186), e.get('delta_T', 1))}
        elif subop == 'carnot':
            return {'exito': True, 'eficiencia': self._termodinamica.eficiencia_carnot(
                e.get('T_caliente', 500), e.get('T_fria', 300))}
        elif subop == 'stefan_boltzmann':
            return {'exito': True, 'potencia_radiacion': self._termodinamica.ley_stefan_boltzmann(
                e.get('temperatura', 300), e.get('emisividad', 1.0))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_electromagnetismo(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['electromagnetismo'] += 1
        subop = e.get('suboperacion', 'coulomb')
        if subop == 'coulomb':
            return {'exito': True, **self._electromagnetismo.ley_coulomb(
                e.get('q1', 1e-6), e.get('q2', 1e-6), e.get('distancia', 1))}
        elif subop == 'ohm':
            return {'exito': True, **self._electromagnetismo.ley_ohm(
                e.get('voltaje'), e.get('corriente'), e.get('resistencia'))}
        elif subop == 'potencia':
            return {'exito': True, **self._electromagnetismo.potencia_electrica(
                e.get('voltaje', 12), e.get('corriente', 1))}
        elif subop == 'resistencia_serie':
            resistencias = e.get('resistencias', [100, 200, 300])
            return {'exito': True, 'resistencia_total': 
                   self._electromagnetismo.resistencias_serie(*resistencias)}
        elif subop == 'resistencia_paralelo':
            resistencias = e.get('resistencias', [100, 200])
            return {'exito': True, 'resistencia_total':
                   self._electromagnetismo.resistencias_paralelo(*resistencias)}
        elif subop == 'lorentz':
            return {'exito': True, 'fuerza': self._electromagnetismo.fuerza_lorentz(
                e.get('q', 1.6e-19), e.get('v', 1e6), e.get('B', 1), e.get('angulo', 90))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_optica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['optica'] += 1
        subop = e.get('suboperacion', 'snell')
        if subop == 'snell':
            return {'exito': True, **self._optica.ley_snell(
                e.get('n1', 1.0), e.get('n2', 1.33), e.get('angulo1', 30))}
        elif subop == 'onda':
            return {'exito': True, **self._optica.ecuacion_onda(
                e.get('amplitud', 1), e.get('frecuencia', 440), 
                e.get('longitud_onda'), e.get('velocidad', 343))}
        elif subop == 'doppler':
            return {'exito': True, 'frecuencia_observada': self._optica.efecto_doppler(
                e.get('f_emisor', 440), e.get('v_emisor', 0), 
                e.get('v_receptor', 34.3), e.get('v_sonido', 343))}
        elif subop == 'nivel_sonoro':
            return {'exito': True, 'decibeles': self._optica.nivel_sonoro(
                e.get('intensidad', 1e-6))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _constantes_fisicas(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'constantes': {
                'G': self._constantes.G, 'c': self._constantes.c,
                'h': self._constantes.h, 'e_carga': self._constantes.e_carga,
                'k_B': self._constantes.k_B, 'N_A': self._constantes.N_A,
                'epsilon_0': self._constantes.epsilon_0, 'mu_0': self._constantes.mu_0,
                'R_gas': self._constantes.R_gas, 'g_tierra': self._constantes.g_tierra,
                'M_tierra': self._constantes.M_tierra, 'R_tierra': self._constantes.R_tierra,
                'M_sol': self._constantes.M_sol, 'UA': self._constantes.UA,
                'pc': self._constantes.pc, 'ly': self._constantes.ly,
                'sigma_SB': self._constantes.sigma_SB,
            }
        }
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'numpy': NUMPY_DISPONIBLE,
            'estadisticas': self._estadisticas,
            'areas': ['cinematica', 'dinamica', 'termodinamica', 
                     'electromagnetismo', 'optica_ondas'],
            'funcionalidades': ['mru', 'mruv', 'tiro_parabolico', 'circular',
                              'newton', 'energia', 'colisiones', 'gravitacion',
                              'gas_ideal', 'calor', 'carnot', 'radiacion',
                              'coulomb', 'ohm', 'circuitos', 'lorentz',
                              'snell', 'doppler', 'sonido', 'onda']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE FÍSICA — MECÁNICA + TERMO + EM + ÓPTICA")
    print("=" * 70)
    motor = None
    try:
        print(f"\n[0] NumPy: {'✅ ' + np.__version__ if NUMPY_DISPONIBLE else '❌ No (no requerido)'}")
        
        motor = MotorFisica()
        motor.inicializar()
        print(f"[1] Motor: {motor.nombre} | Estado: {motor.estado}")

        print(f"\n[2] Cinemática — Tiro parabólico (v0=20, 45°):")
        r = motor.procesar({'operacion': 'cinematica', 'suboperacion': 'parabolico',
                           'v0': 20, 'angulo': 45})
        if r and r.exito and r.datos:
            d = r.datos
            print(f"  🚀 Alcance: {d.get('alcance', 0):.2f} m")
            print(f"  🚀 Altura máx: {d.get('altura_maxima', 0):.2f} m")
            print(f"  🚀 Tiempo vuelo: {d.get('tiempo_vuelo', 0):.2f} s")

        print(f"\n[3] Cinemática — Movimiento circular (r=2, f=0.5 Hz):")
        r = motor.procesar({'operacion': 'cinematica', 'suboperacion': 'circular',
                           'radio': 2, 'frecuencia': 0.5})
        if r and r.exito and r.datos:
            d = r.datos
            print(f"  🔄 ω = {d.get('velocidad_angular', 0):.4f} rad/s")
            print(f"  🔄 v = {d.get('velocidad_tangencial', 0):.4f} m/s")
            print(f"  🔄 ac = {d.get('aceleracion_centripeta', 0):.4f} m/s²")

        print(f"\n[4] Dinámica — Colisión elástica (m1=2, v1=3, m2=1, v2=0):")
        r = motor.procesar({'operacion': 'dinamica', 'suboperacion': 'colision',
                           'm1': 2, 'v1i': 3, 'm2': 1, 'v2i': 0})
        if r and r.exito and r.datos:
            d = r.datos
            print(f"  💥 v1f = {d.get('velocidad_final_1', 0):.2f} m/s")
            print(f"  💥 v2f = {d.get('velocidad_final_2', 0):.2f} m/s")
            print(f"  💥 pi = pf = {d.get('momento_inicial', 0):.2f} kg·m/s")

        print(f"\n[5] Dinámica — Velocidad escape Tierra:")
        r = motor.procesar({'operacion': 'dinamica', 'suboperacion': 'velocidad_escape',
                           'masa': 5.972e24, 'radio': 6.371e6})
        if r and r.exito and r.datos:
            print(f"  🌍 v_escape = {r.datos.get('velocidad_escape', 0):.0f} m/s "
                  f"({r.datos.get('velocidad_escape', 0)/1000:.1f} km/s)")

        print(f"\n[6] Termodinámica — Gas ideal (P=101325, V=0.0224, n=1):")
        r = motor.procesar({'operacion': 'termodinamica', 'suboperacion': 'gas_ideal',
                           'presion': 101325, 'volumen': 0.0224, 'n_moles': 1})
        if r and r.exito and r.datos:
            print(f"  🔥 T = {r.datos.get('temperatura', 0):.1f} K "
                  f"({r.datos.get('temperatura', 0)-273.15:.1f} °C)")

        print(f"\n[7] Termodinámica — Eficiencia Carnot (500K, 300K):")
        r = motor.procesar({'operacion': 'termodinamica', 'suboperacion': 'carnot',
                           'T_caliente': 500, 'T_fria': 300})
        if r and r.exito and r.datos:
            print(f"  ♨️ η = {r.datos.get('eficiencia', 0)*100:.1f}%")

        print(f"\n[8] Electromagnetismo — Ley de Coulomb (q1=q2=1µC, d=0.1m):")
        r = motor.procesar({'operacion': 'electromagnetismo', 'suboperacion': 'coulomb',
                           'q1': 1e-6, 'q2': 1e-6, 'distancia': 0.1})
        if r and r.exito and r.datos:
            print(f"  ⚡ F = {r.datos.get('fuerza', 0):.3f} N "
                  f"({'atractiva' if r.datos.get('atractiva') else 'repulsiva'})")

        print(f"\n[9] Electromagnetismo — Circuito paralelo (100Ω, 200Ω):")
        r = motor.procesar({'operacion': 'electromagnetismo', 'suboperacion': 'resistencia_paralelo',
                           'resistencias': [100, 200]})
        if r and r.exito and r.datos:
            print(f"  🔌 R_eq = {r.datos.get('resistencia_total', 0):.1f} Ω")

        print(f"\n[10] Óptica — Ley de Snell (aire→agua, 30°):")
        r = motor.procesar({'operacion': 'optica', 'suboperacion': 'snell',
                           'n1': 1.0, 'n2': 1.33, 'angulo1': 30})
        if r and r.exito and r.datos:
            d = r.datos
            if d.get('reflexion_total'):
                print(f"  💡 Reflexión total. Ángulo crítico: {d.get('angulo_critico', 0):.1f}°")
            else:
                print(f"  💡 θ₂ = {d.get('angulo_2_grados', 0):.1f}°")

        print(f"\n[11] Óptica — Efecto Doppler (ambulancia acercándose):")
        r = motor.procesar({'operacion': 'optica', 'suboperacion': 'doppler',
                           'f_emisor': 440, 'v_emisor': -30, 'v_receptor': 0, 'v_sonido': 343})
        if r and r.exito and r.datos:
            print(f"  🚑 f' = {r.datos.get('frecuencia_observada', 0):.1f} Hz "
                  f"(original: 440 Hz)")

        print(f"\n[12] Constantes físicas:")
        r = motor.procesar({'operacion': 'constantes'})
        if r and r.exito and r.datos:
            ctes = r.datos.get('constantes', {})
            print(f"  🌌 G = {ctes.get('G', 0):.4e} N·m²/kg²")
            print(f"  🌌 c = {ctes.get('c', 0):.0f} m/s")
            print(f"  🌌 h = {ctes.get('h', 0):.4e} J·s")
            print(f"  🌌 g = {ctes.get('g_tierra', 0):.3f} m/s²")

        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE FÍSICA")
        s = motor._estadisticas
        print(f"   Cálculos: {s['calculos_realizados']} | "
              f"Cin: {s['cinematica']} | Din: {s['dinamica']} | "
              f"Ter: {s['termodinamica']} | EM: {s['electromagnetismo']} | "
              f"Opt: {s['optica']}")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")
    
   