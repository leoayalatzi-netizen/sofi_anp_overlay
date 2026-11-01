#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio de Formateo (El Artista de los Datos)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un sistema completo de formateo
# de datos: fechas, horas, números, monedas, tamaños de archivo,
# duraciones, texto, JSON, y más. Todo localizable y personalizable.
# =====================================================================

import sys
import os
import time
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, date, time as dt_time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import unicodedata
import textwrap
import html

# =====================================================================
# ENUMERACIONES
# =====================================================================

class Idioma(Enum):
    """Idiomas soportados para formateo."""
    ESPANOL = "es"
    INGLES = "en"
    FRANCES = "fr"
    ALEMAN = "de"
    ITALIANO = "it"
    PORTUGUES = "pt"
    JAPONES = "ja"
    CHINO = "zh"
    RUSO = "ru"
    ARABE = "ar"

class FormatoFecha(Enum):
    """Formatos predefinidos para fechas."""
    CORTO = "corto"           # 23/04/2026
    LARGO = "largo"           # 23 de abril de 2026
    ISO = "iso"               # 2026-04-23
    HORA = "hora"             # 14:30
    HORA_COMPLETA = "hora_completa"  # 14:30:45
    FECHA_HORA = "fecha_hora"       # 23/04/2026 14:30
    ISO_COMPLETO = "iso_completo"   # 2026-04-23T14:30:45
    RELATIVO = "relativo"           # hace 5 minutos
    DIA_SEMANA = "dia_semana"       # jueves
    MES_ANO = "mes_ano"             # abril 2026
    PERSONALIZADO = "personalizado"

class FormatoNumero(Enum):
    """Formatos predefinidos para números."""
    ENTERO = "entero"               # 1,234,567
    DECIMAL = "decimal"             # 1,234,567.89
    MONEDA = "moneda"               # $1,234,567.89
    PORCENTAJE = "porcentaje"       # 42.5%
    CIENTIFICO = "cientifico"       # 1.23e6
    HEXADECIMAL = "hexadecimal"     # 0x12D687
    BINARIO = "binario"             # 0b100101101
    OCTAL = "octal"                 # 0o455
    ROMANO = "romano"               # MCMXCIV
    COMPACTO = "compacto"           # 1.2M

class UnidadTamaño(Enum):
    """Unidades para tamaños de datos."""
    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    TERABYTES = "TB"
    PETABYTES = "PB"
    EXABYTES = "EB"

class UnidadTiempo(Enum):
    """Unidades para duraciones."""
    MILISEGUNDOS = "ms"
    SEGUNDOS = "s"
    MINUTOS = "min"
    HORAS = "h"
    DIAS = "d"
    SEMANAS = "sem"
    MESES = "mes"
    AÑOS = "a"

# =====================================================================
# CONFIGURACIÓN DE FORMATEO
# =====================================================================

@dataclass
class ConfigFormateo:
    """Configuración global de formateo."""
    idioma: Idioma = Idioma.ESPANOL
    zona_horaria: str = "America/Mexico_City"
    separador_miles: str = ","
    separador_decimal: str = "."
    simbolo_moneda: str = "$"
    moneda_despues: bool = False
    precision_decimal: int = 2
    usar_abreviaturas: bool = True
    truncar_texto_largo: int = 100
    indentacion_json: int = 2

# =====================================================================
# LOCALIZACIONES
# =====================================================================

class Localizacion:
    """Gestor de localizaciones para formateo."""
    
    CONFIGURACIONES = {
        Idioma.ESPANOL: {
            'meses': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
            'meses_cortos': ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                            'jul', 'ago', 'sep', 'oct', 'nov', 'dic'],
            'dias': ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'],
            'dias_cortos': ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'],
            'separador_miles': '.',
            'separador_decimal': ',',
            'simbolo_moneda': '€' if Idioma.ESPANOL else '$',
            'abreviaturas': ['', 'mil', 'M', 'B', 'T'],
            'relativo_ahora': 'ahora mismo',
            'relativo_hace': 'hace {}',
            'relativo_dentro': 'dentro de {}',
        },
        Idioma.INGLES: {
            'meses': ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December'],
            'meses_cortos': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'dias': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'dias_cortos': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'separador_miles': ',',
            'separador_decimal': '.',
            'simbolo_moneda': '$',
            'abreviaturas': ['', 'K', 'M', 'B', 'T'],
            'relativo_ahora': 'just now',
            'relativo_hace': '{} ago',
            'relativo_dentro': 'in {}',
        }
    }
    
    @classmethod
    def obtener(cls, idioma: Idioma, clave: str, default: Any = None) -> Any:
        config = cls.CONFIGURACIONES.get(idioma, cls.CONFIGURACIONES[Idioma.INGLES])
        return config.get(clave, default)

# =====================================================================
# FORMATEADOR PRINCIPAL
# =====================================================================

class Formateador:
    """
    Formateador Universal de ANP.
    
    Capacidades:
    - Fechas y horas (múltiples formatos, relativo)
    - Números (decimales, moneda, porcentaje, compacto)
    - Tamaños de archivo (bytes, KB, MB, GB, TB)
    - Duraciones (ms, segundos, minutos, horas, días)
    - Texto (capitalización, truncado, wrap, slug)
    - JSON (pretty print)
    - HTML (escape, unescape)
    - Listas (conjunción: "A, B y C")
    """
    
    def __init__(self, config: ConfigFormateo = None):
        self.config = config or ConfigFormateo()
        self.loc = Localizacion()
    
    # ===== FECHAS Y HORAS =====
    
    def fecha(self, valor: Union[datetime, date, str, float], 
              formato: FormatoFecha = FormatoFecha.CORTO,
              formato_personalizado: str = None) -> str:
        """
        Formatea una fecha/hora.
        
        Args:
            valor: datetime, date, string ISO o timestamp
            formato: Formato predefinido
            formato_personalizado: strftime personalizado
            
        Returns:
            Fecha formateada
        """
        dt = self._parsear_fecha(valor)
        if dt is None:
            return str(valor)
        
        meses = self.loc.obtener(self.config.idioma, 'meses', [])
        meses_cortos = self.loc.obtener(self.config.idioma, 'meses_cortos', [])
        dias = self.loc.obtener(self.config.idioma, 'dias', [])
        
        if formato == FormatoFecha.CORTO:
            return dt.strftime("%d/%m/%Y")
        elif formato == FormatoFecha.LARGO:
            return f"{dt.day} de {meses[dt.month - 1]} de {dt.year}"
        elif formato == FormatoFecha.ISO:
            return dt.strftime("%Y-%m-%d")
        elif formato == FormatoFecha.HORA:
            return dt.strftime("%H:%M")
        elif formato == FormatoFecha.HORA_COMPLETA:
            return dt.strftime("%H:%M:%S")
        elif formato == FormatoFecha.FECHA_HORA:
            return dt.strftime("%d/%m/%Y %H:%M")
        elif formato == FormatoFecha.ISO_COMPLETO:
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif formato == FormatoFecha.DIA_SEMANA:
            return dias[dt.weekday()]
        elif formato == FormatoFecha.MES_ANO:
            return f"{meses[dt.month - 1]} {dt.year}"
        elif formato == FormatoFecha.RELATIVO:
            return self._fecha_relativa(dt)
        elif formato == FormatoFecha.PERSONALIZADO and formato_personalizado:
            return dt.strftime(formato_personalizado)
        
        return str(dt)
    
    def _parsear_fecha(self, valor: Any) -> Optional[datetime]:
        """Convierte varios tipos a datetime."""
        if isinstance(valor, datetime):
            return valor
        if isinstance(valor, date):
            return datetime.combine(valor, dt_time.min)
        if isinstance(valor, (int, float)):
            return datetime.fromtimestamp(valor)
        if isinstance(valor, str):
            try:
                return datetime.fromisoformat(valor)
            except ValueError:
                try:
                    return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        return None
    
    def _fecha_relativa(self, dt: datetime) -> str:
        """Formatea una fecha en formato relativo."""
        ahora = datetime.now()
        diff = ahora - dt if dt < ahora else dt - ahora
        es_pasado = dt < ahora
        
        if diff.total_seconds() < 60:
            texto = self.loc.obtener(self.config.idioma, 'relativo_ahora', 'ahora mismo')
            return texto
        
        unidades = [
            (31536000, 'años', 'año'),
            (2592000, 'meses', 'mes'),
            (604800, 'semanas', 'semana'),
            (86400, 'días', 'día'),
            (3600, 'horas', 'hora'),
            (60, 'minutos', 'minuto'),
        ]
        
        for segundos, plural, singular in unidades:
            valor = int(diff.total_seconds() / segundos)
            if valor >= 1:
                unidad = singular if valor == 1 else plural
                if es_pasado:
                    plantilla = self.loc.obtener(self.config.idioma, 'relativo_hace', 'hace {}')
                else:
                    plantilla = self.loc.obtener(self.config.idioma, 'relativo_dentro', 'dentro de {}')
                return plantilla.format(f"{valor} {unidad}")
        
        return str(dt)
    
    def ahora(self, formato: FormatoFecha = FormatoFecha.ISO_COMPLETO) -> str:
        """Retorna la fecha/hora actual formateada."""
        return self.fecha(datetime.now(), formato)
    
    # ===== NÚMEROS =====
    
    def numero(self, valor: Union[int, float, Decimal], 
               formato: FormatoNumero = FormatoNumero.DECIMAL,
               decimales: int = None,
               simbolo: str = None) -> str:
        """
        Formatea un número.
        
        Args:
            valor: Número a formatear
            formato: Formato predefinido
            decimales: Precisión decimal (sobrescribe config)
            simbolo: Símbolo personalizado
            
        Returns:
            Número formateado
        """
        if decimales is None:
            decimales = self.config.precision_decimal
        
        sep_miles = self.loc.obtener(self.config.idioma, 'separador_miles', ',')
        sep_dec = self.loc.obtener(self.config.idioma, 'separador_decimal', '.')
        
        if formato == FormatoNumero.ENTERO:
            return self._formatear_entero(valor, sep_miles)
        elif formato == FormatoNumero.DECIMAL:
            return self._formatear_decimal(valor, decimales, sep_miles, sep_dec)
        elif formato == FormatoNumero.MONEDA:
            simbolo = simbolo or self.loc.obtener(self.config.idioma, 'simbolo_moneda', '$')
            num = self._formatear_decimal(valor, decimales, sep_miles, sep_dec)
            return f"{simbolo}{num}" if not self.config.moneda_despues else f"{num}{simbolo}"
        elif formato == FormatoNumero.PORCENTAJE:
            pct = float(valor) * 100 if float(valor) <= 1 else float(valor)
            return f"{self._formatear_decimal(pct, decimales, sep_miles, sep_dec)}%"
        elif formato == FormatoNumero.CIENTIFICO:
            return f"{float(valor):.{decimales}e}"
        elif formato == FormatoNumero.HEXADECIMAL:
            return hex(int(valor))
        elif formato == FormatoNumero.BINARIO:
            return bin(int(valor))
        elif formato == FormatoNumero.OCTAL:
            return oct(int(valor))
        elif formato == FormatoNumero.ROMANO:
            return self._a_romano(int(valor))
        elif formato == FormatoNumero.COMPACTO:
            return self._formatear_compacto(valor, decimales, sep_dec)
        
        return str(valor)
    
    def _formatear_entero(self, valor: Any, sep_miles: str) -> str:
        """Formatea un número entero con separadores de miles."""
        num = int(float(valor))
        if num == 0:
            return "0"
        
        signo = ""
        if num < 0:
            signo = "-"
            num = abs(num)
        
        num_str = str(num)
        resultado = []
        for i, digito in enumerate(reversed(num_str)):
            if i > 0 and i % 3 == 0:
                resultado.append(sep_miles)
            resultado.append(digito)
        
        return signo + ''.join(reversed(resultado))
    
    def _formatear_decimal(self, valor: Any, decimales: int, sep_miles: str, sep_dec: str) -> str:
        """Formatea un número decimal con separadores."""
        num = float(valor)
        
        signo = ""
        if num < 0:
            signo = "-"
            num = abs(num)
        
        parte_entera = int(num)
        parte_decimal = round(num - parte_entera, decimales)
        
        entera_str = self._formatear_entero(parte_entera, sep_miles)
        if entera_str.startswith('-'):
            entera_str = entera_str[1:]
        
        if decimales > 0:
            decimal_str = f"{parte_decimal:.{decimales}f}".split('.')[1]
            return f"{signo}{entera_str}{sep_dec}{decimal_str}"
        else:
            return f"{signo}{entera_str}"
    
    def _formatear_compacto(self, valor: Any, decimales: int, sep_dec: str) -> str:
        """Formatea un número en formato compacto (1.2K, 3.4M)."""
        num = float(valor)
        abreviaturas = self.loc.obtener(self.config.idioma, 'abreviaturas', ['', 'K', 'M', 'B', 'T'])
        
        indice = 0
        while abs(num) >= 1000 and indice < len(abreviaturas) - 1:
            num /= 1000
            indice += 1
        
        if indice == 0:
            sep_miles = self.loc.obtener(self.config.idioma, 'separador_miles', ',')
            return self._formatear_entero(int(num), sep_miles)
        
        if decimales > 0:
            factor = 10 ** decimales
            num_redondeado = round(num * factor) / factor
            num_str = f"{num_redondeado:.{decimales}f}"
            return f"{num_str}{abreviaturas[indice]}"
        else:
            return f"{int(round(num))}{abreviaturas[indice]}"
    
    def _a_romano(self, num: int) -> str:
        """Convierte un número a numeración romana."""
        if num <= 0 or num >= 4000:
            return str(num)
        
        valores = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        simbolos = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        
        resultado = []
        for i, v in enumerate(valores):
            while num >= v:
                num -= v
                resultado.append(simbolos[i])
        
        return ''.join(resultado)
    
    def moneda(self, valor: Union[int, float], simbolo: str = None) -> str:
        """Formatea un valor como moneda."""
        return self.numero(valor, FormatoNumero.MONEDA, simbolo=simbolo)
    
    def porcentaje(self, valor: Union[int, float], decimales: int = 1) -> str:
        """Formatea un valor como porcentaje."""
        return self.numero(valor, FormatoNumero.PORCENTAJE, decimales=decimales)
    
    def compacto(self, valor: Union[int, float], decimales: int = 1) -> str:
        """Formatea un número en formato compacto (1.2K, 3.4M)."""
        sep_dec = self.loc.obtener(self.config.idioma, 'separador_decimal', '.')
        return self._formatear_compacto(valor, decimales, sep_dec)
    
    # ===== TAMAÑOS DE ARCHIVO =====
    
    def tamaño(self, bytes_valor: int, decimales: int = 2, 
               unidad: UnidadTamaño = None) -> str:
        """
        Formatea un tamaño en bytes a una unidad legible.
        
        Args:
            bytes_valor: Tamaño en bytes
            decimales: Precisión decimal
            unidad: Unidad específica (auto-detecta si None)
            
        Returns:
            Tamaño formateado (ej: "1.5 MB")
        """
        if unidad:
            factor = 1024 ** list(UnidadTamaño).index(unidad)
            valor = bytes_valor / factor
            return f"{self.numero(valor, decimales=decimales)} {unidad.value}"
        
        unidades = list(UnidadTamaño)
        for i, u in enumerate(unidades):
            if bytes_valor < 1024 or i == len(unidades) - 1:
                valor = bytes_valor
                return f"{self.numero(valor, decimales=decimales)} {u.value}"
            bytes_valor /= 1024
        
        return f"{bytes_valor} B"
    
    # ===== DURACIONES =====
    
    def duracion(self, segundos: float, formato: str = "auto") -> str:
        """
        Formatea una duración en segundos.
        
        Args:
            segundos: Duración en segundos
            formato: "auto", "corto" (2h 30m), "largo" (2 horas y 30 minutos)
            
        Returns:
            Duración formateada
        """
        if segundos < 0:
            return f"-{self.duracion(abs(segundos), formato)}"
        
        if segundos < 1:
            return f"{int(segundos * 1000)} ms"
        
        unidades = [
            (31536000, 'año', 'años', 'a'),
            (86400, 'día', 'días', 'd'),
            (3600, 'hora', 'horas', 'h'),
            (60, 'minuto', 'minutos', 'min'),
            (1, 'segundo', 'segundos', 's'),
        ]
        
        partes = []
        restante = segundos
        
        for factor, singular, plural, corto in unidades:
            if restante >= factor:
                valor = int(restante // factor)
                restante %= factor
                
                if formato == "corto":
                    partes.append(f"{valor}{corto}")
                else:
                    unidad_texto = singular if valor == 1 else plural
                    partes.append(f"{valor} {unidad_texto}")
        
        if formato == "corto":
            return " ".join(partes[:2])
        elif len(partes) == 1:
            return partes[0]
        elif len(partes) == 2:
            return f"{partes[0]} y {partes[1]}"
        else:
            return ", ".join(partes[:-1]) + f" y {partes[-1]}"
    
    def duracion_ms(self, milisegundos: float, formato: str = "auto") -> str:
        """Formatea una duración en milisegundos."""
        return self.duracion(milisegundos / 1000, formato)
    
    # ===== TEXTO =====
    
    def capitalizar(self, texto: str) -> str:
        """Capitaliza la primera letra de cada oración."""
        if not texto:
            return ""
        return '. '.join(s.capitalize() for s in texto.split('. '))
    
    def titulo(self, texto: str) -> str:
        """Formatea como título (primera letra de cada palabra)."""
        if not texto:
            return ""
        return texto.title()
    
    def truncar(self, texto: str, longitud: int = None, sufijo: str = "...") -> str:
        """Trunca un texto a una longitud máxima."""
        if longitud is None:
            longitud = self.config.truncar_texto_largo
        
        if not texto or len(texto) <= longitud:
            return texto
        
        return texto[:longitud - len(sufijo)] + sufijo
    
    def wrap(self, texto: str, ancho: int = 80) -> str:
        """Envuelve texto a un ancho específico."""
        return textwrap.fill(texto, width=ancho)
    
    def slug(self, texto: str, separador: str = "-") -> str:
        """
        Convierte texto a un slug URL-friendly.
        
        Ejemplo: "¡Hola Mundo!" -> "hola-mundo"
        """
        if not texto:
            return ""
        
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('ASCII')
        texto = texto.lower()
        texto = re.sub(r'[^a-z0-9]+', separador, texto)
        texto = texto.strip(separador)
        
        return texto
    
    def iniciales(self, texto: str, max_iniciales: int = 2) -> str:
        """Extrae las iniciales de un texto."""
        if not texto:
            return ""
        palabras = texto.split()
        iniciales = ''.join(p[0].upper() for p in palabras if p)
        return iniciales[:max_iniciales]
    
    # ===== JSON Y DATOS ESTRUCTURADOS =====
    
    def json_pretty(self, datos: Any, indent: int = None) -> str:
        """Formatea JSON con indentación."""
        if indent is None:
            indent = self.config.indentacion_json
        return json.dumps(datos, indent=indent, ensure_ascii=False, default=str)
    
    def json_compacto(self, datos: Any) -> str:
        """Formatea JSON sin espacios."""
        return json.dumps(datos, separators=(',', ':'), ensure_ascii=False, default=str)
    
    # ===== HTML =====
    
    def html_escape(self, texto: str) -> str:
        """Escapa caracteres HTML."""
        return html.escape(texto)
    
    def html_unescape(self, texto: str) -> str:
        """Desescapa caracteres HTML."""
        return html.unescape(texto)
    
    # ===== LISTAS =====
    
    def lista(self, items: List[Any], 
              conjuncion: str = None,
              formateador_item: Callable[[Any], str] = str) -> str:
        """
        Formatea una lista con conjunción.
        
        Ejemplo: ["A", "B", "C"] -> "A, B y C"
        """
        if not items:
            return ""
        
        if conjuncion is None:
            if self.config.idioma == Idioma.ESPANOL:
                conjuncion = "y"
            else:
                conjuncion = "and"
        
        formateados = [formateador_item(i) for i in items]
        
        if len(formateados) == 1:
            return formateados[0]
        elif len(formateados) == 2:
            return f"{formateados[0]} {conjuncion} {formateados[1]}"
        else:
            return f"{', '.join(formateados[:-1])} {conjuncion} {formateados[-1]}"
    
    def lista_numerada(self, items: List[Any], 
                       formateador_item: Callable[[Any], str] = str) -> str:
        """Formatea una lista numerada."""
        return "\n".join(f"{i+1}. {formateador_item(item)}" for i, item in enumerate(items))
    
    def lista_viñetas(self, items: List[Any], 
                      viñeta: str = "•",
                      formateador_item: Callable[[Any], str] = str) -> str:
        """Formatea una lista con viñetas."""
        return "\n".join(f"{viñeta} {formateador_item(item)}" for item in items)
    
    # ===== DIRECCIONES Y CONTACTO =====
    
    def telefono(self, numero: str, formato: str = "nacional") -> str:
        """
        Formatea un número de teléfono.
        
        Ejemplo: "+52551234567" -> "+52 55 1234 5678"
        """
        limpio = re.sub(r'[^\d+]', '', numero)
        
        if len(limpio) == 10:
            return f"({limpio[:3]}) {limpio[3:6]}-{limpio[6:]}"
        elif len(limpio) == 12 and limpio.startswith('+'):
            return f"{limpio[:3]} {limpio[3:5]} {limpio[5:9]} {limpio[9:]}"
        
        return numero
    
    # ===== TABLAS =====
    
    def tabla(self, datos: List[Dict[str, Any]], 
              columnas: List[str] = None,
              titulos: Dict[str, str] = None) -> str:
        """
        Formatea una lista de diccionarios como tabla ASCII.
        """
        if not datos:
            return ""
        
        if columnas is None:
            columnas = list(datos[0].keys())
        
        titulos = titulos or {c: c for c in columnas}
        
        anchos = {c: len(titulos.get(c, c)) for c in columnas}
        for fila in datos:
            for c in columnas:
                valor = str(fila.get(c, ''))
                anchos[c] = max(anchos[c], len(valor))
        
        separador = "+" + "+".join("-" * (anchos[c] + 2) for c in columnas) + "+"
        
        lineas = [separador]
        
        cabecera = "|" + "|".join(f" {titulos.get(c, c).ljust(anchos[c])} " for c in columnas) + "|"
        lineas.append(cabecera)
        lineas.append(separador)
        
        for fila in datos:
            linea = "|" + "|".join(f" {str(fila.get(c, '')).ljust(anchos[c])} " for c in columnas) + "|"
            lineas.append(linea)
        
        lineas.append(separador)
        
        return "\n".join(lineas)


# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

_formateador_global: Optional[Formateador] = None

def obtener_formateador(idioma: Idioma = Idioma.ESPANOL) -> Formateador:
    """Obtiene la instancia global del formateador."""
    global _formateador_global
    if _formateador_global is None:
        config = ConfigFormateo(idioma=idioma)
        _formateador_global = Formateador(config)
    return _formateador_global

def fecha(valor: Any, formato: FormatoFecha = FormatoFecha.CORTO) -> str:
    return obtener_formateador().fecha(valor, formato)

def numero(valor: Any, formato: FormatoNumero = FormatoNumero.DECIMAL) -> str:
    return obtener_formateador().numero(valor, formato)

def moneda(valor: Any) -> str:
    return obtener_formateador().moneda(valor)

def tamaño(bytes_valor: int) -> str:
    return obtener_formateador().tamaño(bytes_valor)

def duracion(segundos: float) -> str:
    return obtener_formateador().duracion(segundos)

def slug(texto: str) -> str:
    return obtener_formateador().slug(texto)

def lista(items: List[Any]) -> str:
    return obtener_formateador().lista(items)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL SISTEMA DE FORMATEO")
    print("=" * 70)
    
    fmt = Formateador(ConfigFormateo(idioma=Idioma.ESPANOL))
    
    try:
        print("\n[1/6] Probando formateo de fechas...")
        ahora = datetime.now()
        print(f"  📍 Corto: {fmt.fecha(ahora, FormatoFecha.CORTO)}")
        print(f"  📍 Largo: {fmt.fecha(ahora, FormatoFecha.LARGO)}")
        print(f"  📍 ISO: {fmt.fecha(ahora, FormatoFecha.ISO)}")
        print(f"  📍 Hora: {fmt.fecha(ahora, FormatoFecha.HORA)}")
        print(f"  📍 Relativo (ahora): {fmt.fecha(ahora, FormatoFecha.RELATIVO)}")
        print(f"  📍 Relativo (ayer): {fmt.fecha(ahora - timedelta(days=1), FormatoFecha.RELATIVO)}")
        
        print("\n[2/6] Probando formateo de números...")
        print(f"  📍 Entero: {fmt.numero(1234567, FormatoNumero.ENTERO)}")
        print(f"  📍 Decimal: {fmt.numero(1234567.89, FormatoNumero.DECIMAL)}")
        print(f"  📍 Moneda: {fmt.numero(1234567.89, FormatoNumero.MONEDA)}")
        print(f"  📍 Porcentaje: {fmt.numero(0.425, FormatoNumero.PORCENTAJE)}")
        print(f"  📍 Compacto: {fmt.numero(1234567, FormatoNumero.COMPACTO)}")
        print(f"  📍 Romano: {fmt.numero(1994, FormatoNumero.ROMANO)}")
        print(f"  📍 Hexadecimal: {fmt.numero(255, FormatoNumero.HEXADECIMAL)}")
        
        print("\n[3/6] Probando tamaños de archivo...")
        print(f"  📍 500 B: {fmt.tamaño(500)}")
        print(f"  📍 1.5 KB: {fmt.tamaño(1536)}")
        print(f"  📍 2 MB: {fmt.tamaño(2 * 1024 * 1024)}")
        print(f"  📍 1 GB: {fmt.tamaño(1024 * 1024 * 1024)}")
        
        print("\n[4/6] Probando duraciones...")
        print(f"  📍 30s: {fmt.duracion(30)}")
        print(f"  📍 90s: {fmt.duracion(90)}")
        print(f"  📍 1h 30min: {fmt.duracion(5400)}")
        print(f"  📍 2 días: {fmt.duracion(172800)}")
        print(f"  📍 Corto (2d 3h): {fmt.duracion(183600, formato='corto')}")
        
        print("\n[5/6] Probando formateo de texto...")
        print(f"  📍 Slug: {fmt.slug('¡Hola Mundo! ¿Cómo estás?')}")
        print(f"  📍 Iniciales: {fmt.iniciales('Arquitectura Neuronal Profunda')}")
        print(f"  📍 Truncar: {fmt.truncar('Este es un texto muy largo que será truncado', 30)}")
        print(f"  📍 Capitalizar: {fmt.capitalizar('hola mundo. esto es una prueba.')}")
        print(f"  📍 HTML escape: {fmt.html_escape('<script>alert("XSS")</script>')}")
        
        print("\n[6/6] Probando listas...")
        print(f"  📍 Lista simple: {fmt.lista(['manzanas', 'peras', 'plátanos'])}")
        print(f"  📍 Lista 2 items: {fmt.lista(['A', 'B'])}")
        print(f"  📍 Lista 1 item: {fmt.lista(['Solo'])}")
        print(f"  📍 Lista numerada:\n{fmt.lista_numerada(['Primero', 'Segundo', 'Tercero'])}")
        
        print("\n" + "=" * 70)
        print("   RESUMEN DE FORMATOS")
        print("=" * 70)
        print(f"  🎨 Formateador configurado en: {fmt.config.idioma.value.upper()}")
        print(f"  📅 5 formatos de fecha")
        print(f"  🔢 10 formatos de número")
        print(f"  💾 6 unidades de tamaño")
        print(f"  ⏱️ 7 unidades de tiempo")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Sistema de Formateo está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70 + "\n")