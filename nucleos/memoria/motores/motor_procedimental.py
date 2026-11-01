#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Procedimental — Memoria de Procedimientos y Reglas
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, uuid, traceback, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from collections import OrderedDict, deque, Counter
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
# ENUMERACIONES
# =====================================================================

class TipoProcedimiento(Enum):
    ALGORITMO = "algoritmo"
    RUTINA = "rutina"
    HABITO = "habito"
    PROTOCOLO = "protocolo"
    HEURISTICA = "heuristica"
    REGLA = "regla"
    SCRIPT = "script"
    PATRON = "patron"
    METODO = "metodo"

class EstadoProcedimiento(Enum):
    ACTIVO = "activo"
    EN_EJECUCION = "en_ejecucion"
    PAUSADO = "pausado"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    OBSOLETO = "obsoleto"

class TipoPaso(Enum):
    ACCION = "accion"
    CONDICION = "condicion"
    BUCLE = "bucle"
    ESPERA = "espera"
    SUBPROCEDIMIENTO = "subprocedimiento"
    PARALELO = "paralelo"
    EVENTO = "evento"
    VALIDACION = "validacion"

class TipoRegla(Enum):
    SI_ENTONCES = "si_entonces"
    CUANDO = "cuando"
    DISPARADOR = "disparador"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class PasoProcedimiento:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    tipo: TipoPaso = TipoPaso.ACCION
    instruccion: str = ""
    parametros: Dict[str, Any] = field(default_factory=dict)
    precondiciones: List[str] = field(default_factory=list)
    postcondiciones: List[str] = field(default_factory=list)
    orden: int = 0
    siguiente_id: Optional[str] = None
    anterior_id: Optional[str] = None
    subprocedimiento_id: Optional[str] = None

@dataclass
class Procedimiento:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    tipo: TipoProcedimiento = TipoProcedimiento.ALGORITMO
    descripcion: str = ""
    pasos: OrderedDict = field(default_factory=OrderedDict)
    paso_inicial: Optional[str] = None
    paso_actual: Optional[str] = None
    estado: EstadoProcedimiento = EstadoProcedimiento.ACTIVO
    version: int = 1
    etiquetas: List[str] = field(default_factory=list)
    precondiciones: List[str] = field(default_factory=list)
    postcondiciones: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    contador_ejecuciones: int = 0
    tiempo_promedio: float = 0.0
    tasa_exito: float = 1.0
    timestamp_creacion: float = field(default_factory=time.time)
    timestamp_ultima_ejecucion: float = 0.0

@dataclass
class ReglaProcedimental:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    tipo: TipoRegla = TipoRegla.SI_ENTONCES
    condicion: str = ""
    accion: str = ""
    prioridad: int = 0
    activa: bool = True
    contador_activaciones: int = 0
    efectos: List[str] = field(default_factory=list)

@dataclass
class SistemaReglas:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str = ""
    reglas: Dict[str, ReglaProcedimental] = field(default_factory=dict)
    estrategia: str = "primera"

# =====================================================================
# MOTOR PROCEDIMENTAL PRINCIPAL
# =====================================================================

class MotorProcedimental(MotorBase):
    def __init__(self, config=None):
        super().__init__(config)
        self._procedimientos: Dict[str, Procedimiento] = {}
        self._sistemas_reglas: Dict[str, SistemaReglas] = {}
        self._historial: deque = deque(maxlen=200)
        self._lock = threading.RLock()
        self._estadisticas = {
            'procedimientos_creados': 0, 'pasos_totales': 0,
            'ejecuciones_totales': 0, 'ejecuciones_exitosas': 0,
            'reglas_creadas': 0, 'reglas_activadas': 0,
        }
        self._dir = Path("almacenamiento/procedimental")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _procesar_impl(self, entrada, contexto=None):
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        
        # La clave 'operacion' define qué hace el motor
        operacion = entrada.get('operacion', 'info')
        
        with self._lock:
            if operacion == 'crear_procedimiento':
                return self._crear_proc(entrada)
            elif operacion == 'agregar_paso':
                return self._agregar_paso(entrada)
            elif operacion == 'ejecutar':
                return self._ejecutar(entrada)
            elif operacion == 'crear_regla':
                return self._crear_regla(entrada)
            elif operacion == 'activar_regla':
                return self._activar_regla(entrada)
            elif operacion == 'sistema_reglas_crear':
                return self._sistema_crear(entrada)
            elif operacion == 'obtener_procedimiento':
                return self._obtener_proc(entrada)
            elif operacion == 'listar':
                return self._listar(entrada)
            elif operacion == 'historial':
                return self._historial_acc(entrada)
            elif operacion == 'estadisticas':
                return self._estadisticas_acc(entrada)
            elif operacion == 'guardar':
                return self._guardar(entrada)
            elif operacion == 'cargar':
                return self._cargar(entrada)
            elif operacion == 'info':
                return self._info(entrada)
            else:
                return {'error': f'Operación desconocida: {operacion}', 'exito': False}

    def _crear_proc(self, e):
        tipo_str = e.get('tipo', 'algoritmo')
        try:
            tipo = TipoProcedimiento(tipo_str)
        except ValueError:
            tipo = TipoProcedimiento.ALGORITMO
        
        proc = Procedimiento(
            nombre=e.get('nombre', f'proc_{len(self._procedimientos)+1}'),
            tipo=tipo,
            descripcion=e.get('descripcion', ''),
            etiquetas=e.get('etiquetas', []),
            precondiciones=e.get('precondiciones', []),
            postcondiciones=e.get('postcondiciones', []),
        )
        self._procedimientos[proc.id] = proc
        self._estadisticas['procedimientos_creados'] += 1
        return {'exito': True, 'id': proc.id, 'nombre': proc.nombre, 'tipo': proc.tipo.value}

    def _agregar_paso(self, e):
        proc_id = e.get('procedimiento_id', '')
        if proc_id not in self._procedimientos:
            return {'error': f'Procedimiento no encontrado: {proc_id}', 'exito': False}
        
        proc = self._procedimientos[proc_id]
        
        tipo_str = e.get('tipo', 'accion')
        try:
            tipo = TipoPaso(tipo_str)
        except ValueError:
            tipo = TipoPaso.ACCION
        
        orden = len(proc.pasos) + 1
        paso = PasoProcedimiento(
            nombre=e.get('nombre', f'paso_{orden}'),
            tipo=tipo,
            instruccion=e.get('instruccion', ''),
            parametros=e.get('parametros', {}),
            precondiciones=e.get('precondiciones', []),
            postcondiciones=e.get('postcondiciones', []),
            orden=orden,
            subprocedimiento_id=e.get('subprocedimiento_id'),
        )
        
        if proc.pasos:
            ultimo = list(proc.pasos.values())[-1]
            ultimo.siguiente_id = paso.id
            paso.anterior_id = ultimo.id
        else:
            proc.paso_inicial = paso.id
        
        proc.pasos[paso.id] = paso
        self._estadisticas['pasos_totales'] += 1
        
        return {
            'exito': True,
            'paso_id': paso.id,
            'nombre': paso.nombre,
            'tipo': paso.tipo.value,
            'orden': paso.orden,
            'total_pasos': len(proc.pasos)
        }

    def _ejecutar(self, e):
        proc_id = e.get('procedimiento_id', '')
        if proc_id not in self._procedimientos:
            return {'error': f'Procedimiento no encontrado: {proc_id}', 'exito': False}
        
        proc = self._procedimientos[proc_id]
        proc.estado = EstadoProcedimiento.EN_EJECUCION
        proc.timestamp_ultima_ejecucion = time.time()
        proc.contador_ejecuciones += 1
        proc.variables = e.get('variables_iniciales', {})
        
        t0 = time.time()
        paso_id = proc.paso_inicial
        resultados = []
        exito_total = True
        
        while paso_id and paso_id in proc.pasos:
            paso = proc.pasos[paso_id]
            proc.paso_actual = paso_id
            
            res = {
                'exito': True,
                'paso_id': paso.id[:8],
                'nombre': paso.nombre,
                'tipo': paso.tipo.value,
                'tiempo': 0.0
            }
            
            t_paso = time.time()
            
            try:
                for pre in paso.precondiciones:
                    if pre not in proc.variables:
                        res['exito'] = False
                        res['error'] = f'Precondición no cumplida: {pre}'
                        break
                
                if res['exito']:
                    if paso.tipo in (TipoPaso.ACCION, TipoPaso.SUBPROCEDIMIENTO):
                        for k, v in paso.parametros.items():
                            proc.variables[k] = v
                        proc.variables[f'ejecutado_{paso.nombre}'] = True
                    elif paso.tipo == TipoPaso.VALIDACION:
                        requeridas = paso.parametros.get('requeridas', [])
                        for r in requeridas:
                            proc.variables[r] = r in proc.variables
                
                for post in paso.postcondiciones:
                    proc.variables[post] = True
                    
            except Exception as ex:
                res['exito'] = False
                res['error'] = str(ex)
            
            res['tiempo'] = round(time.time() - t_paso, 4)
            resultados.append(res)
            
            if not res['exito']:
                exito_total = False
                break
            
            paso_id = paso.siguiente_id
        
        tiempo_total = time.time() - t0
        n = max(1, proc.contador_ejecuciones)
        proc.tiempo_promedio = (proc.tiempo_promedio * (n - 1) + tiempo_total) / n
        proc.estado = EstadoProcedimiento.COMPLETADO if exito_total else EstadoProcedimiento.FALLIDO
        
        if exito_total:
            proc.tasa_exito = (proc.tasa_exito * (n - 1) + 1) / n
            self._estadisticas['ejecuciones_exitosas'] += 1
        
        self._estadisticas['ejecuciones_totales'] += 1
        self._historial.extend(resultados)
        
        return {
            'exito': exito_total,
            'procedimiento': proc.nombre,
            'pasos_ejecutados': len(resultados),
            'tiempo_total': round(tiempo_total, 4),
            'estado_final': proc.estado.value,
            'resultados': resultados
        }

    def _crear_regla(self, e):
        tipo_str = e.get('tipo', 'si_entonces')
        try:
            tipo = TipoRegla(tipo_str)
        except ValueError:
            tipo = TipoRegla.SI_ENTONCES
        
        regla = ReglaProcedimental(
            nombre=e.get('nombre', f'regla_{self._estadisticas["reglas_creadas"]+1}'),
            tipo=tipo,
            condicion=e.get('condicion', ''),
            accion=e.get('accion_regla', e.get('accion', '')),
            prioridad=int(e.get('prioridad', 0)),
            activa=bool(e.get('activa', True)),
            efectos=e.get('efectos', [])
        )
        
        sistema_id = e.get('sistema_id', 'default')
        if sistema_id not in self._sistemas_reglas:
            self._sistemas_reglas[sistema_id] = SistemaReglas(nombre=f'Sistema {sistema_id}')
        
        self._sistemas_reglas[sistema_id].reglas[regla.id] = regla
        self._estadisticas['reglas_creadas'] += 1
        
        return {'exito': True, 'regla_id': regla.id, 'nombre': regla.nombre, 'tipo': regla.tipo.value}

    def _activar_regla(self, e):
        sistema_id = e.get('sistema_id', 'default')
        if sistema_id not in self._sistemas_reglas:
            return {'error': f'Sistema no encontrado: {sistema_id}', 'exito': False}
        
        sistema = self._sistemas_reglas[sistema_id]
        contexto = e.get('contexto', {})
        
        reglas_activas = sorted(
            [r for r in sistema.reglas.values() if r.activa],
            key=lambda x: x.prioridad, reverse=True
        )
        
        activadas = []
        for regla in reglas_activas:
            condicion_valor = contexto.get(regla.condicion, False)
            if condicion_valor:
                regla.contador_activaciones += 1
                activadas.append({
                    'regla': regla.nombre,
                    'accion': regla.accion,
                    'efectos': regla.efectos
                })
                if sistema.estrategia == 'primera':
                    break
        
        self._estadisticas['reglas_activadas'] += len(activadas)
        return {'exito': True, 'reglas_activadas': len(activadas), 'resultados': activadas}

    def _sistema_crear(self, e):
        sistema = SistemaReglas(
            nombre=e.get('nombre', f'sistema_{len(self._sistemas_reglas)+1}'),
            estrategia=e.get('estrategia', 'primera')
        )
        self._sistemas_reglas[sistema.id] = sistema
        return {'exito': True, 'sistema_id': sistema.id, 'nombre': sistema.nombre}

    def _obtener_proc(self, e):
        pid = e.get('id', '')
        if pid not in self._procedimientos:
            return {'error': f'Procedimiento no encontrado: {pid}', 'exito': False}
        
        p = self._procedimientos[pid]
        pasos_lista = []
        for ps in p.pasos.values():
            pasos_lista.append({
                'id': ps.id,
                'nombre': ps.nombre,
                'tipo': ps.tipo.value,
                'orden': ps.orden,
                'instruccion': ps.instruccion[:60]
            })
        
        return {
            'exito': True,
            'procedimiento': {
                'id': p.id,
                'nombre': p.nombre,
                'tipo': p.tipo.value,
                'estado': p.estado.value,
                'total_pasos': len(p.pasos),
                'pasos': pasos_lista,
                'contador_ejecuciones': p.contador_ejecuciones,
                'tasa_exito': round(p.tasa_exito, 3),
                'etiquetas': p.etiquetas
            }
        }

    def _listar(self, e):
        procs = []
        for p in self._procedimientos.values():
            procs.append({
                'id': p.id,
                'nombre': p.nombre,
                'tipo': p.tipo.value,
                'estado': p.estado.value,
                'pasos': len(p.pasos),
                'ejecuciones': p.contador_ejecuciones
            })
        return {'exito': True, 'total': len(procs), 'procedimientos': procs[:20]}

    def _historial_acc(self, e):
        lim = e.get('limite', 20)
        hist = list(self._historial)[-lim:]
        return {'exito': True, 'total': len(self._historial), 'mostrados': len(hist), 'eventos': hist}

    def _estadisticas_acc(self, e):
        te = max(1, self._estadisticas['ejecuciones_totales'])
        return {
            'exito': True,
            'procedimientos_creados': self._estadisticas['procedimientos_creados'],
            'pasos_totales': self._estadisticas['pasos_totales'],
            'ejecuciones_totales': self._estadisticas['ejecuciones_totales'],
            'ejecuciones_exitosas': self._estadisticas['ejecuciones_exitosas'],
            'tasa_exito_global': round(self._estadisticas['ejecuciones_exitosas']/te, 3),
            'reglas_creadas': self._estadisticas['reglas_creadas'],
            'reglas_activadas': self._estadisticas['reglas_activadas'],
            'sistemas_reglas': len(self._sistemas_reglas)
        }

    def _guardar(self, e):
        try:
            ruta = e.get('ruta', str(self._dir/'memoria_procedimental'))
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            data = {
                'procedimientos': {},
                'sistemas_reglas': {},
                'estadisticas': self._estadisticas,
                'version': '0.0.1-NEBULA',
                'timestamp': time.time()
            }
            
            for pid, p in self._procedimientos.items():
                data['procedimientos'][pid] = {
                    'id': p.id, 'nombre': p.nombre, 'tipo': p.tipo.value,
                    'descripcion': p.descripcion, 'pasos': {},
                    'estado': p.estado.value, 'version': p.version,
                    'etiquetas': p.etiquetas,
                    'precondiciones': p.precondiciones,
                    'postcondiciones': p.postcondiciones,
                    'variables': p.variables,
                    'contador_ejecuciones': p.contador_ejecuciones,
                    'tiempo_promedio': p.tiempo_promedio,
                    'tasa_exito': p.tasa_exito,
                    'timestamp_creacion': p.timestamp_creacion,
                    'timestamp_ultima_ejecucion': p.timestamp_ultima_ejecucion,
                    'paso_inicial': p.paso_inicial,
                }
                for sid, ps in p.pasos.items():
                    data['procedimientos'][pid]['pasos'][sid] = {
                        'id': ps.id, 'nombre': ps.nombre, 'tipo': ps.tipo.value,
                        'instruccion': ps.instruccion,
                        'parametros': ps.parametros,
                        'precondiciones': ps.precondiciones,
                        'postcondiciones': ps.postcondiciones,
                        'orden': ps.orden,
                        'siguiente_id': ps.siguiente_id,
                        'anterior_id': ps.anterior_id,
                        'subprocedimiento_id': ps.subprocedimiento_id,
                    }
            
            for sid, s in self._sistemas_reglas.items():
                data['sistemas_reglas'][sid] = {
                    'id': s.id, 'nombre': s.nombre, 'reglas': {},
                    'estrategia': s.estrategia
                }
                for rid, r in s.reglas.items():
                    data['sistemas_reglas'][sid]['reglas'][rid] = {
                        'id': r.id, 'nombre': r.nombre, 'tipo': r.tipo.value,
                        'condicion': r.condicion, 'accion': r.accion,
                        'prioridad': r.prioridad, 'activa': r.activa,
                        'contador_activaciones': r.contador_activaciones,
                        'efectos': r.efectos
                    }
            
            with open(ruta+'.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
            return {'exito': True, 'ruta': ruta+'.pkl',
                   'procedimientos': len(data['procedimientos']),
                   'sistemas_reglas': len(data['sistemas_reglas'])}
        except Exception as ex:
            return {'error': str(ex), 'exito': False}

    def _cargar(self, e):
        try:
            ruta = e.get('ruta', '')
            if ruta.endswith('.pkl'): ruta = ruta[:-4]
            
            if not Path(ruta+'.pkl').exists():
                return {'error': f'No existe: {ruta}.pkl', 'exito': False}
            
            with open(ruta+'.pkl', 'rb') as f:
                data = pickle.load(f)
            
            self._procedimientos.clear()
            self._sistemas_reglas.clear()
            self._historial.clear()
            
            for pid, pd in data.get('procedimientos', {}).items():
                try:
                    tipo = TipoProcedimiento(pd['tipo'])
                except (ValueError, KeyError):
                    tipo = TipoProcedimiento.ALGORITMO
                
                p = Procedimiento(
                    id=pd['id'], nombre=pd['nombre'], tipo=tipo,
                    descripcion=pd.get('descripcion', ''),
                    estado=EstadoProcedimiento(pd.get('estado', 'activo')),
                    version=pd.get('version', 1),
                    etiquetas=pd.get('etiquetas', []),
                    precondiciones=pd.get('precondiciones', []),
                    postcondiciones=pd.get('postcondiciones', []),
                    variables=pd.get('variables', {}),
                    contador_ejecuciones=pd.get('contador_ejecuciones', 0),
                    tiempo_promedio=pd.get('tiempo_promedio', 0.0),
                    tasa_exito=pd.get('tasa_exito', 1.0),
                    timestamp_creacion=pd.get('timestamp_creacion', time.time()),
                    timestamp_ultima_ejecucion=pd.get('timestamp_ultima_ejecucion', 0.0),
                )
                
                p.paso_inicial = pd.get('paso_inicial')
                
                for sid, sd in pd.get('pasos', {}).items():
                    try:
                        tp = TipoPaso(sd['tipo'])
                    except (ValueError, KeyError):
                        tp = TipoPaso.ACCION
                    
                    ps = PasoProcedimiento(
                        id=sd['id'], nombre=sd['nombre'], tipo=tp,
                        instruccion=sd.get('instruccion', ''),
                        parametros=sd.get('parametros', {}),
                        precondiciones=sd.get('precondiciones', []),
                        postcondiciones=sd.get('postcondiciones', []),
                        orden=sd.get('orden', 0),
                        siguiente_id=sd.get('siguiente_id'),
                        anterior_id=sd.get('anterior_id'),
                        subprocedimiento_id=sd.get('subprocedimiento_id'),
                    )
                    p.pasos[ps.id] = ps
                
                self._procedimientos[p.id] = p
            
            for sid, sd in data.get('sistemas_reglas', {}).items():
                s = SistemaReglas(
                    id=sd['id'], nombre=sd['nombre'],
                    estrategia=sd.get('estrategia', 'primera')
                )
                for rid, rd in sd.get('reglas', {}).items():
                    try:
                        tr = TipoRegla(rd['tipo'])
                    except (ValueError, KeyError):
                        tr = TipoRegla.SI_ENTONCES
                    r = ReglaProcedimental(
                        id=rd['id'], nombre=rd['nombre'], tipo=tr,
                        condicion=rd.get('condicion', ''),
                        accion=rd.get('accion', ''),
                        prioridad=rd.get('prioridad', 0),
                        activa=rd.get('activa', True),
                        contador_activaciones=rd.get('contador_activaciones', 0),
                        efectos=rd.get('efectos', [])
                    )
                    s.reglas[r.id] = r
                self._sistemas_reglas[s.id] = s
            
            self._estadisticas = data.get('estadisticas', self._estadisticas)
            
            return {'exito': True, 'procedimientos': len(self._procedimientos),
                   'sistemas_reglas': len(self._sistemas_reglas)}
        except Exception as ex:
            return {'error': str(ex), 'exito': False}

    def _info(self, e):
        return {
            'exito': True,
            'nombre': self.nombre,
            'version': '0.0.1-NEBULA',
            'total_procedimientos': len(self._procedimientos),
            'total_reglas': sum(len(s.reglas) for s in self._sistemas_reglas.values()),
            'sistemas_reglas': len(self._sistemas_reglas),
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR PROCEDIMENTAL — MEMORIA DE PROCEDIMIENTOS")
    print("=" * 70)
    motor = None
    try:
        print("\n[0] Inicializando...")
        motor = MotorProcedimental()
        motor.inicializar()
        print(f"  ✅ Motor: {motor.nombre} | Estado: {motor.estado}")

        print("\n[1] Creando procedimiento:")
        r = motor.procesar({
            'operacion': 'crear_procedimiento',
            'nombre': 'Inicializar ANP',
            'tipo': 'rutina',
            'descripcion': 'Secuencia de inicialización del sistema ANP',
            'etiquetas': ['ANP', 'inicializacion', 'sistema']
        })
        d = r.datos if r and r.exito and r.datos else {}
        if not d.get('exito', True):
            print(f"  ❌ Error: {d}")
            sys.exit(1)
        proc_id = d['id']
        print(f"  ✅ {d['nombre']} (ID: {proc_id[:8]}...)")

        print("\n[2] Agregando pasos:")
        pasos = [
            {'nombre': 'Cargar config', 'tipo': 'accion',
             'instruccion': 'cargar_config', 'parametros': {'archivo': 'config.json'}},
            {'nombre': 'Inicializar nucleos', 'tipo': 'accion',
             'instruccion': 'inicializar_nucleos', 'parametros': {'nucleos': 3}},
            {'nombre': 'Verificar memoria', 'tipo': 'validacion',
             'instruccion': 'verificar_memoria', 'parametros': {'requeridas': ['memoria_ok']}},
            {'nombre': 'Cargar modelos', 'tipo': 'subprocedimiento',
             'instruccion': 'cargar_modelos', 'parametros': {'modelos': ['embebido', 'neuronal']}},
            {'nombre': 'Sistema listo', 'tipo': 'accion',
             'instruccion': 'sistema_listo', 'parametros': {'estado': 'activo'}},
        ]
        
        for paso in pasos:
            r = motor.procesar({
                'operacion': 'agregar_paso',
                'procedimiento_id': proc_id,
                **paso
            })
            rd = r.datos if r and r.exito and r.datos else {}
            if rd.get('exito'):
                print(f"  ✅ Paso {rd.get('orden', '?')}: {rd.get('nombre', '?')} [{rd.get('tipo', '?')}]")
            else:
                print(f"  ❌ Error: {rd.get('error', '?')}")

        print(f"\n[2.5] Verificación directa:")
        proc_obj = motor._procedimientos.get(proc_id)
        if proc_obj:
            n_pasos = len(proc_obj.pasos)
            print(f"  🔍 Pasos en objeto: {n_pasos}")
            if n_pasos > 0:
                for p in proc_obj.pasos.values():
                    print(f"  🔍 {p.orden}. {p.nombre} [{p.tipo.value}] → "
                          f"siguiente: {p.siguiente_id[:8] if p.siguiente_id else 'None'}")
            print(f"  🔍 paso_inicial: {proc_obj.paso_inicial[:8] if proc_obj.paso_inicial else 'None'}")
        else:
            print(f"  ❌ Objeto no encontrado")

        print("\n[3] Obteniendo procedimiento (API):")
        r = motor.procesar({'operacion': 'obtener_procedimiento', 'id': proc_id})
        rd = r.datos if r and r.exito and r.datos else {}
        if 'procedimiento' in rd:
            api_p = rd['procedimiento']
            print(f"  📋 {api_p['nombre']} | {api_p['total_pasos']} pasos | Estado: {api_p['estado']}")
            for ps in api_p.get('pasos', []):
                print(f"  📍 {ps['orden']}. [{ps['tipo']}] {ps['nombre']}")
        else:
            print(f"  ❌ Error API: {rd.get('error', '?')}")

        print("\n[4] Ejecutando procedimiento:")
        r = motor.procesar({
            'operacion': 'ejecutar',
            'procedimiento_id': proc_id,
            'variables_iniciales': {'entorno': 'produccion', 'memoria_ok': True}
        })
        rd = r.datos if r and r.exito and r.datos else {}
        if 'procedimiento' in rd:
            print(f"  ▶️ {rd['procedimiento']}: {rd['pasos_ejecutados']} pasos en {rd['tiempo_total']}s")
            print(f"  Estado: {rd['estado_final']}")
            for res in rd.get('resultados', []):
                icono = '✅' if res.get('exito') else '❌'
                print(f"  {icono} {res.get('nombre', '?')} [{res.get('tipo', '?')}] "
                      f"({res.get('tiempo', 0)}s)")
        else:
            print(f"  ❌ Error: {rd.get('error', '?')}")

        print("\n[5] Creando sistema de reglas:")
        r = motor.procesar({
            'operacion': 'sistema_reglas_crear',
            'nombre': 'Validación ANP',
            'estrategia': 'todas'
        })
        rd = r.datos if r and r.exito and r.datos else {}
        sistema_id = rd.get('sistema_id', 'default')
        print(f"  ✅ Sistema: {rd.get('nombre', '?')}")

        print("\n[6] Creando reglas:")
        for regla in [
            {'nombre': 'Memoria llena', 'tipo': 'si_entonces', 'condicion': 'memoria_llena',
             'accion_regla': 'liberar_memoria', 'prioridad': 10, 'efectos': ['memoria_liberada']},
            {'nombre': 'Error critico', 'tipo': 'cuando', 'condicion': 'error_critico',
             'accion_regla': 'reiniciar_modulo', 'prioridad': 20, 'efectos': ['modulo_reiniciado']},
            {'nombre': 'Backup', 'tipo': 'disparador', 'condicion': 'tiempo_backup',
             'accion_regla': 'ejecutar_backup', 'prioridad': 5, 'efectos': ['backup_completado']},
        ]:
            r = motor.procesar({
                'operacion': 'crear_regla',
                'sistema_id': sistema_id,
                **regla
            })
            rd = r.datos if r and r.exito and r.datos else {}
            print(f"  ✅ {rd.get('nombre', '?')} [{rd.get('tipo', '?')}]")

        print("\n[7] Activando reglas:")
        r = motor.procesar({
            'operacion': 'activar_regla',
            'sistema_id': sistema_id,
            'contexto': {'memoria_llena': True, 'error_critico': False}
        })
        rd = r.datos if r and r.exito and r.datos else {}
        print(f"  ⚡ Reglas activadas: {rd.get('reglas_activadas', 0)}")
        for res in rd.get('resultados', []):
            print(f"  📌 {res['regla']}: {res['accion']}")

        print("\n[8] Estadísticas:")
        r = motor.procesar({'operacion': 'estadisticas'})
        s = r.datos if r and r.exito and r.datos else {}
        print(f"  📊 Procs: {s.get('procedimientos_creados', 0)} | "
              f"Pasos: {s.get('pasos_totales', 0)} | "
              f"Ejecuciones: {s.get('ejecuciones_totales', 0)} (éxito: {s.get('tasa_exito_global', 0)})")
        print(f"  📊 Reglas: {s.get('reglas_creadas', 0)} creadas, "
              f"{s.get('reglas_activadas', 0)} activadas")

        print("\n[9] Historial:")
        r = motor.procesar({'operacion': 'historial', 'limite': 10})
        rd = r.datos if r and r.exito and r.datos else {}
        print(f"  📜 {rd.get('mostrados', 0)} de {rd.get('total', 0)} eventos")
        for ev in rd.get('eventos', []):
            icono = '✅' if ev.get('exito') else '❌'
            print(f"  {icono} {ev.get('nombre', '?')} [{ev.get('tipo', '?')}]")

        ruta = 'almacenamiento/procedimental/memoria_test'
        print(f"\n[10] Guardar: {'✅' if motor.procesar({'operacion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")
        
        rc = motor.procesar({'operacion':'cargar','ruta':ruta})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[11] Cargar: {'✅' if ok else '❌'} "
              f"({rc.datos.get('procedimientos','?') if ok else ''} procs)")

        if ok and proc_id in motor._procedimientos:
            pf = motor._procedimientos[proc_id]
            print(f"[12] Post-carga: {pf.nombre} | {len(pf.pasos)} pasos | "
                  f"Ejecuciones: {pf.contador_ejecuciones} | Tasa: {pf.tasa_exito}")

        print(f"\n{'='*70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print(f"\n{'='*70}\n")