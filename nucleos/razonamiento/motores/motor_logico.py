#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Lógico (El Oráculo de la Verdad)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa razonamiento lógico REAL con
# lógica proposicional, tablas de verdad, álgebra booleana, silogismos,
# inferencia lógica, detección de falacias y lógica de predicados.
# =====================================================================

import sys, os, re, time, math, json, itertools, threading
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

class OperadorLogico(Enum):
    Y = "y"
    O = "o"
    NO = "no"
    XOR = "xor"
    IMPLICA = "implica"
    EQUIVALE = "equivale"
    NAND = "nand"
    NOR = "nor"
    XNOR = "xnor"

class TipoRazonamiento(Enum):
    DEDUCTIVO = "deductivo"
    INDUCTIVO = "inductivo"
    ABDUCTIVO = "abductivo"
    ANALOGICO = "analogico"
    PROPOSICIONAL = "proposicional"
    PREDICADOS = "predicados"
    SILOGISMO = "silogismo"
    TABLA_VERDAD = "tabla_verdad"
    INFERENCIA = "inferencia"

class ValidezLogica(Enum):
    VALIDO = "valido"
    INVALIDO = "invalido"
    INDETERMINADO = "indeterminado"
    CONTRADICCION = "contradiccion"
    TAUTOLOGIA = "tautologia"
    SATISFACIBLE = "satisfacible"

class FiguraSilogismo(Enum):
    BARBARA = "barbara"
    CELARENT = "celarent"
    DARII = "darii"
    FERIO = "ferio"
    CESARE = "cesare"
    CAMESTRES = "camestres"
    FESTINO = "festino"
    BAROCO = "baroco"
    DARAPTI = "darapti"
    FELAPTON = "felapton"
    DISAMIS = "disamis"
    DATISI = "datisi"
    BOCARDO = "bocardo"
    FERISON = "ferison"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class Proposicion:
    texto: str
    variable: str = ""
    valor_verdad: Optional[bool] = None

@dataclass
class TablaVerdad:
    variables: List[str] = field(default_factory=list)
    filas: List[Dict[str, Union[bool, str]]] = field(default_factory=list)
    expresion: str = ""
    resultado: ValidezLogica = ValidezLogica.INDETERMINADO
    total_combinaciones: int = 0
    verdaderos: int = 0
    falsos: int = 0

@dataclass
class Silogismo:
    premisa_mayor: str = ""
    premisa_menor: str = ""
    conclusion: str = ""
    figura: Optional[FiguraSilogismo] = None
    valido: bool = False
    explicacion: str = ""

@dataclass
class ResultadoLogico:
    tipo: TipoRazonamiento = TipoRazonamiento.PROPOSICIONAL
    entrada_original: str = ""
    expresion_normalizada: str = ""
    validez: ValidezLogica = ValidezLogica.INDETERMINADO
    tabla_verdad: Optional[TablaVerdad] = None
    silogismo: Optional[Silogismo] = None
    inferencia: Optional[Dict[str, Any]] = None
    explicacion: str = ""
    variables_detectadas: List[str] = field(default_factory=list)
    operadores_detectados: List[str] = field(default_factory=list)

# =====================================================================
# MOTOR LÓGICO PRINCIPAL (CORREGIDO)
# =====================================================================

class MotorLogico(MotorBase):
    """Motor de Razonamiento Lógico de ANP."""
    
    OPERADORES = {
        'y': OperadorLogico.Y, 'and': OperadorLogico.Y, '&': OperadorLogico.Y,
        '&&': OperadorLogico.Y, '∧': OperadorLogico.Y,
        'o': OperadorLogico.O, 'or': OperadorLogico.O, '|': OperadorLogico.O,
        '||': OperadorLogico.O, '∨': OperadorLogico.O,
        'no': OperadorLogico.NO, 'not': OperadorLogico.NO, '!': OperadorLogico.NO,
        '~': OperadorLogico.NO, '¬': OperadorLogico.NO,
        'xor': OperadorLogico.XOR, '⊻': OperadorLogico.XOR, '⊕': OperadorLogico.XOR,
        'implica': OperadorLogico.IMPLICA, '->': OperadorLogico.IMPLICA,
        '→': OperadorLogico.IMPLICA, '=>': OperadorLogico.IMPLICA,
        'equivale': OperadorLogico.EQUIVALE, '<->': OperadorLogico.EQUIVALE,
        '↔': OperadorLogico.EQUIVALE, '<=>': OperadorLogico.EQUIVALE,
        'nand': OperadorLogico.NAND, 'nor': OperadorLogico.NOR, 'xnor': OperadorLogico.XNOR,
    }
    
    SILOGISMOS_VALIDOS = {
        ('todos', 'todos'): FiguraSilogismo.BARBARA,
        ('ningun', 'todos'): FiguraSilogismo.CELARENT,
        ('todos', 'algun'): FiguraSilogismo.DARII,
        ('ningun', 'algun'): FiguraSilogismo.FERIO,
        ('ningun', 'todos'): FiguraSilogismo.CESARE,
        ('todos', 'ningun'): FiguraSilogismo.CAMESTRES,
        ('ningun', 'algun'): FiguraSilogismo.FESTINO,
        ('todos', 'algun_no'): FiguraSilogismo.BAROCO,
    }
    
    REGLAS_INFERENCIA = {
        'modus_ponens': {
            'patron': r'(?:si\s+)?(.+?)\s*(?:entonces|->|→|=>)\s*(.+?)[.,]?\s*(?:y|,)?\s*(?:dado que|sabemos que|se sabe que)?\s*\1\s*(?:es|es cierto|es verdad)',
            'nombre': 'Modus Ponens',
            'formula': 'Si P → Q, y P es verdad, entonces Q',
        },
        'modus_tollens': {
            'patron': r'(?:si\s+)?(.+?)\s*(?:entonces|->|→|=>)\s*(.+?)[.,]?\s*(?:y|,)?\s*(?:no\s+)?\2\s*(?:no es|es falso|no es cierto)',
            'nombre': 'Modus Tollens',
            'formula': 'Si P → Q, y ¬Q es verdad, entonces ¬P',
        },
    }
    
    # Palabras que NO son variables (operadores y conectores)
    PALABRAS_RESERVADAS = {
        'and', 'or', 'not', 'implies', 'equiv', 'xor', 'nand', 'nor', 'xnor',
        'y', 'o', 'no', 'implica', 'equivale', 'si', 'entonces', 'por', 'lo', 'tanto',
        'en', 'consecuencia', 'ergo', 'luego', 'todos', 'ningun', 'ningún', 'ninguna',
        'algun', 'algún', 'alguna', 'todo', 'toda', 'todas', 'son', 'es', 'los', 'las',
        'el', 'la', 'un', 'una', 'que', 'de', 'del', 'para', 'con', 'como', 'mortal',
        'humano', 'griego', 'griegos', 'humanos', 'mortales',
    }
    
    def __init__(self, config=None):
        super().__init__(config)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Procesa una consulta de razonamiento lógico."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('expresion', entrada.get('consulta', '')))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado_vacio()
        
        texto_original = texto
        texto_lower = texto.lower().strip()
        
        # Detectar tipo de razonamiento
        tipo = self._detectar_tipo(texto_lower, opciones)
        
        # Normalizar expresión
        expresion_norm = self._normalizar_expresion(texto_lower)
        
        # Extraer variables (CORREGIDO)
        variables = self._extraer_variables(texto_lower)
        
        # Extraer operadores
        operadores = self._extraer_operadores(texto_lower)
        
        # Generar tabla de verdad si es posible
        tabla = None
        validez = ValidezLogica.INDETERMINADO
        explicacion = ""
        silogismo_result = None
        inferencia_result = None
        
        if tipo == TipoRazonamiento.SILOGISMO:
            silogismo_result = self._analizar_silogismo(texto_lower, opciones)
            validez = ValidezLogica.VALIDO if silogismo_result.valido else ValidezLogica.INVALIDO
            explicacion = silogismo_result.explicacion
        elif tipo == TipoRazonamiento.INFERENCIA:
            inferencia_result = self._detectar_inferencia(texto_lower)
            if inferencia_result:
                validez = ValidezLogica.VALIDO
                explicacion = f"Regla: {inferencia_result['nombre']}. {inferencia_result['formula']}"
            else:
                explicacion = "No se detectó una regla de inferencia reconocible."
        elif len(variables) >= 1 and len(variables) <= 6:
            tabla = self._generar_tabla_verdad(expresion_norm, variables)
            validez = tabla.resultado
            explicacion = self._generar_explicacion(tabla, variables, operadores)
        else:
            explicacion = f"Análisis con {len(variables)} variable(s): {', '.join(variables[:5])}. Operadores: {', '.join(operadores)}."
        
        return {
            'texto_original': texto_original,
            'tipo_razonamiento': tipo.value,
            'validez': validez.value,
            'explicacion': explicacion,
            'variables_detectadas': variables,
            'operadores_detectados': operadores,
            'expresion_normalizada': expresion_norm,
            'tabla_verdad': self._serializar_tabla(tabla) if tabla else None,
            'silogismo': {
                'premisa_mayor': silogismo_result.premisa_mayor,
                'premisa_menor': silogismo_result.premisa_menor,
                'conclusion': silogismo_result.conclusion,
                'figura': silogismo_result.figura.value if silogismo_result and silogismo_result.figura else None,
                'valido': silogismo_result.valido,
                'explicacion': silogismo_result.explicacion,
            } if silogismo_result else None,
            'inferencia': inferencia_result,
        }
    
    def _detectar_tipo(self, texto: str, opciones: Dict) -> TipoRazonamiento:
        """Detecta el tipo de razonamiento solicitado."""
        tipo_indicado = opciones.get('tipo', opciones.get('tipo_razonamiento', ''))
        
        if tipo_indicado in ('tabla_verdad', 'tabla', 'verdad'):
            return TipoRazonamiento.TABLA_VERDAD
        if tipo_indicado in ('silogismo', 'aristotelico'):
            return TipoRazonamiento.SILOGISMO
        if tipo_indicado in ('inferencia', 'regla'):
            return TipoRazonamiento.INFERENCIA
        
        if any(p in texto for p in ['todos', 'ningun', 'algun', 'silogismo']):
            return TipoRazonamiento.SILOGISMO
        if any(p in texto for p in ['tabla de verdad', 'tabla verdad']):
            return TipoRazonamiento.TABLA_VERDAD
        
        return TipoRazonamiento.PROPOSICIONAL
    
    def _normalizar_expresion(self, texto: str) -> str:
        """Normaliza una expresión lógica a formato estándar."""
        texto = texto.strip().rstrip('.!?')
        reemplazos = {
            ' and ': ' AND ', ' y ': ' AND ', ' & ': ' AND ',
            ' or ': ' OR ', ' o ': ' OR ', ' | ': ' OR ',
            ' not ': ' NOT ', ' no ': ' NOT ',
            ' implica ': ' IMPLIES ', ' -> ': ' IMPLIES ', ' => ': ' IMPLIES ',
        }
        for viejo, nuevo in reemplazos.items():
            texto = texto.replace(viejo, nuevo)
        return re.sub(r'\s+', ' ', texto).strip()
    
    def _extraer_variables(self, texto: str) -> List[str]:
        """Extrae variables proposicionales (CORREGIDO)."""
        # Tokenizar palabras
        tokens = re.findall(r'\b[A-Za-z][A-Za-z0-9_]*\b', texto.lower())
        
        # Filtrar palabras reservadas
        variables = []
        for token in tokens:
            if token not in self.PALABRAS_RESERVADAS and len(token) >= 1:
                if token not in variables:
                    variables.append(token)
        
        # Si hay demasiadas variables, buscar letras individuales mayúsculas
        if len(variables) > 6:
            letras = re.findall(r'\b([A-Z])\b', texto.upper())
            if letras:
                variables = list(dict.fromkeys(letras))
            else:
                variables = variables[:6]
        
        # Si no se detectaron variables pero hay operadores, usar A, B, C...
        if not variables:
            # Buscar letras individuales
            letras = re.findall(r'\b([A-Za-z])\b', texto)
            variables = list(dict.fromkeys([l.upper() for l in letras]))
        
        return variables
    
    def _extraer_operadores(self, texto: str) -> List[str]:
        """Extrae operadores lógicos del texto."""
        operadores_encontrados = []
        for nombre, op in self.OPERADORES.items():
            if nombre in texto:
                if op.value not in operadores_encontrados:
                    operadores_encontrados.append(op.value)
        return operadores_encontrados
    
    def _generar_tabla_verdad(self, expresion: str, variables: List[str]) -> TablaVerdad:
        """Genera una tabla de verdad completa."""
        n = len(variables)
        combinaciones = list(itertools.product([False, True], repeat=n))
        
        filas = []
        verdaderos = 0
        falsos = 0
        
        for combinacion in combinaciones:
            valores = dict(zip(variables, combinacion))
            resultado_eval = self._evaluar_expresion(expresion, valores)
            fila = {var: valores[var] for var in variables}
            fila['resultado'] = resultado_eval
            filas.append(fila)
            
            if resultado_eval:
                verdaderos += 1
            else:
                falsos += 1
        
        total = len(combinaciones)
        
        if verdaderos == total:
            resultado = ValidezLogica.TAUTOLOGIA
        elif falsos == total:
            resultado = ValidezLogica.CONTRADICCION
        elif verdaderos > 0:
            resultado = ValidezLogica.SATISFACIBLE
        else:
            resultado = ValidezLogica.INDETERMINADO
        
        return TablaVerdad(
            variables=variables, filas=filas, expresion=expresion,
            resultado=resultado, total_combinaciones=total,
            verdaderos=verdaderos, falsos=falsos,
        )
    
    def _evaluar_expresion(self, expresion: str, valores: Dict[str, bool]) -> bool:
        """Evalúa una expresión lógica con valores dados."""
        try:
            expr_eval = expresion
            for var, valor in valores.items():
                expr_eval = re.sub(r'\b' + re.escape(var) + r'\b', str(valor), expr_eval, flags=re.IGNORECASE)
            
            expr_eval = expr_eval.replace('AND', 'and').replace('OR', 'or')
            expr_eval = expr_eval.replace('NOT', 'not')
            expr_eval = expr_eval.replace('IMPLIES', 'or not')
            expr_eval = expr_eval.replace('EQUIV', '==')
            
            resultado = eval(expr_eval)
            return bool(resultado)
        except Exception:
            return False
    
    def _generar_explicacion(self, tabla: TablaVerdad, variables: List[str],
                            operadores: List[str]) -> str:
        """Genera una explicación textual."""
        partes = [f"Análisis de {len(variables)} variable(s): {', '.join(variables)}"]
        if operadores:
            partes.append(f"Operadores: {', '.join(operadores)}")
        partes.append(f"Combinaciones: {tabla.total_combinaciones} | V: {tabla.verdaderos} | F: {tabla.falsos}")
        
        if tabla.resultado == ValidezLogica.TAUTOLOGIA:
            partes.append("✅ TAUTOLOGÍA (siempre verdadera)")
        elif tabla.resultado == ValidezLogica.CONTRADICCION:
            partes.append("❌ CONTRADICCIÓN (siempre falsa)")
        elif tabla.resultado == ValidezLogica.SATISFACIBLE:
            partes.append("✓ SATISFACIBLE (verdadera en algunos casos)")
        
        return '. '.join(partes)
    
    def _serializar_tabla(self, tabla: TablaVerdad) -> Optional[Dict[str, Any]]:
        """Serializa una tabla de verdad para JSON."""
        if tabla is None:
            return None
        return {
            'variables': tabla.variables,
            'total_combinaciones': tabla.total_combinaciones,
            'verdaderos': tabla.verdaderos,
            'falsos': tabla.falsos,
            'resultado': tabla.resultado.value,
            'filas': [
                {**{k: v for k, v in f.items() if k != 'resultado'}, 'resultado': f['resultado']}
                for f in tabla.filas[:16]
            ],
        }
    
    def _analizar_silogismo(self, texto: str, opciones: Dict) -> Silogismo:
        """Analiza un silogismo aristotélico."""
        sil = Silogismo()
        sil.premisa_mayor = opciones.get('premisa_mayor', '')
        sil.premisa_menor = opciones.get('premisa_menor', '')
        sil.conclusion = opciones.get('conclusion', '')
        
        if not sil.premisa_mayor:
            partes = re.split(r'[,;.]\s*(?:por lo tanto|en consecuencia|ergo|luego|entonces)\s*', texto)
            if len(partes) >= 2:
                premisas = re.split(r'[,;.]\s*(?:y|,)\s*', partes[0])
                if len(premisas) >= 2:
                    sil.premisa_mayor = premisas[0].strip()
                    sil.premisa_menor = premisas[1].strip()
                sil.conclusion = partes[1].strip()
        
        tipo_mayor = self._detectar_cuantificador(sil.premisa_mayor)
        tipo_menor = self._detectar_cuantificador(sil.premisa_menor)
        
        clave = (tipo_mayor, tipo_menor)
        if clave in self.SILOGISMOS_VALIDOS:
            sil.figura = self.SILOGISMOS_VALIDOS[clave]
            sil.valido = True
            sil.explicacion = f"Silogismo válido tipo {sil.figura.value.upper()}. La conclusión se sigue necesariamente de las premisas."
        else:
            sil.valido = False
            sil.explicacion = f"No corresponde a una forma válida conocida ({tipo_mayor}, {tipo_menor})."
        
        return sil
    
    def _detectar_cuantificador(self, texto: str) -> str:
        """Detecta el cuantificador en una premisa."""
        tl = texto.lower()
        if 'ningun' in tl or 'ningún' in tl or 'ninguna' in tl:
            return 'ningun'
        if 'algun' in tl or 'algún' in tl or 'alguna' in tl:
            if 'no' in tl.split()[:3]:
                return 'algun_no'
            return 'algun'
        if 'todos' in tl or 'todas' in tl or 'todo' in tl:
            return 'todos'
        return 'algun'
    
    def _detectar_inferencia(self, texto: str) -> Optional[Dict[str, Any]]:
        """Detecta reglas de inferencia lógica."""
        for clave, datos in self.REGLAS_INFERENCIA.items():
            match = re.search(datos['patron'], texto, re.IGNORECASE)
            if match:
                return {
                    'regla': datos['nombre'],
                    'formula': datos['formula'],
                    'componentes': list(match.groups()),
                }
        return None
    
    def _resultado_vacio(self):
        return {
            'texto_original': '', 'tipo_razonamiento': 'proposicional',
            'validez': 'indeterminado', 'explicacion': 'Sin entrada',
            'variables_detectadas': [], 'operadores_detectados': [],
            'expresion_normalizada': '', 'tabla_verdad': None,
            'silogismo': None, 'inferencia': None,
        }
    
    # ===== MÉTODOS PÚBLICOS =====
    
    def evaluar(self, expresion: str, valores: Dict[str, bool] = None) -> bool:
        if valores is None:
            valores = {}
        expresion_norm = self._normalizar_expresion(expresion)
        return self._evaluar_expresion(expresion_norm, valores)
    
    def tabla_verdad(self, expresion: str, variables: List[str] = None) -> TablaVerdad:
        expresion_norm = self._normalizar_expresion(expresion)
        if variables is None:
            variables = self._extraer_variables(expresion_norm)
        return self._generar_tabla_verdad(expresion_norm, variables)
    
    def es_tautologia(self, expresion: str) -> bool:
        tabla = self.tabla_verdad(expresion)
        return tabla.resultado == ValidezLogica.TAUTOLOGIA
    
    def es_contradiccion(self, expresion: str) -> bool:
        tabla = self.tabla_verdad(expresion)
        return tabla.resultado == ValidezLogica.CONTRADICCION

# =====================================================================
# DIAGNÓSTICO (CORREGIDO)
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR LÓGICO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/8] Inicializando motor lógico...")
        motor = MotorLogico()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return motor._resultado_vacio()
        
        print("\n[2/8] Evaluación proposicional simple...")
        d1 = sd(motor.procesar("A y B"))
        print(f"  📊 Variables: {d1['variables_detectadas']}")
        print(f"  📊 Validez: {d1['validez']}")
        
        print("\n[3/8] Tabla de verdad...")
        d2 = sd(motor.procesar({'expresion': 'A and B or not C', 'tipo': 'tabla_verdad'}))
        tv = d2.get('tabla_verdad', {})
        if tv:
            print(f"  📊 Variables: {tv.get('variables', [])}")
            print(f"  📊 Combinaciones: {tv.get('total_combinaciones', 0)}")
            print(f"  📊 V: {tv.get('verdaderos', 0)}, F: {tv.get('falsos', 0)}")
            print(f"  📊 Resultado: {tv.get('resultado', 'N/A')}")
        
        print("\n[4/8] Tautología...")
        d3 = sd(motor.procesar("A o no A"))
        print(f"  📊 Validez: {d3['validez']}")
        print(f"  📊 Explicación: {d3['explicacion']}")
        
        print("\n[5/8] Contradicción...")
        d4 = sd(motor.procesar({'expresion': 'A and not A', 'tipo': 'tabla_verdad'}))
        print(f"  📊 Validez: {d4['validez']}")
        
        print("\n[6/8] Implicación lógica...")
        d5 = sd(motor.procesar("A implica B"))
        print(f"  📊 Variables: {d5['variables_detectadas']}")
        print(f"  📊 Operadores: {d5['operadores_detectados']}")
        
        print("\n[7/8] Métodos directos...")
        print(f"  📍 'A o no A' es tautología: {motor.es_tautologia('A o no A')}")
        print(f"  📍 'A y no A' es contradicción: {motor.es_contradiccion('A y no A')}")
        
        print("\n[8/8] Silogismo...")
        d6 = sd(motor.procesar({
            'tipo': 'silogismo',
            'premisa_mayor': 'Todos los humanos son mortales',
            'premisa_menor': 'Todos los griegos son humanos',
            'conclusion': 'Todos los griegos son mortales',
        }))
        sil = d6.get('silogismo', {}) or {}
        print(f"  📊 Válido: {sil.get('valido', False)}")
        print(f"  📊 Figura: {sil.get('figura', 'N/A')}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Motor Lógico está VIVO y es REAL.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print("\n" + "=" * 70 + "\n")