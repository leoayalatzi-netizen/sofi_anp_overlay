# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Sistema de Tipos de Eventos (El Lenguaje del Sistema Nervioso)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema de tipos de eventos
# jerárquico, extensible y autoconsciente. Los tipos no son simples
# strings, son entidades vivas con metadatos, validación y capacidades
# de descubrimiento. Es el vocabulario completo del sistema ANP.
# =====================================================================

import sys
import os
import re
import json
import threading
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, Tuple, Set,
    TypeVar, Generic, cast, ClassVar, Type, Iterator
)
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum, auto
from collections import defaultdict, OrderedDict
from functools import lru_cache, wraps

# =====================================================================
# IMPORTACIONES (con fallback)
# =====================================================================

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
# METADATOS DE TIPO DE EVENTO
# =====================================================================

@dataclass(frozen=True)
class MetadatosTipoEvento:
    """Metadatos inmutables que describen un tipo de evento."""
    nombre: str
    descripcion: str
    categoria: str
    prioridad_default: PrioridadEvento = PrioridadEvento.MEDIA
    requiere_datos: bool = False
    esquema_datos: Optional[Dict[str, Any]] = None
    es_critico: bool = False
    es_interno: bool = False
    es_logueable: bool = True
    es_metricable: bool = False
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    ejemplos: List[str] = field(default_factory=list)
    
    def a_dict(self) -> Dict[str, Any]:
        """Serializa los metadatos a diccionario."""
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'prioridad_default': self.prioridad_default.name,
            'requiere_datos': self.requiere_datos,
            'esquema_datos': self.esquema_datos,
            'es_critico': self.es_critico,
            'es_interno': self.es_interno,
            'es_logueable': self.es_logueable,
            'es_metricable': self.es_metricable,
            'version': self.version,
            'tags': self.tags,
            'ejemplos': self.ejemplos,
        }

# =====================================================================
# CATEGORÍAS DE EVENTOS
# =====================================================================

class CategoriaEvento(Enum):
    """Categorías principales de eventos en el sistema."""
    SISTEMA = "sistema"
    NUCLEO = "nucleo"
    TAREA = "tarea"
    FALLO = "fallo"
    USUARIO = "usuario"
    IA = "ia"
    CONCIENCIA = "conciencia"
    METRICA = "metrica"
    CONTEXTO = "contexto"
    MEMORIA = "memoria"
    BUSQUEDA = "busqueda"
    RAZONAMIENTO = "razonamiento"
    COMUNICACION = "comunicacion"
    FALLBACK = "fallback"
    DEBUG = "debug"
    PERSONALIZADO = "personalizado"
    
    @classmethod
    def todas(cls) -> List[str]:
        return [c.value for c in cls]

# =====================================================================
# REGISTRO CENTRAL DE TIPOS DE EVENTOS
# =====================================================================

class RegistroTiposEvento:
    """
    Registro central de todos los tipos de eventos del sistema.
    Implementa patrón Singleton thread-safe.
    """
    
    _instancia: Optional['RegistroTiposEvento'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia
    
    def __init__(self):
        if self._inicializado:
            return
        
        with self._lock:
            if self._inicializado:
                return
            
            self._tipos: Dict[str, MetadatosTipoEvento] = {}
            self._tipos_por_categoria: Dict[str, List[str]] = defaultdict(list)
            self._jerarquia: Dict[str, List[str]] = defaultdict(list)
            self._patrones: Dict[str, List[str]] = {}
            
            self._inicializar_tipos()
            self._construir_jerarquia()
            self._inicializado = True
    
    def _inicializar_tipos(self):
        """Inicializa todos los tipos de eventos del sistema."""
        self._registrar_tipos_sistema()
        self._registrar_tipos_nucleo()
        self._registrar_tipos_tarea()
        self._registrar_tipos_fallo()
        self._registrar_tipos_usuario()
        self._registrar_tipos_ia()
        self._registrar_tipos_conciencia()
        self._registrar_tipos_metrica()
        self._registrar_tipos_contexto()
        self._registrar_tipos_memoria()
        self._registrar_tipos_fallback()
    
    def _registrar(self, tipo: str, metadatos: MetadatosTipoEvento):
        """Registra un tipo de evento."""
        self._tipos[tipo] = metadatos
        self._tipos_por_categoria[metadatos.categoria].append(tipo)
    
    def _registrar_tipos_sistema(self):
        """Registra eventos del sistema."""
        eventos = [
            ("sistema.iniciando", "Sistema iniciando", True, PrioridadEvento.CRITICA),
            ("sistema.listo", "Sistema listo para operar", True, PrioridadEvento.ALTA),
            ("sistema.apagando", "Sistema apagándose", True, PrioridadEvento.CRITICA),
            ("sistema.error", "Error general del sistema", True, PrioridadEvento.CRITICA),
            ("sistema.advertencia", "Advertencia del sistema", False, PrioridadEvento.ALTA),
            ("sistema.info", "Información del sistema", False, PrioridadEvento.BAJA),
            ("sistema.debug", "Depuración del sistema", False, PrioridadEvento.DIFERIDA),
            ("sistema.configuracion_cambiada", "Configuración modificada", True, PrioridadEvento.MEDIA),
            ("sistema.reiniciando", "Sistema reiniciando", True, PrioridadEvento.CRITICA),
            ("sistema.modo_cambiado", "Modo de operación cambiado", True, PrioridadEvento.ALTA),
        ]
        
        for nombre, desc, es_critico, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.SISTEMA.value,
                prioridad_default=prioridad,
                es_critico=es_critico,
                es_logueable=True,
                tags=["sistema", "core"],
            ))
    
    def _registrar_tipos_nucleo(self):
        """Registra eventos relacionados con núcleos."""
        eventos = [
            ("nucleo.activado", "Núcleo activado", PrioridadEvento.ALTA),
            ("nucleo.desactivado", "Núcleo desactivado", PrioridadEvento.ALTA),
            ("nucleo.degradado", "Núcleo degradado", PrioridadEvento.ALTA),
            ("nucleo.recuperado", "Núcleo recuperado", PrioridadEvento.ALTA),
            ("nucleo.fallback", "Núcleo en modo fallback", PrioridadEvento.ALTA),
            ("nucleo.error", "Error en núcleo", PrioridadEvento.CRITICA),
            ("nucleo.latido", "Latido de núcleo", PrioridadEvento.BAJA),
            ("nucleo.carga_actualizada", "Carga de núcleo actualizada", PrioridadEvento.MEDIA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.NUCLEO.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                tags=["nucleo", "orquestador"],
            ))
    
    def _registrar_tipos_tarea(self):
        """Registra eventos relacionados con tareas."""
        eventos = [
            ("tarea.creada", "Tarea creada", PrioridadEvento.MEDIA),
            ("tarea.asignada", "Tarea asignada a núcleo", PrioridadEvento.MEDIA),
            ("tarea.iniciada", "Tarea iniciada", PrioridadEvento.MEDIA),
            ("tarea.completada", "Tarea completada exitosamente", PrioridadEvento.MEDIA),
            ("tarea.fallida", "Tarea fallida", PrioridadEvento.ALTA),
            ("tarea.cancelada", "Tarea cancelada", PrioridadEvento.MEDIA),
            ("tarea.reintentada", "Tarea reintentada", PrioridadEvento.MEDIA),
            ("tarea.timeout", "Tarea excedió tiempo límite", PrioridadEvento.ALTA),
            ("tarea.progreso", "Progreso de tarea", PrioridadEvento.BAJA),
            ("tarea.encolada", "Tarea encolada", PrioridadEvento.BAJA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.TAREA.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                es_metricable=True,
                tags=["tarea", "planificador"],
            ))
    
    def _registrar_tipos_fallo(self):
        """Registra eventos de fallo."""
        eventos = [
            ("fallo.general", "Fallo general", PrioridadEvento.CRITICA, True),
            ("fallo.timeout", "Timeout de operación", PrioridadEvento.ALTA, True),
            ("fallo.memoria", "Memoria insuficiente", PrioridadEvento.CRITICA, True),
            ("fallo.nucleo", "Fallo de núcleo", PrioridadEvento.CRITICA, True),
            ("fallo.red", "Fallo de red", PrioridadEvento.ALTA, False),
            ("fallo.datos", "Datos corruptos", PrioridadEvento.CRITICA, True),
            ("fallo.validacion", "Error de validación", PrioridadEvento.MEDIA, False),
            ("fallo.dependencia", "Dependencia fallida", PrioridadEvento.ALTA, True),
            ("fallo.persistencia", "Error de persistencia", PrioridadEvento.CRITICA, True),
            ("fallo.circuit_breaker", "Circuit breaker abierto", PrioridadEvento.ALTA, True),
            ("fallo.degradacion", "Degradación activada", PrioridadEvento.ALTA, True),
            ("fallo.recuperacion", "Fallo en recuperación", PrioridadEvento.CRITICA, True),
        ]
        
        for item in eventos:
            if len(item) == 4:
                nombre, desc, prioridad, es_critico = item
            else:
                nombre, desc, prioridad = item
                es_critico = prioridad <= PrioridadEvento.ALTA
            
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.FALLO.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_critico=es_critico,
                es_logueable=True,
                es_metricable=True,
                tags=["fallo", "error"],
            ))
    
    def _registrar_tipos_usuario(self):
        """Registra eventos de interacción con usuario."""
        eventos = [
            ("usuario.hablando", "Usuario enviando mensaje", PrioridadEvento.ALTA),
            ("usuario.conectado", "Usuario conectado", PrioridadEvento.MEDIA),
            ("usuario.desconectado", "Usuario desconectado", PrioridadEvento.MEDIA),
            ("usuario.tipeando", "Usuario escribiendo", PrioridadEvento.BAJA),
            ("usuario.archivo_subido", "Usuario subió archivo", PrioridadEvento.MEDIA),
            ("usuario.comando", "Usuario ejecutó comando", PrioridadEvento.ALTA),
            ("usuario.feedback", "Usuario envió feedback", PrioridadEvento.MEDIA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.USUARIO.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                es_metricable=True,
                tags=["usuario", "interaccion"],
            ))
    
    def _registrar_tipos_ia(self):
        """Registra eventos de la IA."""
        eventos = [
            ("ia.pensando", "IA procesando", PrioridadEvento.MEDIA),
            ("ia.respondiendo", "IA generando respuesta", PrioridadEvento.ALTA),
            ("ia.respuesta_parcial", "Respuesta parcial generada", PrioridadEvento.BAJA),
            ("ia.razonando", "IA razonando", PrioridadEvento.MEDIA),
            ("ia.buscando", "IA buscando información", PrioridadEvento.MEDIA),
            ("ia.recordando", "IA accediendo a memoria", PrioridadEvento.MEDIA),
            ("ia.aprendiendo", "IA aprendiendo", PrioridadEvento.BAJA),
            ("ia.creando", "IA generando contenido creativo", PrioridadEvento.MEDIA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.IA.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                tags=["ia", "procesamiento"],
            ))
    
    def _registrar_tipos_conciencia(self):
        """Registra eventos de la conciencia sistémica."""
        eventos = [
            ("conciencia.latido", "Latido de conciencia", PrioridadEvento.BAJA),
            ("conciencia.alerta", "Alerta de conciencia", PrioridadEvento.ALTA),
            ("conciencia.anomalia", "Anomalía detectada", PrioridadEvento.ALTA),
            ("conciencia.estado_cambiado", "Estado sistémico cambiado", PrioridadEvento.MEDIA),
            ("conciencia.fase_cambiada", "Fase lunar cambiada", PrioridadEvento.BAJA),
            ("conciencia.auto_curacion", "Auto-curación aplicada", PrioridadEvento.ALTA),
            ("conciencia.aprendizaje", "Aprendizaje registrado", PrioridadEvento.BAJA),
            ("conciencia.reflexion", "Reflexión completada", PrioridadEvento.BAJA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.CONCIENCIA.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                tags=["conciencia", "monitoreo"],
            ))
    
    def _registrar_tipos_metrica(self):
        """Registra eventos de métricas."""
        eventos = [
            ("metrica.registrada", "Métrica registrada", PrioridadEvento.BAJA),
            ("metrica.alerta", "Alerta de métrica", PrioridadEvento.MEDIA),
            ("metrica.umbral_superado", "Umbral de métrica superado", PrioridadEvento.ALTA),
            ("metrica.tendencia", "Tendencia detectada", PrioridadEvento.BAJA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.METRICA.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=False,
                es_metricable=True,
                tags=["metrica", "monitoreo"],
            ))
    
    def _registrar_tipos_contexto(self):
        """Registra eventos de contexto."""
        eventos = [
            ("contexto.cambiado", "Contexto modificado", PrioridadEvento.MEDIA),
            ("contexto.sesion_iniciada", "Sesión iniciada", PrioridadEvento.MEDIA),
            ("contexto.sesion_finalizada", "Sesión finalizada", PrioridadEvento.MEDIA),
            ("contexto.memoria_actualizada", "Memoria de contexto actualizada", PrioridadEvento.BAJA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.CONTEXTO.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                tags=["contexto", "sesion"],
            ))
    
    def _registrar_tipos_memoria(self):
        """Registra eventos de memoria."""
        eventos = [
            ("memoria.actualizada", "Memoria actualizada", PrioridadEvento.BAJA),
            ("memoria.consolidada", "Memoria consolidada", PrioridadEvento.BAJA),
            ("memoria.recuperada", "Memoria recuperada", PrioridadEvento.MEDIA),
            ("memoria.olvidada", "Memoria olvidada", PrioridadEvento.BAJA),
            ("memoria.error", "Error de memoria", PrioridadEvento.ALTA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.MEMORIA.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                tags=["memoria", "almacenamiento"],
            ))
    
    def _registrar_tipos_fallback(self):
        """Registra eventos de fallback."""
        eventos = [
            ("fallback.activado", "Modo fallback activado", PrioridadEvento.ALTA),
            ("fallback.desactivado", "Modo fallback desactivado", PrioridadEvento.MEDIA),
            ("fallback.respuesta_emergencia", "Respuesta de emergencia usada", PrioridadEvento.ALTA),
            ("fallback.circuit_breaker_abierto", "Circuit breaker abierto", PrioridadEvento.ALTA),
            ("fallback.circuit_breaker_cerrado", "Circuit breaker cerrado", PrioridadEvento.MEDIA),
            ("fallback.degradacion", "Degradación aplicada", PrioridadEvento.ALTA),
            ("fallback.nucleo_alternativo", "Núcleo alternativo usado", PrioridadEvento.MEDIA),
        ]
        
        for nombre, desc, prioridad in eventos:
            self._registrar(nombre, MetadatosTipoEvento(
                nombre=nombre,
                descripcion=desc,
                categoria=CategoriaEvento.FALLBACK.value,
                prioridad_default=prioridad,
                requiere_datos=True,
                es_logueable=True,
                es_metricable=True,
                tags=["fallback", "resiliencia"],
            ))
    
    def _construir_jerarquia(self):
        """Construye la jerarquía de tipos basada en notación de puntos."""
        for tipo in self._tipos:
            partes = tipo.split('.')
            for i in range(1, len(partes)):
                padre = '.'.join(partes[:i])
                if padre not in self._jerarquia:
                    self._jerarquia[padre] = []
                if tipo not in self._jerarquia[padre]:
                    self._jerarquia[padre].append(tipo)
    
    # ===== MÉTODOS DE CONSULTA =====
    
    def obtener(self, tipo: str) -> Optional[MetadatosTipoEvento]:
        """Obtiene los metadatos de un tipo de evento."""
        return self._tipos.get(tipo)
    
    def existe(self, tipo: str) -> bool:
        """Verifica si un tipo de evento existe."""
        return tipo in self._tipos
    
    def todos(self) -> List[str]:
        """Obtiene todos los tipos de eventos registrados."""
        return list(self._tipos.keys())
    
    def por_categoria(self, categoria: str) -> List[str]:
        """Obtiene tipos de evento por categoría."""
        return self._tipos_por_categoria.get(categoria, [])
    
    def por_tag(self, tag: str) -> List[str]:
        """Obtiene tipos de evento por tag."""
        return [t for t, m in self._tipos.items() if tag in m.tags]
    
    def criticos(self) -> List[str]:
        """Obtiene tipos de evento críticos."""
        return [t for t, m in self._tipos.items() if m.es_critico]
    
    def hijos(self, prefijo: str) -> List[str]:
        """Obtiene tipos de evento que son hijos de un prefijo."""
        return self._jerarquia.get(prefijo, [])
    
    def buscar(self, patron: str) -> List[str]:
        """Busca tipos de evento que coinciden con un patrón."""
        regex = re.compile(patron.replace('*', '.*'))
        return [t for t in self._tipos if regex.match(t)]
    
    def validar_tipo(self, tipo: str) -> Tuple[bool, Optional[str]]:
        """
        Valida si un string es un tipo de evento válido.
        Retorna (es_valido, sugerencia).
        """
        if self.existe(tipo):
            return True, None
        
        # Buscar sugerencias
        sugerencia = None
        if '.' in tipo:
            prefijo = tipo.rsplit('.', 1)[0]
            hijos = self.hijos(prefijo)
            if hijos:
                sugerencia = hijos[0]
        else:
            similares = self.buscar(f"*{tipo}*")
            if similares:
                sugerencia = similares[0]
        
        return False, sugerencia
    
    @lru_cache(maxsize=128)
    def prioridad_para(self, tipo: str) -> PrioridadEvento:
        """Obtiene la prioridad por defecto para un tipo de evento."""
        meta = self.obtener(tipo)
        return meta.prioridad_default if meta else PrioridadEvento.MEDIA
    
    def exportar(self, formato: str = "dict") -> Dict[str, Any]:
        """Exporta todos los tipos de eventos."""
        return {
            'total': len(self._tipos),
            'categorias': list(self._tipos_por_categoria.keys()),
            'por_categoria': {
                cat: len(tipos) for cat, tipos in self._tipos_por_categoria.items()
            },
            'tipos': {t: m.a_dict() for t, m in self._tipos.items()},
        }
    
    def __len__(self) -> int:
        return len(self._tipos)
    
    def __contains__(self, tipo: str) -> bool:
        return self.existe(tipo)
    
    def __iter__(self) -> Iterator[str]:
        return iter(self._tipos)

# =====================================================================
# CLASE PRINCIPAL DE TIPOS DE EVENTO
# =====================================================================

class TipoEvento:
    """
    Clase principal para tipos de eventos.
    Proporciona acceso unificado a todos los tipos definidos.
    """
    
    _registro: ClassVar[RegistroTiposEvento] = None
    
    def __init__(self):
        raise TypeError("TipoEvento es una clase estática, no debe instanciarse")
    
    @classmethod
    def _get_registro(cls) -> RegistroTiposEvento:
        if cls._registro is None:
            cls._registro = RegistroTiposEvento()
        return cls._registro
    
    # ===== ACCESO A TIPOS =====
    
    @classmethod
    def todos(cls) -> List[str]:
        return cls._get_registro().todos()
    
    @classmethod
    def existe(cls, tipo: str) -> bool:
        return cls._get_registro().existe(tipo)
    
    @classmethod
    def obtener(cls, tipo: str) -> Optional[MetadatosTipoEvento]:
        return cls._get_registro().obtener(tipo)
    
    @classmethod
    def validar(cls, tipo: str) -> Tuple[bool, Optional[str]]:
        return cls._get_registro().validar_tipo(tipo)
    
    @classmethod
    def prioridad(cls, tipo: str) -> PrioridadEvento:
        return cls._get_registro().prioridad_para(tipo)
    
    # ===== CONSULTAS POR CATEGORÍA =====
    
    @classmethod
    def sistema(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.SISTEMA.value)
    
    @classmethod
    def nucleo(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.NUCLEO.value)
    
    @classmethod
    def tarea(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.TAREA.value)
    
    @classmethod
    def fallo(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.FALLO.value)
    
    @classmethod
    def usuario(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.USUARIO.value)
    
    @classmethod
    def ia(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.IA.value)
    
    @classmethod
    def conciencia(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.CONCIENCIA.value)
    
    @classmethod
    def metrica(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.METRICA.value)
    
    @classmethod
    def fallback(cls) -> List[str]:
        return cls._get_registro().por_categoria(CategoriaEvento.FALLBACK.value)
    
    # ===== CONSULTAS ESPECIALES =====
    
    @classmethod
    def criticos(cls) -> List[str]:
        return cls._get_registro().criticos()
    
    @classmethod
    def hijos_de(cls, prefijo: str) -> List[str]:
        return cls._get_registro().hijos(prefijo)
    
    @classmethod
    def buscar(cls, patron: str) -> List[str]:
        return cls._get_registro().buscar(patron)
    
    @classmethod
    def por_tag(cls, tag: str) -> List[str]:
        return cls._get_registro().por_tag(tag)
    
    # ===== MÉTODOS DE CONVENIENCIA =====
    
    @classmethod
    def SISTEMA_INICIANDO(cls) -> str: return "sistema.iniciando"
    @classmethod
    def SISTEMA_LISTO(cls) -> str: return "sistema.listo"
    @classmethod
    def SISTEMA_APAGANDO(cls) -> str: return "sistema.apagando"
    @classmethod
    def SISTEMA_ERROR(cls) -> str: return "sistema.error"
    
    @classmethod
    def NUCLEO_ACTIVADO(cls) -> str: return "nucleo.activado"
    @classmethod
    def NUCLEO_DESACTIVADO(cls) -> str: return "nucleo.desactivado"
    @classmethod
    def NUCLEO_FALLBACK(cls) -> str: return "nucleo.fallback"
    
    @classmethod
    def TAREA_CREADA(cls) -> str: return "tarea.creada"
    @classmethod
    def TAREA_COMPLETADA(cls) -> str: return "tarea.completada"
    @classmethod
    def TAREA_FALLIDA(cls) -> str: return "tarea.fallida"
    
    @classmethod
    def FALLO_GENERAL(cls) -> str: return "fallo.general"
    @classmethod
    def FALLO_TIMEOUT(cls) -> str: return "fallo.timeout"
    @classmethod
    def FALLO_MEMORIA(cls) -> str: return "fallo.memoria"
    @classmethod
    def FALLO_NUCLEO(cls) -> str: return "fallo.nucleo"
    
    @classmethod
    def USUARIO_HABLANDO(cls) -> str: return "usuario.hablando"
    
    @classmethod
    def IA_PENSANDO(cls) -> str: return "ia.pensando"
    @classmethod
    def IA_RESPONDIENDO(cls) -> str: return "ia.respondiendo"
    
    @classmethod
    def CONCIENCIA_LATIDO(cls) -> str: return "conciencia.latido"
    @classmethod
    def CONCIENCIA_ALERTA(cls) -> str: return "conciencia.alerta"
    
    @classmethod
    def METRICA_REGISTRADA(cls) -> str: return "metrica.registrada"
    
    @classmethod
    def CONTEXTO_CAMBIADO(cls) -> str: return "contexto.cambiado"
    
    @classmethod
    def MEMORIA_ACTUALIZADA(cls) -> str: return "memoria.actualizada"
    
    @classmethod
    def FALLBACK_ACTIVADO(cls) -> str: return "fallback.activado"
    
    # ===== INFORMACIÓN =====
    
    @classmethod
    def estadisticas(cls) -> Dict[str, Any]:
        return cls._get_registro().exportar()
    
    @classmethod
    def resumen(cls) -> str:
        reg = cls._get_registro()
        return f"TipoEvento: {len(reg)} tipos en {len(reg._tipos_por_categoria)} categorías"
    
    @classmethod
    def info_tipo(cls, tipo: str) -> Optional[Dict[str, Any]]:
        meta = cls.obtener(tipo)
        return meta.a_dict() if meta else None

# =====================================================================
# DECORADOR PARA VALIDACIÓN DE TIPOS
# =====================================================================

def validar_tipo_evento(tipo: str) -> Callable:
    """
    Decorador para validar que un tipo de evento es válido.
    
    Uso:
        @validar_tipo_evento("sistema.iniciando")
        def publicar_inicio(datos):
            pass
    """
    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not TipoEvento.existe(tipo):
                es_valido, sugerencia = TipoEvento.validar(tipo)
                if sugerencia:
                    warnings.warn(
                        f"Tipo de evento '{tipo}' no existe. "
                        f"¿Quisiste decir '{sugerencia}'?",
                        UserWarning
                    )
            return func(*args, **kwargs)
        return wrapper
    return decorador
    
# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def es_tipo_valido(tipo: str) -> bool:
    """Verifica rápidamente si un tipo de evento es válido."""
    return TipoEvento.existe(tipo)

def obtener_prioridad(tipo: str) -> PrioridadEvento:
    """Obtiene la prioridad por defecto para un tipo de evento."""
    return TipoEvento.prioridad(tipo)

def listar_tipos(categoria: Optional[str] = None) -> List[str]:
    """Lista tipos de evento, opcionalmente filtrados por categoría."""
    if categoria:
        return TipoEvento._get_registro().por_categoria(categoria)
    return TipoEvento.todos()

def buscar_tipos(patron: str) -> List[str]:
    """Busca tipos de evento por patrón (soporta wildcards *)."""
    return TipoEvento.buscar(patron)

def es_tipo_critico(tipo: str) -> bool:
    """Verifica si un tipo de evento es crítico."""
    meta = TipoEvento.obtener(tipo)
    return meta.es_critico if meta else False

def requiere_datos(tipo: str) -> bool:
    """Verifica si un tipo de evento requiere datos."""
    meta = TipoEvento.obtener(tipo)
    return meta.requiere_datos if meta else True


# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def es_tipo_valido(tipo: str) -> bool:
    """Verifica rápidamente si un tipo de evento es válido."""
    return TipoEvento.existe(tipo)

def obtener_prioridad(tipo: str) -> PrioridadEvento:
    """Obtiene la prioridad por defecto para un tipo de evento."""
    return TipoEvento.prioridad(tipo)

def listar_tipos(categoria: Optional[str] = None) -> List[str]:
    """Lista tipos de evento, opcionalmente filtrados por categoría."""
    if categoria:
        return TipoEvento._get_registro().por_categoria(categoria)
    return TipoEvento.todos()

def buscar_tipos(patron: str) -> List[str]:
    """Busca tipos de evento por patrón (soporta wildcards *)."""
    return TipoEvento.buscar(patron)

def es_tipo_critico(tipo: str) -> bool:
    """Verifica si un tipo de evento es crítico."""
    meta = TipoEvento.obtener(tipo)
    return meta.es_critico if meta else False

def requiere_datos(tipo: str) -> bool:
    """Verifica si un tipo de evento requiere datos."""
    meta = TipoEvento.obtener(tipo)
    return meta.requiere_datos if meta else True

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE TIPOS DE EVENTOS")
    print("=" * 70)
    
    try:
        # 1. Inicializar
        print("\n[1/8] Inicializando registro de tipos...")
        print(f"  ✅ {TipoEvento.resumen()}")
        
        # 2. Categorías
        print("\n[2/8] Categorías disponibles:")
        categorias = list(TipoEvento._get_registro()._tipos_por_categoria.keys())
        for cat in sorted(categorias):
            count = len(TipoEvento._get_registro().por_categoria(cat))
            print(f"  📁 {cat}: {count} tipos")
        
        # 3. Tipos de sistema
        print("\n[3/8] Tipos de sistema:")
        for tipo in TipoEvento.sistema()[:5]:
            meta = TipoEvento.obtener(tipo)
            print(f"  📍 {tipo}: {meta.descripcion}")
        if len(TipoEvento.sistema()) > 5:
            print(f"  ... y {len(TipoEvento.sistema()) - 5} más")
        
        # 4. Tipos de fallo
        print("\n[4/8] Tipos de fallo:")
        for tipo in TipoEvento.fallo():
            meta = TipoEvento.obtener(tipo)
            critico = "🚨" if meta.es_critico else "⚠️"
            print(f"  {critico} {tipo}: {meta.descripcion}")
        
        # 5. Tipos críticos
        print("\n[5/8] Tipos críticos:")
        criticos = TipoEvento.criticos()
        for tipo in criticos[:5]:
            print(f"  🔴 {tipo}")
        print(f"  Total críticos: {len(criticos)}")
        
        # 6. Validación
        print("\n[6/8] Probando validación...")
        pruebas = [
            "sistema.iniciando",
            "fallo.timeout",
            "evento.inexistente",
            "tarea.completada",
            "fallo.*",
        ]
        for prueba in pruebas:
            if TipoEvento.existe(prueba):
                print(f"  ✅ '{prueba}' es válido")
            else:
                valido, sugerencia = TipoEvento.validar(prueba)
                if sugerencia:
                    print(f"  ❌ '{prueba}' no existe. ¿Quisiste decir '{sugerencia}'?")
                else:
                    print(f"  ❌ '{prueba}' no existe")
        
        # 7. Jerarquía
        print("\n[7/8] Probando jerarquía...")
        hijos_sistema = TipoEvento.hijos_de("sistema")
        print(f"  📍 Hijos de 'sistema': {len(hijos_sistema)}")
        for hijo in hijos_sistema[:5]:
            print(f"     - {hijo}")
        
        hijos_fallo = TipoEvento.hijos_de("fallo")
        print(f"  📍 Hijos de 'fallo': {len(hijos_fallo)}")
        for hijo in hijos_fallo[:5]:
            print(f"     - {hijo}")
        
        # 8. Búsqueda
        print("\n[8/8] Probando búsqueda...")
        resultados = TipoEvento.buscar("*memoria*")
        print(f"  🔍 Búsqueda '*memoria*': {len(resultados)} resultados")
        for r in resultados:
            print(f"     - {r}")
        
        resultados = TipoEvento.buscar("tarea.*")
        print(f"  🔍 Búsqueda 'tarea.*': {len(resultados)} resultados")
        for r in resultados[:5]:
            print(f"     - {r}")
        
        # Estadísticas finales
        print("\n" + "=" * 70)
        stats = TipoEvento.estadisticas()
        print(f"   📊 ESTADÍSTICAS FINALES")
        print(f"   Total tipos: {stats['total']}")
        print(f"   Categorías: {len(stats['categorias'])}")
        print("=" * 70)
        
        # Mostrar distribución
        print("\n📈 Distribución por categoría:")
        for cat, count in stats['por_categoria'].items():
            barra = "█" * (count // 2)
            print(f"   {cat:15} {barra} {count}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Tipos de Eventos está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")