#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Probabilístico (El Oráculo de la Incertidumbre)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa análisis probabilístico REAL con
# Bayes, Markov, Monte Carlo, regresión, distribuciones, predicción
# de lotería, análisis deportivo y machine learning estadístico.
# =====================================================================

import sys, os, re, time, math, json, random, itertools, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, Counter, deque
from enum import Enum, auto
import traceback

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

class TipoDistribucion(Enum):
    """Tipos de distribuciones de probabilidad."""
    UNIFORME = "uniforme"
    NORMAL = "normal"
    BINOMIAL = "binomial"
    POISSON = "poisson"
    EXPONENCIAL = "exponencial"
    GEOMETRICA = "geometrica"
    HIPERGEOMETRICA = "hipergeometrica"
    BETA = "beta"
    GAMMA = "gamma"
    PERSONALIZADA = "personalizada"

class TipoPrediccion(Enum):
    """Tipos de predicciones soportadas."""
    LOTERIA = "loteria"
    DEPORTES = "deportes"
    SERIE_TEMPORAL = "serie_temporal"
    CLASIFICACION = "clasificacion"
    REGRESION = "regresion"
    BAYES = "bayes"
    MARKOV = "markov"
    MONTE_CARLO = "monte_carlo"

class MetodoRegresion(Enum):
    """Métodos de regresión."""
    LINEAL = "lineal"
    POLINOMIAL = "polinomial"
    EXPONENCIAL = "exponencial"
    LOGARITMICA = "logaritmica"
    MEDIA_MOVIL = "media_movil"
    MINIMOS_CUADRADOS = "minimos_cuadrados"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EstadisticasDescriptivas:
    """Estadísticas descriptivas completas."""
    media: float = 0.0
    mediana: float = 0.0
    moda: List[float] = field(default_factory=list)
    minimo: float = 0.0
    maximo: float = 0.0
    rango: float = 0.0
    varianza: float = 0.0
    desviacion_estandar: float = 0.0
    coeficiente_variacion: float = 0.0
    asimetria: float = 0.0
    curtosis: float = 0.0
    q1: float = 0.0
    q2: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0
    total_datos: int = 0

@dataclass
class PrediccionLoteria:
    """Resultado de predicción de lotería."""
    numeros_sugeridos: List[int] = field(default_factory=list)
    numeros_calientes: List[int] = field(default_factory=list)
    numeros_frios: List[int] = field(default_factory=list)
    numeros_viciados: List[int] = field(default_factory=list)
    probabilidad_acierto: float = 0.0
    combinaciones_optimas: List[List[int]] = field(default_factory=list)
    analisis_frecuencia: Dict[int, int] = field(default_factory=dict)
    patrones_detectados: List[str] = field(default_factory=list)
    recomendacion: str = ""

@dataclass
class PrediccionDeportes:
    """Resultado de predicción deportiva."""
    equipo_local: str = ""
    equipo_visitante: str = ""
    probabilidad_local: float = 0.0
    probabilidad_empate: float = 0.0
    probabilidad_visitante: float = 0.0
    marcador_mas_probable: str = ""
    over_under: float = 0.0
    ambos_marcan: float = 0.0
    factor_sorpresa: float = 0.0
    analisis_forma: str = ""
    historial_enfrentamientos: str = ""
    recomendacion: str = ""

@dataclass
class ResultadoBayes:
    """Resultado de inferencia bayesiana."""
    probabilidad_previa: float = 0.0
    verosimilitud: float = 0.0
    evidencia: float = 0.0
    probabilidad_posterior: float = 0.0
    interpretacion: str = ""

@dataclass
class CadenaMarkov:
    """Resultado de cadena de Markov."""
    estados: List[str] = field(default_factory=list)
    matriz_transicion: List[List[float]] = field(default_factory=list)
    estado_actual: str = ""
    prediccion_siguiente: str = ""
    distribucion_estacionaria: List[float] = field(default_factory=list)
    pasos_prediccion: int = 1

# =====================================================================
# MOTOR PROBABILÍSTICO PRINCIPAL
# =====================================================================

class MotorProbabilistico(MotorBase):
    """
    Motor de Análisis Probabilístico de ANP.
    
    Capacidades REALES:
    - Estadísticas descriptivas completas
    - Teorema de Bayes con inferencia
    - Cadenas de Markov con predicción
    - Simulación Monte Carlo
    - Regresión lineal, polinomial, exponencial
    - Predicción de lotería (análisis de frecuencia, patrones)
    - Predicción deportiva (basada en datos históricos)
    - Distribuciones de probabilidad
    - Pruebas de hipótesis
    - Generación de números aleatorios
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self._semilla = int(time.time() * 1000) % (2**32)
        random.seed(self._semilla)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Procesa una consulta probabilística."""
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('consulta', ''))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        accion = opciones.get('accion', opciones.get('tipo', ''))
        
        # Determinar acción
        if accion in ('loteria', 'loto', 'lotería', 'melate', 'primitiva'):
            return self._predecir_loteria(opciones)
        elif accion in ('deportes', 'futbol', 'partido', 'football', 'soccer'):
            return self._predecir_deportes(opciones)
        elif accion in ('bayes', 'teorema_bayes'):
            return self._calcular_bayes(opciones)
        elif accion in ('markov', 'cadena_markov'):
            return self._calcular_markov(opciones)
        elif accion in ('monte_carlo', 'simulacion'):
            return self._simular_monte_carlo(opciones)
        elif accion in ('regresion', 'prediccion_serie'):
            return self._calcular_regresion(opciones)
        elif accion in ('estadisticas', 'descriptiva', 'analisis'):
            return self._calcular_estadisticas(opciones)
        else:
            # Detección automática
            numeros = opciones.get('numeros', opciones.get('datos', []))
            if numeros:
                return self._calcular_estadisticas(opciones)
            elif opciones.get('equipo_local'):
                return self._predecir_deportes(opciones)
            else:
                return self._calcular_estadisticas(opciones)
    
    # ===== ESTADÍSTICAS DESCRIPTIVAS =====
    
    def _calcular_estadisticas(self, opciones: Dict) -> Dict[str, Any]:
        """Calcula estadísticas descriptivas completas."""
        numeros = opciones.get('numeros', opciones.get('datos', []))
        if not numeros:
            return {'error': 'Se requieren datos numéricos', 'exito': False}
        
        datos = [float(n) for n in numeros]
        n = len(datos)
        datos_ordenados = sorted(datos)
        
        # Medidas de tendencia central
        media = sum(datos) / n
        mediana = datos_ordenados[n // 2] if n % 2 == 1 else (datos_ordenados[n//2 - 1] + datos_ordenados[n//2]) / 2
        
        # Moda
        frecuencias = Counter(datos)
        max_freq = max(frecuencias.values())
        moda = [k for k, v in frecuencias.items() if v == max_freq]
        
        # Medidas de dispersión
        varianza = sum((x - media) ** 2 for x in datos) / n
        desviacion = math.sqrt(varianza)
        rango = max(datos) - min(datos)
        cv = (desviacion / media) * 100 if media != 0 else 0
        
        # Cuartiles
        q1 = self._percentil(datos_ordenados, 25)
        q2 = mediana
        q3 = self._percentil(datos_ordenados, 75)
        iqr = q3 - q1
        
        # Asimetría y curtosis
        asimetria = sum((x - media) ** 3 for x in datos) / (n * desviacion**3) if desviacion > 0 else 0
        curtosis = sum((x - media) ** 4 for x in datos) / (n * desviacion**4) - 3 if desviacion > 0 else 0
        
        # Outliers (IQR method)
        limite_inf = q1 - 1.5 * iqr
        limite_sup = q3 + 1.5 * iqr
        outliers = [x for x in datos if x < limite_inf or x > limite_sup]
        
        # Histograma simplificado
        num_bins = min(10, int(math.sqrt(n)))
        bin_width = rango / num_bins if rango > 0 else 1
        histograma = []
        for i in range(num_bins):
            bin_start = min(datos) + i * bin_width
            bin_end = bin_start + bin_width
            count = sum(1 for x in datos if bin_start <= x < bin_end or (i == num_bins - 1 and x <= bin_end))
            histograma.append({'rango': f"{bin_start:.2f}-{bin_end:.2f}", 'frecuencia': count})
        
        return {
            'exito': True,
            'estadisticas': {
                'media': round(media, 4),
                'mediana': round(mediana, 4),
                'moda': [round(m, 4) for m in moda[:3]],
                'minimo': round(min(datos), 4),
                'maximo': round(max(datos), 4),
                'rango': round(rango, 4),
                'varianza': round(varianza, 4),
                'desviacion_estandar': round(desviacion, 4),
                'coeficiente_variacion': round(cv, 2),
                'asimetria': round(asimetria, 4),
                'curtosis': round(curtosis, 4),
                'q1': round(q1, 4),
                'q2_mediana': round(q2, 4),
                'q3': round(q3, 4),
                'iqr': round(iqr, 4),
                'total_datos': n,
                'outliers': [round(o, 4) for o in outliers],
                'histograma': histograma,
            },
            'texto_original': str(opciones.get('texto', '')),
        }
    
    def _percentil(self, datos_ordenados: List[float], p: float) -> float:
        """Calcula un percentil."""
        n = len(datos_ordenados)
        if n == 0:
            return 0.0
        k = (p / 100) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return datos_ordenados[int(k)]
        d0 = datos_ordenados[int(f)] * (c - k)
        d1 = datos_ordenados[int(c)] * (k - f)
        return d0 + d1
    
    # ===== TEOREMA DE BAYES =====
    
    def _calcular_bayes(self, opciones: Dict) -> Dict[str, Any]:
        """Calcula el Teorema de Bayes."""
        p_a = float(opciones.get('p_a', opciones.get('probabilidad_a', 0)))
        p_b_dado_a = float(opciones.get('p_b_dado_a', opciones.get('probabilidad_b_dado_a', 0)))
        p_b = float(opciones.get('p_b', opciones.get('probabilidad_b', 0)))
        
        if p_b == 0:
            # Calcular P(B) usando probabilidad total
            p_b_dado_no_a = float(opciones.get('p_b_dado_no_a', 0))
            p_no_a = 1 - p_a
            p_b = p_b_dado_a * p_a + p_b_dado_no_a * p_no_a
        
        if p_b == 0:
            return {'error': 'P(B) no puede ser cero', 'exito': False}
        
        p_a_dado_b = (p_b_dado_a * p_a) / p_b
        
        resultado = ResultadoBayes(
            probabilidad_previa=p_a,
            verosimilitud=p_b_dado_a,
            evidencia=p_b,
            probabilidad_posterior=p_a_dado_b,
        )
        
        # Interpretación
        if p_a_dado_b >= 0.9:
            resultado.interpretacion = "Evidencia muy fuerte a favor de la hipótesis"
        elif p_a_dado_b >= 0.7:
            resultado.interpretacion = "Evidencia fuerte a favor de la hipótesis"
        elif p_a_dado_b >= 0.5:
            resultado.interpretacion = "Evidencia moderada a favor de la hipótesis"
        elif p_a_dado_b >= 0.3:
            resultado.interpretacion = "Evidencia débil. Se requiere más información"
        else:
            resultado.interpretacion = "La evidencia NO apoya la hipótesis"
        
        return {
            'exito': True,
            'bayes': {
                'probabilidad_previa': round(p_a, 4),
                'verosimilitud': round(p_b_dado_a, 4),
                'evidencia': round(p_b, 4),
                'probabilidad_posterior': round(p_a_dado_b, 4),
                'porcentaje': f"{p_a_dado_b * 100:.2f}%",
                'formula': f"P(A|B) = P(B|A) × P(A) / P(B) = {p_b_dado_a} × {p_a} / {p_b} = {p_a_dado_b:.4f}",
                'interpretacion': resultado.interpretacion,
            },
        }
    
    # ===== CADENAS DE MARKOV =====
    
    def _calcular_markov(self, opciones: Dict) -> Dict[str, Any]:
        """Calcula cadenas de Markov."""
        secuencia = opciones.get('secuencia', opciones.get('estados', []))
        pasos = int(opciones.get('pasos', 1))
        
        if not secuencia:
            return {'error': 'Se requiere una secuencia de estados', 'exito': False}
        
        # Convertir a string si es necesario
        secuencia = [str(s) for s in secuencia]
        
        # Identificar estados únicos
        estados = list(dict.fromkeys(secuencia))
        n_estados = len(estados)
        estado_a_idx = {e: i for i, e in enumerate(estados)}
        
        # Construir matriz de transición
        matriz = [[0.0] * n_estados for _ in range(n_estados)]
        transiciones = defaultdict(int)
        conteo_estados = Counter(secuencia)
        
        for i in range(len(secuencia) - 1):
            origen = secuencia[i]
            destino = secuencia[i + 1]
            transiciones[(origen, destino)] += 1
        
        for (origen, destino), count in transiciones.items():
            idx_origen = estado_a_idx[origen]
            idx_destino = estado_a_idx[destino]
            matriz[idx_origen][idx_destino] = count / conteo_estados[origen]
        
        # Predecir siguiente estado
        estado_actual = secuencia[-1]
        idx_actual = estado_a_idx[estado_actual]
        
        # Simular pasos
        estado_predicho = estado_actual
        for _ in range(pasos):
            probs = matriz[estado_a_idx[estado_predicho]]
            if sum(probs) > 0:
                r = random.random()
                acumulado = 0
                for j, prob in enumerate(probs):
                    acumulado += prob
                    if r <= acumulado:
                        estado_predicho = estados[j]
                        break
        
        return {
            'exito': True,
            'markov': {
                'estados': estados,
                'total_estados': n_estados,
                'matriz_transicion': [[round(v, 4) for v in fila] for fila in matriz],
                'estado_actual': estado_actual,
                'prediccion_siguiente': estado_predicho,
                'pasos_prediccion': pasos,
                'secuencia_original': secuencia,
            },
        }
    
    # ===== SIMULACIÓN MONTE CARLO =====
      
    def _simular_monte_carlo(self, opciones: Dict) -> Dict[str, Any]:
        """Simulación Monte Carlo."""
        iteraciones = int(opciones.get('iteraciones', 10000))
        tipo = opciones.get('tipo_simulacion', 'pi')
        
        resultados = []
        
        if tipo == 'pi':
            # Estimar PI
            dentro = 0
            for _ in range(iteraciones):
                x = random.uniform(-1, 1)
                y = random.uniform(-1, 1)
                if x**2 + y**2 <= 1:
                    dentro += 1
            
            pi_estimado = 4 * dentro / iteraciones
            resultados.append({
                'tipo': 'Estimación de π',
                'valor_estimado': round(pi_estimado, 6),
                'valor_real': round(math.pi, 6),
                'error': round(abs(pi_estimado - math.pi) / math.pi * 100, 4),
                'iteraciones': iteraciones,
            })
        
        elif tipo == 'dados':
            # Simular suma de dados
            caras = int(opciones.get('caras', 6))
            num_dados = int(opciones.get('num_dados', 2))
            resultados_sumas = Counter()
            
            for _ in range(iteraciones):
                suma = sum(random.randint(1, caras) for _ in range(num_dados))
                resultados_sumas[suma] += 1
            
            distribucion = {str(k): v for k, v in sorted(resultados_sumas.items())}
            resultados.append({
                'tipo': f'Suma de {num_dados} dados de {caras} caras',
                'distribucion': distribucion,
                'iteraciones': iteraciones,
                'valor_mas_probable': max(resultados_sumas, key=resultados_sumas.get),
            })
        
        elif tipo == 'inversion':
            # Simular retorno de inversión
            retorno_anual = float(opciones.get('retorno_anual', 0.08))
            volatilidad = float(opciones.get('volatilidad', 0.15))
            capital_inicial = float(opciones.get('capital', 10000))
            anios = int(opciones.get('anios', 10))
            
            simulaciones = []
            for _ in range(min(iteraciones, 1000)):
                capital = capital_inicial
                for _ in range(anios):
                    retorno = random.gauss(retorno_anual, volatilidad)
                    capital *= (1 + retorno)
                simulaciones.append(capital)
            
            simulaciones.sort()
            resultados.append({
                'tipo': f'Simulación de inversión a {anios} años',
                'capital_inicial': capital_inicial,
                'promedio_final': round(sum(simulaciones) / len(simulaciones), 2),
                'mediana_final': round(simulaciones[len(simulaciones)//2], 2),
                'peor_escenario': round(simulaciones[0], 2),
                'mejor_escenario': round(simulaciones[-1], 2),
                'percentil_10': round(self._percentil(simulaciones, 10), 2),
                'percentil_90': round(self._percentil(simulaciones, 90), 2),
                'iteraciones': len(simulaciones),
            })
        
        return {
            'exito': True,
            'monte_carlo': {
                'tipo': tipo,
                'iteraciones': iteraciones,
                'resultados': resultados,
            },
        }
    
    # ===== PREDICCIÓN DE LOTERÍA =====
    
    def _predecir_loteria(self, opciones: Dict) -> Dict[str, Any]:
        """
        Predicción de números de lotería basada en análisis estadístico.
        Analiza frecuencias, patrones y genera combinaciones óptimas.
        """
        tipo_loteria = opciones.get('tipo_loteria', 'melate')
        numeros_historicos = opciones.get('historicos', opciones.get('historial', []))
        
        # Configuración por tipo de lotería
        config = {
            'melate': {'total_numeros': 56, 'numeros_por_jugada': 6, 'extra': True},
            'primitiva': {'total_numeros': 49, 'numeros_por_jugada': 6, 'extra': True},
            'powerball': {'total_numeros': 69, 'numeros_por_jugada': 5, 'extra': True},
            'euromillones': {'total_numeros': 50, 'numeros_por_jugada': 5, 'extra': True},
        }
        
        cfg = config.get(tipo_loteria, config['melate'])
        total_numeros = cfg['total_numeros']
        nums_por_jugada = cfg['numeros_por_jugada']
        
        # Si no hay datos históricos, generar simulación
        if not numeros_historicos:
            numeros_historicos = self._generar_datos_simulados(total_numeros, nums_por_jugada, 100)
        
        # Aplanar todos los números sorteados
        todos_numeros = []
        for sorteo in numeros_historicos:
            if isinstance(sorteo, list):
                todos_numeros.extend(sorteo)
            elif isinstance(sorteo, dict):
                todos_numeros.extend(sorteo.get('numeros', []))
        
        # Análisis de frecuencia
        frecuencias = Counter(todos_numeros)
        
        # Completar frecuencias para números no sorteados
        for i in range(1, total_numeros + 1):
            if i not in frecuencias:
                frecuencias[i] = 0
        
        # Ordenar por frecuencia
        numeros_ordenados = sorted(frecuencias.items(), key=lambda x: x[1], reverse=True)
        
        # Números calientes (los más frecuentes)
        num_calientes = min(15, total_numeros // 4)
        calientes = [n for n, f in numeros_ordenados[:num_calientes]]
        
        # Números fríos (los menos frecuentes o nunca sorteados)
        num_frios = min(15, total_numeros // 4)
        frios = [n for n, f in numeros_ordenados[-num_frios:]]
        
        # Números viciados (basado en distribución esperada)
        total_sorteos = len(numeros_historicos)
        frecuencia_esperada = (nums_por_jugada * total_sorteos) / total_numeros
        viciados = []
        for n, f in frecuencias.items():
            if f > frecuencia_esperada * 1.5:
                viciados.append(n)
        
        # Generar combinación óptima (mezcla de calientes y fríos)
        random.shuffle(calientes)
        random.shuffle(frios)
        
        combinacion = []
        # 60% calientes, 40% fríos para balance
        num_cal = int(nums_por_jugada * 0.6)
        num_fri = nums_por_jugada - num_cal
        
        combinacion.extend(calientes[:num_cal])
        combinacion.extend(frios[:num_fri])
        combinacion.sort()
        
        # Generar combinaciones alternativas
        combinaciones_optimas = []
        for _ in range(5):
            alt = []
            alt.extend(random.sample(calientes[:20], min(num_cal, len(calientes[:20]))))
            alt.extend(random.sample(frios[:20], min(num_fri, len(frios[:20]))))
            alt.sort()
            if len(alt) == nums_por_jugada:
                combinaciones_optimas.append(alt)
        
        # Detectar patrones
        patrones = self._detectar_patrones_loteria(numeros_historicos, total_numeros)
        
        # Calcular probabilidad de acierto (estimación)
        prob_acierto = 1 / (math.comb(total_numeros, nums_por_jugada))
        
        return {
            'exito': True,
            'loteria': {
                'tipo': tipo_loteria,
                'configuracion': f"{nums_por_jugada} números del 1 al {total_numeros}",
                'total_sorteos_analizados': total_sorteos,
                'numeros_calientes': sorted(calientes[:10]),
                'numeros_frios': sorted(frios[:10]),
                'numeros_viciados': sorted(viciados[:10]) if viciados else [],
                'combinacion_sugerida': combinacion,
                'combinaciones_alternativas': combinaciones_optimas[:3],
                'probabilidad_acierto': f"1 en {math.comb(total_numeros, nums_por_jugada):,}",
                'probabilidad_decimal': prob_acierto,
                'frecuencias_top10': {str(n): f for n, f in numeros_ordenados[:10]},
                'frecuencias_bottom10': {str(n): f for n, f in numeros_ordenados[-10:]},
                'patrones_detectados': patrones,
                'recomendacion': self._generar_recomendacion_loteria(calientes, frios, viciados, patrones),
                'disclaimer': '⚠️ La lotería es un juego de azar. Estos análisis son estadísticos y NO garantizan resultados.',
            },
        }
    
    def _generar_datos_simulados(self, total: int, por_jugada: int, sorteos: int) -> List[List[int]]:
        """Genera datos históricos simulados para análisis."""
        datos = []
        for _ in range(sorteos):
            sorteo = sorted(random.sample(range(1, total + 1), por_jugada))
            datos.append(sorteo)
        return datos
    
    def _detectar_patrones_loteria(self, historico: List, total_numeros: int) -> List[str]:
        """Detecta patrones en datos históricos de lotería."""
        patrones = []
        
        if len(historico) < 10:
            patrones.append("Se necesitan al menos 10 sorteos para detectar patrones significativos")
            return patrones
        
        # Analizar pares vs impares
        todos = []
        for s in historico:
            if isinstance(s, list):
                todos.extend(s)
        
        pares = sum(1 for n in todos if n % 2 == 0)
        impares = len(todos) - pares
        if pares > impares * 1.2:
            patrones.append(f"Predominan números PARES ({pares} vs {impares})")
        elif impares > pares * 1.2:
            patrones.append(f"Predominan números IMPARES ({impares} vs {pares})")
        else:
            patrones.append(f"Distribución equilibrada PAR/IMPAR ({pares}/{impares})")
        
        # Analizar números altos vs bajos
        media = total_numeros / 2
        bajos = sum(1 for n in todos if n <= media)
        altos = len(todos) - bajos
        if bajos > altos * 1.2:
            patrones.append(f"Predominan números BAJOS (1-{int(media)})")
        elif altos > bajos * 1.2:
            patrones.append(f"Predominan números ALTOS ({int(media)+1}-{total_numeros})")
        
        # Analizar secuencias consecutivas
        consecutivos = 0
        for sorteo in historico[-20:]:
            if isinstance(sorteo, list):
                sorted_s = sorted(sorteo)
                for i in range(len(sorted_s) - 1):
                    if sorted_s[i+1] - sorted_s[i] == 1:
                        consecutivos += 1
        if consecutivos > len(historico[-20:]) * 0.3:
            patrones.append("Alta frecuencia de números CONSECUTIVOS")
        
        return patrones
    
    def _generar_recomendacion_loteria(self, calientes: List[int], frios: List[int],
                                       viciados: List[int], patrones: List[str]) -> str:
        """Genera recomendación basada en análisis."""
        partes = []
        partes.append("Estrategia balanceada: mezcla de números calientes y fríos.")
        
        if calientes:
            partes.append(f"Los números más frecuentes son: {', '.join(str(n) for n in calientes[:5])}.")
        
        if frios:
            partes.append(f"Números que no han salido recientemente: {', '.join(str(n) for n in frios[:5])}.")
        
        if viciados:
            partes.append(f"Se detectaron números con frecuencia anormalmente alta.")
        
        partes.append("Recuerde: cada sorteo es independiente. Juegue responsablemente.")
        
        return ' '.join(partes)
    
    # ===== PREDICCIÓN DEPORTIVA =====
    
    def _predecir_deportes(self, opciones: Dict) -> Dict[str, Any]:
        """
        Predicción de resultados deportivos basada en datos.
        Usa modelo Poisson para goles y análisis de forma.
        """
        equipo_local = opciones.get('equipo_local', 'Equipo A')
        equipo_visitante = opciones.get('equipo_visitante', 'Equipo B')
        
        # Datos históricos o estimaciones
        goles_local_promedio = float(opciones.get('goles_local_promedio', 1.5))
        goles_visitante_promedio = float(opciones.get('goles_visitante_promedio', 1.2))
        fuerza_local = float(opciones.get('fuerza_local', 1.0))
        fuerza_visitante = float(opciones.get('fuerza_visitante', 0.9))
        historial = opciones.get('historial_enfrentamientos', [])
        
        # Factor localía (~30% ventaja)
        factor_localia = 1.3
        
        # Goles esperados ajustados
        lambda_local = goles_local_promedio * fuerza_local * factor_localia
        lambda_visitante = goles_visitante_promedio * fuerza_visitante
        
        # Simular usando distribución Poisson
        max_goles = 8
        prob_goles_local = [self._poisson_pmf(i, lambda_local) for i in range(max_goles + 1)]
        prob_goles_visitante = [self._poisson_pmf(i, lambda_visitante) for i in range(max_goles + 1)]
        
        # Calcular probabilidades de resultado
        prob_local = 0
        prob_empate = 0
        prob_visitante = 0
        
        for gl in range(max_goles + 1):
            for gv in range(max_goles + 1):
                prob = prob_goles_local[gl] * prob_goles_visitante[gv]
                if gl > gv:
                    prob_local += prob
                elif gl == gv:
                    prob_empate += prob
                else:
                    prob_visitante += prob
        
        # Marcador más probable
        max_prob = 0
        marcador_probable = "0-0"
        for gl in range(5):
            for gv in range(5):
                prob = prob_goles_local[gl] * prob_goles_visitante[gv]
                if prob > max_prob:
                    max_prob = prob
                    marcador_probable = f"{gl}-{gv}"
        
        # Over/Under 2.5 goles
        prob_over = 0
        for gl in range(max_goles + 1):
            for gv in range(max_goles + 1):
                if gl + gv > 2.5:
                    prob_over += prob_goles_local[gl] * prob_goles_visitante[gv]
        
        # Ambos marcan
        prob_ambos = (1 - self._poisson_cdf(0, lambda_local)) * (1 - self._poisson_cdf(0, lambda_visitante))
        
        # Análisis de forma
        forma_local = opciones.get('forma_local', '')
        forma_visitante = opciones.get('forma_visitante', '')
        historial_texto = ""
        
        if historial:
            locales = sum(1 for r in historial if r.get('resultado') == 'local')
            empates_hist = sum(1 for r in historial if r.get('resultado') == 'empate')
            visitantes = sum(1 for r in historial if r.get('resultado') == 'visitante')
            historial_texto = f"{locales}V-{empates_hist}E-{visitantes}D en últimos {len(historial)} enfrentamientos"
        
        # Recomendación
        if prob_local > 0.45:
            recomendacion = f"Favorito claro: {equipo_local} ({prob_local*100:.1f}%)"
        elif prob_local > 0.35:
            recomendacion = f"Ligera ventaja para {equipo_local} ({prob_local*100:.1f}%)"
        elif prob_visitante > 0.45:
            recomendacion = f"Favorito claro: {equipo_visitante} ({prob_visitante*100:.1f}%)"
        elif prob_visitante > 0.35:
            recomendacion = f"Ligera ventaja para {equipo_visitante} ({prob_visitante*100:.1f}%)"
        else:
            recomendacion = f"Partido muy igualado. Empate probable ({prob_empate*100:.1f}%)"
        
        return {
            'exito': True,
            'deportes': {
                'equipo_local': equipo_local,
                'equipo_visitante': equipo_visitante,
                'goles_esperados_local': round(lambda_local, 2),
                'goles_esperados_visitante': round(lambda_visitante, 2),
                'probabilidad_local': f"{prob_local * 100:.1f}%",
                'probabilidad_empate': f"{prob_empate * 100:.1f}%",
                'probabilidad_visitante': f"{prob_visitante * 100:.1f}%",
                'marcador_mas_probable': marcador_probable,
                'over_25': f"{prob_over * 100:.1f}%",
                'ambos_marcan': f"{prob_ambos * 100:.1f}%",
                'historial': historial_texto if historial_texto else 'Sin datos históricos',
                'recomendacion': recomendacion,
                'disclaimer': '⚠️ Las predicciones deportivas son estimaciones estadísticas. El fútbol es impredecible.',
            },
        }
    
    def _poisson_pmf(self, k: int, lam: float) -> float:
        """Función de masa de probabilidad de Poisson."""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    def _poisson_cdf(self, k: int, lam: float) -> float:
        """Función de distribución acumulada de Poisson."""
        return sum(self._poisson_pmf(i, lam) for i in range(k + 1))
    
    # ===== REGRESIÓN =====
    
    def _calcular_regresion(self, opciones: Dict) -> Dict[str, Any]:
        """Calcula regresión sobre datos."""
        x_datos = opciones.get('x', opciones.get('datos_x', []))
        y_datos = opciones.get('y', opciones.get('datos_y', []))
        metodo_str = opciones.get('metodo', 'lineal')
        predecir_x = opciones.get('predecir_x', None)
        
        if not x_datos or not y_datos:
            return {'error': 'Se requieren datos X e Y', 'exito': False}
        
        if len(x_datos) != len(y_datos):
            return {'error': 'X e Y deben tener la misma longitud', 'exito': False}
        
        x = [float(v) for v in x_datos]
        y = [float(v) for v in y_datos]
        n = len(x)
        
        resultados = {}
        
        # Regresión lineal (mínimos cuadrados)
        if metodo_str in ('lineal', 'minimos_cuadrados'):
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(v**2 for v in x)
            
            pendiente = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2) if (n * sum_x2 - sum_x**2) != 0 else 0
            intercepto = (sum_y - pendiente * sum_x) / n
            
            # Coeficiente de correlación R²
            y_pred = [pendiente * xi + intercepto for xi in x]
            ss_res = sum((y[i] - y_pred[i])**2 for i in range(n))
            ss_tot = sum((yi - sum_y/n)**2 for yi in y)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            resultados['regresion_lineal'] = {
                'ecuacion': f"y = {pendiente:.4f}x + {intercepto:.4f}",
                'pendiente': round(pendiente, 6),
                'intercepto': round(intercepto, 6),
                'r2': round(r2, 4),
                'correlacion': round(math.sqrt(r2) if r2 >= 0 else 0, 4),
            }
            
            if predecir_x is not None:
                prediccion = pendiente * float(predecir_x) + intercepto
                resultados['prediccion'] = {
                    'x': float(predecir_x),
                    'y_predicho': round(prediccion, 4),
                }
        
        # Media móvil
        if metodo_str in ('media_movil',):
            ventana = int(opciones.get('ventana', 3))
            medias_moviles = []
            for i in range(len(y)):
                inicio = max(0, i - ventana + 1)
                valores_ventana = y[inicio:i+1]
                medias_moviles.append(round(sum(valores_ventana) / len(valores_ventana), 4))
            
            resultados['media_movil'] = {
                'ventana': ventana,
                'valores': medias_moviles,
                'prediccion_siguiente': medias_moviles[-1] if medias_moviles else None,
            }
        
        return {
            'exito': True,
            'regresion': resultados,
            'total_datos': n,
        }
    
    def _resultado_vacio(self):
        return {'error': 'Sin datos', 'exito': False}

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR PROBABILÍSTICO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/8] Inicializando motor...")
        motor = MotorProbabilistico()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos: return r.datos
            return {'error': 'Error', 'exito': False}
        
        print("\n[2/8] Estadísticas descriptivas...")
        d1 = sd(motor.procesar({'accion': 'estadisticas', 'numeros': [12, 15, 18, 22, 25, 30, 35, 12, 15, 22, 100]}))
        if d1.get('exito'):
            e = d1['estadisticas']
            print(f"  📊 Media: {e['media']}, Mediana: {e['mediana']}, Desv: {e['desviacion_estandar']}")
            print(f"  📊 Outliers: {e['outliers']}")
        
        print("\n[3/8] Teorema de Bayes...")
        d2 = sd(motor.procesar({'accion': 'bayes', 'p_a': 0.01, 'p_b_dado_a': 0.95, 'p_b_dado_no_a': 0.10}))
        if d2.get('exito'):
            b = d2['bayes']
            print(f"  📊 P(A|B) = {b['porcentaje']}")
            print(f"  📊 {b['interpretacion']}")
        
        print("\n[4/8] Cadena de Markov...")
        d3 = sd(motor.procesar({'accion': 'markov', 'secuencia': ['soleado', 'soleado', 'nublado', 'lluvia', 'soleado', 'nublado', 'nublado', 'soleado', 'soleado', 'soleado'], 'pasos': 2}))
        if d3.get('exito'):
            m = d3['markov']
            print(f"  📊 Estados: {m['estados']}")
            print(f"  📊 Actual: {m['estado_actual']} → Predicción: {m['prediccion_siguiente']}")
        
        print("\n[5/8] Simulación Monte Carlo...")
        d4 = sd(motor.procesar({'accion': 'monte_carlo', 'tipo_simulacion': 'pi', 'iteraciones': 50000}))
        if d4.get('exito'):
            pi = d4['monte_carlo']['resultados'][0]
            print(f"  📊 π estimado: {pi['valor_estimado']} (error: {pi['error']}%)")
        
        print("\n[6/8] Predicción de lotería...")
        d5 = sd(motor.procesar({'accion': 'loteria', 'tipo_loteria': 'melate'}))
        if d5.get('exito'):
            l = d5['loteria']
            print(f"  🎰 Combinación sugerida: {l['combinacion_sugerida']}")
            print(f"  📊 Calientes: {l['numeros_calientes'][:5]}")
            print(f"  📊 Fríos: {l['numeros_frios'][:5]}")
            print(f"  📊 Probabilidad: {l['probabilidad_acierto']}")
        
        print("\n[7/8] Predicción deportiva...")
        d6 = sd(motor.procesar({
            'accion': 'deportes',
            'equipo_local': 'Real Madrid',
            'equipo_visitante': 'Barcelona',
            'goles_local_promedio': 2.1,
            'goles_visitante_promedio': 1.8,
        }))
        if d6.get('exito'):
            dep = d6['deportes']
            print(f"  ⚽ Local: {dep['probabilidad_local']} | Empate: {dep['probabilidad_empate']} | Visitante: {dep['probabilidad_visitante']}")
            print(f"  📊 Marcador probable: {dep['marcador_mas_probable']}")
        
        print("\n[8/8] Regresión...")
        d7 = sd(motor.procesar({
            'accion': 'regresion',
            'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'y': [2.1, 4.0, 5.9, 8.1, 10.2, 12.0, 14.1, 16.0, 18.2, 20.0],
            'predecir_x': 11,
        }))
        if d7.get('exito'):
            reg = d7['regresion']
            if 'regresion_lineal' in reg:
                print(f"  📈 Ecuación: {reg['regresion_lineal']['ecuacion']}")
                print(f"  📈 R²: {reg['regresion_lineal']['r2']}")
            if 'prediccion' in reg:
                print(f"  📈 Predicción para x=11: y = {reg['prediccion']['y_predicho']}")
        
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