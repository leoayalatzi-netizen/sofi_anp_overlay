#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio de Validación (El Guardián de la Integridad)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema completo de validación
# de datos con tipos, rangos, formatos, sanitización, y mensajes de
# error localizados. Es la primera línea de defensa contra datos corruptos.
# =====================================================================

import re
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, Set, Pattern
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, date, time as dt_time
from ipaddress import ip_address, IPv4Address, IPv6Address
from urllib.parse import urlparse
import hashlib
import base64

# =====================================================================
# ENUMERACIONES
# =====================================================================

class TipoValidacion(Enum):
    """Tipos de validación soportados."""
    TIPO = "tipo"
    REQUERIDO = "requerido"
    RANGO = "rango"
    LONGITUD = "longitud"
    PATRON = "patron"
    ENUM = "enum"
    EMAIL = "email"
    URL = "url"
    IP = "ip"
    UUID = "uuid"
    FECHA = "fecha"
    HORA = "hora"
    DATETIME = "datetime"
    CREDIT_CARD = "credit_card"
    PHONE = "phone"
    JSON = "json"
    BASE64 = "base64"
    HASH = "hash"
    COLOR_HEX = "color_hex"
    SLUG = "slug"
    USERNAME = "username"
    PASSWORD = "password"
    PERSONALIZADA = "personalizada"

class SeveridadError(Enum):
    """Severidad de los errores de validación."""
    INFO = "info"
    ADVERTENCIA = "warning"
    ERROR = "error"
    CRITICO = "critico"

class Idioma(Enum):
    """Idiomas soportados para mensajes de error."""
    ESPANOL = "es"
    INGLES = "en"
    FRANCES = "fr"
    ALEMAN = "de"
    ITALIANO = "it"
    PORTUGUES = "pt"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class ErrorValidacion:
    """Representa un error de validación individual."""
    campo: str
    tipo: TipoValidacion
    mensaje: str
    valor_recibido: Any
    valor_esperado: Optional[Any] = None
    severidad: SeveridadError = SeveridadError.ERROR
    contexto: Dict[str, Any] = field(default_factory=dict)
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'campo': self.campo,
            'tipo': self.tipo.value,
            'mensaje': self.mensaje,
            'valor_recibido': str(self.valor_recibido),
            'valor_esperado': self.valor_esperado,
            'severidad': self.severidad.value,
            'contexto': self.contexto,
        }

@dataclass
class ResultadoValidacion:
    """Resultado de una validación completa."""
    valido: bool
    datos_validados: Dict[str, Any] = field(default_factory=dict)
    datos_sanitizados: Dict[str, Any] = field(default_factory=dict)
    errores: List[ErrorValidacion] = field(default_factory=list)
    advertencias: List[ErrorValidacion] = field(default_factory=list)
    
    def agregar_error(self, error: ErrorValidacion):
        if error.severidad == SeveridadError.ADVERTENCIA:
            self.advertencias.append(error)
        else:
            self.errores.append(error)
            self.valido = False
    
    def tiene_errores(self) -> bool:
        return len(self.errores) > 0
    
    def tiene_advertencias(self) -> bool:
        return len(self.advertencias) > 0
    
    def a_dict(self) -> Dict[str, Any]:
        return {
            'valido': self.valido,
            'datos_validados': self.datos_validados,
            'errores': [e.a_dict() for e in self.errores],
            'advertencias': [a.a_dict() for a in self.advertencias],
        }

@dataclass
class ReglaValidacion:
    """Define una regla de validación para un campo."""
    campo: str
    tipo: TipoValidacion
    parametros: Dict[str, Any] = field(default_factory=dict)
    requerido: bool = True
    severidad: SeveridadError = SeveridadError.ERROR
    mensaje_personalizado: Optional[str] = None
    sanitizar: Optional[Callable[[Any], Any]] = None

# =====================================================================
# MENSAJES DE ERROR LOCALIZADOS
# =====================================================================

class MensajesError:
    """Gestor de mensajes de error localizados."""
    
    MENSAJES = {
        Idioma.ESPANOL: {
            'requerido': "El campo '{campo}' es obligatorio",
            'tipo_str': "El campo '{campo}' debe ser texto",
            'tipo_int': "El campo '{campo}' debe ser un número entero",
            'tipo_float': "El campo '{campo}' debe ser un número decimal",
            'tipo_bool': "El campo '{campo}' debe ser verdadero/falso",
            'tipo_list': "El campo '{campo}' debe ser una lista",
            'tipo_dict': "El campo '{campo}' debe ser un objeto",
            'rango_min': "El campo '{campo}' debe ser mayor o igual a {min}",
            'rango_max': "El campo '{campo}' debe ser menor o igual a {max}",
            'rango_entre': "El campo '{campo}' debe estar entre {min} y {max}",
            'longitud_min': "El campo '{campo}' debe tener al menos {min} caracteres",
            'longitud_max': "El campo '{campo}' debe tener como máximo {max} caracteres",
            'longitud_entre': "El campo '{campo}' debe tener entre {min} y {max} caracteres",
            'patron': "El campo '{campo}' no tiene el formato correcto",
            'enum': "El campo '{campo}' debe ser uno de: {valores}",
            'email': "El campo '{campo}' debe ser un correo electrónico válido",
            'url': "El campo '{campo}' debe ser una URL válida",
            'ip': "El campo '{campo}' debe ser una dirección IP válida",
            'uuid': "El campo '{campo}' debe ser un UUID válido",
            'fecha': "El campo '{campo}' debe ser una fecha válida (YYYY-MM-DD)",
            'hora': "El campo '{campo}' debe ser una hora válida (HH:MM:SS)",
            'datetime': "El campo '{campo}' debe ser una fecha y hora válida",
            'json': "El campo '{campo}' debe ser un JSON válido",
            'color_hex': "El campo '{campo}' debe ser un color hexadecimal válido (#RRGGBB)",
            'username': "El campo '{campo}' debe contener solo letras, números y guiones bajos",
            'password': "El campo '{campo}' debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número",
        },
        Idioma.INGLES: {
            'requerido': "Field '{campo}' is required",
            'email': "Field '{campo}' must be a valid email address",
            'url': "Field '{campo}' must be a valid URL",
        }
    }
    
    @classmethod
    def obtener(cls, clave: str, idioma: Idioma = Idioma.ESPANOL, **kwargs) -> str:
        mensajes = cls.MENSAJES.get(idioma, cls.MENSAJES[Idioma.ESPANOL])
        plantilla = mensajes.get(clave, f"Validation error on '{clave}'")
        return plantilla.format(**kwargs)

# =====================================================================
# VALIDADORES UNITARIOS
# =====================================================================

class Validador:
    """Colección de validadores unitarios."""
    
    # ===== VALIDACIONES DE TIPO =====
    
    @staticmethod
    def es_string(valor: Any) -> bool:
        return isinstance(valor, str)
    
    @staticmethod
    def es_entero(valor: Any) -> bool:
        return isinstance(valor, int) and not isinstance(valor, bool)
    
    @staticmethod
    def es_flotante(valor: Any) -> bool:
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    
    @staticmethod
    def es_booleano(valor: Any) -> bool:
        return isinstance(valor, bool)
    
    @staticmethod
    def es_lista(valor: Any) -> bool:
        return isinstance(valor, list)
    
    @staticmethod
    def es_diccionario(valor: Any) -> bool:
        return isinstance(valor, dict)
    
    # ===== VALIDACIONES DE FORMATO =====
    
    @staticmethod
    def es_email(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(patron, valor))
    
    @staticmethod
    def es_url(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            resultado = urlparse(valor)
            return all([resultado.scheme, resultado.netloc])
        except Exception:
            return False
    
    @staticmethod
    def es_ip(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            ip_address(valor)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def es_uuid(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            uuid.UUID(valor)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def es_fecha(valor: str, formato: str = "%Y-%m-%d") -> bool:
        if not isinstance(valor, str):
            return False
        try:
            datetime.strptime(valor, formato)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def es_hora(valor: str, formato: str = "%H:%M:%S") -> bool:
        return Validador.es_fecha(valor, formato)
    
    @staticmethod
    def es_datetime(valor: str, formato: str = "%Y-%m-%d %H:%M:%S") -> bool:
        return Validador.es_fecha(valor, formato)
    
    @staticmethod
    def es_json(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            json.loads(valor)
            return True
        except json.JSONDecodeError:
            return False
    
    @staticmethod
    def es_color_hex(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        patron = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        return bool(re.match(patron, valor))
    
    @staticmethod
    def es_slug(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        patron = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        return bool(re.match(patron, valor))
    
    @staticmethod
    def es_username(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        patron = r'^[a-zA-Z0-9_]{3,20}$'
        return bool(re.match(patron, valor))
    
    @staticmethod
    def es_password_fuerte(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        if len(valor) < 8:
            return False
        if not re.search(r'[A-Z]', valor):
            return False
        if not re.search(r'[a-z]', valor):
            return False
        if not re.search(r'[0-9]', valor):
            return False
        return True
    
    @staticmethod
    def es_base64(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            base64.b64decode(valor)
            return True
        except Exception:
            return False
    
    @staticmethod
    def es_telefono(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        patron = r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$'
        return bool(re.match(patron, valor))
    
    @staticmethod
    def es_tarjeta_credito(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        valor = valor.replace(' ', '').replace('-', '')
        if not valor.isdigit():
            return False
        # Algoritmo de Luhn
        suma = 0
        for i, digito in enumerate(reversed(valor)):
            n = int(digito)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            suma += n
        return suma % 10 == 0 and len(valor) >= 13 and len(valor) <= 19

# =====================================================================
# SANITIZADORES
# =====================================================================

class Sanitizador:
    """Colección de funciones de sanitización."""
    
    @staticmethod
    def texto(valor: Any) -> str:
        """Convierte a string y elimina espacios extra."""
        if valor is None:
            return ""
        return str(valor).strip()
    
    @staticmethod
    def entero(valor: Any, default: int = 0) -> int:
        try:
            return int(valor)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def flotante(valor: Any, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def booleano(valor: Any) -> bool:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str):
            return valor.lower() in ('true', '1', 'yes', 'on', 'si', 'sí')
        return bool(valor)
    
    @staticmethod
    def email(valor: str) -> str:
        return valor.lower().strip() if valor else ""
    
    @staticmethod
    def slug(valor: str) -> str:
        import unicodedata
        if not valor:
            return ""
        valor = unicodedata.normalize('NFKD', valor).encode('ASCII', 'ignore').decode('ASCII')
        valor = re.sub(r'[^\w\s-]', '', valor).strip().lower()
        return re.sub(r'[-\s]+', '-', valor)
    
    @staticmethod
    def html(valor: str) -> str:
        """Escapa caracteres HTML."""
        if not valor:
            return ""
        escape_map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        }
        return ''.join(escape_map.get(c, c) for c in valor)
    
    @staticmethod
    def xss(valor: str) -> str:
        """Sanitización básica contra XSS."""
        if not valor:
            return ""
        valor = re.sub(r'<script\b[^>]*>.*?</script>', '', valor, flags=re.IGNORECASE | re.DOTALL)
        valor = re.sub(r'javascript:', '', valor, flags=re.IGNORECASE)
        valor = re.sub(r'on\w+\s*=', '', valor, flags=re.IGNORECASE)
        return valor

# =====================================================================
# ESQUEMA DE VALIDACIÓN
# =====================================================================


class EsquemaValidacion:
    """Define un esquema completo de validación."""
    
    def __init__(self, nombre: str = ""):
        self.nombre = nombre
        self._reglas: Dict[str, List[ReglaValidacion]] = {}
        self._idioma = Idioma.ESPANOL
        self._sanitizar_global = True
    
    def agregar_regla(self, regla: ReglaValidacion) -> 'EsquemaValidacion':
        if regla.campo not in self._reglas:
            self._reglas[regla.campo] = []
        self._reglas[regla.campo].append(regla)
        return self
    
    def campo(self, nombre: str) -> 'CampoBuilder':
        return CampoBuilder(self, nombre)
    
    def validar(self, datos: Dict[str, Any]) -> ResultadoValidacion:
        resultado = ResultadoValidacion(valido=True)
        datos_procesados = {}
        datos_sanitizados = {}
        
        for campo, reglas in self._reglas.items():
            valor = datos.get(campo)
            
            for regla in reglas:
                # Validar requerido
                if regla.requerido and valor is None:
                    error = ErrorValidacion(
                        campo=campo,
                        tipo=TipoValidacion.REQUERIDO,
                        mensaje=regla.mensaje_personalizado or 
                                MensajesError.obtener('requerido', self._idioma, campo=campo),
                        valor_recibido=valor,
                        severidad=regla.severidad
                    )
                    resultado.agregar_error(error)
                    continue
                
                if valor is None:
                    continue
                
                # Aplicar sanitización si existe
                if self._sanitizar_global and regla.sanitizar:
                    try:
                        valor = regla.sanitizar(valor)
                    except Exception:
                        pass
                
                # Aplicar validación según tipo
                self._aplicar_validacion(regla, campo, valor, resultado)
            
            if campo not in [e.campo for e in resultado.errores]:
                datos_procesados[campo] = valor
                datos_sanitizados[campo] = valor
        
        resultado.datos_validados = datos_procesados
        resultado.datos_sanitizados = datos_sanitizados
        return resultado
    
    def _aplicar_validacion(self, regla: ReglaValidacion, campo: str, 
                            valor: Any, resultado: ResultadoValidacion):
        tipo = regla.tipo
        params = regla.parametros
        
        if tipo == TipoValidacion.TIPO:
            tipo_esperado = params.get('tipo')
            valido = self._validar_tipo(valor, tipo_esperado)
            if not valido:
                self._agregar_error(regla, campo, valor, f"tipo_{tipo_esperado}", resultado, 
                                   tipo_esperado=tipo_esperado)
        
        elif tipo == TipoValidacion.RANGO:
            min_val = params.get('min')
            max_val = params.get('max')
            if min_val is not None and valor < min_val:
                self._agregar_error(regla, campo, valor, 'rango_min', resultado, min=min_val)
            if max_val is not None and valor > max_val:
                self._agregar_error(regla, campo, valor, 'rango_max', resultado, max=max_val)
        
        elif tipo == TipoValidacion.LONGITUD:
            min_len = params.get('min')
            max_len = params.get('max')
            if min_len is not None and len(str(valor)) < min_len:
                self._agregar_error(regla, campo, valor, 'longitud_min', resultado, min=min_len)
            if max_len is not None and len(str(valor)) > max_len:
                self._agregar_error(regla, campo, valor, 'longitud_max', resultado, max=max_len)
        
        elif tipo == TipoValidacion.PATRON:
            patron = params.get('patron')
            if isinstance(patron, str):
                patron = re.compile(patron)
            if not patron.match(str(valor)):
                self._agregar_error(regla, campo, valor, 'patron', resultado)
        
        elif tipo == TipoValidacion.ENUM:
            valores = params.get('valores', [])
            if valor not in valores:
                self._agregar_error(regla, campo, valor, 'enum', resultado, 
                                   valores=', '.join(str(v) for v in valores))
        
        elif tipo == TipoValidacion.EMAIL:
            if not Validador.es_email(valor):
                self._agregar_error(regla, campo, valor, 'email', resultado)
        
        elif tipo == TipoValidacion.URL:
            if not Validador.es_url(valor):
                self._agregar_error(regla, campo, valor, 'url', resultado)
        
        elif tipo == TipoValidacion.IP:
            if not Validador.es_ip(valor):
                self._agregar_error(regla, campo, valor, 'ip', resultado)
        
        elif tipo == TipoValidacion.UUID:
            if not Validador.es_uuid(valor):
                self._agregar_error(regla, campo, valor, 'uuid', resultado)
        
        elif tipo == TipoValidacion.FECHA:
            formato = params.get('formato', '%Y-%m-%d')
            if not Validador.es_fecha(valor, formato):
                self._agregar_error(regla, campo, valor, 'fecha', resultado)
        
        elif tipo == TipoValidacion.COLOR_HEX:
            if not Validador.es_color_hex(valor):
                self._agregar_error(regla, campo, valor, 'color_hex', resultado)
        
        elif tipo == TipoValidacion.USERNAME:
            if not Validador.es_username(valor):
                self._agregar_error(regla, campo, valor, 'username', resultado)
        
        elif tipo == TipoValidacion.PASSWORD:
            if not Validador.es_password_fuerte(valor):
                self._agregar_error(regla, campo, valor, 'password', resultado)
        
        elif tipo == TipoValidacion.PERSONALIZADA:
            validador = params.get('funcion')
            if validador and not validador(valor):
                self._agregar_error(regla, campo, valor, 'personalizada', resultado)
    
    def _validar_tipo(self, valor: Any, tipo_esperado: str) -> bool:
        if tipo_esperado == 'str':
            return Validador.es_string(valor)
        elif tipo_esperado == 'int':
            return Validador.es_entero(valor)
        elif tipo_esperado == 'float':
            return Validador.es_flotante(valor)
        elif tipo_esperado == 'bool':
            return Validador.es_booleano(valor)
        elif tipo_esperado == 'list':
            return Validador.es_lista(valor)
        elif tipo_esperado == 'dict':
            return Validador.es_diccionario(valor)
        return True
    
    def _agregar_error(self, regla: ReglaValidacion, campo: str, valor: Any, 
                       clave: str, resultado: ResultadoValidacion, **kwargs):
        mensaje = regla.mensaje_personalizado or MensajesError.obtener(clave, self._idioma, campo=campo, **kwargs)
        error = ErrorValidacion(
            campo=campo,
            tipo=regla.tipo,
            mensaje=mensaje,
            valor_recibido=valor,
            severidad=regla.severidad
        )
        resultado.agregar_error(error)

# =====================================================================
# BUILDER DE CAMPOS (FLUENT API)
# =====================================================================

class CampoBuilder:
    """Builder fluido para definir reglas de validación por campo."""
    
    def __init__(self, esquema: EsquemaValidacion, nombre: str):
        self.esquema = esquema
        self.nombre = nombre
        self._requerido = True
        self._severidad = SeveridadError.ERROR
        self._mensaje = None
        self._sanitizar = None
    
    def requerido(self, valor: bool = True) -> 'CampoBuilder':
        self._requerido = valor
        return self
    
    def opcional(self) -> 'CampoBuilder':
        self._requerido = False
        return self
    
    def severidad(self, severidad: SeveridadError) -> 'CampoBuilder':
        self._severidad = severidad
        return self
    
    def mensaje(self, mensaje: str) -> 'CampoBuilder':
        self._mensaje = mensaje
        return self
    
    def sanitizar(self, funcion: Callable[[Any], Any]) -> 'CampoBuilder':
        self._sanitizar = funcion
        return self
    
    def rango(self, min_val: Optional[float] = None, max_val: Optional[float] = None) -> 'CampoBuilder':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.RANGO,
            parametros={'min': min_val, 'max': max_val},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        self.esquema.agregar_regla(regla)
        return self
    
    def longitud(self, min_len: Optional[int] = None, max_len: Optional[int] = None) -> 'CampoBuilder':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.LONGITUD,
            parametros={'min': min_len, 'max': max_len},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        self.esquema.agregar_regla(regla)
        return self
    
    def patron(self, patron: Union[str, Pattern]) -> 'CampoBuilder':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.PATRON,
            parametros={'patron': patron},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        self.esquema.agregar_regla(regla)
        return self
    
    def enum(self, valores: List[Any]) -> 'CampoBuilder':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.ENUM,
            parametros={'valores': valores},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        self.esquema.agregar_regla(regla)
        return self
    
    # ===== MÉTODOS TERMINALES (retornan EsquemaValidacion) =====
    
    def tipo(self, tipo_esperado: str) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.TIPO,
            parametros={'tipo': tipo_esperado},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def string(self) -> 'EsquemaValidacion':
        return self.tipo('str')
    
    def entero(self) -> 'EsquemaValidacion':
        return self.tipo('int')
    
    def flotante(self) -> 'EsquemaValidacion':
        return self.tipo('float')
    
    def booleano(self) -> 'EsquemaValidacion':
        return self.tipo('bool')
    
    def lista(self) -> 'EsquemaValidacion':
        return self.tipo('list')
    
    def diccionario(self) -> 'EsquemaValidacion':
        return self.tipo('dict')
    
    def email(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.EMAIL,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar or Sanitizador.email
        )
        return self.esquema.agregar_regla(regla)
    
    def url(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.URL,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def ip(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.IP,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def uuid(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.UUID,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def fecha(self, formato: str = "%Y-%m-%d") -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.FECHA,
            parametros={'formato': formato},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def hora(self, formato: str = "%H:%M:%S") -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.HORA,
            parametros={'formato': formato},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def datetime(self, formato: str = "%Y-%m-%d %H:%M:%S") -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.DATETIME,
            parametros={'formato': formato},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def color_hex(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.COLOR_HEX,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def slug(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.SLUG,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar or Sanitizador.slug
        )
        return self.esquema.agregar_regla(regla)
    
    def username(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.USERNAME,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def password(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.PASSWORD,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def json(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.JSON,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def telefono(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.PHONE,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def tarjeta_credito(self) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.CREDIT_CARD,
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
    
    def personalizada(self, funcion: Callable[[Any], bool]) -> 'EsquemaValidacion':
        regla = ReglaValidacion(
            campo=self.nombre,
            tipo=TipoValidacion.PERSONALIZADA,
            parametros={'funcion': funcion},
            requerido=self._requerido,
            severidad=self._severidad,
            mensaje_personalizado=self._mensaje,
            sanitizar=self._sanitizar
        )
        return self.esquema.agregar_regla(regla)
        
# =====================================================================
# FÁBRICA DE ESQUEMAS
# =====================================================================

class FabricaEsquemas:
    """Fábrica de esquemas de validación predefinidos."""
    
    @staticmethod
    def usuario() -> EsquemaValidacion:
        esquema = EsquemaValidacion("usuario")
        esquema.campo("username").longitud(3, 20).patron(r'^[a-zA-Z0-9_]+$').string()
        esquema.campo("email").email()
        esquema.campo("password").password()
        esquema.campo("nombre").opcional().longitud(1, 100).string()
        esquema.campo("edad").opcional().rango(0, 150).entero()
        return esquema
    
    @staticmethod
    def login() -> EsquemaValidacion:
        esquema = EsquemaValidacion("login")
        esquema.campo("username").longitud(3, 50).string()
        esquema.campo("password").longitud(1, 100).string()
        return esquema
    
    @staticmethod
    def tarea() -> EsquemaValidacion:
        esquema = EsquemaValidacion("tarea")
        esquema.campo("titulo").longitud(1, 200).string()
        esquema.campo("descripcion").opcional().longitud(0, 5000).string()
        esquema.campo("prioridad").opcional().rango(0, 5).entero()
        esquema.campo("fecha_limite").opcional().fecha()
        esquema.campo("tags").opcional().lista()
        return esquema
    
    @staticmethod
    def configuracion() -> EsquemaValidacion:
        esquema = EsquemaValidacion("configuracion")
        esquema.campo("clave").longitud(1, 100).patron(r'^[a-z0-9_.]+$').string()
        esquema.campo("valor").string()
        esquema.campo("tipo").opcional().string()
        return esquema
    
    @staticmethod
    def evento() -> EsquemaValidacion:
        esquema = EsquemaValidacion("evento")
        esquema.campo("tipo").longitud(1, 100).string()
        esquema.campo("datos").opcional().diccionario()
        esquema.campo("origen").opcional().longitud(1, 50).string()
        esquema.campo("prioridad").opcional().rango(0, 5).entero()
        return esquema
    
    @staticmethod
    def api_key() -> EsquemaValidacion:
        esquema = EsquemaValidacion("api_key")
        esquema.campo("nombre").longitud(1, 100).string()
        esquema.campo("key").longitud(16, 256).string()
        esquema.campo("servicio").opcional().longitud(1, 50).string()
        esquema.campo("activa").opcional().booleano()
        return esquema
    
    @staticmethod
    def busqueda() -> EsquemaValidacion:
        esquema = EsquemaValidacion("busqueda")
        esquema.campo("query").longitud(1, 500).string()
        esquema.campo("fuente").opcional().string()
        esquema.campo("max_resultados").opcional().rango(1, 100).entero()
        esquema.campo("idioma").opcional().longitud(2, 5).string()
        return esquema
    
    @staticmethod
    def mensaje() -> EsquemaValidacion:
        esquema = EsquemaValidacion("mensaje")
        esquema.campo("contenido").longitud(1, 10000).string()
        esquema.campo("rol").opcional().string()
        esquema.campo("timestamp").opcional().flotante()
        esquema.campo("metadatos").opcional().diccionario()
        return esquema

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def validar(datos: Dict[str, Any], esquema: EsquemaValidacion) -> ResultadoValidacion:
    """Función rápida para validar datos contra un esquema."""
    return esquema.validar(datos)

def validar_usuario(datos: Dict[str, Any]) -> ResultadoValidacion:
    return FabricaEsquemas.usuario().validar(datos)

def validar_login(datos: Dict[str, Any]) -> ResultadoValidacion:
    return FabricaEsquemas.login().validar(datos)

def validar_tarea(datos: Dict[str, Any]) -> ResultadoValidacion:
    return FabricaEsquemas.tarea().validar(datos)

def es_email(valor: str) -> bool:
    return Validador.es_email(valor)

def es_url(valor: str) -> bool:
    return Validador.es_url(valor)

def sanitizar_texto(valor: Any) -> str:
    return Sanitizador.texto(valor)

def sanitizar_html(valor: str) -> str:
    return Sanitizador.html(valor)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE VALIDACIÓN")
    print("=" * 70)
    
    try:
        print("\n[1/6] Probando validadores unitarios...")
        print(f"  ✅ es_email('test@example.com'): {Validador.es_email('test@example.com')}")
        print(f"  ✅ es_email('invalido'): {Validador.es_email('invalido')}")
        print(f"  ✅ es_url('https://google.com'): {Validador.es_url('https://google.com')}")
        print(f"  ✅ es_url('invalido'): {Validador.es_url('invalido')}")
        print(f"  ✅ es_uuid('123e4567-e89b-12d3-a456-426614174000'): {Validador.es_uuid('123e4567-e89b-12d3-a456-426614174000')}")
        print(f"  ✅ es_color_hex('#FF5733'): {Validador.es_color_hex('#FF5733')}")
        print(f"  ✅ es_password_fuerte('Abc12345'): {Validador.es_password_fuerte('Abc12345')}")
        print(f"  ✅ es_password_fuerte('12345'): {Validador.es_password_fuerte('12345')}")
        
        print("\n[2/6] Probando sanitizadores...")
        print(f"  📍 texto('  Hola  '): '{Sanitizador.texto('  Hola  ')}'")
        print(f"  📍 email('  TEST@EXAMPLE.COM  '): '{Sanitizador.email('  TEST@EXAMPLE.COM  ')}'")
        print(f"  📍 slug('¡Hola Mundo!'): '{Sanitizador.slug('¡Hola Mundo!')}'")
        print(f"  📍 html('<script>alert(\"XSS\")</script>'): '{Sanitizador.html('<script>alert(\"XSS\")</script>')}'")
        print(f"  📍 booleano('true'): {Sanitizador.booleano('true')}")
        print(f"  📍 booleano('false'): {Sanitizador.booleano('false')}")
        
        print("\n[3/6] Probando esquema de usuario...")
        esquema = FabricaEsquemas.usuario()
        
        datos_validos = {
            "username": "usuario123",
            "email": "test@example.com",
            "password": "Abc12345",
            "nombre": "Usuario Test",
            "edad": 25
        }
        
        resultado = esquema.validar(datos_validos)
        print(f"  ✅ Datos válidos: {resultado.valido}")
        print(f"  📍 Datos sanitizados: {resultado.datos_sanitizados}")
        
        print("\n[4/6] Probando datos inválidos...")
        datos_invalidos = {
            "username": "us",
            "email": "no-es-email",
            "password": "123",
        }
        
        resultado = esquema.validar(datos_invalidos)
        print(f"  ❌ Datos válidos: {resultado.valido}")
        print(f"  📍 Errores ({len(resultado.errores)}):")
        for error in resultado.errores:
            print(f"     - {error.campo}: {error.mensaje}")
        
        print("\n[5/6] Probando esquema de login...")
        esquema_login = FabricaEsquemas.login()
        datos_login = {"username": "usuario123", "password": "miclave"}
        resultado = esquema_login.validar(datos_login)
        print(f"  ✅ Login válido: {resultado.valido}")
        
        print("\n[6/6] Probando esquema de tarea...")
        esquema_tarea = FabricaEsquemas.tarea()
        datos_tarea = {
            "titulo": "Mi tarea",
            "descripcion": "Descripción de la tarea",
            "prioridad": 3,
            "fecha_limite": "2026-12-31",
            "tags": ["importante", "urgente"]
        }
        resultado = esquema_tarea.validar(datos_tarea)
        print(f"  ✅ Tarea válida: {resultado.valido}")
        print(f"  📍 Datos validados: {resultado.datos_validados}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Validación está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")        