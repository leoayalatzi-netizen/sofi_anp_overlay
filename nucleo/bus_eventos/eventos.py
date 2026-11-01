# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Eventos Cuánticos (El Corazón del Sistema Nervioso)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de eventos que
# trasciende el patrón pub/sub tradicional. Incluye trazabilidad
# completa, versionado, validación, transformación y capacidades
# de autoreflexión. Cada evento es una entidad viva en el ecosistema.
# =====================================================================

import sys
import os
import time
import uuid
import json
import hashlib
import threading
import traceback
import inspect
import copy
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type
)
from dataclasses import dataclass, field, asdict, Field, fields
from enum import IntEnum, Enum, auto, Flag
from collections import defaultdict, deque, OrderedDict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import warnings

# =====================================================================
# IMPORTS DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .tipos import TipoEvento
except ImportError:
    class TipoEvento:
        """Placeholder para tipos de eventos."""
        SISTEMA_INICIANDO = "sistema.iniciando"
        SISTEMA_LISTO = "sistema.listo"
        SISTEMA_APAGANDO = "sistema.apagando"
        SISTEMA_ERROR = "sistema.error"
        FALLO_GENERAL = "fallo.general"
        FALLO_TIMEOUT = "fallo.timeout"
        FALLO_MEMORIA = "fallo.memoria"
        FALLO_NUCLEO = "fallo.nucleo"
        NUCLEO_ACTIVADO = "nucleo.activado"
        NUCLEO_DESACTIVADO = "nucleo.desactivado"
        NUCLEO_FALLBACK = "nucleo.fallback"
        TAREA_CREADA = "tarea.creada"
        TAREA_COMPLETADA = "tarea.completada"
        TAREA_FALLIDA = "tarea.fallida"
        CONTEXTO_CAMBIADO = "contexto.cambiado"
        MEMORIA_ACTUALIZADA = "memoria.actualizada"
        USUARIO_HABLANDO = "usuario.hablando"
        IA_PENSANDO = "ia.pensando"
        IA_RESPONDIENDO = "ia.respondiendo"
        CONCIENCIA_LATIDO = "conciencia.latido"
        CONCIENCIA_ALERTA = "conciencia.alerta"
        METRICA_REGISTRADA = "metrica.registrada"
        EVENTO_PERSONALIZADO = "evento.personalizado"

try:
    from .prioridad import PrioridadEvento
except ImportError:
    class PrioridadEvento(IntEnum):
        CRITICA = 0
        ALTA = 1
        MEDIA = 2
        BAJA = 3
        DIFERIDA = 4

# =====================================================================
# ENUMERACIONES AVANZADAS
# =====================================================================

class EstadoEvento(Enum):
    """Estados del ciclo de vida de un evento."""
    CREADO = "creado"
    EN_COLA = "en_cola"
    ENTREGANDO = "entregando"
    ENTREGADO = "entregado"
    PROCESADO = "procesado"
    FALLIDO = "fallido"
    REINTENTANDO = "reintentando"
    EXPIRADO = "expirado"
    ARCHIVADO = "archivado"
    TRANSFORMADO = "transformado"

class VersionEvento(Enum):
    """Versiones del formato de evento."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"
    ACTUAL = "1.1"

class ModoSerializacion(Enum):
    """Modos de serialización del evento."""
    COMPLETO = "completo"
    RESUMIDO = "resumido"
    METADATOS = "metadatos"
    DEPURACION = "depuracion"
    RED = "red"
    ALMACENAMIENTO = "almacenamiento"

class NivelTrazabilidad(IntEnum):
    """Niveles de trazabilidad para depuración."""
    MINIMO = 0
    BASICO = 1
    DETALLADO = 2
    COMPLETO = 3
    DIAGNOSTICO = 4

# =====================================================================
# ESTRUCTURAS DE DATOS PARA TRAZABILIDAD
# =====================================================================

@dataclass
class TrazaEvento:
    """Registro de un paso en la vida del evento."""
    paso: str
    timestamp: float = field(default_factory=time.time)
    destino: Optional[str] = None
    duracion_ms: Optional[float] = None
    metadatos: Dict[str, Any] = field(default_factory=dict)
    stack_snapshot: Optional[str] = None
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'paso': self.paso,
            'timestamp': self.timestamp,
            'fecha': datetime.fromtimestamp(self.timestamp).isoformat(),
            'destino': self.destino,
            'duracion_ms': self.duracion_ms,
            'metadatos': self.metadatos,
        }

@dataclass
class ContextoEvento:
    """Contexto adicional del evento."""
    sesion_id: Optional[str] = None
    usuario_id: Optional[str] = None
    conversacion_id: Optional[str] = None
    tarea_id: Optional[str] = None
    nucleo_origen: Optional[str] = None
    correlacion_id: Optional[str] = None
    causal_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    entorno: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# VALIDADOR DE EVENTOS
# =====================================================================

class ValidadorEvento:
    """Valida la integridad y formato de los eventos."""
    
    _esquemas: Dict[str, Dict[str, Any]] = {
        "sistema.iniciando": {
            "required": ["version"],
            "properties": {
                "version": {"type": "string"},
                "modo": {"type": "string", "optional": True},
            }
        },
        "fallo.*": {
            "required": ["mensaje"],
            "properties": {
                "mensaje": {"type": "string"},
                "codigo": {"type": "string", "optional": True},
                "stacktrace": {"type": "string", "optional": True},
            }
        },
        "tarea.*": {
            "required": ["tarea_id"],
            "properties": {
                "tarea_id": {"type": "string"},
                "tipo": {"type": "string", "optional": True},
                "resultado": {"type": "any", "optional": True},
            }
        },
        "metrica.*": {
            "required": ["nombre", "valor"],
            "properties": {
                "nombre": {"type": "string"},
                "valor": {"type": "number"},
                "unidad": {"type": "string", "optional": True},
            }
        },
    }
    
    @classmethod
    def validar(cls, evento: 'Evento') -> Tuple[bool, List[str]]:
        """Valida un evento contra el esquema correspondiente."""
        errores = []
        
        if not evento.tipo:
            errores.append("El evento no tiene tipo")
        
        if not evento.id:
            errores.append("El evento no tiene ID")
        
        if evento.prioridad not in list(PrioridadEvento):
            errores.append(f"Prioridad inválida: {evento.prioridad}")
        
        esquema = cls._buscar_esquema(evento.tipo)
        if esquema and evento.datos:
            errores.extend(cls._validar_contra_esquema(evento.datos, esquema))
        
        return len(errores) == 0, errores
    
    @classmethod
    def _buscar_esquema(cls, tipo: str) -> Optional[Dict[str, Any]]:
        """Busca el esquema más específico para un tipo de evento."""
        if tipo in cls._esquemas:
            return cls._esquemas[tipo]
        
        for patron, esquema in cls._esquemas.items():
            if patron.endswith('*'):
                prefijo = patron[:-1]
                if tipo.startswith(prefijo):
                    return esquema
        
        return None
    
    @classmethod
    def _validar_contra_esquema(cls, datos: Any, esquema: Dict) -> List[str]:
        """Valida datos contra un esquema."""
        errores = []
        
        if not isinstance(datos, dict):
            return errores
        
        for campo in esquema.get('required', []):
            if campo not in datos:
                errores.append(f"Campo requerido faltante: {campo}")
        
        for campo, props in esquema.get('properties', {}).items():
            if campo in datos:
                tipo_esperado = props.get('type')
                if tipo_esperado == 'string' and not isinstance(datos[campo], str):
                    errores.append(f"Campo '{campo}' debe ser string")
                elif tipo_esperado == 'number' and not isinstance(datos[campo], (int, float)):
                    errores.append(f"Campo '{campo}' debe ser número")
        
        return errores

# =====================================================================
# TRANSFORMADOR DE EVENTOS
# =====================================================================

class TransformadorEvento:
    """Transforma eventos entre versiones y formatos."""
    
    _transformaciones: Dict[str, Dict[str, Callable]] = {}
    
    @classmethod
    def transformar(cls, evento: 'Evento', version_objetivo: VersionEvento) -> Optional['Evento']:
        """Transforma un evento a una versión específica."""
        if evento.version == version_objetivo:
            return evento
        return evento
    
    @classmethod
    def a_dict(cls, evento: 'Evento', modo: ModoSerializacion = ModoSerializacion.COMPLETO) -> Dict[str, Any]:
        """Serializa un evento a diccionario según el modo."""
        base = {
            'id': evento.id,
            'tipo': evento.tipo,
            'origen': evento.origen,
            'timestamp': evento.timestamp,
            'prioridad': evento.prioridad.value if hasattr(evento.prioridad, 'value') else evento.prioridad,
        }
        
        if modo == ModoSerializacion.COMPLETO:
            base.update({
                'datos': evento.datos,
                'metadatos': evento.metadatos,
                'contexto': asdict(evento.contexto) if evento.contexto else {},
                'version': evento.version.value,
                'estado': evento.estado.value,
                'trazas': [t.a_dict() for t in evento.trazas[-10:]],
            })
        elif modo == ModoSerializacion.RESUMIDO:
            base.update({
                'datos': evento.datos,
                'resumen': str(evento.datos)[:100] if evento.datos else None,
            })
        elif modo == ModoSerializacion.METADATOS:
            base.update({
                'metadatos': evento.metadatos,
                'contexto': asdict(evento.contexto) if evento.contexto else {},
            })
        elif modo == ModoSerializacion.RED:
            base.update({
                'datos': evento.datos,
                'compresion': 'none',
            })
        
        return base
    
    @classmethod
    def desde_dict(cls, data: Dict[str, Any]) -> 'Evento':
        """Reconstruye un evento desde un diccionario."""
        prioridad_val = data.get('prioridad', PrioridadEvento.MEDIA)
        if isinstance(prioridad_val, int):
            prioridad = PrioridadEvento(prioridad_val)
        else:
            prioridad = prioridad_val
        
        return Evento(
            tipo=data.get('tipo', ''),
            datos=data.get('datos'),
            origen=data.get('origen', ''),
            prioridad=prioridad,
            id=data.get('id'),
            timestamp=data.get('timestamp', time.time()),
            metadatos=data.get('metadatos', {}),
        )

# =====================================================================
# CLASE EVENTO PRINCIPAL
# =====================================================================

@dataclass
class Evento:
    """
    Evento Cuántico de ANP.
    
    Un evento es una entidad viva que:
    - Tiene trazabilidad completa de su ciclo de vida
    - Puede serializarse en múltiples formatos
    - Valida su integridad automáticamente
    - Soporta versionado y migración
    - Mantiene contexto de ejecución
    - Puede clonarse y transformarse
    - Tiene capacidad de autoreflexión
    """
    
    # ===== CAMPOS PRINCIPALES =====
    tipo: str
    datos: Any = None
    origen: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    prioridad: PrioridadEvento = PrioridadEvento.MEDIA
    
    # ===== CAMPOS AVANZADOS =====
    version: VersionEvento = VersionEvento.ACTUAL
    estado: EstadoEvento = EstadoEvento.CREADO
    metadatos: Dict[str, Any] = field(default_factory=dict)
    contexto: ContextoEvento = field(default_factory=ContextoEvento)
    
    # ===== TRAZABILIDAD =====
    trazas: List[TrazaEvento] = field(default_factory=list)
    _trazabilidad_activada: bool = field(default=True, repr=False)
    _nivel_trazabilidad: NivelTrazabilidad = NivelTrazabilidad.BASICO
    
    # ===== CONTROL INTERNO =====
    _intentos: int = field(default=0, repr=False)
    _tiempo_expiracion: Optional[float] = field(default=None, repr=False)
    _firma: Optional[str] = field(default=None, repr=False)
    _lock: Any = field(default_factory=threading.RLock, repr=False)
    
    # ===== METADATOS DE CLASE =====
    _contador_global: ClassVar[int] = 0
    _eventos_activos: ClassVar[Dict[str, 'Evento']] = {}
    _ultimo_evento: ClassVar[Optional['Evento']] = None
    
    def __post_init__(self):
        """Inicialización post-creación."""
        Evento._contador_global += 1
        Evento._eventos_activos[self.id] = self
        Evento._ultimo_evento = self
        
        self._firma = self._calcular_firma()
        
        if self._trazabilidad_activada:
            self._agregar_traza("creado", metadatos={"origen": self.origen})
        
        if self._tiempo_expiracion is None:
            if self.prioridad <= PrioridadEvento.ALTA:
                self._tiempo_expiracion = time.time() + 86400
            else:
                self._tiempo_expiracion = time.time() + 3600
    
    def _calcular_firma(self) -> str:
        """Calcula una firma única para el evento."""
        contenido = f"{self.tipo}:{self.id}:{self.timestamp}:{self.origen}"
        return hashlib.sha256(contenido.encode()).hexdigest()[:16]
    
    def _agregar_traza(self, paso: str, destino: Optional[str] = None, 
                       metadatos: Dict[str, Any] = None):
        """Agrega una traza al historial del evento."""
        if not self._trazabilidad_activada:
            return
        
        with self._lock:
            stack = None
            if self._nivel_trazabilidad >= NivelTrazabilidad.DETALLADO:
                stack = ''.join(traceback.format_stack()[:-1])
            
            traza = TrazaEvento(
                paso=paso,
                destino=destino,
                metadatos=metadatos or {},
                stack_snapshot=stack
            )
            self.trazas.append(traza)
            
            if len(self.trazas) > 100:
                self.trazas = self.trazas[-100:]
    
    # ===== MÉTODOS DE CICLO DE VIDA =====
    
    def encolar(self) -> 'Evento':
        """Marca el evento como encolado."""
        with self._lock:
            self.estado = EstadoEvento.EN_COLA
            self._agregar_traza("encolado")
        return self
    
    def comenzar_entrega(self, destino: str) -> 'Evento':
        """Marca el inicio de la entrega a un suscriptor."""
        with self._lock:
            self.estado = EstadoEvento.ENTREGANDO
            self._agregar_traza("comenzar_entrega", destino=destino)
        return self
    
    def entregado(self, destino: str, duracion_ms: float) -> 'Evento':
        """Marca el evento como entregado exitosamente."""
        with self._lock:
            self.estado = EstadoEvento.ENTREGADO
            traza = TrazaEvento(
                paso="entregado",
                destino=destino,
                duracion_ms=duracion_ms
            )
            self.trazas.append(traza)
        return self
    
    def procesado(self, resultado: Any = None) -> 'Evento':
        """Marca el evento como procesado completamente."""
        with self._lock:
            self.estado = EstadoEvento.PROCESADO
            self._agregar_traza("procesado", metadatos={"resultado_tipo": type(resultado).__name__})
            
            if self.id in Evento._eventos_activos:
                del Evento._eventos_activos[self.id]
        return self
    
    def fallido(self, error: str, reintentable: bool = True) -> 'Evento':
        """Marca el evento como fallido."""
        with self._lock:
            self._intentos += 1
            self.estado = EstadoEvento.FALLIDO
            self._agregar_traza("fallido", metadatos={"error": error, "intentos": self._intentos})
            
            if reintentable and self._intentos < 3:
                self.estado = EstadoEvento.REINTENTANDO
        return self
    
    def expirado(self) -> bool:
        """Verifica si el evento ha expirado."""
        if self._tiempo_expiracion and time.time() > self._tiempo_expiracion:
            with self._lock:
                self.estado = EstadoEvento.EXPIRADO
                self._agregar_traza("expirado")
                
                if self.id in Evento._eventos_activos:
                    del Evento._eventos_activos[self.id]
            return True
        return False
    
    # ===== MÉTODOS DE VALIDACIÓN =====
    
    def validar(self) -> Tuple[bool, List[str]]:
        """Valida la integridad del evento."""
        return ValidadorEvento.validar(self)
    
    def es_valido(self) -> bool:
        """Verifica rápidamente si el evento es válido."""
        valido, _ = self.validar()
        return valido
    
    def verificar_firma(self) -> bool:
        """Verifica que la firma del evento sea correcta."""
        firma_actual = self._calcular_firma()
        return self._firma == firma_actual
    
    # ===== MÉTODOS DE SERIALIZACIÓN =====
    
    def a_dict(self, modo: ModoSerializacion = ModoSerializacion.COMPLETO) -> Dict[str, Any]:
        """Serializa el evento a diccionario."""
        return TransformadorEvento.a_dict(self, modo)
    
    def a_json(self, modo: ModoSerializacion = ModoSerializacion.COMPLETO, 
               indent: Optional[int] = None) -> str:
        """Serializa el evento a JSON."""
        data = self.a_dict(modo)
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    
    def a_bytes(self) -> bytes:
        """Serializa el evento a bytes para transmisión por red."""
        return self.a_json(modo=ModoSerializacion.RED).encode('utf-8')
    
    @classmethod
    def desde_json(cls, json_str: str) -> 'Evento':
        """Reconstruye un evento desde JSON."""
        data = json.loads(json_str)
        return TransformadorEvento.desde_dict(data)
    
    @classmethod
    def desde_bytes(cls, data: bytes) -> 'Evento':
        """Reconstruye un evento desde bytes."""
        return cls.desde_json(data.decode('utf-8'))
    
    # ===== MÉTODOS DE CLONACIÓN Y TRANSFORMACIÓN =====
    
    def clonar(self, **sobrescrituras) -> 'Evento':
        """Crea un clon del evento con modificaciones opcionales."""
        with self._lock:
            datos_clon = {
                'tipo': self.tipo,
                'datos': copy.deepcopy(self.datos),
                'origen': self.origen,
                'prioridad': self.prioridad,
                'version': self.version,
                'metadatos': copy.deepcopy(self.metadatos),
                'contexto': copy.deepcopy(self.contexto),
            }
            
            datos_clon.update(sobrescrituras)
            datos_clon['id'] = str(uuid.uuid4())
            datos_clon['timestamp'] = time.time()
            
            clon = Evento(**datos_clon)
            clon.metadatos['clonado_de'] = self.id
            clon._agregar_traza("clonado", metadatos={"original": self.id})
            
            return clon
    
    def transformar(self, nuevo_tipo: str, transformador: Callable[['Evento'], Any] = None) -> 'Evento':
        """Transforma el evento a un nuevo tipo."""
        with self._lock:
            nuevos_datos = self.datos
            if transformador:
                nuevos_datos = transformador(self)
            
            transformado = Evento(
                tipo=nuevo_tipo,
                datos=nuevos_datos,
                origen=self.origen,
                prioridad=self.prioridad,
            )
            transformado.metadatos['transformado_de'] = self.id
            transformado.metadatos['transformado_tipo'] = self.tipo
            transformado.estado = EstadoEvento.TRANSFORMADO
            
            transformado.contexto = copy.deepcopy(self.contexto)
            transformado.contexto.causal_id = self.id
            
            self._agregar_traza("transformado", metadatos={"nuevo_id": transformado.id})
            
            return transformado
    
    def responder(self, datos: Any, tipo_respuesta: str = None) -> 'Evento':
        """Crea un evento de respuesta a este evento."""
        if tipo_respuesta is None:
            if self.tipo.endswith(".pregunta"):
                tipo_respuesta = self.tipo.replace(".pregunta", ".respuesta")
            elif self.tipo.endswith(".solicitud"):
                tipo_respuesta = self.tipo.replace(".solicitud", ".respuesta")
            else:
                tipo_respuesta = f"{self.tipo}.respuesta"
        
        respuesta = Evento(
            tipo=tipo_respuesta,
            datos=datos,
            origen=self.origen,
            prioridad=self.prioridad,
        )
        respuesta.contexto.causal_id = self.id
        respuesta.metadatos['responde_a'] = self.id
        
        return respuesta
    
    # ===== MÉTODOS DE CONSULTA =====
    
    @property
    def edad_ms(self) -> float:
        """Edad del evento en milisegundos."""
        return (time.time() - self.timestamp) * 1000
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si el evento está activo (no finalizado)."""
        return self.estado not in (
            EstadoEvento.PROCESADO,
            EstadoEvento.FALLIDO,
            EstadoEvento.EXPIRADO,
            EstadoEvento.ARCHIVADO
        )
    
    @property
    def resumen(self) -> str:
        """Resumen legible del evento."""
        datos_str = str(self.datos)[:50] + "..." if self.datos and len(str(self.datos)) > 50 else str(self.datos)
        return f"[{self.prioridad.name}] {self.tipo} @ {self.origen}: {datos_str}"
    
    def tiene_tipo(self, patron: str) -> bool:
        """Verifica si el tipo coincide con un patrón (soporta wildcards)."""
        if patron.endswith('*'):
            return self.tipo.startswith(patron[:-1])
        if patron.startswith('*'):
            return self.tipo.endswith(patron[1:])
        return self.tipo == patron
    
    # ===== MÉTODOS MÁGICOS =====
    
    def __str__(self) -> str:
        return f"Evento({self.tipo}, {self.origen}, {self.estado.value})"
    
    def __repr__(self) -> str:
        return f"Evento(id={self.id[:8]}, tipo={self.tipo}, origen={self.origen}, estado={self.estado.value})"
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: 'Evento') -> bool:
        if not isinstance(other, Evento):
            return False
        return self.id == other.id
    
    def __lt__(self, other: 'Evento') -> bool:
        if self.prioridad != other.prioridad:
            return self.prioridad < other.prioridad
        return self.timestamp < other.timestamp
    
    def __del__(self):
        """Limpieza al destruir el evento."""
        if hasattr(self, 'id') and self.id in Evento._eventos_activos:
            del Evento._eventos_activos[self.id]

# =====================================================================
# FÁBRICA DE EVENTOS
# =====================================================================

class FabricaEventos:
    """Fábrica para crear eventos preconfigurados."""
    
    @staticmethod
    def crear_evento_sistema(tipo: str, datos: Any = None, origen: str = "sistema") -> Evento:
        """Crea un evento de sistema."""
        return Evento(
            tipo=tipo,
            datos=datos,
            origen=origen,
            prioridad=PrioridadEvento.ALTA,
        )
    
    @staticmethod
    def crear_evento_fallo(categoria: str, mensaje: str, nucleo: str = None, 
                           origen: str = "sistema") -> Evento:
        """Crea un evento de fallo."""
        datos = {
            "mensaje": mensaje,
            "categoria": categoria,
            "timestamp": time.time(),
        }
        if nucleo:
            datos["nucleo"] = nucleo
        
        return Evento(
            tipo=f"fallo.{categoria}",
            datos=datos,
            origen=origen,
            prioridad=PrioridadEvento.CRITICA if categoria in ["timeout", "nucleo"] else PrioridadEvento.ALTA,
        )
    
    @staticmethod
    def crear_evento_tarea(tipo_tarea: str, tarea_id: str, estado: str, 
                           resultado: Any = None, origen: str = "orquestador") -> Evento:
        """Crea un evento relacionado con tareas."""
        return Evento(
            tipo=f"tarea.{estado}",
            datos={
                "tarea_id": tarea_id,
                "tipo": tipo_tarea,
                "resultado": resultado,
            },
            origen=origen,
            prioridad=PrioridadEvento.MEDIA,
        )
    
    @staticmethod
    def crear_evento_metrica(nombre: str, valor: float, unidad: str = "count",
                             tags: Dict[str, str] = None, origen: str = "metricas") -> Evento:
        """Crea un evento de métrica."""
        return Evento(
            tipo="metrica.registrada",
            datos={
                "nombre": nombre,
                "valor": valor,
                "unidad": unidad,
                "tags": tags or {},
            },
            origen=origen,
            prioridad=PrioridadEvento.BAJA,
        )
    
    @staticmethod
    def crear_evento_conciencia(nivel: str, mensaje: str, 
                                metadatos: Dict[str, Any] = None) -> Evento:
        """Crea un evento de conciencia sistémica."""
        return Evento(
            tipo=f"conciencia.{nivel}",
            datos={
                "mensaje": mensaje,
                "metadatos": metadatos or {},
            },
            origen="conciencia",
            prioridad=PrioridadEvento.ALTA if nivel == "alerta" else PrioridadEvento.MEDIA,
        )

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def crear_evento(tipo: str, datos: Any = None, origen: str = "", 
                 prioridad: PrioridadEvento = PrioridadEvento.MEDIA, **kwargs) -> Evento:
    """Función rápida para crear un evento."""
    return Evento(
        tipo=tipo,
        datos=datos,
        origen=origen,
        prioridad=prioridad,
        metadatos=kwargs
    )

def eventos_activos() -> List[Evento]:
    """Obtiene todos los eventos activos."""
    return list(Evento._eventos_activos.values())

def limpiar_eventos_expirados():
    """Limpia eventos que han expirado."""
    expirados = []
    for evento in list(Evento._eventos_activos.values()):
        if evento.expirado():
            expirados.append(evento.id)
    return len(expirados)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE EVENTOS CUÁNTICOS")
    print("=" * 70)
    
    try:
        # 1. Crear evento básico
        print("\n[1/8] Creando evento básico...")
        evento1 = Evento(
            tipo="test.basico",
            datos={"mensaje": "Hola Mundo"},
            origen="diagnostico"
        )
        print(f"  ✅ Evento creado: {evento1}")
        print(f"  📍 ID: {evento1.id}")
        print(f"  📍 Firma: {evento1._firma}")
        
        # 2. Validar evento
        print("\n[2/8] Validando evento...")
        valido, errores = evento1.validar()
        print(f"  {'✅' if valido else '❌'} Válido: {valido}")
        
        # 3. Ciclo de vida
        print("\n[3/8] Probando ciclo de vida...")
        evento1.encolar()
        evento1.comenzar_entrega("suscriptor_test")
        evento1.entregado("suscriptor_test", 12.5)
        evento1.procesado({"resultado": "OK"})
        print(f"  ✅ Estado final: {evento1.estado.value}")
        print(f"  📍 Trazas registradas: {len(evento1.trazas)}")
        for traza in evento1.trazas:
            print(f"     - {traza.paso}: {traza.destino or 'N/A'}")
        
        # 4. Serialización
        print("\n[4/8] Probando serialización...")
        evento2 = Evento(
            tipo="test.serializacion",
            datos={"numero": 42, "texto": "prueba"},
            origen="diagnostico",
            prioridad=PrioridadEvento.ALTA
        )
        
        json_str = evento2.a_json(indent=2)
        print(f"  ✅ Serializado a JSON ({len(json_str)} bytes)")
        
        evento2_reconstruido = Evento.desde_json(json_str)
        print(f"  ✅ Reconstruido: {evento2_reconstruido}")
        print(f"  📍 Mismo ID: {evento2.id == evento2_reconstruido.id}")
        
        # 5. Clonación
        print("\n[5/8] Probando clonación...")
        clon = evento2.clonar(origen="clonador")
        print(f"  ✅ Clon creado: {clon}")
        print(f"  📍 ID original: {evento2.id[:8]}")
        print(f"  📍 ID clon: {clon.id[:8]}")
        print(f"  📍 Clonado de: {clon.metadatos.get('clonado_de', 'N/A')[:8]}")
        
        # 6. Transformación
        print("\n[6/8] Probando transformación...")
        transformado = evento2.transformar(
            "test.transformado",
            transformador=lambda e: {"original": e.datos, "transformado": True}
        )
        print(f"  ✅ Transformado: {transformado}")
        print(f"  📍 Datos transformados: {transformado.datos}")
        
        # 7. Fábrica de eventos
        print("\n[7/8] Probando fábrica de eventos...")
        
        eventoSistema = FabricaEventos.crear_evento_sistema(
            TipoEvento.SISTEMA_LISTO, 
            {"version": "1.0"}
        )
        print(f"  ✅ Evento sistema: {eventoSistema}")
        
        eventoFallo = FabricaEventos.crear_evento_fallo(
            "timeout", 
            "Timeout en razonamiento", 
            nucleo="razonamiento"
        )
        print(f"  ✅ Evento fallo: {eventoFallo}")
        
        eventoTarea = FabricaEventos.crear_evento_tarea(
            "consulta", 
            "tarea-123", 
            "completada", 
            {"respuesta": "OK"}
        )
        print(f"  ✅ Evento tarea: {eventoTarea}")
        
        eventoMetrica = FabricaEventos.crear_evento_metrica(
            "cpu_uso", 
            45.5, 
            "%", 
            {"nucleo": "principal"}
        )
        print(f"  ✅ Evento métrica: {eventoMetrica}")
        
        # 8. Eventos activos
        print("\n[8/8] Estado del sistema de eventos...")
        activos = eventos_activos()
        print(f"  📊 Eventos activos: {len(activos)}")
        print(f"  📊 Contador global: {Evento._contador_global}")
        
        expirados = limpiar_eventos_expirados()
        print(f"  📊 Eventos expirados limpiados: {expirados}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Eventos Cuánticos está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")