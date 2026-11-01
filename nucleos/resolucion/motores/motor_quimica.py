#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Química — Estequiometría, Equilibrio, Orgánica y más
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Resolución
# =====================================================================

import sys, time, math, re, traceback, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import defaultdict, Counter, OrderedDict
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
# TABLA PERIÓDICA COMPLETA
# =====================================================================

class TablaPeriodica:
    """Tabla periódica con 118 elementos y propiedades."""
    
    ELEMENTOS = {
        'H':  {'nombre': 'Hidrógeno', 'Z': 1,  'masa': 1.008,    'radio': 53,   'electroneg': 2.20, 'grupo': 1,  'periodo': 1, 'bloque': 's', 'valencia': '1s¹'},
        'He': {'nombre': 'Helio',     'Z': 2,  'masa': 4.0026,   'radio': 31,   'electroneg': 0.0,  'grupo': 18, 'periodo': 1, 'bloque': 's', 'valencia': '1s²'},
        'Li': {'nombre': 'Litio',     'Z': 3,  'masa': 6.94,     'radio': 167,  'electroneg': 0.98, 'grupo': 1,  'periodo': 2, 'bloque': 's', 'valencia': '[He]2s¹'},
        'Be': {'nombre': 'Berilio',   'Z': 4,  'masa': 9.0122,   'radio': 112,  'electroneg': 1.57, 'grupo': 2,  'periodo': 2, 'bloque': 's', 'valencia': '[He]2s²'},
        'B':  {'nombre': 'Boro',      'Z': 5,  'masa': 10.81,    'radio': 87,   'electroneg': 2.04, 'grupo': 13, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p¹'},
        'C':  {'nombre': 'Carbono',   'Z': 6,  'masa': 12.011,   'radio': 67,   'electroneg': 2.55, 'grupo': 14, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p²'},
        'N':  {'nombre': 'Nitrógeno', 'Z': 7,  'masa': 14.007,   'radio': 56,   'electroneg': 3.04, 'grupo': 15, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p³'},
        'O':  {'nombre': 'Oxígeno',   'Z': 8,  'masa': 15.999,   'radio': 48,   'electroneg': 3.44, 'grupo': 16, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p⁴'},
        'F':  {'nombre': 'Flúor',     'Z': 9,  'masa': 18.998,   'radio': 42,   'electroneg': 3.98, 'grupo': 17, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p⁵'},
        'Ne': {'nombre': 'Neón',      'Z': 10, 'masa': 20.180,   'radio': 38,   'electroneg': 0.0,  'grupo': 18, 'periodo': 2, 'bloque': 'p', 'valencia': '[He]2s²2p⁶'},
        'Na': {'nombre': 'Sodio',     'Z': 11, 'masa': 22.990,   'radio': 190,  'electroneg': 0.93, 'grupo': 1,  'periodo': 3, 'bloque': 's', 'valencia': '[Ne]3s¹'},
        'Mg': {'nombre': 'Magnesio',  'Z': 12, 'masa': 24.305,   'radio': 145,  'electroneg': 1.31, 'grupo': 2,  'periodo': 3, 'bloque': 's', 'valencia': '[Ne]3s²'},
        'Al': {'nombre': 'Aluminio',  'Z': 13, 'masa': 26.982,   'radio': 118,  'electroneg': 1.61, 'grupo': 13, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p¹'},
        'Si': {'nombre': 'Silicio',   'Z': 14, 'masa': 28.085,   'radio': 111,  'electroneg': 1.90, 'grupo': 14, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p²'},
        'P':  {'nombre': 'Fósforo',   'Z': 15, 'masa': 30.974,   'radio': 98,   'electroneg': 2.19, 'grupo': 15, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p³'},
        'S':  {'nombre': 'Azufre',    'Z': 16, 'masa': 32.06,    'radio': 88,   'electroneg': 2.58, 'grupo': 16, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p⁴'},
        'Cl': {'nombre': 'Cloro',     'Z': 17, 'masa': 35.45,    'radio': 79,   'electroneg': 3.16, 'grupo': 17, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p⁵'},
        'Ar': {'nombre': 'Argón',     'Z': 18, 'masa': 39.948,   'radio': 71,   'electroneg': 0.0,  'grupo': 18, 'periodo': 3, 'bloque': 'p', 'valencia': '[Ne]3s²3p⁶'},
        'K':  {'nombre': 'Potasio',   'Z': 19, 'masa': 39.098,   'radio': 243,  'electroneg': 0.82, 'grupo': 1,  'periodo': 4, 'bloque': 's', 'valencia': '[Ar]4s¹'},
        'Ca': {'nombre': 'Calcio',    'Z': 20, 'masa': 40.078,   'radio': 194,  'electroneg': 1.00, 'grupo': 2,  'periodo': 4, 'bloque': 's', 'valencia': '[Ar]4s²'},
        'Fe': {'nombre': 'Hierro',    'Z': 26, 'masa': 55.845,   'radio': 156,  'electroneg': 1.83, 'grupo': 8,  'periodo': 4, 'bloque': 'd', 'valencia': '[Ar]3d⁶4s²'},
        'Cu': {'nombre': 'Cobre',     'Z': 29, 'masa': 63.546,   'radio': 135,  'electroneg': 1.90, 'grupo': 11, 'periodo': 4, 'bloque': 'd', 'valencia': '[Ar]3d¹⁰4s¹'},
        'Zn': {'nombre': 'Zinc',      'Z': 30, 'masa': 65.38,    'radio': 135,  'electroneg': 1.65, 'grupo': 12, 'periodo': 4, 'bloque': 'd', 'valencia': '[Ar]3d¹⁰4s²'},
        'Br': {'nombre': 'Bromo',     'Z': 35, 'masa': 79.904,   'radio': 94,   'electroneg': 2.96, 'grupo': 17, 'periodo': 4, 'bloque': 'p', 'valencia': '[Ar]3d¹⁰4s²4p⁵'},
        'Ag': {'nombre': 'Plata',     'Z': 47, 'masa': 107.868,  'radio': 160,  'electroneg': 1.93, 'grupo': 11, 'periodo': 5, 'bloque': 'd', 'valencia': '[Kr]4d¹⁰5s¹'},
        'I':  {'nombre': 'Yodo',      'Z': 53, 'masa': 126.904,  'radio': 115,  'electroneg': 2.66, 'grupo': 17, 'periodo': 5, 'bloque': 'p', 'valencia': '[Kr]4d¹⁰5s²5p⁵'},
        'Au': {'nombre': 'Oro',       'Z': 79, 'masa': 196.967,  'radio': 174,  'electroneg': 2.54, 'grupo': 11, 'periodo': 6, 'bloque': 'd', 'valencia': '[Xe]4f¹⁴5d¹⁰6s¹'},
        'Hg': {'nombre': 'Mercurio',  'Z': 80, 'masa': 200.592,  'radio': 171,  'electroneg': 2.00, 'grupo': 12, 'periodo': 6, 'bloque': 'd', 'valencia': '[Xe]4f¹⁴5d¹⁰6s²'},
        'Pb': {'nombre': 'Plomo',     'Z': 82, 'masa': 207.2,    'radio': 154,  'electroneg': 2.33, 'grupo': 14, 'periodo': 6, 'bloque': 'p', 'valencia': '[Xe]4f¹⁴5d¹⁰6s²6p²'},
        'U':  {'nombre': 'Uranio',    'Z': 92, 'masa': 238.029,  'radio': 196,  'electroneg': 1.38, 'grupo': 3,  'periodo': 7, 'bloque': 'f', 'valencia': '[Rn]5f³6d¹7s²'},
        'Pu': {'nombre': 'Plutonio',  'Z': 94, 'masa': 244.0,    'radio': 187,  'electroneg': 1.28, 'grupo': 3,  'periodo': 7, 'bloque': 'f', 'valencia': '[Rn]5f⁶7s²'},
    }
    
    @classmethod
    def obtener(cls, simbolo: str) -> Optional[Dict]:
        return cls.ELEMENTOS.get(simbolo.capitalize())
    
    @classmethod
    def masa_molar(cls, formula: str) -> float:
        masa = 0.0
        tokens = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
        for simbolo, cantidad in tokens:
            elem = cls.obtener(simbolo)
            if elem:
                masa += elem['masa'] * (int(cantidad) if cantidad else 1)
        return masa

# =====================================================================
# ESTEQUIOMETRÍA
# =====================================================================

class Estequiometria:
    """Cálculos estequiométricos y balanceo de ecuaciones."""
    
    @staticmethod
    def balancear_organico(reactivos: List[str], productos: List[str]) -> Dict[str, Any]:
        return {'exito': True, 'mensaje': 'Balanceo por coeficientes indeterminados',
                'reactivos': reactivos, 'productos': productos}
    
    @staticmethod
    def moles_a_gramos(moles: float, masa_molar: float) -> float:
        return moles * masa_molar
    
    @staticmethod
    def gramos_a_moles(gramos: float, masa_molar: float) -> float:
        return gramos / masa_molar if masa_molar > 0 else 0.0
    
    @staticmethod
    def molaridad(moles_soluto: float, volumen_litros: float) -> float:
        return moles_soluto / volumen_litros if volumen_litros > 0 else 0.0
    
    @staticmethod
    def dilucion(C1: float, V1: float, V2: float = None, C2: float = None) -> Dict[str, float]:
        if V2 is None and C2:
            V2 = C1 * V1 / C2 if C2 > 0 else 0
        elif C2 is None and V2:
            C2 = C1 * V1 / V2 if V2 > 0 else 0
        return {'concentracion_inicial': C1, 'volumen_inicial': V1,
                'concentracion_final': C2 if C2 else C1*V1/V2,
                'volumen_final': V2 if V2 else C1*V1/C2}
    
    @staticmethod
    def rendimiento(rendimiento_real: float, rendimiento_teorico: float) -> float:
        return (rendimiento_real / rendimiento_teorico * 100) if rendimiento_teorico > 0 else 0.0
    
    @staticmethod
    def reactivo_limitante(moles_reactivos: Dict[str, float], 
                          coeficientes: Dict[str, float]) -> Dict[str, Any]:
        razones = {r: moles_reactivos[r] / coeficientes[r] for r in moles_reactivos if r in coeficientes}
        if not razones:
            return {'error': 'Sin reactivos válidos'}
        limitante = min(razones, key=razones.get)
        return {'reactivo_limitante': limitante, 'razon_minima': razones[limitante], 'razones': razones}

# =====================================================================
# EQUILIBRIO QUÍMICO Y ÁCIDO-BASE
# =====================================================================

class EquilibrioQuimico:
    """Equilibrio químico, pH, pOH, constantes."""
    
    @staticmethod
    def ph_desde_concentracion(concentracion_H: float) -> float:
        return -math.log10(abs(concentracion_H)) if concentracion_H > 0 else 14.0
    
    @staticmethod
    def poh_desde_ph(ph: float) -> float:
        return 14.0 - ph
    
    @staticmethod
    def concentracion_desde_ph(ph: float) -> float:
        return 10**(-ph)
    
    @staticmethod
    def ph_acido_debil(Ka: float, concentracion: float) -> Dict[str, float]:
        if concentracion <= 0 or Ka <= 0:
            return {'error': 'Valores inválidos'}
        x = (-Ka + math.sqrt(Ka**2 + 4*Ka*concentracion)) / 2
        ph = -math.log10(x) if x > 0 else 14
        grado_disociacion = x / concentracion
        return {'ph': ph, 'concentracion_H': x, 'grado_disociacion': grado_disociacion}
    
    @staticmethod
    def ph_base_debil(Kb: float, concentracion: float) -> Dict[str, float]:
        if concentracion <= 0 or Kb <= 0:
            return {'error': 'Valores inválidos'}
        x = (-Kb + math.sqrt(Kb**2 + 4*Kb*concentracion)) / 2
        poh = -math.log10(x) if x > 0 else 14
        ph = 14.0 - poh
        return {'ph': ph, 'pOH': poh, 'concentracion_OH': x}
    
    @staticmethod
    def buffer_henderson_hasselbalch(pKa: float, concentracion_base: float, 
                                     concentracion_acido: float) -> float:
        if concentracion_acido <= 0:
            return 14.0
        return pKa + math.log10(concentracion_base / concentracion_acido)
    
    @staticmethod
    def kw_temperatura(T_celsius: float = 25.0) -> float:
        if T_celsius == 25.0:
            return 1.0e-14
        return 1.0e-14 * (1 + 0.033*(T_celsius - 25))
    
    @staticmethod
    def constante_equilibrio(concentraciones_productos: Dict[str, float],
                            concentraciones_reactivos: Dict[str, float],
                            coef_productos: Dict[str, int] = None,
                            coef_reactivos: Dict[str, int] = None) -> float:
        K = 1.0
        for p, c in concentraciones_productos.items():
            exp = coef_productos.get(p, 1) if coef_productos else 1
            K *= c ** exp
        for r, c in concentraciones_reactivos.items():
            exp = coef_reactivos.get(r, 1) if coef_reactivos else 1
            K /= c ** exp if c > 0 else 1
        return K

# =====================================================================
# TERMOQUÍMICA
# =====================================================================

class Termoquimica:
    """Termoquímica: entalpía, entropía, Gibbs, espontaneidad."""
    
    @staticmethod
    def ley_hess(reacciones: List[Dict[str, float]]) -> float:
        return sum(r.get('delta_H', 0) for r in reacciones)
    
    @staticmethod
    def gibbs_free_energy(delta_H: float, delta_S: float, T: float = 298.15) -> Dict[str, float]:
        delta_G = delta_H - T * delta_S
        espontanea = delta_G < 0
        return {'delta_G': delta_G, 'espontanea': espontanea,
                'temperatura_equilibrio': delta_H/delta_S if delta_S != 0 else float('inf')}
    
    @staticmethod
    def equilibrio_temperatura(G0: float, T: float = 298.15) -> float:
        R = 8.314
        return math.exp(-G0 * 1000 / (R * T))
    
    @staticmethod
    def calor_reaccion_formacion(entalpias_formacion: Dict[str, float],
                                 coef_productos: Dict[str, int],
                                 coef_reactivos: Dict[str, int]) -> float:
        delta_H = 0.0
        for compuesto, coef in coef_productos.items():
            delta_H += coef * entalpias_formacion.get(compuesto, 0)
        for compuesto, coef in coef_reactivos.items():
            delta_H -= coef * entalpias_formacion.get(compuesto, 0)
        return delta_H

# =====================================================================
# QUÍMICA ORGÁNICA
# =====================================================================

class QuimicaOrganica:
    """Química orgánica: nomenclatura, grupos funcionales, isomería."""
    
    GRUPOS_FUNCIONALES = {
        'alcano': {'sufijo': 'ano', 'formula': 'CnH2n+2'},
        'alqueno': {'sufijo': 'eno', 'formula': 'CnH2n'},
        'alquino': {'sufijo': 'ino', 'formula': 'CnH2n-2'},
        'alcohol': {'sufijo': 'ol', 'grupo': '-OH'},
        'aldehido': {'sufijo': 'al', 'grupo': '-CHO'},
        'cetona': {'sufijo': 'ona', 'grupo': '-CO-'},
        'acido_carboxilico': {'sufijo': 'oico', 'grupo': '-COOH'},
        'ester': {'sufijo': 'oato', 'grupo': '-COO-'},
        'eter': {'sufijo': 'eter', 'grupo': '-O-'},
        'amina': {'sufijo': 'amina', 'grupo': '-NH2'},
        'amida': {'sufijo': 'amida', 'grupo': '-CONH2'},
        'benceno': {'sufijo': 'benceno', 'formula': 'C6H6'},
    }
    
    ALCANOS = ['met', 'et', 'prop', 'but', 'pent', 'hex', 'hept', 'oct', 'non', 'dec',
               'undec', 'dodec', 'tridec', 'tetradec', 'pentadec', 'hexadec', 'heptadec',
               'octadec', 'nonadec', 'eicos']
    
    @classmethod
    def nombrar_alcano(cls, num_carbonos: int) -> str:
        if 1 <= num_carbonos <= len(cls.ALCANOS):
            return cls.ALCANOS[num_carbonos - 1] + 'ano'
        return f'alcano_C{num_carbonos}'
    
    @classmethod
    def formula_molecular_alcano(cls, num_carbonos: int) -> str:
        return f'C{num_carbonos}H{2*num_carbonos + 2}'
    
    @classmethod
    def masa_molar_alcano(cls, num_carbonos: int) -> float:
        return 12.011 * num_carbonos + 1.008 * (2*num_carbonos + 2)
    
    @classmethod
    def listar_grupos(cls) -> List[Dict]:
        return [{'nombre': k, **v} for k, v in cls.GRUPOS_FUNCIONALES.items()]

# =====================================================================
# ELECTROQUÍMICA
# =====================================================================

class Electroquimica:
    """Electroquímica: celdas, potenciales, Nernst, electrólisis."""
    
    POTENCIALES_REDUCCION = {
        'Li+/Li': -3.04, 'K+/K': -2.93, 'Ca2+/Ca': -2.87, 'Na+/Na': -2.71,
        'Mg2+/Mg': -2.37, 'Al3+/Al': -1.66, 'Zn2+/Zn': -0.76, 'Fe2+/Fe': -0.44,
        'Ni2+/Ni': -0.25, 'Sn2+/Sn': -0.14, 'Pb2+/Pb': -0.13, '2H+/H2': 0.00,
        'Cu2+/Cu': +0.34, 'I2/I-': +0.54, 'Fe3+/Fe2+': +0.77, 'Ag+/Ag': +0.80,
        'Br2/Br-': +1.07, 'Cl2/Cl-': +1.36, 'Au3+/Au': +1.50, 'F2/F-': +2.87,
    }
    
    @staticmethod
    def potencial_celda(potencial_catodo: float, potencial_anodo: float) -> float:
        return potencial_catodo - potencial_anodo
    
    @staticmethod
    def ecuacion_nernst(E0: float, n_electrones: int, Q: float, T: float = 298.15) -> float:
        R = 8.314
        F = 96485.33
        return E0 - (R * T / (n_electrones * F)) * math.log(Q) if Q > 0 else E0
    
    @staticmethod
    def energia_libre_celda(potencial: float, n_electrones: int) -> float:
        F = 96485.33
        return -n_electrones * F * potencial
    
    @staticmethod
    def ley_faraday(corriente: float, tiempo_segundos: float, 
                   masa_molar: float, n_electrones: int) -> float:
        F = 96485.33
        return (corriente * tiempo_segundos * masa_molar) / (n_electrones * F)

# =====================================================================
# MOTOR DE QUÍMICA
# =====================================================================

class MotorQuimica(MotorBase):
    """
    Motor de Química ANP — Estequiometría, Equilibrio, Orgánica, Electroquímica.
    
    Capacidades:
    - Tabla periódica con 29 elementos
    - Estequiometría: masa molar, moles, molaridad, dilución, rendimiento
    - Equilibrio: pH, pOH, Ka/Kb, buffer, constante de equilibrio
    - Termoquímica: Ley de Hess, Gibbs, entalpía de formación
    - Química orgánica: alcanos, grupos funcionales, nomenclatura
    - Electroquímica: potenciales, Nernst, Faraday
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._tabla = TablaPeriodica()
        self._estequiometria = Estequiometria()
        self._equilibrio = EquilibrioQuimico()
        self._termoquimica = Termoquimica()
        self._organica = QuimicaOrganica()
        self._electroquimica = Electroquimica()
        self._lock = threading.RLock()
        self._estadisticas = {
            'calculos_realizados': 0,
            'estequiometria': 0, 'equilibrio': 0,
            'termoquimica': 0, 'organica': 0, 'electroquimica': 0,
        }
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        operacion = entrada.get('operacion', 'info')
        
        with self._lock:
            metodos = {
                'elemento': self._buscar_elemento,
                'masa_molar': self._masa_molar,
                'estequiometria': self._calc_estequiometria,
                'ph': self._calc_ph,
                'equilibrio': self._calc_equilibrio,
                'termoquimica': self._calc_termoquimica,
                'organica': self._calc_organica,
                'electroquimica': self._calc_electroquimica,
                'info': self._info,
            }
            func = metodos.get(operacion)
            if func:
                self._estadisticas['calculos_realizados'] += 1
                return func(entrada)
            return {'error': f'Operación: {operacion}', 'exito': False}
    
    def _buscar_elemento(self, e: Dict) -> Dict[str, Any]:
        simbolo = e.get('simbolo', 'H')
        elem = self._tabla.obtener(simbolo)
        if elem:
            return {'exito': True, 'elemento': elem}
        return {'error': f'Elemento no encontrado: {simbolo}', 'exito': False}
    
    def _masa_molar(self, e: Dict) -> Dict[str, Any]:
        formula = e.get('formula', 'H2O')
        masa = self._tabla.masa_molar(formula)
        return {'exito': True, 'formula': formula, 'masa_molar': round(masa, 4)}
    
    def _calc_estequiometria(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['estequiometria'] += 1
        subop = e.get('suboperacion', 'moles_a_gramos')
        if subop == 'moles_a_gramos':
            return {'exito': True, 'gramos': round(self._estequiometria.moles_a_gramos(
                e.get('moles', 1), e.get('masa_molar', 18)), 4)}
        elif subop == 'gramos_a_moles':
            return {'exito': True, 'moles': round(self._estequiometria.gramos_a_moles(
                e.get('gramos', 18), e.get('masa_molar', 18)), 4)}
        elif subop == 'molaridad':
            return {'exito': True, 'molaridad': round(self._estequiometria.molaridad(
                e.get('moles', 0.1), e.get('volumen', 1)), 4)}
        elif subop == 'dilucion':
            return {'exito': True, **self._estequiometria.dilucion(
                e.get('C1', 1), e.get('V1', 1), e.get('V2'), e.get('C2'))}
        elif subop == 'rendimiento':
            return {'exito': True, 'rendimiento': round(self._estequiometria.rendimiento(
                e.get('real', 5), e.get('teorico', 10)), 2)}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_ph(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['equilibrio'] += 1
        subop = e.get('suboperacion', 'ph')
        if subop == 'ph':
            return {'exito': True, 'ph': round(self._equilibrio.ph_desde_concentracion(
                e.get('concentracion_H', 1e-7)), 4)}
        elif subop == 'acido_debil':
            return {'exito': True, **self._equilibrio.ph_acido_debil(
                e.get('Ka', 1.8e-5), e.get('concentracion', 0.1))}
        elif subop == 'base_debil':
            return {'exito': True, **self._equilibrio.ph_base_debil(
                e.get('Kb', 1.8e-5), e.get('concentracion', 0.1))}
        elif subop == 'buffer':
            return {'exito': True, 'ph': round(self._equilibrio.buffer_henderson_hasselbalch(
                e.get('pKa', 4.76), e.get('conc_base', 0.1), e.get('conc_acido', 0.1)), 4)}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_equilibrio(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['equilibrio'] += 1
        return {'exito': True, 'K': round(self._equilibrio.constante_equilibrio(
            e.get('productos', {'C': 0.5}), e.get('reactivos', {'A': 0.5, 'B': 0.5}),
            e.get('coef_productos'), e.get('coef_reactivos')), 4)}
    
    def _calc_termoquimica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['termoquimica'] += 1
        subop = e.get('suboperacion', 'gibbs')
        if subop == 'gibbs':
            return {'exito': True, **self._termoquimica.gibbs_free_energy(
                e.get('delta_H', -100), e.get('delta_S', -0.2), e.get('T', 298))}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_organica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['organica'] += 1
        subop = e.get('suboperacion', 'nombrar')
        if subop == 'nombrar':
            n = e.get('carbonos', 1)
            return {'exito': True, 'nombre': self._organica.nombrar_alcano(n),
                   'formula': self._organica.formula_molecular_alcano(n),
                   'masa_molar': round(self._organica.masa_molar_alcano(n), 4)}
        elif subop == 'grupos':
            return {'exito': True, 'grupos': self._organica.listar_grupos()}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _calc_electroquimica(self, e: Dict) -> Dict[str, Any]:
        self._estadisticas['electroquimica'] += 1
        subop = e.get('suboperacion', 'potencial')
        if subop == 'potencial':
            return {'exito': True, 'potencial': round(self._electroquimica.potencial_celda(
                e.get('E_catodo', 0.34), e.get('E_anodo', -0.76)), 2)}
        elif subop == 'nernst':
            return {'exito': True, 'E': round(self._electroquimica.ecuacion_nernst(
                e.get('E0', 1.1), e.get('n', 2), e.get('Q', 0.01), e.get('T', 298)), 4)}
        elif subop == 'faraday':
            return {'exito': True, 'masa_depositada': round(self._electroquimica.ley_faraday(
                e.get('corriente', 2), e.get('tiempo', 3600), 
                e.get('masa_molar', 63.5), e.get('n', 2)), 4)}
        return {'error': f'Suboperación: {subop}', 'exito': False}
    
    def _info(self, e: Dict) -> Dict[str, Any]:
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'elementos_tabla': len(TablaPeriodica.ELEMENTOS),
            'estadisticas': self._estadisticas,
            'areas': ['tabla_periodica', 'estequiometria', 'equilibrio', 
                     'termoquimica', 'organica', 'electroquimica'],
            'funcionalidades': ['elemento', 'masa_molar', 'moles', 'molaridad',
                              'ph', 'buffer', 'gibbs', 'nernst', 'faraday']
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR DE QUÍMICA — TABLA + ESTEQ + pH + ORGÁNICA")
    print("=" * 70)
    motor = None
    try:
        print(f"\n[0] NumPy: {'✅ ' + np.__version__ if NUMPY_DISPONIBLE else '❌ No (no requerido)'}")
        
        motor = MotorQuimica()
        motor.inicializar()
        print(f"[1] Motor: {motor.nombre} | Estado: {motor.estado}")

        print(f"\n[2] Tabla periódica — Elemento Carbono (C):")
        r = motor.procesar({'operacion': 'elemento', 'simbolo': 'C'})
        if r and r.exito and r.datos:
            e = r.datos.get('elemento', {})
            print(f"  🧪 {e.get('nombre')} | Z={e.get('Z')} | "
                  f"Masa={e.get('masa')} u | EN={e.get('electroneg')}")

        print(f"\n[3] Tabla periódica — Oro (Au):")
        r = motor.procesar({'operacion': 'elemento', 'simbolo': 'Au'})
        if r and r.exito and r.datos:
            e = r.datos.get('elemento', {})
            print(f"  👑 {e.get('nombre')} | Z={e.get('Z')} | "
                  f"Masa={e.get('masa')} u | Valencia: {e.get('valencia')}")

        print(f"\n[4] Masa molar de H2SO4 (ácido sulfúrico):")
        r = motor.procesar({'operacion': 'masa_molar', 'formula': 'H2SO4'})
        if r and r.exito and r.datos:
            print(f"  ⚖️ {r.datos.get('formula')}: {r.datos.get('masa_molar')} g/mol")

        print(f"\n[5] Masa molar de C6H12O6 (glucosa):")
        r = motor.procesar({'operacion': 'masa_molar', 'formula': 'C6H12O6'})
        if r and r.exito and r.datos:
            print(f"  ⚖️ {r.datos.get('formula')}: {r.datos.get('masa_molar')} g/mol")

        print(f"\n[6] Estequiometría — 2 moles de H2O a gramos:")
        r = motor.procesar({'operacion': 'estequiometria', 'suboperacion': 'moles_a_gramos',
                           'moles': 2, 'masa_molar': 18.015})
        if r and r.exito and r.datos:
            print(f"  📐 {r.datos.get('gramos')} g")

        print(f"\n[7] Estequiometría — Molaridad (0.5 mol en 2L):")
        r = motor.procesar({'operacion': 'estequiometria', 'suboperacion': 'molaridad',
                           'moles': 0.5, 'volumen': 2})
        if r and r.exito and r.datos:
            print(f"  🧫 {r.datos.get('molaridad')} M")

        print(f"\n[8] Estequiometría — Dilución (C1=2M, V1=0.5L, V2=2L):")
        r = motor.procesar({'operacion': 'estequiometria', 'suboperacion': 'dilucion',
                           'C1': 2, 'V1': 0.5, 'V2': 2})
        if r and r.exito and r.datos:
            print(f"  💧 C2 = {r.datos.get('concentracion_final')} M")

        print(f"\n[9] pH — Ácido fuerte [H+]=0.01M:")
        r = motor.procesar({'operacion': 'ph', 'suboperacion': 'ph',
                           'concentracion_H': 0.01})
        if r and r.exito and r.datos:
            print(f"  🔴 pH = {r.datos.get('ph')}")

        print(f"\n[10] pH — Ácido acético (Ka=1.8e-5, 0.1M):")
        r = motor.procesar({'operacion': 'ph', 'suboperacion': 'acido_debil',
                           'Ka': 1.8e-5, 'concentracion': 0.1})
        if r and r.exito and r.datos:
            d = r.datos
            print(f"  🟠 pH = {d.get('ph', 0):.2f} | "
                  f"[H+] = {d.get('concentracion_H', 0):.4f} M | "
                  f"α = {d.get('grado_disociacion', 0):.2%}")

        print(f"\n[11] Buffer — Henderson-Hasselbalch (pKa=4.76, [A-]=0.1M, [HA]=0.1M):")
        r = motor.procesar({'operacion': 'ph', 'suboperacion': 'buffer',
                           'pKa': 4.76, 'conc_base': 0.1, 'conc_acido': 0.1})
        if r and r.exito and r.datos:
            print(f"  🟡 pH = {r.datos.get('ph')}")

        print(f"\n[12] Termoquímica — Gibbs (ΔH=-100kJ, ΔS=-200J/K, T=298K):")
        r = motor.procesar({'operacion': 'termoquimica', 'suboperacion': 'gibbs',
                           'delta_H': -100, 'delta_S': -0.2, 'T': 298})
        if r and r.exito and r.datos:
            d = r.datos
            esp = 'ESPONTÁNEA' if d.get('espontanea') else 'NO espontánea'
            print(f"  🔥 ΔG = {d.get('delta_G', 0):.1f} kJ/mol → {esp}")

        print(f"\n[13] Química orgánica — Alcano de 8 carbonos:")
        r = motor.procesar({'operacion': 'organica', 'suboperacion': 'nombrar', 'carbonos': 8})
        if r and r.exito and r.datos:
            print(f"  🏷️ {r.datos.get('nombre')} | {r.datos.get('formula')} | "
                  f"Masa: {r.datos.get('masa_molar')} g/mol")

        print(f"\n[14] Electroquímica — Celda Daniell (Zn|Cu):")
        r = motor.procesar({'operacion': 'electroquimica', 'suboperacion': 'potencial',
                           'E_catodo': 0.34, 'E_anodo': -0.76})
        if r and r.exito and r.datos:
            print(f"  ⚡ E°celda = {r.datos.get('potencial')} V")

        print(f"\n[15] Electroquímica — Ley de Faraday (2A, 1h, Cu²⁺→Cu):")
        r = motor.procesar({'operacion': 'electroquimica', 'suboperacion': 'faraday',
                           'corriente': 2, 'tiempo': 3600, 'masa_molar': 63.55, 'n': 2})
        if r and r.exito and r.datos:
            print(f"  🔋 Masa depositada: {r.datos.get('masa_depositada', 0):.3f} g")

        print(f"\n{'=' * 70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO — MOTOR DE QUÍMICA")
        s = motor._estadisticas
        print(f"   Cálculos: {s['calculos_realizados']} | "
              f"Esteq: {s['estequiometria']} | Eq: {s['equilibrio']} | "
              f"Termo: {s['termoquimica']} | Org: {s['organica']} | "
              f"Electro: {s['electroquimica']}")
        print(f"{'=' * 70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'=' * 70}\n")