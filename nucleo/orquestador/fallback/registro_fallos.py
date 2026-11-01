# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Registro de Fallos (Sistema de Auditoría de Errores)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# Este módulo implementa un sistema completo de registro, análisis
# y persistencia de fallos para diagnóstico y aprendizaje.
# =====================================================================

import sys
import os
import time
import json
import threading
import hashlib
import traceback
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import IntEnum, Enum, auto
from collections import defaultdict, deque, Counter
from datetime import datetime, timedelta

# =====================================================================
# ENUMERACIONES
# =====================================================================

class TipoFallo(Enum):
    """Tipos de fallo para clasificación."""
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
    DEPENDENCIA_FALLIDA = "dependencia_fallida"
    VALIDACION_FALLIDA = "validacion_fallida"
    PERSISTENCIA_FALLIDA = "persistencia_fallida"

class SeveridadFallo(IntEnum):
    """Niveles de severidad del fallo."""
    DEBUG = 0
    INFO = 1
    ADVERTENCIA = 2
    ERROR = 3
    CRITICO = 4
    FATAL = 5

class EstadoFallo(Enum):
    """Estado de resolución del fallo."""
    ACTIVO = "activo"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"
    MITIGADO = "mitigado"
    DESCARTADO = "descartado"
    RECURRENTE = "recurrente"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class RegistroFallo:
    """Representa un fallo registrado en el sistema."""
    id: str = field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:12])
    tipo: TipoFallo = TipoFallo.DESCONOCIDO
    severidad: SeveridadFallo = SeveridadFallo.ERROR
    mensaje: str = ""
    origen: str = ""
    nucleo_afectado: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    estado: EstadoFallo = EstadoFallo.ACTIVO
    stacktrace: Optional[str] = None
    contexto: Dict[str, Any] = field(default_factory=dict)
    intentos_recuperacion: int = 0
    acciones_tomadas: List[str] = field(default_factory=list)
    tiempo_resolucion: Optional[float] = None
    metadatos: Dict[str, Any] = field(default_factory=dict)
    
    def marcar_resuelto(self, accion: str = ""):
        """Marca el fallo como resuelto."""
        self.estado = EstadoFallo.RESUELTO
        self.tiempo_resolucion = time.time() - self.timestamp
        if accion:
            self.acciones_tomadas.append(accion)
    
    def marcar_mitigado(self, accion: str = ""):
        """Marca el fallo como mitigado (parcialmente resuelto)."""
        self.estado = EstadoFallo.MITIGADO
        if accion:
            self.acciones_tomadas.append(accion)
    
    def incrementar_intentos(self):
        """Incrementa el contador de intentos de recuperación."""
        self.intentos_recuperacion += 1
        
    def agregar_accion(self, accion: str):
        """Agrega una acción tomada."""
        self.acciones_tomadas.append(accion)
    
    def a_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        data = asdict(self)
        data['tipo'] = self.tipo.value
        data['severidad'] = self.severidad.value
        data['estado'] = self.estado.value
        data['fecha'] = datetime.fromtimestamp(self.timestamp).isoformat()
        if self.tiempo_resolucion:
            data['tiempo_resolucion'] = self.tiempo_resolucion
        return data

@dataclass
class EstadisticasFallo:
    """Estadísticas agregadas de fallos."""
    total_fallos: int = 0
    por_tipo: Counter = field(default_factory=Counter)
    por_severidad: Counter = field(default_factory=Counter)
    por_nucleo: Counter = field(default_factory=Counter)
    por_estado: Counter = field(default_factory=Counter)
    tiempo_promedio_resolucion: float = 0.0
    fallos_activos: int = 0
    fallos_recurrentes: int = 0
    ultimo_fallo: Optional[float] = None
    periodo_analisis: Tuple[float, float] = field(default_factory=lambda: (time.time() - 3600, time.time()))

# =====================================================================
# PERSISTENCIA DE FALLOS
# =====================================================================

class PersistenciaFallos:
    """Maneja la persistencia de fallos en disco."""
    
    def __init__(self, directorio: Optional[Path] = None):
        if directorio is None:
            directorio = Path("almacenamiento/fallback/fallos")
        self.directorio = directorio
        self.directorio.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
    
    def guardar(self, fallo: RegistroFallo) -> bool:
        """Guarda un fallo en disco."""
        with self._lock:
            try:
                fecha = datetime.fromtimestamp(fallo.timestamp).strftime("%Y%m%d")
                archivo = self.directorio / f"fallos_{fecha}.jsonl"
                
                with open(archivo, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(fallo.a_dict(), ensure_ascii=False) + '\n')
                
                return True
            except Exception:
                return False
    
    def cargar(self, desde: Optional[float] = None, hasta: Optional[float] = None) -> List[RegistroFallo]:
        """Carga fallos desde disco en un rango de tiempo."""
        fallos = []
        
        if desde is None:
            desde = time.time() - 86400
        if hasta is None:
            hasta = time.time()
        
        with self._lock:
            try:
                for archivo in sorted(self.directorio.glob("fallos_*.jsonl")):
                    with open(archivo, 'r', encoding='utf-8') as f:
                        for linea in f:
                            try:
                                data = json.loads(linea.strip())
                                ts = data.get('timestamp', 0)
                                if desde <= ts <= hasta:
                                    fallo = self._dict_a_fallo(data)
                                    fallos.append(fallo)
                            except:
                                pass
            except Exception:
                pass
        
        return fallos
    
    def _dict_a_fallo(self, data: Dict[str, Any]) -> RegistroFallo:
        """Convierte diccionario a RegistroFallo."""
        return RegistroFallo(
            id=data.get('id', ''),
            tipo=TipoFallo(data.get('tipo', 'desconocido')),
            severidad=SeveridadFallo(data.get('severidad', 3)),
            mensaje=data.get('mensaje', ''),
            origen=data.get('origen', ''),
            nucleo_afectado=data.get('nucleo_afectado'),
            timestamp=data.get('timestamp', time.time()),
            estado=EstadoFallo(data.get('estado', 'activo')),
            stacktrace=data.get('stacktrace'),
            contexto=data.get('contexto', {}),
            intentos_recuperacion=data.get('intentos_recuperacion', 0),
            acciones_tomadas=data.get('acciones_tomadas', []),
            tiempo_resolucion=data.get('tiempo_resolucion'),
            metadatos=data.get('metadatos', {})
        )
    
    def limpiar_antiguos(self, dias: int = 30):
        """Elimina fallos más antiguos que ciertos días."""
        limite = time.time() - (dias * 86400)
        with self._lock:
            try:
                for archivo in self.directorio.glob("fallos_*.jsonl"):
                    fecha_str = archivo.stem.replace("fallos_", "")
                    try:
                        fecha = datetime.strptime(fecha_str, "%Y%m%d")
                        if fecha.timestamp() < limite:
                            archivo.unlink()
                    except:
                        pass
            except Exception:
                pass

# =====================================================================
# ANALIZADOR DE PATRONES
# =====================================================================

class AnalizadorPatrones:
    """Analiza patrones en los fallos para detectar problemas sistémicos."""
    
    def __init__(self, ventana_tiempo: float = 3600.0):
        self.ventana_tiempo = ventana_tiempo
        self._patrones_detectados: Dict[str, int] = defaultdict(int)
        self._secuencias: deque = deque(maxlen=100)
    
    def analizar(self, fallos: List[RegistroFallo]) -> Dict[str, Any]:
        """Analiza una lista de fallos para encontrar patrones."""
        if not fallos:
            return {}
        
        ahora = time.time()
        fallos_recientes = [f for f in fallos if ahora - f.timestamp <= self.ventana_tiempo]
        
        patrones = {
            'total_recientes': len(fallos_recientes),
            'frecuencia_por_minuto': self._calcular_frecuencia(fallos_recientes),
            'tipo_mas_comun': self._tipo_mas_comun(fallos_recientes),
            'nucleo_mas_afectado': self._nucleo_mas_afectado(fallos_recientes),
            'severidad_predominante': self._severidad_predominante(fallos_recientes),
            'secuencias_detectadas': self._detectar_secuencias(fallos_recientes),
            'alerta_sobrecarga': self._detectar_sobrecarga(fallos_recientes),
        }
        
        if patrones['tipo_mas_comun']:
            self._patrones_detectados[patrones['tipo_mas_comun']] += 1
        
        return patrones
    
    def _calcular_frecuencia(self, fallos: List[RegistroFallo]) -> float:
        """Calcula frecuencia de fallos por minuto."""
        if len(fallos) < 2:
            return 0.0
        
        timestamps = sorted([f.timestamp for f in fallos])
        duracion = timestamps[-1] - timestamps[0]
        if duracion > 0:
            return len(fallos) / (duracion / 60.0)
        return 0.0
    
    def _tipo_mas_comun(self, fallos: List[RegistroFallo]) -> Optional[str]:
        """Encuentra el tipo de fallo más común."""
        if not fallos:
            return None
        contador = Counter(f.tipo.value for f in fallos)
        return contador.most_common(1)[0][0] if contador else None
    
    def _nucleo_mas_afectado(self, fallos: List[RegistroFallo]) -> Optional[str]:
        """Encuentra el núcleo más afectado."""
        nucleos = [f.nucleo_afectado for f in fallos if f.nucleo_afectado]
        if not nucleos:
            return None
        contador = Counter(nucleos)
        return contador.most_common(1)[0][0]
    
    def _severidad_predominante(self, fallos: List[RegistroFallo]) -> Optional[str]:
        """Encuentra la severidad predominante."""
        if not fallos:
            return None
        contador = Counter(f.severidad.value for f in fallos)
        return contador.most_common(1)[0][0]
    
    def _detectar_secuencias(self, fallos: List[RegistroFallo]) -> List[str]:
        """Detecta secuencias de fallos que ocurren juntos."""
        if len(fallos) < 3:
            return []
        
        secuencias = []
        tipos = [f.tipo.value for f in sorted(fallos, key=lambda x: x.timestamp)]
        
        for i in range(len(tipos) - 2):
            seq = tuple(tipos[i:i+3])
            self._secuencias.append(seq)
        
        contador = Counter(self._secuencias)
        for seq, count in contador.most_common(3):
            if count >= 2:
                secuencias.append(f"{' -> '.join(seq)} ({count} veces)")
        
        return secuencias
    
    def _detectar_sobrecarga(self, fallos: List[RegistroFallo]) -> bool:
        """Detecta si hay una situación de sobrecarga."""
        if len(fallos) < 10:
            return False
        
        frecuencia = self._calcular_frecuencia(fallos)
        tipos_criticos = sum(1 for f in fallos 
                           if f.severidad >= SeveridadFallo.CRITICO)
        
        return frecuencia > 5 or tipos_criticos > len(fallos) * 0.3

# =====================================================================
# REGISTRO DE FALLOS PRINCIPAL
# =====================================================================

class RegistroFallos:
    """
    Sistema central de registro de fallos.
    Implementa patrón Singleton thread-safe.
    """
    
    _instancia: Optional['RegistroFallos'] = None
    _lock_instancia = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock_instancia:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self, directorio: Optional[Path] = None, max_memoria: int = 1000):
        if self._inicializado:
            return
        
        with self._lock_instancia:
            if self._inicializado:
                return
            
            self.max_memoria = max_memoria
            self._fallos: deque = deque(maxlen=max_memoria)
            self._fallos_activos: Dict[str, RegistroFallo] = {}
            self._lock = threading.RLock()
            
            self.persistencia = PersistenciaFallos(directorio)
            self.analizador = AnalizadorPatrones()
            
            self._estadisticas_cache: Optional[EstadisticasFallo] = None
            self._ultimo_analisis: float = 0.0
            
            self._inicializado = True
    
    def registrar(self, tipo: Union[TipoFallo, str], mensaje: str, 
                  origen: str = "", severidad: SeveridadFallo = SeveridadFallo.ERROR,
                  nucleo_afectado: Optional[str] = None, contexto: Dict[str, Any] = None,
                  stacktrace: Optional[str] = None, persistir: bool = True) -> str:
        """
        Registra un nuevo fallo en el sistema.
        
        Returns:
            ID del fallo registrado
        """
        with self._lock:
            if isinstance(tipo, str):
                try:
                    tipo = TipoFallo(tipo)
                except ValueError:
                    tipo = TipoFallo.DESCONOCIDO
            
            # Determinar stacktrace
            stacktrace_final = stacktrace
            if stacktrace_final is None and severidad >= SeveridadFallo.ERROR:
                stacktrace_final = traceback.format_exc()
            
            fallo = RegistroFallo(
                tipo=tipo,
                severidad=severidad,
                mensaje=mensaje,
                origen=origen,
                nucleo_afectado=nucleo_afectado,
                contexto=contexto or {},
                stacktrace=stacktrace_final
            )
            
            self._fallos.append(fallo)
            self._fallos_activos[fallo.id] = fallo
            
            if persistir:
                self.persistencia.guardar(fallo)
            
            self._estadisticas_cache = None
            
            return fallo.id
    
    def registrar_excepcion(self, excepcion: Exception, origen: str = "",
                           nucleo_afectado: Optional[str] = None,
                           contexto: Dict[str, Any] = None) -> str:
        """Registra una excepción de Python como fallo."""
        return self.registrar(
            tipo=TipoFallo.ERROR_INTERNO,
            mensaje=str(excepcion),
            origen=origen,
            severidad=SeveridadFallo.ERROR,
            nucleo_afectado=nucleo_afectado,
            contexto=contexto,
            stacktrace=traceback.format_exc()
        )
    
    def marcar_resuelto(self, fallo_id: str, accion: str = "") -> bool:
        """Marca un fallo como resuelto."""
        with self._lock:
            if fallo_id in self._fallos_activos:
                self._fallos_activos[fallo_id].marcar_resuelto(accion)
                del self._fallos_activos[fallo_id]
                self._estadisticas_cache = None
                return True
            return False
    
    def marcar_mitigado(self, fallo_id: str, accion: str = "") -> bool:
        """Marca un fallo como mitigado."""
        with self._lock:
            if fallo_id in self._fallos_activos:
                self._fallos_activos[fallo_id].marcar_mitigado(accion)
                self._estadisticas_cache = None
                return True
            return False
    
    def obtener_fallo(self, fallo_id: str) -> Optional[RegistroFallo]:
        """Obtiene un fallo por su ID."""
        with self._lock:
            return self._fallos_activos.get(fallo_id)
    
    def obtener_fallos_activos(self) -> List[RegistroFallo]:
        """Obtiene todos los fallos activos."""
        with self._lock:
            return list(self._fallos_activos.values())
    
    def obtener_fallos_recientes(self, limite: int = 50) -> List[RegistroFallo]:
        """Obtiene los fallos más recientes."""
        with self._lock:
            fallos = list(self._fallos)
            fallos.sort(key=lambda x: x.timestamp, reverse=True)
            return fallos[:limite]
    
    def obtener_fallos_por_nucleo(self, nucleo: str, limite: int = 50) -> List[RegistroFallo]:
        """Obtiene fallos asociados a un núcleo específico."""
        with self._lock:
            return [f for f in self._fallos if f.nucleo_afectado == nucleo][:limite]
    
    def obtener_fallos_por_tipo(self, tipo: TipoFallo, limite: int = 50) -> List[RegistroFallo]:
        """Obtiene fallos de un tipo específico."""
        with self._lock:
            return [f for f in self._fallos if f.tipo == tipo][:limite]
    
    def obtener_estadisticas(self, forzar_recalculo: bool = False) -> EstadisticasFallo:
        """Obtiene estadísticas agregadas de fallos."""
        ahora = time.time()
        
        if not forzar_recalculo and self._estadisticas_cache and ahora - self._ultimo_analisis < 60:
            return self._estadisticas_cache
        
        with self._lock:
            stats = EstadisticasFallo()
            fallos = list(self._fallos)
            
            if not fallos:
                self._estadisticas_cache = stats
                return stats
            
            stats.total_fallos = len(fallos)
            stats.ultimo_fallo = max(f.timestamp for f in fallos)
            stats.fallos_activos = len(self._fallos_activos)
            
            for f in fallos:
                stats.por_tipo[f.tipo.value] += 1
                stats.por_severidad[f.severidad.value] += 1
                stats.por_estado[f.estado.value] += 1
                if f.nucleo_afectado:
                    stats.por_nucleo[f.nucleo_afectado] += 1
                if f.estado == EstadoFallo.RECURRENTE:
                    stats.fallos_recurrentes += 1
            
            tiempos = [f.tiempo_resolucion for f in fallos if f.tiempo_resolucion]
            if tiempos:
                stats.tiempo_promedio_resolucion = sum(tiempos) / len(tiempos)
            
            self._estadisticas_cache = stats
            self._ultimo_analisis = ahora
            
            return stats
    
    def analizar_patrones(self) -> Dict[str, Any]:
        """Analiza patrones en los fallos registrados."""
        with self._lock:
            fallos = list(self._fallos)
            return self.analizador.analizar(fallos)
    
    def detectar_anomalias(self) -> List[str]:
        """Detecta anomalías en los patrones de fallos."""
        alertas = []
        stats = self.obtener_estadisticas()
        patrones = self.analizar_patrones()
        
        if patrones.get('alerta_sobrecarga'):
            alertas.append("⚠️ SOBRECARGA DETECTADA: Alta frecuencia de fallos")
        
        nucleo_mas = patrones.get('nucleo_mas_afectado')
        if nucleo_mas and stats.total_fallos > 0:
            pct = (stats.por_nucleo[nucleo_mas] / stats.total_fallos) * 100
            if pct > 40:
                alertas.append(f"⚠️ NÚCLEO PROBLEMÁTICO: {nucleo_mas} genera el {pct:.1f}% de fallos")
        
        tipo_mas = patrones.get('tipo_mas_comun')
        if tipo_mas and stats.total_fallos > 0:
            pct = (stats.por_tipo[tipo_mas] / stats.total_fallos) * 100
            if pct > 30:
                alertas.append(f"⚠️ FALLO RECURRENTE: '{tipo_mas}' representa el {pct:.1f}% de fallos")
        
        criticos_activos = len([f for f in self._fallos_activos.values() 
                               if f.severidad >= SeveridadFallo.CRITICO])
        if criticos_activos > 0:
            alertas.append(f"🚨 FALLOS CRÍTICOS ACTIVOS: {criticos_activos}")
        
        return alertas
    
    def limpiar_resueltos(self, dias: int = 7):
        """Limpia fallos resueltos más antiguos que ciertos días."""
        self.persistencia.limpiar_antiguos(dias)
    
    def exportar(self, formato: str = "json") -> str:
        """Exporta todos los fallos a formato JSON."""
        with self._lock:
            fallos_dict = [f.a_dict() for f in self._fallos]
            return json.dumps(fallos_dict, indent=2, ensure_ascii=False)
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen ejecutivo del estado de fallos."""
        stats = self.obtener_estadisticas()
        patrones = self.analizar_patrones()
        alertas = self.detectar_anomalias()
        
        return {
            'total_fallos': stats.total_fallos,
            'fallos_activos': stats.fallos_activos,
            'ultimo_fallo_hace': f"{(time.time() - (stats.ultimo_fallo or time.time())):.0f}s",
            'tipo_mas_comun': patrones.get('tipo_mas_comun'),
            'nucleo_mas_afectado': patrones.get('nucleo_mas_afectado'),
            'alertas': alertas,
        }
    
    def __len__(self) -> int:
        return len(self._fallos)
    
    def __repr__(self) -> str:
        return f"RegistroFallos(total={len(self._fallos)}, activos={len(self._fallos_activos)})"

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_registro_global: Optional[RegistroFallos] = None

def obtener_registro_fallos() -> RegistroFallos:
    """Obtiene la instancia global del registro de fallos."""
    global _registro_global
    if _registro_global is None:
        _registro_global = RegistroFallos()
    return _registro_global

def registrar_fallo(tipo: Union[TipoFallo, str], mensaje: str, **kwargs) -> str:
    """Función rápida para registrar un fallo."""
    return obtener_registro_fallos().registrar(tipo, mensaje, **kwargs)

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL REGISTRO DE FALLOS")
    print("=" * 70)
    
    registro = None
    
    try:
        print("\n[1/5] Inicializando registro de fallos...")
        registro = RegistroFallos()
        print(f"  ✅ Registro inicializado: {registro}")
        
        print("\n[2/5] Registrando fallos de prueba...")
        
        ids = []
        ids.append(registro.registrar(
            TipoFallo.TIMEOUT, 
            "Timeout en núcleo de razonamiento",
            origen="test",
            nucleo_afectado="razonamiento"
        ))
        print(f"  📍 Timeout registrado: {ids[-1]}")
        
        ids.append(registro.registrar(
            TipoFallo.MEMORIA_INSUFICIENTE,
            "Memoria de trabajo agotada",
            origen="test",
            severidad=SeveridadFallo.CRITICO,
            nucleo_afectado="memoria"
        ))
        print(f"  📍 Memoria insuficiente: {ids[-1]}")
        
        ids.append(registro.registrar(
            TipoFallo.NUCLEO_CAIDO,
            "Núcleo de búsqueda no responde",
            origen="test",
            nucleo_afectado="busqueda"
        ))
        print(f"  📍 Núcleo caído: {ids[-1]}")
        
        print("\n[3/5] Marcando fallos como resueltos...")
        registro.marcar_resuelto(ids[0], "Reintento exitoso")
        print(f"  ✅ Fallo {ids[0]} marcado como resuelto")
        
        print("\n[4/5] Estadísticas del registro:")
        stats = registro.obtener_estadisticas()
        print(f"  📊 Total fallos: {stats.total_fallos}")
        print(f"  📊 Fallos activos: {stats.fallos_activos}")
        print(f"  📊 Por tipo: {dict(stats.por_tipo)}")
        print(f"  📊 Por núcleo: {dict(stats.por_nucleo)}")
        
        print("\n[5/5] Análisis de patrones:")
        patrones = registro.analizar_patrones()
        print(f"  📈 Frecuencia: {patrones.get('frecuencia_por_minuto', 0):.2f} fallos/min")
        print(f"  📈 Tipo más común: {patrones.get('tipo_mas_comun')}")
        print(f"  📈 Núcleo más afectado: {patrones.get('nucleo_mas_afectado')}")
        
        alertas = registro.detectar_anomalias()
        if alertas:
            print(f"  🚨 Alertas detectadas:")
            for alerta in alertas:
                print(f"     {alerta}")
        else:
            print(f"  ✅ Sin alertas detectadas")
        
        print("\n📋 Resumen:")
        resumen = registro.obtener_resumen()
        for k, v in resumen.items():
            print(f"  {k}: {v}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")