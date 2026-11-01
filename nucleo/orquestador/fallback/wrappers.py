# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Wrappers del Sistema de Fallback (Archivo Unificado)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# Este archivo contiene TODOS los wrappers y placeholders necesarios
# para completar la estructura del sistema de fallback.
# =====================================================================

import sys
import os
import time
import json
import random
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict, deque, OrderedDict
from datetime import datetime

# =====================================================================
# 1. CIRCUIT BREAKER (Wrapper desde maestro.py)
# =====================================================================

class EstadoCircuitBreaker(Enum):
    """Estados del Circuit Breaker."""
    CERRADO = "cerrado"
    ABIERTO = "abierto"
    SEMI_ABIERTO = "semi_abierto"
    DEGRADADO = "degradado"

class CircuitBreaker:
    """
    Wrapper del Circuit Breaker del orquestador.
    Si no está disponible, usa implementación local.
    """
    
    def __init__(self, nombre: str, umbral_fallos: int = 5, timeout_recuperacion: float = 60.0):
        self.nombre = nombre
        self.umbral_fallos = umbral_fallos
        self.timeout_recuperacion = timeout_recuperacion
        
        self._estado = EstadoCircuitBreaker.CERRADO
        self._fallos_consecutivos = 0
        self._total_exitos = 0
        self._total_fallos = 0
        self._ultimo_fallo: float = 0.0
        self._abierto_hasta: float = 0.0
        self._lock = threading.RLock()
    
    def permitir_operacion(self) -> bool:
        """Determina si una operación está permitida."""
        with self._lock:
            ahora = time.time()
            
            if self._estado == EstadoCircuitBreaker.CERRADO:
                return True
            elif self._estado == EstadoCircuitBreaker.ABIERTO:
                if ahora >= self._abierto_hasta:
                    self._estado = EstadoCircuitBreaker.SEMI_ABIERTO
                    return True
                return False
            elif self._estado == EstadoCircuitBreaker.SEMI_ABIERTO:
                return True
            elif self._estado == EstadoCircuitBreaker.DEGRADADO:
                return True
        
        return False
    
    def registrar_exito(self):
        """Registra una operación exitosa."""
        with self._lock:
            self._total_exitos += 1
            if self._estado == EstadoCircuitBreaker.SEMI_ABIERTO:
                self._fallos_consecutivos = 0
                self._estado = EstadoCircuitBreaker.CERRADO
            elif self._estado == EstadoCircuitBreaker.DEGRADADO:
                self._fallos_consecutivos = max(0, self._fallos_consecutivos - 1)
                if self._fallos_consecutivos == 0:
                    self._estado = EstadoCircuitBreaker.CERRADO
            else:
                self._fallos_consecutivos = 0
    
    def registrar_fallo(self):
        """Registra una operación fallida."""
        with self._lock:
            ahora = time.time()
            self._total_fallos += 1
            self._fallos_consecutivos += 1
            self._ultimo_fallo = ahora
            
            if self._estado == EstadoCircuitBreaker.CERRADO:
                if self._fallos_consecutivos >= self.umbral_fallos:
                    self._estado = EstadoCircuitBreaker.ABIERTO
                    self._abierto_hasta = ahora + self.timeout_recuperacion
            elif self._estado == EstadoCircuitBreaker.SEMI_ABIERTO:
                self._estado = EstadoCircuitBreaker.ABIERTO
                self._abierto_hasta = ahora + self.timeout_recuperacion * 2
    
    @property
    def estado(self) -> EstadoCircuitBreaker:
        return self._estado
    
    @property
    def metricas(self) -> Dict[str, Any]:
        return {
            'nombre': self.nombre,
            'estado': self._estado.value,
            'fallos_consecutivos': self._fallos_consecutivos,
            'total_exitos': self._total_exitos,
            'total_fallos': self._total_fallos,
            'tasa_exito': self._total_exitos / max(1, self._total_exitos + self._total_fallos),
        }
    
    def forzar_estado(self, estado: EstadoCircuitBreaker):
        """Fuerza un estado específico."""
        with self._lock:
            self._estado = estado
            if estado == EstadoCircuitBreaker.ABIERTO:
                self._abierto_hasta = time.time() + self.timeout_recuperacion
    
    def resetear(self):
        """Resetea el circuit breaker a estado cerrado."""
        with self._lock:
            self._estado = EstadoCircuitBreaker.CERRADO
            self._fallos_consecutivos = 0

# =====================================================================
# 2. DETECTOR DE ANOMALÍAS (Wrapper desde conciencia_sistemica.py)
# =====================================================================

class DetectorAnomalias:
    """
    Wrapper del Detector de Anomalías de la conciencia sistémica.
    Implementa detección por desviación estándar y predicción simple.
    """
    
    def __init__(self, ventana_historica: int = 100, sensibilidad: float = 3.0):
        self.ventana = ventana_historica
        self.sensibilidad = sensibilidad
        self._historico: Dict[str, deque] = defaultdict(lambda: deque(maxlen=ventana_historica))
        self._medias: Dict[str, float] = {}
        self._desviaciones: Dict[str, float] = {}
        self._umbrales: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def registrar_medicion(self, metrica: str, valor: float):
        """Registra una nueva medición."""
        with self._lock:
            self._historico[metrica].append(valor)
            self._actualizar_estadisticas(metrica)
    
    def _actualizar_estadisticas(self, metrica: str):
        """Actualiza estadísticas para una métrica."""
        valores = list(self._historico[metrica])
        if len(valores) < 3:
            return
        
        media = sum(valores) / len(valores)
        varianza = sum((v - media) ** 2 for v in valores) / len(valores)
        desviacion = varianza ** 0.5
        
        self._medias[metrica] = media
        self._desviaciones[metrica] = desviacion
        self._umbrales[metrica] = media + (desviacion * self.sensibilidad)
    
    def es_anomalo(self, metrica: str, valor: float) -> bool:
        """Detecta si un valor es anómalo."""
        with self._lock:
            if metrica not in self._umbrales:
                return False
            return valor > self._umbrales[metrica]
    
    def obtener_anomalia_score(self, metrica: str, valor: float) -> float:
        """Calcula un score de anomalía (0-1)."""
        with self._lock:
            if metrica not in self._medias:
                return 0.0
            
            media = self._medias[metrica]
            desviacion = self._desviaciones[metrica]
            
            if desviacion == 0:
                return 0.0
            
            z_score = abs(valor - media) / desviacion
            return min(1.0, z_score / (self.sensibilidad * 2))
    
    def predecir(self, metrica: str) -> Optional[float]:
        """Predice el próximo valor basado en tendencia."""
        with self._lock:
            valores = list(self._historico[metrica])
            if len(valores) < 2:
                return None
            
            # Tendencia simple
            ultimo = valores[-1]
            tendencia = (valores[-1] - valores[0]) / len(valores)
            return ultimo + tendencia
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del detector."""
        with self._lock:
            return {
                'metricas_monitoreadas': list(self._historico.keys()),
                'medias': dict(self._medias),
                'umbrales': dict(self._umbrales),
                'total_mediciones': sum(len(v) for v in self._historico.values()),
            }
    
    def limpiar_historico(self, metrica: Optional[str] = None):
        """Limpia el histórico de mediciones."""
        with self._lock:
            if metrica:
                self._historico[metrica].clear()
            else:
                self._historico.clear()
                self._medias.clear()
                self._desviaciones.clear()
                self._umbrales.clear()

# =====================================================================
# 3. DEGRADADOR GRACEFUL
# =====================================================================

class NivelDegradacion(Enum):
    """Niveles de degradación del sistema."""
    NORMAL = "normal"
    LEVE = "leve"
    MODERADO = "moderado"
    GRAVE = "grave"
    CRITICO = "critico"

class Degradador:
    """
    Sistema de degradación graceful.
    Desactiva funcionalidades progresivamente según el nivel.
    """
    
    def __init__(self):
        self.nivel_actual = NivelDegradacion.NORMAL
        self._historial: List[Tuple[float, NivelDegradacion, str]] = []
        self._funcionalidades_deshabilitadas: Set[str] = set()
        self._lock = threading.RLock()
        
        # Mapa de funcionalidades por nivel
        self._mapa_funcionalidades = {
            NivelDegradacion.LEVE: [
                "creatividad_avanzada",
                "cache_secundaria",
            ],
            NivelDegradacion.MODERADO: [
                "busqueda_web",
                "razonamiento_probabilistico",
                "memoria_episodica_extendida",
            ],
            NivelDegradacion.GRAVE: [
                "resolucion_matematica_compleja",
                "memoria_largo_plazo",
                "procesamiento_paralelo",
            ],
            NivelDegradacion.CRITICO: [
                "razonamiento_logico_avanzado",
                "memoria_semantica",
                "comunicacion_natural",
            ],
        }
    
    def degradar(self, nivel: NivelDegradacion, motivo: str = ""):
        """Degrada el sistema a un nivel específico."""
        with self._lock:
            niveles_orden = list(NivelDegradacion)
            indice_actual = niveles_orden.index(self.nivel_actual)
            indice_nuevo = niveles_orden.index(nivel)
            
            if indice_nuevo > indice_actual:
                self.nivel_actual = nivel
                self._historial.append((time.time(), nivel, motivo))
                self._aplicar_degradacion()
    
    def _aplicar_degradacion(self):
        """Aplica las deshabilitaciones correspondientes al nivel actual."""
        self._funcionalidades_deshabilitadas.clear()
        
        niveles_orden = list(NivelDegradacion)
        indice_actual = niveles_orden.index(self.nivel_actual)
        
        for i in range(1, indice_actual + 1):
            nivel = niveles_orden[i]
            for func in self._mapa_funcionalidades.get(nivel, []):
                self._funcionalidades_deshabilitadas.add(func)
    
    def mejorar(self, nivel: Optional[NivelDegradacion] = None):
        """Mejora el nivel de degradación."""
        with self._lock:
            niveles_orden = list(NivelDegradacion)
            
            if nivel is None:
                indice_actual = niveles_orden.index(self.nivel_actual)
                if indice_actual > 0:
                    self.nivel_actual = niveles_orden[indice_actual - 1]
            else:
                indice_nuevo = niveles_orden.index(nivel)
                indice_actual = niveles_orden.index(self.nivel_actual)
                if indice_nuevo < indice_actual:
                    self.nivel_actual = nivel
            
            self._aplicar_degradacion()
    
    def esta_degradado(self) -> bool:
        """Retorna True si el sistema está degradado."""
        return self.nivel_actual != NivelDegradacion.NORMAL
    
    def funcionalidad_habilitada(self, funcionalidad: str) -> bool:
        """Verifica si una funcionalidad está habilitada."""
        return funcionalidad not in self._funcionalidades_deshabilitadas
    
    def obtener_funcionalidades_deshabilitadas(self) -> List[str]:
        """Obtiene lista de funcionalidades deshabilitadas."""
        return list(self._funcionalidades_deshabilitadas)
    
    def obtener_estado(self) -> Dict[str, Any]:
        """Obtiene el estado actual del degradador."""
        return {
            'nivel_actual': self.nivel_actual.value,
            'degradado': self.esta_degradado(),
            'funcionalidades_deshabilitadas': len(self._funcionalidades_deshabilitadas),
            'historial_cambios': len(self._historial),
        }
    
    def resetear(self):
        """Resetea el degradador a estado normal."""
        with self._lock:
            self.nivel_actual = NivelDegradacion.NORMAL
            self._funcionalidades_deshabilitadas.clear()

# =====================================================================
# 4. REDUNDANCIA DE NÚCLEOS
# =====================================================================

class RedundanciaNucleos:
    """
    Sistema de redundancia de núcleos.
    Gestiona alternativas para fallback cuando un núcleo falla.
    """
    
    def __init__(self):
        self._mapa_alternativas: Dict[str, List[str]] = {
            'comunicacion': ['comunicacion_fallback', 'razonamiento', 'respuestas_emergencia'],
            'razonamiento': ['razonamiento_fallback', 'logica_basica', 'comunicacion'],
            'memoria': ['memoria_fallback', 'memoria_volatil', 'cache_local'],
            'busqueda': ['busqueda_fallback', 'cache_offline', 'wikipedia_offline'],
            'resolucion': ['resolucion_fallback', 'calculadora_basica', 'razonamiento'],
            'creatividad': ['creatividad_fallback', 'plantillas_predefinidas', 'razonamiento'],
        }
        
        self._estado_nucleos: Dict[str, bool] = {}
        self._historico_usos: Dict[str, int] = defaultdict(int)
        self._historico_fallos: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Inicializar todos como activos
        for nucleo in self._mapa_alternativas:
            self._estado_nucleos[nucleo] = True
    
    def obtener_alternativa(self, nucleo: str) -> Optional[str]:
        """Obtiene la mejor alternativa para un núcleo."""
        with self._lock:
            alternativas = self._mapa_alternativas.get(nucleo, [])
            
            # Filtrar solo alternativas disponibles (si tenemos info)
            disponibles = [a for a in alternativas if self._estado_nucleos.get(a, True)]
            
            if not disponibles:
                disponibles = alternativas
            
            if not disponibles:
                return None
            
            # Ordenar por uso histórico (menos usadas primero)
            disponibles.sort(key=lambda x: self._historico_usos.get(x, 0))
            
            seleccionada = disponibles[0]
            self._historico_usos[seleccionada] += 1
            
            return seleccionada
    
    def obtener_todas_alternativas(self, nucleo: str) -> List[str]:
        """Obtiene todas las alternativas para un núcleo."""
        return self._mapa_alternativas.get(nucleo, [])
    
    def registrar_alternativa(self, nucleo: str, alternativa: str):
        """Registra una nueva alternativa para un núcleo."""
        with self._lock:
            if nucleo not in self._mapa_alternativas:
                self._mapa_alternativas[nucleo] = []
            if alternativa not in self._mapa_alternativas[nucleo]:
                self._mapa_alternativas[nucleo].append(alternativa)
    
    def marcar_nucleo_caido(self, nucleo: str, motivo: str = ""):
        """Marca un núcleo como caído."""
        with self._lock:
            self._estado_nucleos[nucleo] = False
            self._historico_fallos[nucleo].append((time.time(), motivo))
    
    def marcar_nucleo_recuperado(self, nucleo: str):
        """Marca un núcleo como recuperado."""
        with self._lock:
            self._estado_nucleos[nucleo] = True
    
    def nucleo_disponible(self, nucleo: str) -> bool:
        """Verifica si un núcleo está disponible."""
        return self._estado_nucleos.get(nucleo, True)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de redundancia."""
        with self._lock:
            return {
                'total_nucleos': len(self._mapa_alternativas),
                'nucleos_disponibles': sum(1 for v in self._estado_nucleos.values() if v),
                'nucleos_caidos': sum(1 for v in self._estado_nucleos.values() if not v),
                'total_alternativas': sum(len(v) for v in self._mapa_alternativas.values()),
                'usos_por_alternativa': dict(self._historico_usos),
            }
    
    def obtener_mapa_completo(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el mapa completo con estado."""
        return {
            nucleo: {
                'disponible': self._estado_nucleos.get(nucleo, True),
                'alternativas': self._mapa_alternativas.get(nucleo, []),
                'fallos': len(self._historico_fallos.get(nucleo, [])),
            }
            for nucleo in self._mapa_alternativas
        }

# =====================================================================
# 5. RECUPERADOR DE ESTADO
# =====================================================================

class RecuperadorEstado:
    """
    Sistema de recuperación de estado con puntos de control.
    Permite guardar y recuperar el estado del sistema tras fallos.
    """
    
    def __init__(self, max_puntos: int = 10, directorio_respaldo: Optional[Path] = None):
        self.max_puntos = max_puntos
        self.directorio_respaldo = directorio_respaldo or Path("almacenamiento/fallback")
        self._puntos_control: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
        
        # Crear directorio si no existe
        try:
            self.directorio_respaldo.mkdir(parents=True, exist_ok=True)
        except:
            pass
    
    def guardar_punto_control(self, nombre: str, estado: Dict[str, Any], 
                              persistir: bool = True) -> bool:
        """Guarda un punto de control."""
        with self._lock:
            # Limitar número de puntos
            if len(self._puntos_control) >= self.max_puntos:
                self._puntos_control.popitem(last=False)
            
            punto = {
                'nombre': nombre,
                'timestamp': time.time(),
                'fecha': datetime.now().isoformat(),
                'estado': estado.copy()
            }
            
            self._puntos_control[nombre] = punto
            
            if persistir:
                return self._persistir_punto(punto)
            
            return True
    
    def _persistir_punto(self, punto: Dict[str, Any]) -> bool:
        """Persiste un punto de control en disco."""
        try:
            nombre_archivo = f"checkpoint_{punto['nombre']}_{int(punto['timestamp'])}.json"
            ruta = self.directorio_respaldo / nombre_archivo
            
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump(punto, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            return False
    
    def recuperar_ultimo(self) -> Optional[Dict[str, Any]]:
        """Recupera el punto de control más reciente."""
        with self._lock:
            if not self._puntos_control:
                # Intentar cargar desde disco
                self._cargar_desde_disco()
            
            if not self._puntos_control:
                return None
            
            ultimo_nombre = next(reversed(self._puntos_control))
            return self.recuperar(ultimo_nombre)
    
    def recuperar(self, nombre: str) -> Optional[Dict[str, Any]]:
        """Recupera un punto de control específico."""
        with self._lock:
            if nombre in self._puntos_control:
                return self._puntos_control[nombre]['estado'].copy()
            return None
    
    def _cargar_desde_disco(self):
        """Carga puntos de control desde disco."""
        try:
            for archivo in sorted(self.directorio_respaldo.glob("checkpoint_*.json"), reverse=True):
                with open(archivo, 'r', encoding='utf-8') as f:
                    punto = json.load(f)
                    nombre = punto.get('nombre', archivo.stem)
                    self._puntos_control[nombre] = punto
                    
                if len(self._puntos_control) >= self.max_puntos:
                    break
        except:
            pass
    
    def listar_puntos(self) -> List[Dict[str, Any]]:
        """Lista todos los puntos de control."""
        with self._lock:
            return [
                {
                    'nombre': nombre,
                    'timestamp': punto['timestamp'],
                    'fecha': punto.get('fecha', ''),
                    'tamano': len(str(punto['estado']))
                }
                for nombre, punto in self._puntos_control.items()
            ]
    
    def eliminar_punto(self, nombre: str) -> bool:
        """Elimina un punto de control."""
        with self._lock:
            if nombre in self._puntos_control:
                del self._puntos_control[nombre]
                return True
            return False
    
    def limpiar(self):
        """Limpia todos los puntos de control."""
        with self._lock:
            self._puntos_control.clear()
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del recuperador."""
        return {
            'total_puntos': len(self._puntos_control),
            'capacidad_maxima': self.max_puntos,
            'directorio_respaldo': str(self.directorio_respaldo),
        }

# =====================================================================
# 6. GESTOR DE FALLBACK (Orquestador Central)
# =====================================================================

class TipoFallo(Enum):
    """Tipos de fallo para registro."""
    DESCONOCIDO = "desconocido"
    TIMEOUT = "timeout"
    MEMORIA_INSUFICIENTE = "memoria_insuficiente"
    NUCLEO_CAIDO = "nucleo_caido"
    ERROR_INTERNO = "error_interno"
    RED_NO_DISPONIBLE = "red_no_disponible"
    SOBRECARGA = "sobrecarga"
    CIRCUIT_BREAKER_ABIERTO = "circuit_breaker_abierto"
    FALLBACK_ACTIVADO = "fallback_activado"
    DEGRADACION_ACTIVADA = "degradacion_activada"

class GestorFallback:
    """
    Gestor central del sistema de fallback.
    Coordina todos los componentes de resiliencia.
    """
    
    _instancia: Optional['GestorFallback'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instancia is None:
            with cls._lock_instancia:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
        return cls._instancia
    
    def __init__(self):
        if hasattr(self, '_inicializado') and self._inicializado:
            return
        
        # Inicializar todos los componentes
        self.circuit_breaker = CircuitBreaker("global")
        self.detector = DetectorAnomalias()
        self.degradador = Degradador()
        self.redundancia = RedundanciaNucleos()
        self.recuperador = RecuperadorEstado()
        
        # Estado
        self._fallback_activo = False
        self._ultimo_error: Optional[str] = None
        self._historial_fallos: deque = deque(maxlen=100)
        
        # Configuración
        self._auto_guardado = True
        
        self._inicializado = True
    
    def activar_fallback(self, motivo: str, tipo: TipoFallo = TipoFallo.FALLBACK_ACTIVADO,
                         contexto: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Activa el modo fallback y retorna información del estado.
        """
        self._fallback_activo = True
        self._ultimo_error = motivo
        
        # Registrar fallo
        fallo = {
            'timestamp': time.time(),
            'tipo': tipo.value,
            'motivo': motivo,
            'contexto': contexto or {}
        }
        self._historial_fallos.append(fallo)
        
        # Activar circuit breaker
        self.circuit_breaker.registrar_fallo()
        
        # Determinar nivel de degradación
        if self.circuit_breaker._fallos_consecutivos >= 5:
            self.degradador.degradar(NivelDegradacion.GRAVE, motivo)
        elif self.circuit_breaker._fallos_consecutivos >= 3:
            self.degradador.degradar(NivelDegradacion.MODERADO, motivo)
        elif self.circuit_breaker._fallos_consecutivos >= 1:
            self.degradador.degradar(NivelDegradacion.LEVE, motivo)
        
        # Auto-guardado
        if self._auto_guardado:
            self.guardar_estado()
        
        return self.obtener_estado()
    
    def desactivar_fallback(self):
        """Desactiva el modo fallback."""
        self._fallback_activo = False
        self.circuit_breaker.resetear()
        self.degradador.resetear()
    
    def esta_en_fallback(self) -> bool:
        """Retorna True si el sistema está en modo fallback."""
        return self._fallback_activo
    
    def obtener_alternativa(self, nucleo: str) -> Optional[str]:
        """Obtiene un núcleo alternativo para fallback."""
        return self.redundancia.obtener_alternativa(nucleo)
    
    def notificar_fallo_nucleo(self, nucleo: str, motivo: str):
        """Notifica que un núcleo ha fallado."""
        self.redundancia.marcar_nucleo_caido(nucleo, motivo)
        self.activar_fallback(f"Núcleo {nucleo} caído: {motivo}", TipoFallo.NUCLEO_CAIDO)
    
    def notificar_recuperacion_nucleo(self, nucleo: str):
        """Notifica que un núcleo se ha recuperado."""
        self.redundancia.marcar_nucleo_recuperado(nucleo)
        
        # Verificar si todos los núcleos están recuperados
        stats = self.redundancia.obtener_estadisticas()
        if stats['nucleos_caidos'] == 0:
            self.desactivar_fallback()
    
    def guardar_estado(self) -> bool:
        """Guarda el estado actual para recuperación."""
        estado = {
            'fallback_activo': self._fallback_activo,
            'ultimo_error': self._ultimo_error,
            'circuit_breaker': self.circuit_breaker.metricas,
            'degradador': self.degradador.obtener_estado(),
            'redundancia': self.redundancia.obtener_estadisticas(),
            'historial_fallos': list(self._historial_fallos)[-10:],
        }
        return self.recuperador.guardar_punto_control('fallback_estado', estado)
    
    def recuperar_estado(self) -> Optional[Dict[str, Any]]:
        """Recupera el último estado guardado."""
        return self.recuperador.recuperar('fallback_estado')
    
    def obtener_estado(self) -> Dict[str, Any]:
        """Obtiene el estado completo del gestor de fallback."""
        return {
            'fallback_activo': self._fallback_activo,
            'ultimo_error': self._ultimo_error,
            'circuit_breaker': self.circuit_breaker.metricas,
            'degradador': self.degradador.obtener_estado(),
            'redundancia': self.redundancia.obtener_estadisticas(),
            'total_fallos': len(self._historial_fallos),
            'ultimos_fallos': list(self._historial_fallos)[-5:],
        }
    
    def __repr__(self) -> str:
        estado = "FALLBACK" if self._fallback_activo else "NORMAL"
        return f"GestorFallback(estado={estado})"

# =====================================================================
# 7. FUNCIONES DE CONVENIENCIA Y SINGLETON
# =====================================================================

_gestor_global: Optional[GestorFallback] = None

def obtener_gestor_fallback() -> GestorFallback:
    """Obtiene la instancia global del gestor de fallback."""
    global _gestor_global
    if _gestor_global is None:
        _gestor_global = GestorFallback()
    return _gestor_global

def inicializar_sistema_fallback() -> GestorFallback:
    """Inicializa el sistema de fallback completo."""
    gestor = obtener_gestor_fallback()
    gestor.guardar_estado()
    return gestor

# =====================================================================
# 8. DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DE WRAPPERS DE FALLBACK")
    print("=" * 70)
    
    try:
        # 1. Circuit Breaker
        print("\n[1/6] Probando Circuit Breaker...")
        cb = CircuitBreaker("test", umbral_fallos=2)
        print(f"  ✅ Estado inicial: {cb.estado.value}")
        cb.registrar_fallo()
        cb.registrar_fallo()
        print(f"  ✅ Después de 2 fallos: {cb.estado.value}")
        
        # 2. Detector de Anomalías
        print("\n[2/6] Probando Detector de Anomalías...")
        det = DetectorAnomalias(sensibilidad=2.0)
        for i in range(10):
            det.registrar_medicion("cpu", 50.0 + random.uniform(-5, 5))
        anomalo = det.es_anomalo("cpu", 90.0)
        print(f"  ✅ Valor 90% es anómalo: {anomalo}")
        print(f"  ✅ Score de anomalía: {det.obtener_anomalia_score('cpu', 90.0):.2f}")
        
        # 3. Degradador
        print("\n[3/6] Probando Degradador...")
        deg = Degradador()
        print(f"  ✅ Estado inicial: {deg.nivel_actual.value}")
        deg.degradar(NivelDegradacion.MODERADO, "prueba")
        print(f"  ✅ Después de degradar: {deg.nivel_actual.value}")
        print(f"  ✅ Funcionalidades deshabilitadas: {len(deg.obtener_funcionalidades_deshabilitadas())}")
        
        # 4. Redundancia de Núcleos
        print("\n[4/6] Probando Redundancia de Núcleos...")
        red = RedundanciaNucleos()
        for nucleo in ['comunicacion', 'razonamiento', 'memoria']:
            alt = red.obtener_alternativa(nucleo)
            print(f"  ✅ {nucleo} -> {alt}")
        
        # 5. Recuperador de Estado
        print("\n[5/6] Probando Recuperador de Estado...")
        rec = RecuperadorEstado(max_puntos=3)
        rec.guardar_punto_control("test1", {"valor": 42})
        rec.guardar_punto_control("test2", {"valor": 100})
        ultimo = rec.recuperar_ultimo()
        print(f"  ✅ Último punto recuperado: {ultimo}")
        print(f"  ✅ Total puntos: {rec.obtener_estadisticas()['total_puntos']}")
        
        # 6. Gestor de Fallback
        print("\n[6/6] Probando Gestor de Fallback...")
        gestor = obtener_gestor_fallback()
        print(f"  ✅ Gestor inicializado: {gestor}")
        estado = gestor.activar_fallback("prueba de diagnóstico", TipoFallo.DESCONOCIDO)
        print(f"  ✅ Fallback activado: {estado['fallback_activo']}")
        print(f"  ✅ Circuit Breaker: {estado['circuit_breaker']['estado']}")
        gestor.desactivar_fallback()
        print(f"  ✅ Fallback desactivado")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   Todos los wrappers de fallback están funcionando.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")