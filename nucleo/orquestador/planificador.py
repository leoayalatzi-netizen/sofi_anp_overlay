# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Planificador de Ejecución (Sistema de Planificación Cuántica)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================

import sys
import os
import time
import threading
import uuid
import json
import math
import random
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple, DefaultDict
from dataclasses import dataclass, field
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, OrderedDict, Counter
import heapq

# =====================================================================
# ENUMERACIONES Y ESTRUCTURAS FUNDAMENTALES
# =====================================================================

class PrioridadTarea(IntEnum):
    CRITICA = 0
    ALTA = 1
    MEDIA = 2
    BAJA = 3
    DIFERIDA = 4

class TipoTarea(Enum):
    CONSULTA = "consulta"
    RAZONAMIENTO = "razonamiento"
    BUSQUEDA = "busqueda"
    MEMORIA = "memoria"
    RESOLUCION = "resolucion"
    CREATIVIDAD = "creatividad"
    SISTEMA = "sistema"
    FALLBACK = "fallback"
    COMPUESTA = "compuesta"

class EstadoTarea(Enum):
    PENDIENTE = "pendiente"
    EN_COLA = "en_cola"
    ASIGNADA = "asignada"
    EN_EJECUCION = "en_ejecucion"
    COMPLETADA = "completada"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"
    BLOQUEADA = "bloqueada"
    REINTENTANDO = "reintentando"

class EstrategiaPlanificacion(Enum):
    FIFO = "fifo"
    PRIORIDAD = "prioridad"
    MENOR_TIEMPO_PRIMERO = "srtf"
    FECHA_LIMITE = "deadline"
    CUANTICO = "cuantico"

class TipoDependencia(Enum):
    TERMINA_ANTES = "termina_antes"
    COMIENZA_DESPUES = "comienza_despues"
    EXCLUSIVA = "exclusiva"

class VentanaTemporal(Enum):
    INMEDIATA = "inmediata"
    DIFERIDA = "diferida"
    PROGRAMADA = "programada"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class RestriccionTemporal:
    ventana: VentanaTemporal = VentanaTemporal.INMEDIATA
    tiempo_estimado: float = 1.0
    tiempo_maximo: Optional[float] = None
    fecha_limite: Optional[float] = None
    prioridad_temporal: float = 1.0
    
    def urgencia(self, tiempo_actual: float) -> float:
        if not self.fecha_limite:
            return 0.0
        tiempo_restante = self.fecha_limite - tiempo_actual
        if tiempo_restante <= 0:
            return float('inf')
        return self.tiempo_estimado / max(tiempo_restante, 0.001)

@dataclass
class Dependencia:
    tarea_dependiente: str
    tarea_requerida: str
    tipo: TipoDependencia = TipoDependencia.TERMINA_ANTES

@dataclass
class RecursoRequerido:
    nucleo_preferido: Optional[str] = None
    nucleos_compatibles: List[str] = field(default_factory=list)
    memoria_estimada_mb: float = 10.0
    cpu_estimada: float = 0.1
    requiere_gpu: bool = False
    exclusividad: bool = False

@dataclass
class MetricaPlanificacion:
    tiempo_llegada: float = field(default_factory=time.time)
    tiempo_inicio: Optional[float] = None
    tiempo_fin: Optional[float] = None
    tiempo_espera: float = 0.0
    tiempo_ejecucion: float = 0.0
    intentos: int = 0
    prioridad_inicial: PrioridadTarea = PrioridadTarea.MEDIA
    prioridad_actual: PrioridadTarea = PrioridadTarea.MEDIA
    
    def finalizar(self, exito: bool = True):
        self.tiempo_fin = time.time()
        if self.tiempo_inicio:
            self.tiempo_ejecucion = self.tiempo_fin - self.tiempo_inicio

@dataclass
class TareaPlanificada:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tipo: TipoTarea = TipoTarea.SISTEMA
    nombre: str = ""
    datos: Any = None
    contexto: Dict[str, Any] = field(default_factory=dict)
    estado: EstadoTarea = EstadoTarea.PENDIENTE
    restriccion_temporal: RestriccionTemporal = field(default_factory=RestriccionTemporal)
    recursos: RecursoRequerido = field(default_factory=RecursoRequerido)
    dependencias: List[Dependencia] = field(default_factory=list)
    dependientes: List[str] = field(default_factory=list)
    metricas: MetricaPlanificacion = field(default_factory=MetricaPlanificacion)
    resultado: Any = None
    error: Optional[str] = None
    padre_id: Optional[str] = None
    hijos_ids: List[str] = field(default_factory=list)
    on_completado: Optional[Callable] = None
    on_error: Optional[Callable] = None
    
    def __post_init__(self):
        if not self.nombre:
            self.nombre = f"{self.tipo.value}_{self.id[:8]}"
        self.metricas.prioridad_inicial = self.restriccion_temporal.prioridad_temporal
        self.metricas.prioridad_actual = self.metricas.prioridad_inicial
    
    @property
    def puede_ejecutarse(self) -> bool:
        return self.estado in (EstadoTarea.PENDIENTE, EstadoTarea.EN_COLA)
    
    @property
    def urgencia(self) -> float:
        urgencia_base = self.restriccion_temporal.urgencia(time.time())
        urgencia_prioridad = (5 - self.metricas.prioridad_actual.value) / 5.0
        urgencia_espera = min(self.metricas.tiempo_espera / 60.0, 1.0)
        return urgencia_base * 0.5 + urgencia_prioridad * 0.3 + urgencia_espera * 0.2
    
    def __lt__(self, other: 'TareaPlanificada') -> bool:
        if self.metricas.prioridad_actual != other.metricas.prioridad_actual:
            return self.metricas.prioridad_actual < other.metricas.prioridad_actual
        return self.urgencia > other.urgencia

# =====================================================================
# GRAFO DE DEPENDENCIAS
# =====================================================================

class GrafoDependencias:
    def __init__(self):
        self._nodos: Dict[str, TareaPlanificada] = {}
        self._adyacencia: DefaultDict[str, List[str]] = defaultdict(list)
        self._inverso: DefaultDict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()
        
    def agregar_nodo(self, tarea: TareaPlanificada) -> bool:
        with self._lock:
            if tarea.id in self._nodos:
                return False
            self._nodos[tarea.id] = tarea
            return True
    
    def agregar_dependencia(self, dependencia: Dependencia) -> bool:
        with self._lock:
            origen = dependencia.tarea_requerida
            destino = dependencia.tarea_dependiente
            
            if origen not in self._nodos or destino not in self._nodos:
                return False
            
            if self._crea_ciclo(origen, destino):
                return False
            
            self._adyacencia[origen].append(destino)
            self._inverso[destino].append(origen)
            
            self._nodos[origen].dependientes.append(destino)
            self._nodos[destino].dependencias.append(dependencia)
            
            return True
    
    def _crea_ciclo(self, origen: str, destino: str) -> bool:
        visitados = set()
        def dfs(nodo: str) -> bool:
            if nodo == origen:
                return True
            if nodo in visitados:
                return False
            visitados.add(nodo)
            for vecino in self._adyacencia[nodo]:
                if dfs(vecino):
                    return True
            return False
        return dfs(destino)
    
    def tarea_esta_lista(self, tarea_id: str) -> bool:
        with self._lock:
            for origen in self._inverso.get(tarea_id, []):
                tarea_origen = self._nodos.get(origen)
                if tarea_origen and tarea_origen.estado != EstadoTarea.COMPLETADA:
                    return False
            return True
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_nodos': len(self._nodos),
                'total_aristas': sum(len(v) for v in self._adyacencia.values()),
            }

# =====================================================================
# COLA DE PRIORIDAD ADAPTATIVA
# =====================================================================

class ColaPrioridadAdaptativa:
    def __init__(self, factor_envejecimiento: float = 0.1):
        self._heap: List[Tuple[float, int, TareaPlanificada]] = []
        self._contador = 0
        self._factor_envejecimiento = factor_envejecimiento
        self._lock = threading.RLock()
        self._tareas_por_id: Dict[str, TareaPlanificada] = {}
        
    def poner(self, tarea: TareaPlanificada) -> bool:
        with self._lock:
            if tarea.id in self._tareas_por_id:
                return False
            self._contador += 1
            prioridad = self._calcular_prioridad(tarea)
            heapq.heappush(self._heap, (-prioridad, self._contador, tarea))
            self._tareas_por_id[tarea.id] = tarea
            return True
    
    def obtener(self) -> Optional[TareaPlanificada]:
        with self._lock:
            if not self._heap:
                return None
            _, _, tarea = heapq.heappop(self._heap)
            del self._tareas_por_id[tarea.id]
            self._envejecer_tareas()
            return tarea
    
    def _calcular_prioridad(self, tarea: TareaPlanificada) -> float:
        if hasattr(tarea.metricas.prioridad_actual, 'value'):
            prioridad_valor = tarea.metricas.prioridad_actual.value
        else:
            prioridad_valor = int(tarea.metricas.prioridad_actual) if tarea.metricas.prioridad_actual else 2
        prioridad_base = (5 - prioridad_valor) / 5.0
        urgencia = tarea.urgencia
        espera = min(tarea.metricas.tiempo_espera / 30.0, 2.0)
        return prioridad_base * 0.4 + urgencia * 0.4 + espera * 0.2
    
    def _envejecer_tareas(self):
        nuevas_tareas = []
        for prioridad_neg, contador, tarea in self._heap:
            tarea.metricas.tiempo_espera += self._factor_envejecimiento
            nueva_prioridad = self._calcular_prioridad(tarea)
            nuevas_tareas.append((-nueva_prioridad, contador, tarea))
        heapq.heapify(nuevas_tareas)
        self._heap = nuevas_tareas
    
    def eliminar(self, tarea_id: str) -> bool:
        with self._lock:
            if tarea_id not in self._tareas_por_id:
                return False
            self._heap = [(p, c, t) for p, c, t in self._heap if t.id != tarea_id]
            heapq.heapify(self._heap)
            del self._tareas_por_id[tarea_id]
            return True
    
    def __len__(self) -> int:
        return len(self._heap)
    
    def __bool__(self) -> bool:
        return len(self._heap) > 0

# =====================================================================
# PLANIFICADOR PRINCIPAL
# =====================================================================

class Planificador:
    def __init__(self, estrategia: EstrategiaPlanificacion = EstrategiaPlanificacion.CUANTICO):
        self.estrategia = estrategia
        self.id_planificador = str(uuid.uuid4())
        self.timestamp_inicio = time.time()
        
        self._cola_principal = ColaPrioridadAdaptativa()
        self._cola_diferida = deque()
        
        self._tareas: Dict[str, TareaPlanificada] = {}
        self._tareas_en_ejecucion: Dict[str, TareaPlanificada] = {}
        self._tareas_completadas: OrderedDict[str, TareaPlanificada] = OrderedDict()
        self._tareas_fallidas: Dict[str, TareaPlanificada] = {}
        
        self._grafo = GrafoDependencias()
        
        self._recursos_disponibles: Dict[str, float] = {
            'cpu': 1.0,
            'memoria': 1024.0,
            'gpu': 0.0,
        }
        self._recursos_en_uso: Dict[str, float] = defaultdict(float)
        
        self._metricas: DefaultDict[str, List[float]] = defaultdict(list)
        self._contador_tareas: DefaultDict[str, int] = defaultdict(int)
        
        self._activo = True
        self._pausado = False
        self._lock = threading.RLock()
        
        self._hilo_planificador: Optional[threading.Thread] = None
        self._hilo_monitor: Optional[threading.Thread] = None
        
        self._iniciar_hilos()
    
    # =====================================================================
    # INICIALIZACIÓN
        # =====================================================================
    
    def _iniciar_hilos(self):
        self._hilo_planificador = threading.Thread(target=self._bucle_planificador, daemon=True)
        self._hilo_planificador.start()
        self._hilo_monitor = threading.Thread(target=self._bucle_monitor, daemon=True)
        self._hilo_monitor.start()
    
    # =====================================================================
    # BUCLES DE PLANIFICACIÓN
    # =====================================================================
    
    def _bucle_planificador(self):
        while self._activo:
            if self._pausado:
                time.sleep(0.1)
                continue
            
            try:
                self._procesar_tareas_diferidas()
                tarea = self._seleccionar_siguiente_tarea()
                
                if tarea:
                    if self._recursos_suficientes(tarea):
                        self._asignar_tarea(tarea)
                    else:
                        self._encolar_tarea(tarea)
                        time.sleep(0.05)
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                time.sleep(0.1)
    
    def _bucle_monitor(self):
        while self._activo:
            try:
                ahora = time.time()
                tareas_a_mover = []
                
                with self._lock:
                    for tarea_id, tarea in list(self._tareas_en_ejecucion.items()):
                        if tarea.metricas.tiempo_inicio:
                            tiempo_ejecucion = ahora - tarea.metricas.tiempo_inicio
                            if tarea.restriccion_temporal.tiempo_maximo:
                                if tiempo_ejecucion > tarea.restriccion_temporal.tiempo_maximo:
                                    tareas_a_mover.append(tarea_id)
                
                for tarea_id in tareas_a_mover:
                    with self._lock:
                        if tarea_id in self._tareas_en_ejecucion:
                            tarea = self._tareas_en_ejecucion.pop(tarea_id)
                            tarea.estado = EstadoTarea.FALLIDA
                            tarea.error = "Timeout"
                            self._tareas_fallidas[tarea_id] = tarea
                            self._liberar_recursos(tarea)
                            self._intentar_fallback(tarea)
                
                time.sleep(0.5)
                
            except Exception as e:
                time.sleep(1.0)
    
    # =====================================================================
    # SELECCIÓN DE TAREAS
    # =====================================================================
    
    def _seleccionar_siguiente_tarea(self) -> Optional[TareaPlanificada]:
        if not self._cola_principal:
            return None
        return self._cola_principal.obtener()
    
    def _procesar_tareas_diferidas(self):
        ahora = time.time()
        while self._cola_diferida:
            tarea, tiempo_ejecucion = self._cola_diferida[0]
            if tiempo_ejecucion <= ahora:
                self._cola_diferida.popleft()
                self._encolar_tarea(tarea)
            else:
                break
    
    # =====================================================================
    # GESTIÓN DE RECURSOS
    # =====================================================================
    
    def _recursos_suficientes(self, tarea: TareaPlanificada) -> bool:
        recursos = tarea.recursos
        if self._recursos_disponibles.get('memoria', 0) < recursos.memoria_estimada_mb:
            return False
        if self._recursos_disponibles.get('cpu', 0) < recursos.cpu_estimada:
            return False
        if recursos.exclusividad and self._tareas_en_ejecucion:
            return False
        return True
    
    def _reservar_recursos(self, tarea: TareaPlanificada):
        recursos = tarea.recursos
        self._recursos_disponibles['memoria'] -= recursos.memoria_estimada_mb
        self._recursos_disponibles['cpu'] -= recursos.cpu_estimada
        self._recursos_en_uso['memoria'] += recursos.memoria_estimada_mb
        self._recursos_en_uso['cpu'] += recursos.cpu_estimada
    
    def _liberar_recursos(self, tarea: TareaPlanificada):
        recursos = tarea.recursos
        self._recursos_disponibles['memoria'] += recursos.memoria_estimada_mb
        self._recursos_disponibles['cpu'] += recursos.cpu_estimada
        self._recursos_en_uso['memoria'] -= recursos.memoria_estimada_mb
        self._recursos_en_uso['cpu'] -= recursos.cpu_estimada
    
    # =====================================================================
    # GESTIÓN DE TAREAS (EJECUCIÓN)
    # =====================================================================
    
    def _encolar_tarea(self, tarea: TareaPlanificada):
        tarea.estado = EstadoTarea.EN_COLA
        self._cola_principal.poner(tarea)
    
    def _asignar_tarea(self, tarea: TareaPlanificada):
        with self._lock:
            tarea.estado = EstadoTarea.ASIGNADA
            tarea.metricas.tiempo_inicio = time.time()
            tarea.metricas.tiempo_espera = tarea.metricas.tiempo_inicio - tarea.metricas.tiempo_llegada
            self._tareas_en_ejecucion[tarea.id] = tarea
            self._reservar_recursos(tarea)
            threading.Thread(target=self._ejecutar_tarea, args=(tarea,), daemon=True).start()
    
    def _ejecutar_tarea(self, tarea: TareaPlanificada):
        tarea.estado = EstadoTarea.EN_EJECUCION
        try:
            time.sleep(min(tarea.restriccion_temporal.tiempo_estimado, random.uniform(0.1, 2.0)))
            if random.random() > 0.05:
                self._completar_tarea(tarea, {"status": "success", "data": tarea.datos})
            else:
                raise Exception("Error simulado")
        except Exception as e:
            self._fallar_tarea(tarea, str(e))
    
    def _completar_tarea(self, tarea: TareaPlanificada, resultado: Any):
        with self._lock:
            tarea.estado = EstadoTarea.COMPLETADA
            tarea.resultado = resultado
            tarea.metricas.finalizar(True)
            if tarea.id in self._tareas_en_ejecucion:
                del self._tareas_en_ejecucion[tarea.id]
            self._tareas_completadas[tarea.id] = tarea
            self._liberar_recursos(tarea)
            self._contador_tareas['completadas'] += 1
            self._desbloquear_dependientes(tarea.id)
            if tarea.on_completado:
                try:
                    tarea.on_completado(resultado)
                except:
                    pass
            if tarea.padre_id:
                self._verificar_tarea_padre(tarea.padre_id)
    
    def _fallar_tarea(self, tarea: TareaPlanificada, error: str):
        with self._lock:
            tarea.estado = EstadoTarea.FALLIDA
            tarea.error = error
            tarea.metricas.finalizar(False)
            tarea.metricas.intentos += 1
            if tarea.id in self._tareas_en_ejecucion:
                del self._tareas_en_ejecucion[tarea.id]
            self._tareas_fallidas[tarea.id] = tarea
            self._liberar_recursos(tarea)
            self._contador_tareas['fallidas'] += 1
            if tarea.on_error:
                try:
                    tarea.on_error(error)
                except:
                    pass
            self._intentar_fallback(tarea)
    
    def _intentar_fallback(self, tarea: TareaPlanificada):
        if tarea.metricas.intentos < 3:
            tarea.estado = EstadoTarea.REINTENTANDO
            self._encolar_tarea(tarea)
            self._contador_tareas['reintentos'] += 1
    
    def _desbloquear_dependientes(self, tarea_id: str):
        tarea = self._tareas.get(tarea_id)
        if not tarea:
            return
        for dependiente_id in tarea.dependientes:
            if dependiente_id in self._tareas:
                tarea_dep = self._tareas[dependiente_id]
                if tarea_dep.estado == EstadoTarea.BLOQUEADA:
                    if self._grafo.tarea_esta_lista(dependiente_id):
                        tarea_dep.estado = EstadoTarea.PENDIENTE
                        self._encolar_tarea(tarea_dep)
    
    def _verificar_tarea_padre(self, padre_id: str):
        padre = self._tareas.get(padre_id)
        if not padre:
            return
        todos_completados = all(
            self._tareas[h].estado == EstadoTarea.COMPLETADA
            for h in padre.hijos_ids if h in self._tareas
        )
        if todos_completados:
            self._completar_tarea(padre, {"status": "compuesta_completada"})
    
    # =====================================================================
    # API PÚBLICA
        # =====================================================================
    
    def planificar(
        self,
        tipo: TipoTarea,
        datos: Any = None,
        nombre: str = "",
        prioridad: PrioridadTarea = PrioridadTarea.MEDIA,
        dependencias: List[str] = None,
        tiempo_estimado: float = 1.0,
        fecha_limite: Optional[float] = None,
        recursos: Optional[RecursoRequerido] = None,
        contexto: Dict[str, Any] = None,
        on_completado: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        **kwargs
    ) -> str:
        with self._lock:
            restriccion = RestriccionTemporal(
                tiempo_estimado=tiempo_estimado,
                fecha_limite=fecha_limite,
                prioridad_temporal=float(5 - prioridad.value) / 5.0,
            )
            tarea = TareaPlanificada(
                tipo=tipo,
                nombre=nombre or f"{tipo.value}_{uuid.uuid4().hex[:8]}",
                datos=datos,
                contexto=contexto or {},
                restriccion_temporal=restriccion,
                recursos=recursos or RecursoRequerido(),
                on_completado=on_completado,
                on_error=on_error,
            )
            tarea.metricas.prioridad_inicial = prioridad
            tarea.metricas.prioridad_actual = prioridad
            tarea.metricas.tiempo_llegada = time.time()
            
            self._tareas[tarea.id] = tarea
            self._grafo.agregar_nodo(tarea)
            
            if dependencias:
                for dep_id in dependencias:
                    if dep_id in self._tareas:
                        dep = Dependencia(
                            tarea_dependiente=tarea.id,
                            tarea_requerida=dep_id,
                            tipo=TipoDependencia.TERMINA_ANTES
                        )
                        self._grafo.agregar_dependencia(dep)
            
            if self._grafo.tarea_esta_lista(tarea.id):
                self._encolar_tarea(tarea)
            else:
                tarea.estado = EstadoTarea.BLOQUEADA
            
            self._contador_tareas['planificadas'] += 1
            return tarea.id
    
    def planificar_compuesta(
        self,
        tareas: List[Tuple[TipoTarea, Any]],
        nombre: str = "",
        prioridad: PrioridadTarea = PrioridadTarea.MEDIA,
        **kwargs
    ) -> str:
        with self._lock:
            tarea_padre = TareaPlanificada(
                tipo=TipoTarea.COMPUESTA,
                nombre=nombre or f"compuesta_{uuid.uuid4().hex[:8]}",
            )
            tarea_padre.metricas.tiempo_llegada = time.time()
            tarea_padre.metricas.prioridad_inicial = prioridad
            tarea_padre.metricas.prioridad_actual = prioridad
            
            self._tareas[tarea_padre.id] = tarea_padre
            self._grafo.agregar_nodo(tarea_padre)
            
            tareas_previas = []
            for i, (tipo, datos) in enumerate(tareas):
                sub_tarea = TareaPlanificada(
                    tipo=tipo,
                    nombre=f"{nombre}_sub_{i}",
                    datos=datos,
                    padre_id=tarea_padre.id,
                )
                sub_tarea.metricas.tiempo_llegada = time.time()
                sub_tarea.metricas.prioridad_inicial = prioridad
                sub_tarea.metricas.prioridad_actual = prioridad
                
                self._tareas[sub_tarea.id] = sub_tarea
                self._grafo.agregar_nodo(sub_tarea)
                tarea_padre.hijos_ids.append(sub_tarea.id)
                
                if tareas_previas:
                    for prev_id in tareas_previas:
                        dep = Dependencia(
                            tarea_dependiente=sub_tarea.id,
                            tarea_requerida=prev_id,
                            tipo=TipoDependencia.TERMINA_ANTES
                        )
                        self._grafo.agregar_dependencia(dep)
                
                tareas_previas.append(sub_tarea.id)
                
                if self._grafo.tarea_esta_lista(sub_tarea.id):
                    self._encolar_tarea(sub_tarea)
                else:
                    sub_tarea.estado = EstadoTarea.BLOQUEADA
            
            self._contador_tareas['planificadas'] += 1
            return tarea_padre.id
    
    def cancelar_tarea(self, tarea_id: str) -> bool:
        with self._lock:
            if tarea_id not in self._tareas:
                return False
            tarea = self._tareas[tarea_id]
            if not tarea.puede_ejecutarse:
                return False
            tarea.estado = EstadoTarea.CANCELADA
            self._cola_principal.eliminar(tarea_id)
            self._contador_tareas['canceladas'] += 1
            return True
    
    def obtener_estado_tarea(self, tarea_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if tarea_id not in self._tareas:
                return None
            tarea = self._tareas[tarea_id]
            if hasattr(tarea.metricas.prioridad_actual, 'value'):
                prioridad_val = tarea.metricas.prioridad_actual.value
            else:
                prioridad_val = int(tarea.metricas.prioridad_actual) if tarea.metricas.prioridad_actual else 2
            return {
                'id': tarea.id,
                'nombre': tarea.nombre,
                'tipo': tarea.tipo.value,
                'estado': tarea.estado.value,
                'prioridad': prioridad_val,
                'urgencia': tarea.urgencia,
                'tiempo_espera': tarea.metricas.tiempo_espera,
            }
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'planificador': {
                    'id': self.id_planificador,
                    'estrategia': self.estrategia.value,
                    'uptime': time.time() - self.timestamp_inicio,
                    'activo': self._activo,
                    'pausado': self._pausado,
                },
                'tareas': {
                    'total': len(self._tareas),
                    'en_cola': len(self._cola_principal),
                    'en_ejecucion': len(self._tareas_en_ejecucion),
                    'completadas': len(self._tareas_completadas),
                    'fallidas': len(self._tareas_fallidas),
                    'bloqueadas': sum(1 for t in self._tareas.values() if t.estado == EstadoTarea.BLOQUEADA),
                },
                'contadores': dict(self._contador_tareas),
                'grafo': self._grafo.obtener_estadisticas(),
                'recursos': {
                    'disponibles': dict(self._recursos_disponibles),
                    'en_uso': dict(self._recursos_en_uso),
                },
            }
    
    def cambiar_estrategia(self, nueva_estrategia: EstrategiaPlanificacion):
        self.estrategia = nueva_estrategia
    
    def pausar(self):
        self._pausado = True
    
    def reanudar(self):
        self._pausado = False
    
    def apagar(self, graceful: bool = True):
        self._activo = False
        if graceful:
            while self._tareas_en_ejecucion:
                time.sleep(0.1)
        if self._hilo_planificador:
            self._hilo_planificador.join(timeout=5.0)
        if self._hilo_monitor:
            self._hilo_monitor.join(timeout=5.0)
    
    def __repr__(self) -> str:
        return f"Planificador(estrategia={self.estrategia.value}, tareas={len(self._tareas)})"

# =====================================================================
# FÁBRICA Y SINGLETON
# =====================================================================

class FabricaPlanificador:
    @staticmethod
    def crear_planificador_cuantico() -> Planificador:
        return Planificador(estrategia=EstrategiaPlanificacion.CUANTICO)

_planificador_global: Optional[Planificador] = None
_lock_planificador = threading.RLock()

def obtener_planificador() -> Planificador:
    global _planificador_global
    with _lock_planificador:
        if _planificador_global is None:
            _planificador_global = FabricaPlanificador.crear_planificador_cuantico()
        return _planificador_global

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL PLANIFICADOR DE EJECUCIÓN")
    print("=" * 70)
    
    planificador = None
    
    try:
        print("\n[1/6] Creando planificador...")
        planificador = FabricaPlanificador.crear_planificador_cuantico()
        print(f"  ✅ Planificador creado: {planificador}")
        
        print("\n[2/6] Planificando tareas simples...")
        tareas_ids = []
        for i in range(5):
            tipo = random.choice(list(TipoTarea))
            tarea_id = planificador.planificar(
                tipo=tipo,
                datos=f"Tarea {i}",
                nombre=f"test_{i}",
                prioridad=PrioridadTarea(random.randint(0, 4))
            )
            tareas_ids.append(tarea_id)
            print(f"  ✓ Tarea {i}: {tarea_id[:8]}... ({tipo.value})")
        
        print("\n[3/6] Planificando tarea con dependencias...")
        tarea_base = planificador.planificar(
            tipo=TipoTarea.RAZONAMIENTO,
            datos="Tarea base",
            nombre="tarea_base"
        )
        print(f"  ✓ Tarea base: {tarea_base[:8]}...")
        
        tarea_dependiente = planificador.planificar(
            tipo=TipoTarea.CONSULTA,
            datos="Tarea dependiente",
            nombre="tarea_dep",
            dependencias=[tarea_base]
        )
        print(f"  ✓ Tarea dependiente: {tarea_dependiente[:8]}...")
        
        print("\n[4/6] Procesando tareas...")
        time.sleep(3.0)
        
        print("\n[5/6] Verificando estados:")
        for tarea_id in tareas_ids[:3]:
            estado = planificador.obtener_estado_tarea(tarea_id)
            if estado:
                print(f"  ✓ {tarea_id[:8]}: {estado['estado']} (prioridad={estado['prioridad']})")
        
        print("\n[6/6] Estadísticas:")
        stats = planificador.obtener_estadisticas()
        print(f"  📊 Uptime: {stats['planificador']['uptime']:.2f}s")
        print(f"  📊 Tareas: total={stats['tareas']['total']}, completadas={stats['tareas']['completadas']}, fallidas={stats['tareas']['fallidas']}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        
    finally:
        if planificador:
            print("\n🛑 Apagando planificador...")
            planificador.apagar(graceful=True)
            print("   ✓ Apagado correctamente")
    
    print("\n" + "=" * 70 + "\n")