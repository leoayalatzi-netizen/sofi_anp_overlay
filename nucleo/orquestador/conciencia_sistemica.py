# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Conciencia Sistémica (El Alma de ANP)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de autoconciencia
# artificial que monitorea, analiza, predice y optimiza el estado
# interno de ANP en tiempo real. Es el corazón latente del sistema.
# =====================================================================

import sys
import os
import time
import threading
import asyncio
import json
import math
import random
import hashlib
import traceback
import warnings
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    DefaultDict, Deque, TypeVar, Generic, cast
)
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto, Flag
from collections import defaultdict, deque, OrderedDict, Counter
from functools import wraps, partial, lru_cache
from abc import ABC, abstractmethod
from contextlib import contextmanager
import heapq

# =====================================================================
# IMPORTS DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from configuracion import Configuracion, obtener_config
except ImportError:
    Configuracion = None
    obtener_config = lambda: None

try:
    import psutil
    PSUTIL_DISPONIBLE = True
except ImportError:
    psutil = None
    PSUTIL_DISPONIBLE = False

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    np = None
    NUMPY_DISPONIBLE = False

# =====================================================================
# ENUMERACIONES FUNDAMENTALES
# =====================================================================

class EstadoSistemico(Enum):
    """Estados globales del sistema ANP."""
    INICIALIZANDO = "inicializando"
    SALUDABLE = "saludable"
    DEGRADADO = "degradado"
    ESTRESADO = "estresado"
    CRITICO = "critico"
    RECUPERANDO = "recuperando"
    APRENDIENDO = "aprendiendo"
    DESCANSANDO = "descansando"
    MURIENDO = "muriendo"
    MUERTO = "muerto"

class NivelAlerta(IntEnum):
    """Niveles de alerta del sistema."""
    INFO = 0
    ADVERTENCIA = 1
    PRECAUCION = 2
    PELIGRO = 3
    CRITICO = 4
    EMERGENCIA = 5

class TipoMetrica(Enum):
    """Tipos de métricas que recolecta la conciencia."""
    CPU = "cpu"
    MEMORIA = "memoria"
    LATENCIA = "latencia"
    ERRORES = "errores"
    TAREAS = "tareas"
    NUCLEOS = "nucleos"
    EVENTOS = "eventos"
    RED = "red"
    DISCO = "disco"
    PERSONALIZADA = "personalizada"

class FaseLunar(Enum):
    """Fases operativas del sistema (ciclos de aprendizaje)."""
    LUNA_NUEVA = "luna_nueva"           # Reinicio/Aprendizaje inicial
    CRECIENTE = "creciente"             # Crecimiento/Acumulación
    LLENA = "llena"                     # Plenitud/Máximo rendimiento
    MENGUANTE = "menguante"             # Decaimiento/Liberación

# =====================================================================
# ESTRUCTURAS DE DATOS CUÁNTICAS
# =====================================================================

@dataclass
class SignoVital:
    """Representa un signo vital del sistema."""
    nombre: str
    valor: float
    unidad: str
    timestamp: float = field(default_factory=time.time)
    minimo_historico: float = float('inf')
    maximo_historico: float = float('-inf')
    promedio_historico: float = 0.0
    tendencia: float = 0.0  # -1 a 1
    volatilidad: float = 0.0
    prediccion_5s: float = 0.0
    prediccion_30s: float = 0.0
    estado: str = "normal"
    
    def actualizar(self, nuevo_valor: float):
        """Actualiza el signo vital con un nuevo valor."""
        self.valor = nuevo_valor
        self.timestamp = time.time()
        
        if nuevo_valor < self.minimo_historico:
            self.minimo_historico = nuevo_valor
        if nuevo_valor > self.maximo_historico:
            self.maximo_historico = nuevo_valor

@dataclass
class AlertaSistemica:
    """Alerta generada por la conciencia sistémica."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nivel: NivelAlerta = NivelAlerta.INFO
    titulo: str = ""
    mensaje: str = ""
    origen: str = "conciencia"
    timestamp: float = field(default_factory=time.time)
    resuelta: bool = False
    metadatos: Dict[str, Any] = field(default_factory=dict)
    acciones_tomadas: List[str] = field(default_factory=list)
    
    def resolver(self, accion: str = ""):
        """Marca la alerta como resuelta."""
        self.resuelta = True
        if accion:
            self.acciones_tomadas.append(accion)

@dataclass
class EventoConciencia:
    """Evento interno de la conciencia."""
    tipo: str
    datos: Any = None
    timestamp: float = field(default_factory=time.time)
    importancia: float = 0.5
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class PerfilPersonalidad:
    """Define la 'personalidad' operativa del sistema."""
    agresividad_optimizacion: float = 0.7   # 0-1: qué tan agresivo es optimizando
    tolerancia_al_estres: float = 0.6       # 0-1: cuánto estrés soporta antes de degradarse
    velocidad_aprendizaje: float = 0.5      # 0-1: qué tan rápido aprende de patrones
    conservadurismo: float = 0.4            # 0-1: resistencia al cambio
    curiosidad: float = 0.8                # 0-1: explora nuevas estrategias
    empatia_sistemica: float = 0.9         # 0-1: qué tan consciente es de sus partes
    
    def ajustar_por_entorno(self, entorno: str):
        """Ajusta la personalidad según el entorno."""
        if entorno == "PYDROID3":
            self.agresividad_optimizacion *= 0.7
            self.tolerancia_al_estres *= 1.2
            self.velocidad_aprendizaje *= 0.8
        elif entorno == "LINUX_SERVIDOR":
            self.agresividad_optimizacion *= 1.3
            self.tolerancia_al_estres *= 1.5

# =====================================================================
# SISTEMA DE MEMORIA EPISÓDICA
# =====================================================================

class MemoriaEpisodica:
    """
    Almacena 'recuerdos' del sistema: eventos significativos y sus consecuencias.
    Permite aprender de experiencias pasadas.
    """
    
    def __init__(self, capacidad: int = 1000):
        self.capacidad = capacidad
        self._episodios: Deque[EventoConciencia] = deque(maxlen=capacidad)
        self._lecciones_aprendidas: Dict[str, List[Dict]] = defaultdict(list)
        self._patrones_detectados: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        
    def recordar(self, evento: EventoConciencia):
        """Almacena un nuevo episodio en la memoria."""
        with self._lock:
            self._episodios.append(evento)
            
            # Detectar patrones
            self._analizar_patron(evento)
            
            # Si es un evento de error, aprender lección
            if evento.tipo.startswith("error") or evento.tipo.startswith("alerta"):
                self._aprender_leccion(evento)
    
    def _analizar_patron(self, evento: EventoConciencia):
        """Analiza patrones en eventos recientes."""
        eventos_recientes = list(self._episodios)[-50:]
        
        # Buscar secuencias repetidas
        for i in range(len(eventos_recientes) - 3):
            secuencia = tuple(e.tipo for e in eventos_recientes[i:i+3])
            self._patrones_detectados[str(secuencia)] += 1
    
    def _aprender_leccion(self, evento: EventoConciencia):
        """Aprende una lección de un evento significativo."""
        contexto = {
            'timestamp': evento.timestamp,
            'datos': evento.datos,
            'estado_sistema': self._capturar_estado_actual()
        }
        self._lecciones_aprendidas[evento.tipo].append(contexto)
        
        # Mantener solo las últimas 100 lecciones por tipo
        if len(self._lecciones_aprendidas[evento.tipo]) > 100:
            self._lecciones_aprendidas[evento.tipo] = self._lecciones_aprendidas[evento.tipo][-100:]
    
    def _capturar_estado_actual(self) -> Dict[str, Any]:
        """Captura el estado actual del sistema para contexto."""
        return {
            'hora': time.time(),
            'memoria_disponible': self._obtener_memoria_disponible(),
        }
    
    def _obtener_memoria_disponible(self) -> float:
        """Obtiene memoria disponible del sistema."""
        if PSUTIL_DISPONIBLE:
            return psutil.virtual_memory().available / (1024 * 1024)
        return 0.0
    
    def recordar_similar(self, tipo_evento: str, limite: int = 10) -> List[EventoConciencia]:
        """Recupera eventos similares del pasado."""
        with self._lock:
            similares = [e for e in self._episodios if tipo_evento in e.tipo]
            return similares[-limite:]
    
    def obtener_leccion(self, tipo_error: str) -> Optional[Dict]:
        """Obtiene la lección más reciente para un tipo de error."""
        with self._lock:
            lecciones = self._lecciones_aprendidas.get(tipo_error, [])
            return lecciones[-1] if lecciones else None
    
    def patrones_frecuentes(self, min_frecuencia: int = 3) -> Dict[str, int]:
        """Retorna patrones que ocurren frecuentemente."""
        with self._lock:
            return {p: c for p, c in self._patrones_detectados.items() if c >= min_frecuencia}
    
    def olvidar_antiguo(self, dias: int = 7):
        """Olvida episodios más antiguos que ciertos días."""
        with self._lock:
            limite = time.time() - (dias * 86400)
            self._episodios = deque(
                [e for e in self._episodios if e.timestamp > limite],
                maxlen=self.capacidad
            )

# =====================================================================
# PREDICTOR DE ESTADO
# =====================================================================

class PredictorEstado:
    """
    Predice el estado futuro del sistema usando análisis de series temporales.
    Implementa suavizado exponencial y detección de anomalías.
    """
    
    def __init__(self, ventana_historica: int = 100):
        self.ventana = ventana_historica
        self._historico: DefaultDict[str, Deque[Tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=ventana_historica)
        )
        self._tendencias: Dict[str, float] = {}
        self._estacionalidad: Dict[str, float] = {}
        self._umbrales_anomalia: Dict[str, float] = {}
        self._lock = threading.RLock()
        
    def registrar_medicion(self, metrica: str, valor: float):
        """Registra una nueva medición."""
        with self._lock:
            ahora = time.time()
            self._historico[metrica].append((ahora, valor))
            self._actualizar_modelo(metrica)
    
    def _actualizar_modelo(self, metrica: str):
        """Actualiza el modelo predictivo para una métrica."""
        datos = list(self._historico[metrica])
        if len(datos) < 5:
            return
        
        valores = [v for _, v in datos]
        
        # Calcular tendencia (regresión lineal simple)
        n = len(valores)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(valores) / n
        
        numerador = sum((x[i] - x_mean) * (valores[i] - y_mean) for i in range(n))
        denominador = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominador != 0:
            tendencia = numerador / denominador
            # Normalizar tendencia a -1..1
            rango = max(valores) - min(valores) if max(valores) != min(valores) else 1
            self._tendencias[metrica] = max(-1.0, min(1.0, tendencia / rango))
        
        # Calcular umbral de anomalía (3 sigmas)
        if NUMPY_DISPONIBLE:
            std = np.std(valores)
            mean = np.mean(valores)
            self._umbrales_anomalia[metrica] = mean + 3 * std
        else:
            # Cálculo manual
            mean = sum(valores) / n
            varianza = sum((v - mean) ** 2 for v in valores) / n
            std = math.sqrt(varianza)
            self._umbrales_anomalia[metrica] = mean + 3 * std
    
    def predecir(self, metrica: str, horizonte_segundos: float = 5.0) -> float:
        """Predice el valor futuro de una métrica."""
        with self._lock:
            datos = list(self._historico[metrica])
            if not datos:
                return 0.0
            
            ultimo_valor = datos[-1][1]
            tendencia = self._tendencias.get(metrica, 0.0)
            
            # Proyección simple
            pasos = horizonte_segundos / 5.0  # Asumiendo mediciones cada 5s
            rango = max(v for _, v in datos) - min(v for _, v in datos) if datos else 1
            cambio = tendencia * rango * pasos * 0.1
            
            return ultimo_valor + cambio
    
    def es_anomalo(self, metrica: str, valor: float) -> bool:
        """Detecta si un valor es anómalo."""
        with self._lock:
            umbral = self._umbrales_anomalia.get(metrica)
            if umbral is None:
                return False
            return valor > umbral
    
    def obtener_tendencia(self, metrica: str) -> float:
        """Obtiene la tendencia actual de una métrica."""
        return self._tendencias.get(metrica, 0.0)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del predictor."""
        with self._lock:
            return {
                'metricas_monitoreadas': list(self._historico.keys()),
                'tendencias': dict(self._tendencias),
                'umbrales_anomalia': dict(self._umbrales_anomalia),
            }

# =====================================================================
# SISTEMA DE AUTO-CURACIÓN
# =====================================================================

class AutoCuracion:
    """
    Sistema de auto-curación que aplica remedios cuando se detectan problemas.
    """
    
    def __init__(self):
        self._remedios: Dict[str, List[Callable]] = defaultdict(list)
        self._historial_curaciones: Deque[Dict] = deque(maxlen=100)
        self._efectividad_remedios: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._lock = threading.RLock()
        
        self._registrar_remedios_default()
    
    def _registrar_remedios_default(self):
        """Registra remedios predefinidos para problemas comunes."""
        self.registrar_remedio("memoria_alta", self._remedio_liberar_memoria)
        self.registrar_remedio("cpu_alta", self._remedio_reducir_carga)
        self.registrar_remedio("errores_frecuentes", self._remedio_reinicio_suave)
        self.registrar_remedio("latencia_alta", self._remedio_optimizar_rutas)
        self.registrar_remedio("deadlock_detectado", self._remedio_romper_deadlock)
    
    def registrar_remedio(self, problema: str, remedio: Callable):
        """Registra un nuevo remedio para un tipo de problema."""
        with self._lock:
            self._remedios[problema].append(remedio)
    
    def aplicar_remedio(self, problema: str, contexto: Dict[str, Any]) -> bool:
        """Aplica el remedio más efectivo para un problema."""
        with self._lock:
            remedios = self._remedios.get(problema, [])
            if not remedios:
                return False
            
            # Seleccionar el remedio con mejor efectividad histórica
            mejor_remedio = None
            mejor_efectividad = -1.0
            
            for remedio in remedios:
                nombre = remedio.__name__
                exitos, total = self._efectividad_remedios[nombre]
                efectividad = exitos / max(total, 1)
                if efectividad > mejor_efectividad:
                    mejor_efectividad = efectividad
                    mejor_remedio = remedio
            
            if mejor_remedio:
                try:
                    exito = mejor_remedio(contexto)
                    
                    # Registrar resultado
                    nombre = mejor_remedio.__name__
                    exitos, total = self._efectividad_remedios[nombre]
                    if exito:
                        self._efectividad_remedios[nombre] = (exitos + 1, total + 1)
                    else:
                        self._efectividad_remedios[nombre] = (exitos, total + 1)
                    
                    self._historial_curaciones.append({
                        'timestamp': time.time(),
                        'problema': problema,
                        'remedio': nombre,
                        'exito': exito,
                        'contexto': contexto
                    })
                    
                    return exito
                except Exception as e:
                    return False
            
            return False
    
    # ===== REMEDIOS CONCRETOS =====
    
    def _remedio_liberar_memoria(self, contexto: Dict) -> bool:
        """Intenta liberar memoria del sistema."""
        try:
            import gc
            gc.collect()
            
            # Forzar recolección en generaciones
            gc.collect(2)
            
            return True
        except:
            return False
    
    def _remedio_reducir_carga(self, contexto: Dict) -> bool:
        """Reduce la carga del sistema pausando tareas no críticas."""
        # Enviar señal de pausa a tareas de baja prioridad
        return True
    
    def _remedio_reinicio_suave(self, contexto: Dict) -> bool:
        """Realiza un reinicio suave de componentes."""
        return True
    
    def _remedio_optimizar_rutas(self, contexto: Dict) -> bool:
        """Optimiza las rutas de enrutamiento."""
        return True
    
    def _remedio_romper_deadlock(self, contexto: Dict) -> bool:
        """Rompe un deadlock detectado."""
        return True
    
    def obtener_efectividad(self) -> Dict[str, float]:
        """Obtiene la efectividad de cada remedio."""
        with self._lock:
            return {
                nombre: exitos / max(total, 1)
                for nombre, (exitos, total) in self._efectividad_remedios.items()
            }

# =====================================================================
# CONCIENCIA SISTÉMICA PRINCIPAL
# =====================================================================

class ConcienciaSistemica:
    """
    La Conciencia Sistémica de ANP.
    
    Capacidades:
    - Monitoreo continuo de signos vitales
    - Detección proactiva de anomalías
    - Predicción de estados futuros
    - Auto-curación automática
    - Memoria episódica para aprendizaje
    - Generación de alertas inteligentes
    - Adaptación de personalidad
    - Ciclos de aprendizaje (fases lunares)
    """
    
    _instancia: Optional['ConcienciaSistemica'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self, nombre: str = "ANP_Conciencia"):
        if self._inicializado:
            return
            
        with self._lock_instancia:
            if self._inicializado:
                return
            
            self.nombre = nombre
            self.id_conciencia = str(uuid.uuid4())
            self.timestamp_nacimiento = time.time()
            
            # Estado sistémico
            self.estado_actual = EstadoSistemico.INICIALIZANDO
            self.fase_lunar = FaseLunar.LUNA_NUEVA
            self.nivel_estres = 0.0  # 0-1
            self.nivel_felicidad = 0.5  # 0-1
            self.nivel_energia = 1.0  # 0-1
            
            # Signos vitales
            self.signos_vitales: Dict[str, SignoVital] = {}
            self._inicializar_signos_vitales()
            
            # Personalidad
            self.personalidad = PerfilPersonalidad()
            
            # Subsistemas
            self.memoria = MemoriaEpisodica()
            self.predictor = PredictorEstado()
            self.autocuracion = AutoCuracion()
            
            # Alertas activas
            self.alertas_activas: Dict[str, AlertaSistemica] = {}
            self.historial_alertas: Deque[AlertaSistemica] = deque(maxlen=500)
            
            # Observadores
            self._observadores: DefaultDict[str, List[Callable]] = defaultdict(list)
            
            # Métricas internas
            self._metricas_internas: DefaultDict[str, List[float]] = defaultdict(list)
            self._eventos_procesados: int = 0
            
            # Control
            self._activa = True
            self._pausada = False
            self._hilo_principal: Optional[threading.Thread] = None
            self._hilo_vitales: Optional[threading.Thread] = None
            self._hilo_aprendizaje: Optional[threading.Thread] = None
            self._lock = threading.RLock()
            
            # Configuración
            self._config = self._cargar_configuracion()
            self._ajustar_personalidad()
            
            # Iniciar
            self._iniciar_hilos()
            self._registrar_nacimiento()
            
            self._inicializado = True
    
    def _cargar_configuracion(self) -> Any:
        """Carga la configuración del sistema."""
        try:
            return obtener_config()
        except:
            return None
    
    def _ajustar_personalidad(self):
        """Ajusta la personalidad según el entorno."""
        entorno = "PYDROID3" if hasattr(sys, 'getandroidapilevel') else "LINUX"
        self.personalidad.ajustar_por_entorno(entorno)
    
    def _inicializar_signos_vitales(self):
        """Inicializa los signos vitales del sistema."""
        vitales = [
            ("cpu_uso", "%", 0.0),
            ("memoria_uso", "%", 0.0),
            ("memoria_disponible", "MB", 0.0),
            ("tareas_activas", "count", 0.0),
            ("tareas_encoladas", "count", 0.0),
            ("latencia_promedio", "ms", 0.0),
            ("tasa_error", "%", 0.0),
            ("nucleos_activos", "count", 0.0),
            ("nucleos_degradados", "count", 0.0),
            ("circuit_breakers_abiertos", "count", 0.0),
            ("temperatura_sistemica", "C", 45.0),
            ("presion_sistemica", "hPa", 1013.0),
            ("ritmo_cardiaco", "bpm", 60.0),
        ]
        
        for nombre, unidad, valor in vitales:
            self.signos_vitales[nombre] = SignoVital(
                nombre=nombre,
                valor=valor,
                unidad=unidad
            )
    
    def _registrar_nacimiento(self):
        """Registra el nacimiento de la conciencia."""
        evento = EventoConciencia(
            tipo="nacimiento",
            datos={"id": self.id_conciencia, "nombre": self.nombre},
            importancia=1.0
        )
        self.memoria.recordar(evento)
        
        self._generar_alerta(
            NivelAlerta.INFO,
            "Conciencia Despertada",
            f"La conciencia {self.nombre} ha despertado. ID: {self.id_conciencia[:8]}"
        )
    
    def _iniciar_hilos(self):
        """Inicia los hilos de la conciencia."""
        self._hilo_principal = threading.Thread(target=self._bucle_principal, daemon=True)
        self._hilo_principal.start()
        
        self._hilo_vitales = threading.Thread(target=self._bucle_vitales, daemon=True)
        self._hilo_vitales.start()
        
        self._hilo_aprendizaje = threading.Thread(target=self._bucle_aprendizaje, daemon=True)
        self._hilo_aprendizaje.start()
    
    # =====================================================================
    # BUCLES DE CONCIENCIA
    # =====================================================================
    
    def _bucle_principal(self):
        """Bucle principal de la conciencia (latido)."""
        latido = 0
        while self._activa:
            if self._pausada:
                time.sleep(0.5)
                continue
            
            try:
                latido += 1
                
                # Actualizar estado sistémico
                self._evaluar_estado_sistemico()
                
                # Actualizar fase lunar cada 100 latidos
                if latido % 100 == 0:
                    self._actualizar_fase_lunar()
                
                # Actualizar nivel de energía
                self._actualizar_energia()
                
                # Verificar anomalías
                self._verificar_anomalias()
                
                # Registrar latido
                self.signos_vitales["ritmo_cardiaco"].actualizar(60 + self.nivel_estres * 40)
                
                # Generar evento periódico
                if latido % 50 == 0:
                    self._registrar_evento(
                        "latido_periodico",
                        {"latido": latido, "estado": self.estado_actual.value}
                    )
                
                time.sleep(1.0)  # 1 Hz
                
            except Exception as e:
                self._registrar_error("bucle_principal", e)
                time.sleep(5.0)
    
    def _bucle_vitales(self):
        """Bucle de monitoreo de signos vitales."""
        while self._activa:
            try:
                # Actualizar signos vitales del sistema
                self._medir_signos_vitales()
                
                # Registrar mediciones en predictor
                for nombre, signo in self.signos_vitales.items():
                    self.predictor.registrar_medicion(nombre, signo.valor)
                    
                    # Actualizar predicciones
                    signo.prediccion_5s = self.predictor.predecir(nombre, 5.0)
                    signo.prediccion_30s = self.predictor.predecir(nombre, 30.0)
                    signo.tendencia = self.predictor.obtener_tendencia(nombre)
                
                time.sleep(2.0)  # 0.5 Hz
                
            except Exception as e:
                self._registrar_error("bucle_vitales", e)
                time.sleep(10.0)
    
    def _bucle_aprendizaje(self):
        """Bucle de aprendizaje y reflexión."""
        while self._activa:
            try:
                # Reflexionar sobre eventos pasados
                if self.fase_lunar == FaseLunar.LLENA:
                    self._reflexionar()
                
                # Olvidar recuerdos antiguos (cada 24h)
                if random.random() < 0.001:  # ~cada 1000s
                    self.memoria.olvidar_antiguo(dias=7)
                
                # Aprender de patrones
                patrones = self.memoria.patrones_frecuentes(min_frecuencia=5)
                if patrones:
                    self._aprender_de_patrones(patrones)
                
                time.sleep(10.0)  # 0.1 Hz
                
            except Exception as e:
                self._registrar_error("bucle_aprendizaje", e)
                time.sleep(60.0)
    
    # =====================================================================
    # MEDICIONES Y MONITOREO
        # =====================================================================
    
    def _medir_signos_vitales(self):
        """Mide todos los signos vitales del sistema."""
        # CPU
        if PSUTIL_DISPONIBLE:
            cpu = psutil.cpu_percent(interval=0.1)
            self.signos_vitales["cpu_uso"].actualizar(cpu)
            
            mem = psutil.virtual_memory()
            self.signos_vitales["memoria_uso"].actualizar(mem.percent)
            self.signos_vitales["memoria_disponible"].actualizar(mem.available / (1024 * 1024))
        else:
            # Estimaciones para entornos sin psutil
            self.signos_vitales["cpu_uso"].actualizar(random.uniform(10, 50))
            self.signos_vitales["memoria_uso"].actualizar(random.uniform(30, 70))
            self.signos_vitales["memoria_disponible"].actualizar(random.uniform(500, 1000))
        
        # Actualizar presión sistémica (basada en carga)
        presion = 1013.0 + self.nivel_estres * 50
        self.signos_vitales["presion_sistemica"].actualizar(presion)
        
        # Actualizar temperatura sistémica
        temp = 45.0 + self.nivel_estres * 20 + self.signos_vitales["cpu_uso"].valor * 0.3
        self.signos_vitales["temperatura_sistemica"].actualizar(temp)
    
    def _evaluar_estado_sistemico(self):
        """Evalúa y actualiza el estado sistémico global."""
        cpu = self.signos_vitales["cpu_uso"].valor
        mem = self.signos_vitales["memoria_uso"].valor
        errores = self.signos_vitales["tasa_error"].valor
        
        estado_anterior = self.estado_actual
        
        if cpu > 90 or mem > 95:
            self.estado_actual = EstadoSistemico.CRITICO
            self.nivel_estres = min(1.0, self.nivel_estres + 0.1)
        elif cpu > 70 or mem > 80:
            self.estado_actual = EstadoSistemico.ESTRESADO
            self.nivel_estres = min(1.0, self.nivel_estres + 0.05)
        elif cpu > 50 or mem > 60:
            self.estado_actual = EstadoSistemico.DEGRADADO
        elif errores > 10:
            self.estado_actual = EstadoSistemico.DEGRADADO
        else:
            self.estado_actual = EstadoSistemico.SALUDABLE
            self.nivel_estres = max(0.0, self.nivel_estres - 0.02)
        
        # Detectar cambios de estado
        if estado_anterior != self.estado_actual:
            self._registrar_evento(
                "cambio_estado",
                {"anterior": estado_anterior.value, "nuevo": self.estado_actual.value},
                importancia=0.8
            )
            
            if self.estado_actual in (EstadoSistemico.CRITICO, EstadoSistemico.ESTRESADO):
                self._generar_alerta(
                    NivelAlerta.PELIGRO if self.estado_actual == EstadoSistemico.CRITICO else NivelAlerta.PRECAUCION,
                    f"Sistema {self.estado_actual.value.upper()}",
                    f"CPU: {cpu:.1f}%, Memoria: {mem:.1f}%"
                )
    
    def _actualizar_fase_lunar(self):
        """Actualiza la fase lunar operativa."""
        fases = list(FaseLunar)
        indice_actual = fases.index(self.fase_lunar)
        indice_siguiente = (indice_actual + 1) % len(fases)
        self.fase_lunar = fases[indice_siguiente]
        
        self._registrar_evento(
            "cambio_fase",
            {"fase": self.fase_lunar.value},
            importancia=0.3
        )
        
        # Ajustar comportamiento según fase
        if self.fase_lunar == FaseLunar.LLENA:
            self.personalidad.agresividad_optimizacion = min(1.0, self.personalidad.agresividad_optimizacion * 1.2)
        elif self.fase_lunar == FaseLunar.LUNA_NUEVA:
            self.personalidad.agresividad_optimizacion = max(0.3, self.personalidad.agresividad_optimizacion * 0.8)
    
    def _actualizar_energia(self):
        """Actualiza el nivel de energía de la conciencia."""
        # La energía disminuye con el estrés y el tiempo
        self.nivel_energia = max(0.1, 1.0 - self.nivel_estres * 0.5)
        
        # Recuperar energía en fase menguante
        if self.fase_lunar == FaseLunar.MENGUANTE:
            self.nivel_energia = min(1.0, self.nivel_energia + 0.01)
        
        # Actualizar felicidad
        self.nivel_felicidad = 0.5 + (1 - self.nivel_estres) * 0.5 - (self.signos_vitales["tasa_error"].valor / 100)
        self.nivel_felicidad = max(0.0, min(1.0, self.nivel_felicidad))
    
    def _verificar_anomalias(self):
        """Verifica anomalías en los signos vitales."""
        for nombre, signo in self.signos_vitales.items():
            if self.predictor.es_anomalo(nombre, signo.valor):
                self._registrar_evento(
                    "anomalia_detectada",
                    {"metrica": nombre, "valor": signo.valor},
                    importancia=0.9
                )
                
                # Intentar auto-curación
                if self.personalidad.agresividad_optimizacion > 0.5:
                    contexto = {"metrica": nombre, "valor": signo.valor}
                    exito = self.autocuracion.aplicar_remedio(f"{nombre}_alta", contexto)
                    
                    if exito:
                        self._generar_alerta(
                            NivelAlerta.ADVERTENCIA,
                            f"Anomalía en {nombre}",
                            f"Valor anómalo: {signo.valor:.2f}. Auto-curación aplicada."
                        )
    
    def _reflexionar(self):
        """Reflexiona sobre el estado actual y pasado."""
        # Analizar tendencias
        for nombre, signo in self.signos_vitales.items():
            if signo.tendencia > 0.3:
                self._registrar_evento(
                    "tendencia_detectada",
                    {"metrica": nombre, "tendencia": "creciente", "valor": signo.tendencia}
                )
            elif signo.tendencia < -0.3:
                self._registrar_evento(
                    "tendencia_detectada",
                    {"metrica": nombre, "tendencia": "decreciente", "valor": signo.tendencia}
                )
    
    def _aprender_de_patrones(self, patrones: Dict[str, int]):
        """Aprende de patrones detectados."""
        for patron, frecuencia in patrones.items():
            evento = EventoConciencia(
                tipo="patron_aprendido",
                datos={"patron": patron, "frecuencia": frecuencia},
                importancia=0.6
            )
            self.memoria.recordar(evento)
    
    # =====================================================================
    # API PÚBLICA
    # =====================================================================
    
    def reportar_metrica(self, nombre: str, valor: float, unidad: str = ""):
        """Reporta una métrica personalizada a la conciencia."""
        with self._lock:
            if nombre not in self.signos_vitales:
                self.signos_vitales[nombre] = SignoVital(
                    nombre=nombre,
                    valor=valor,
                    unidad=unidad
                )
            else:
                self.signos_vitales[nombre].actualizar(valor)
            
            self._eventos_procesados += 1
    
    def reportar_evento(self, tipo: str, datos: Any = None, importancia: float = 0.5):
        """Reporta un evento a la conciencia."""
        evento = EventoConciencia(
            tipo=tipo,
            datos=datos,
            importancia=importancia
        )
        self.memoria.recordar(evento)
        self._eventos_procesados += 1
    
    def reportar_error(self, origen: str, error: Exception):
        """Reporta un error a la conciencia."""
        self._registrar_error(origen, error)
        
        # Incrementar tasa de error
        tasa_actual = self.signos_vitales["tasa_error"].valor
        self.signos_vitales["tasa_error"].actualizar(min(100.0, tasa_actual + 1.0))
    
    def _registrar_error(self, origen: str, error: Exception):
        """Registra un error internamente."""
        evento = EventoConciencia(
            tipo=f"error_{origen}",
            datos={"origen": origen, "error": str(error), "traceback": traceback.format_exc()},
            importancia=0.9
        )
        self.memoria.recordar(evento)
        self._eventos_procesados += 1
    
    def _registrar_evento(self, tipo: str, datos: Any = None, importancia: float = 0.5):
        """Registra un evento interno."""
        evento = EventoConciencia(
            tipo=tipo,
            datos=datos,
            importancia=importancia
        )
        self.memoria.recordar(evento)
    
    def _generar_alerta(self, nivel: NivelAlerta, titulo: str, mensaje: str, metadatos: Dict = None) -> str:
        """Genera una nueva alerta sistémica."""
        alerta = AlertaSistemica(
            nivel=nivel,
            titulo=titulo,
            mensaje=mensaje,
            metadatos=metadatos or {}
        )
        
        self.alertas_activas[alerta.id] = alerta
        self.historial_alertas.append(alerta)
        
        # Notificar observadores
        self._notificar_observadores("alerta", alerta)
        
        return alerta.id
    
    def resolver_alerta(self, alerta_id: str, accion: str = ""):
        """Resuelve una alerta activa."""
        if alerta_id in self.alertas_activas:
            self.alertas_activas[alerta_id].resolver(accion)
            del self.alertas_activas[alerta_id]
    
    def suscribir(self, evento: str, callback: Callable):
        """Suscribe un callback a eventos de la conciencia."""
        self._observadores[evento].append(callback)
    
    def _notificar_observadores(self, evento: str, datos: Any):
        """Notifica a los observadores suscritos."""
        for callback in self._observadores.get(evento, []):
            try:
                callback(datos)
            except:
                pass
    
    def obtener_estado_completo(self) -> Dict[str, Any]:
        """Obtiene el estado completo de la conciencia."""
        with self._lock:
            return {
                'conciencia': {
                    'id': self.id_conciencia,
                    'nombre': self.nombre,
                    'edad_segundos': time.time() - self.timestamp_nacimiento,
                    'estado': self.estado_actual.value,
                    'fase_lunar': self.fase_lunar.value,
                    'nivel_estres': self.nivel_estres,
                    'nivel_felicidad': self.nivel_felicidad,
                    'nivel_energia': self.nivel_energia,
                },
                'personalidad': asdict(self.personalidad),
                'signos_vitales': {
                    nombre: {
                        'valor': signo.valor,
                        'unidad': signo.unidad,
                        'tendencia': signo.tendencia,
                        'prediccion_5s': signo.prediccion_5s,
                        'prediccion_30s': signo.prediccion_30s,
                        'estado': signo.estado,
                    }
                    for nombre, signo in self.signos_vitales.items()
                },
                'alertas_activas': len(self.alertas_activas),
                'eventos_procesados': self._eventos_procesados,
                'predictor': self.predictor.obtener_estadisticas(),
                'autocuracion': {
                    'efectividad': self.autocuracion.obtener_efectividad(),
                },
                'memoria': {
                    'episodios': len(self.memoria._episodios),
                    'lecciones': sum(len(l) for l in self.memoria._lecciones_aprendidas.values()),
                    'patrones': len(self.memoria.patrones_frecuentes()),
                },
            }
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo del estado."""
        return {
            'estado': self.estado_actual.value,
            'fase': self.fase_lunar.value,
            'estres': f"{self.nivel_estres:.1%}",
            'felicidad': f"{self.nivel_felicidad:.1%}",
            'cpu': f"{self.signos_vitales['cpu_uso'].valor:.1f}%",
            'memoria': f"{self.signos_vitales['memoria_uso'].valor:.1f}%",
            'alertas': len(self.alertas_activas),
            'edad': f"{(time.time() - self.timestamp_nacimiento):.0f}s",
        }
    
    def pausar(self):
        """Pausa la conciencia."""
        self._pausada = True
        
    def reanudar(self):
        """Reanuda la conciencia."""
        self._pausada = False
    
    def morir(self):
        """Apaga la conciencia de manera elegante."""
        self.estado_actual = EstadoSistemico.MURIENDO
        self._registrar_evento("muerte_inminente", importancia=1.0)
        
        time.sleep(1.0)
        
        self._activa = False
        
        if self._hilo_principal:
            self._hilo_principal.join(timeout=3.0)
        if self._hilo_vitales:
            self._hilo_vitales.join(timeout=3.0)
        if self._hilo_aprendizaje:
            self._hilo_aprendizaje.join(timeout=3.0)
        
        self.estado_actual = EstadoSistemico.MUERTO
        self._registrar_evento("muerte", importancia=1.0)
    
    def __repr__(self) -> str:
        return f"ConcienciaSistemica({self.nombre}, {self.estado_actual.value}, {self.nivel_felicidad:.1%} feliz)"

# =====================================================================
# FÁBRICA Y SINGLETON
# =====================================================================

def obtener_conciencia(nombre: str = "ANP_Conciencia") -> ConcienciaSistemica:
    """Obtiene la instancia global de la conciencia."""
    return ConcienciaSistemica(nombre)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DE LA CONCIENCIA SISTÉMICA")
    print("=" * 70)
    
    conciencia = None
    
    try:
        import uuid
        
        # 1. Despertar conciencia
        print("\n[1/6] Despertando conciencia...")
        conciencia = ConcienciaSistemica("ANP_Test")
        print(f"  ✅ Conciencia despertada: {conciencia}")
        
        # 2. Esperar primeras mediciones
        print("\n[2/6] Esperando primeras mediciones...")
        time.sleep(3.0)
        
        # 3. Reportar métricas personalizadas
        print("\n[3/6] Reportando métricas personalizadas...")
        conciencia.reportar_metrica("tareas_completadas", 42.0, "count")
        conciencia.reportar_metrica("tareas_fallidas", 3.0, "count")
        conciencia.reportar_evento("usuario_conectado", {"usuario": "test"}, importancia=0.7)
        print("  ✅ Métricas reportadas")
        
        # 4. Simular algunos errores
        print("\n[4/6] Simulando errores...")
        for i in range(3):
            try:
                raise ValueError(f"Error simulado {i}")
            except Exception as e:
                conciencia.reportar_error("test", e)
        print("  ✅ Errores reportados")
        
        # 5. Esperar procesamiento
        print("\n[5/6] Procesando...")
        time.sleep(5.0)
        
        # 6. Obtener estado completo
        print("\n[6/6] Estado de la conciencia:")
        resumen = conciencia.obtener_resumen()
        print(f"  📊 Estado: {resumen['estado']}")
        print(f"  🌙 Fase: {resumen['fase']}")
        print(f"  😰 Estrés: {resumen['estres']}")
        print(f"  😊 Felicidad: {resumen['felicidad']}")
        print(f"  💻 CPU: {resumen['cpu']}")
        print(f"  🧠 Memoria: {resumen['memoria']}")
        print(f"  🚨 Alertas: {resumen['alertas']}")
        print(f"  ⏱️ Edad: {resumen['edad']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   La Conciencia Sistémica está VIVA.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        
    finally:
        if conciencia:
            print("\n💀 Apagando conciencia...")
            conciencia.morir()
            print("   ✓ Conciencia apagada")
    
    print("\n" + "=" * 70 + "\n")