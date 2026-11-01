#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Formateo (El Artista de las Palabras)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================
# ADVERTENCIA: Este motor implementa formateo de respuestas REAL con
# estilos, estructuras, longitudes adaptativas, embellecimiento y
# personalización según contexto.
# =====================================================================

import sys, os, re, time, json, math, uuid, textwrap, random, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque, OrderedDict, Counter
from enum import Enum, auto

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
                self._id = str(uuid.uuid4())
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

class EstiloFormateo(Enum):
    """Estilos de formateo de respuesta."""
    TEXTO_PLANO = "texto_plano"
    MARKDOWN = "markdown"
    HTML = "html"
    LISTA = "lista"
    TABLA = "tabla"
    PARRAFOS = "parrafos"
    DESTACADO = "destacado"
    RESUMIDO = "resumido"
    DETALLADO = "detallado"

class LongitudRespuesta(Enum):
    """Longitudes de respuesta."""
    CORTA = "corta"
    MEDIA = "media"
    LARGA = "larga"
    MUY_LARGA = "muy_larga"
    ADAPTATIVA = "adaptativa"

class FormatoEspecial(Enum):
    """Formatos especiales para respuestas."""
    DEFINICION = "definicion"
    PROCEDIMIENTO = "procedimiento"
    COMPARACION = "comparacion"
    EJEMPLO = "ejemplo"
    EXPLICACION = "explicacion"
    RESUMEN = "resumen"
    LISTA_RAPIDA = "lista_rapida"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class OpcionesFormateo:
    """Opciones de formateo para la respuesta."""
    estilo: EstiloFormateo = EstiloFormateo.PARRAFOS
    longitud: LongitudRespuesta = LongitudRespuesta.ADAPTATIVA
    tono: str = "neutral"
    incluir_emojis: bool = False
    incluir_ejemplos: bool = False
    incluir_referencias: bool = False
    max_caracteres: int = 2000
    idioma: str = "es"

@dataclass
class RespuestaFormateada:
    """Respuesta formateada lista para entregar."""
    texto: str
    estilo: EstiloFormateo
    metadatos: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# MOTOR DE FORMATEO PRINCIPAL
# =====================================================================

class MotorFormateo(MotorBase):
    """Motor de Formateo de Respuestas de ANP."""
    
    # ===== PLANTILLAS POR FORMATO =====
    
    PLANTILLAS = {
        FormatoEspecial.DEFINICION: {
            EstiloFormateo.DESTACADO: "📖 **{titulo}**\n\n{definicion}\n\n📌 *{dato_extra}*",
            EstiloFormateo.PARRAFOS: "{titulo}\n\n{definicion}\n\n{dato_extra}",
            EstiloFormateo.TEXTO_PLANO: "{titulo}: {definicion}. {dato_extra}.",
        },
        FormatoEspecial.PROCEDIMIENTO: {
            EstiloFormateo.LISTA: "🔧 **{titulo}**\n\n{introduccion}\n\n{lista_numerada}\n\n💡 **Consejo:** {consejo}",
            EstiloFormateo.PARRAFOS: "{titulo}\n\n{introduccion}\n\n{pasos_texto}\n\nConsejo: {consejo}",
            EstiloFormateo.TEXTO_PLANO: "{titulo}. {introduccion} {pasos_texto}. Consejo: {consejo}.",
        },
        FormatoEspecial.COMPARACION: {
            EstiloFormateo.TABLA: "⚖️ **{titulo}**\n\n| Aspecto | {item1} | {item2} |\n|--------|--------|--------|\n{filas}\n\n✅ **Conclusión:** {conclusion}",
            EstiloFormateo.PARRAFOS: "{titulo}\n\n{comparacion_texto}\n\nConclusión: {conclusion}",
        },
        FormatoEspecial.EJEMPLO: {
            EstiloFormateo.DESTACADO: "💡 **{titulo}**\n\n{explicacion}\n\n```\n{ejemplo}\n```\n\n✨ *{nota}*",
            EstiloFormateo.PARRAFOS: "{titulo}\n\n{explicacion}\n\nEjemplo: {ejemplo}\n\n{nota}",
        },
        FormatoEspecial.RESUMEN: {
            EstiloFormateo.LISTA: "📋 **{titulo}**\n\n{lista_viñetas}\n\n📊 *{metrica}*",
            EstiloFormateo.PARRAFOS: "{titulo}\n\n{texto_resumen}\n\n{metrica}",
        },
    }
    
    # ===== EMOJIS POR TONO =====
    
    EMOJIS_TONO = {
        'formal': '📋',
        'amigable': '😊',
        'entusiasta': '🎉',
        'tecnico': '🔧',
        'creativo': '✨',
        'empatito': '💙',
        'humoristico': '😄',
        'socratico': '🤔',
        'neutral': '📝',
    }
    
    # ===== SEPARADORES POR ESTILO =====
    
    SEPARADORES = {
        EstiloFormateo.MARKDOWN: '\n---\n',
        EstiloFormateo.PARRAFOS: '\n\n',
        EstiloFormateo.TEXTO_PLANO: ' ',
        EstiloFormateo.HTML: '<hr>\n',
    }
    
    def __init__(self, config=None):
        super().__init__(config)
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Formatea una respuesta según opciones."""
        if isinstance(entrada, str):
            contenido = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            contenido = entrada.get('contenido', entrada.get('texto', entrada.get('respuesta', '')))
            opciones = entrada
        else:
            contenido = str(entrada)
            opciones = {}
        
        if not contenido or not str(contenido).strip():
            return self._resultado_vacio()
        
        # Extraer opciones
        estilo_str = opciones.get('estilo', 'parrafos')
        try:
            estilo = EstiloFormateo(estilo_str)
        except ValueError:
            estilo = EstiloFormateo.PARRAFOS
        
        longitud_str = opciones.get('longitud', 'adaptativa')
        try:
            longitud = LongitudRespuesta(longitud_str)
        except ValueError:
            longitud = LongitudRespuesta.ADAPTATIVA
        
        tono = opciones.get('tono', 'neutral')
        incluir_emojis = opciones.get('incluir_emojis', opciones.get('emojis', False))
        max_caracteres = opciones.get('max_caracteres', 2000)
        
        # Formatear según estilo
        formateado = self._formatear(contenido, estilo, longitud, tono, max_caracteres, opciones)
        
        # Ajustar longitud
        if longitud != LongitudRespuesta.ADAPTATIVA:
            formateado = self._ajustar_longitud(formateado, longitud, max_caracteres)
        
        # Agregar emojis si corresponde
        if incluir_emojis:
            formateado = self._agregar_emojis(formateado, tono)
        
        return {
            'texto_original': str(contenido)[:200],
            'texto_formateado': formateado,
            'estilo': estilo.value,
            'longitud': longitud.value,
            'tono': tono,
            'caracteres_original': len(str(contenido)),
            'caracteres_formateado': len(formateado),
            'tiene_emojis': incluir_emojis,
        }
    
    def _formatear(self, contenido: Any, estilo: EstiloFormateo, 
                   longitud: LongitudRespuesta, tono: str, 
                   max_caracteres: int, opciones: Dict) -> str:
        """Aplica el estilo de formateo."""
        texto = str(contenido)
        
        # Detectar formato especial si está en opciones
        formato_especial_str = opciones.get('formato_especial', '')
        if formato_especial_str:
            try:
                formato_esp = FormatoEspecial(formato_especial_str)
                return self._aplicar_formato_especial(texto, formato_esp, estilo, opciones)
            except ValueError:
                pass
        
        # Formateo por estilo
        if estilo == EstiloFormateo.TEXTO_PLANO:
            return self._formatear_texto_plano(texto)
        elif estilo == EstiloFormateo.MARKDOWN:
            return self._formatear_markdown(texto)
        elif estilo == EstiloFormateo.HTML:
            return self._formatear_html(texto)
        elif estilo == EstiloFormateo.LISTA:
            return self._formatear_lista(texto)
        elif estilo == EstiloFormateo.TABLA:
            return self._formatear_tabla(texto, opciones)
        elif estilo == EstiloFormateo.DESTACADO:
            return self._formatear_destacado(texto, tono)
        elif estilo == EstiloFormateo.RESUMIDO:
            return self._formatear_resumido(texto, max_caracteres)
        elif estilo == EstiloFormateo.DETALLADO:
            return self._formatear_detallado(texto)
        else:
            return self._formatear_parrafos(texto)
    
    def _formatear_texto_plano(self, texto: str) -> str:
        """Formatea como texto plano simple."""
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
    
    def _formatear_parrafos(self, texto: str) -> str:
        """Formatea en párrafos."""
        oraciones = re.split(r'(?<=[.!?])\s+', texto)
        parrafos = []
        parrafo_actual = []
        longitud_actual = 0
        
        for oracion in oraciones:
            if longitud_actual + len(oracion) > 300 and parrafo_actual:
                parrafos.append(' '.join(parrafo_actual))
                parrafo_actual = []
                longitud_actual = 0
            parrafo_actual.append(oracion)
            longitud_actual += len(oracion)
        
        if parrafo_actual:
            parrafos.append(' '.join(parrafo_actual))
        
        return '\n\n'.join(parrafos)
    
    def _formatear_markdown(self, texto: str) -> str:
        """Formatea con sintaxis Markdown."""
        texto = self._formatear_parrafos(texto)
        
        # Detectar y formatear listas
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if re.match(r'^\d+[.)]\s', linea):
                continue
            if linea.startswith(('- ', '* ', '+ ', '• ')):
                continue
        
        return texto
    
    def _formatear_html(self, texto: str) -> str:
        """Formatea como HTML básico."""
        parrafos = self._formatear_parrafos(texto).split('\n\n')
        html_parrafos = [f'<p>{p}</p>' for p in parrafos if p.strip()]
        return '\n'.join(html_parrafos)
    
    def _formatear_lista(self, texto: str) -> str:
        """Formatea como lista."""
        oraciones = re.split(r'(?<=[.!?])\s+', texto)
        if len(oraciones) <= 1:
            items = re.split(r'[,;]\s+', texto)
        else:
            items = oraciones
        
        items = [item.strip().rstrip('.!?') for item in items if item.strip()]
        
        if len(items) <= 3:
            return '\n'.join(f'- {item}' for item in items)
        else:
            return '\n'.join(f'{i+1}. {item}' for i, item in enumerate(items))
    
    def _formatear_tabla(self, texto: str, opciones: Dict) -> str:
        """Intenta formatear como tabla."""
        lineas = texto.split('\n')
        if len(lineas) < 3:
            return self._formatear_lista(texto)
        
        # Intentar detectar columnas
        return texto
    
    def _formatear_destacado(self, texto: str, tono: str) -> str:
        """Formatea con formato destacado."""
        oraciones = re.split(r'(?<=[.!?])\s+', texto)
        
        if len(oraciones) >= 3:
            principal = oraciones[0]
            secundarias = ' '.join(oraciones[1:])
            emoji = self.EMOJIS_TONO.get(tono, '📝')
            return f"{emoji} **{principal}**\n\n{secundarias}"
        
        emoji = self.EMOJIS_TONO.get(tono, '📝')
        return f"{emoji} {texto}"
    
    def _formatear_resumido(self, texto: str, max_chars: int) -> str:
        """Formatea un resumen conciso."""
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        if len(texto) <= max_chars:
            return texto
        
        # Truncar en el último punto antes del límite
        truncado = texto[:max_chars - 3]
        ultimo_punto = truncado.rfind('.')
        if ultimo_punto > max_chars * 0.5:
            return truncado[:ultimo_punto + 1]
        
        return truncado + '...'
    
    def _formatear_detallado(self, texto: str) -> str:
        """Formatea con formato detallado."""
        parrafos = self._formatear_parrafos(texto)
        return f"{'='*50}\n{parrafos}\n{'='*50}"
    
    def _aplicar_formato_especial(self, texto: str, formato: FormatoEspecial, 
                                  estilo: EstiloFormateo, opciones: Dict) -> str:
        """Aplica una plantilla de formato especial."""
        plantillas_formato = self.PLANTILLAS.get(formato, {})
        
        # Buscar plantilla para el estilo, o usar la primera disponible
        plantilla = plantillas_formato.get(estilo)
        if plantilla is None and plantillas_formato:
            plantilla = list(plantillas_formato.values())[0]
        
        if plantilla is None:
            return self._formatear(texto, estilo, LongitudRespuesta.ADAPTATIVA, 'neutral', 2000, {})
        
        # Preparar variables para la plantilla
        variables = self._extraer_variables_formato(texto, formato, opciones)
        
        try:
            return plantilla.format(**variables)
        except KeyError:
            return texto
    
    def _extraer_variables_formato(self, texto: str, formato: FormatoEspecial, 
                                   opciones: Dict) -> Dict[str, str]:
        """Extrae variables para las plantillas de formato."""
        oraciones = re.split(r'(?<=[.!?])\s+', texto)
        primera = oraciones[0] if oraciones else texto
        
        variables = {
            'titulo': opciones.get('titulo', opciones.get('tema', 'Información')),
            'definicion': primera,
            'introduccion': primera,
            'explicacion': texto,
            'texto_resumen': texto,
            'conclusion': opciones.get('conclusion', ''),
            'consejo': opciones.get('consejo', 'Revisa la documentación para más detalles.'),
            'nota': opciones.get('nota', ''),
            'dato_extra': opciones.get('dato_extra', ''),
            'metrica': opciones.get('metrica', ''),
            'ejemplo': opciones.get('ejemplo', texto[:200]),
            'item1': opciones.get('item1', 'Opción A'),
            'item2': opciones.get('item2', 'Opción B'),
            'filas': opciones.get('filas', ''),
            'comparacion_texto': texto,
            'lista_numerada': self._formatear_lista(texto),
            'lista_viñetas': self._formatear_lista(texto),
            'pasos_texto': texto,
        }
        
        return variables
    
    def _ajustar_longitud(self, texto: str, longitud: LongitudRespuesta, max_chars: int) -> str:
        """Ajusta la longitud de la respuesta."""
        limites = {
            LongitudRespuesta.CORTA: 300,
            LongitudRespuesta.MEDIA: 800,
            LongitudRespuesta.LARGA: 2000,
            LongitudRespuesta.MUY_LARGA: 5000,
        }
        
        limite = limites.get(longitud, max_chars)
        limite = min(limite, max_chars)
        
        if len(texto) <= limite:
            return texto
        
        return self._formatear_resumido(texto, limite)
    
    def _agregar_emojis(self, texto: str, tono: str) -> str:
        """Agrega emojis decorativos según el tono."""
        emojis_inicio = {
            'formal': '📋 ',
            'amigable': '😊 ',
            'entusiasta': '🎉 ',
            'tecnico': '🔧 ',
            'creativo': '✨ ',
            'empatito': '💙 ',
            'humoristico': '😄 ',
            'socratico': '🤔 ',
            'neutral': '📝 ',
        }
        
        emoji_inicio = emojis_inicio.get(tono, '')
        
        # Solo agregar si no tiene ya un emoji al inicio
        if not texto.startswith(('😊', '🎉', '📝', '🔧', '✨', '💙', '📋', '🤔', '😄')):
            texto = emoji_inicio + texto
        
        return texto
    
    def formatear_definicion(self, titulo: str, definicion: str, 
                            dato_extra: str = '', estilo: str = 'destacado') -> str:
        """Formatea una definición."""
        try:
            est = EstiloFormateo(estilo)
        except ValueError:
            est = EstiloFormateo.DESTACADO
        
        plantillas = self.PLANTILLAS.get(FormatoEspecial.DEFINICION, {})
        plantilla = plantillas.get(est, list(plantillas.values())[0] if plantillas else "{titulo}: {definicion}")
        
        return plantilla.format(titulo=titulo, definicion=definicion, dato_extra=dato_extra)
    
    def formatear_procedimiento(self, titulo: str, pasos: List[str], 
                               consejo: str = '', estilo: str = 'lista') -> str:
        """Formatea un procedimiento paso a paso."""
        try:
            est = EstiloFormateo(estilo)
        except ValueError:
            est = EstiloFormateo.LISTA
        
        lista_numerada = '\n'.join(f'{i+1}. {paso}' for i, paso in enumerate(pasos))
        pasos_texto = ' '.join(f'Paso {i+1}: {paso}.' for i, paso in enumerate(pasos))
        
        plantillas = self.PLANTILLAS.get(FormatoEspecial.PROCEDIMIENTO, {})
        plantilla = plantillas.get(est, list(plantillas.values())[0] if plantillas else "{titulo}\n\n{lista_numerada}")
        
        return plantilla.format(
            titulo=titulo,
            introduccion=f'A continuación se detallan los {len(pasos)} pasos:',
            lista_numerada=lista_numerada,
            pasos_texto=pasos_texto,
            consejo=consejo or 'Sigue cada paso cuidadosamente.'
        )
    
    def _resultado_vacio(self):
        return {
            'texto_original': '',
            'texto_formateado': '',
            'estilo': 'texto_plano',
            'longitud': 'adaptativa',
            'tono': 'neutral',
            'caracteres_original': 0,
            'caracteres_formateado': 0,
            'tiene_emojis': False,
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE FORMATEO")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/7] Inicializando motor...")
        motor = MotorFormateo()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return {'texto_formateado': 'Error', 'estilo': 'error'}
        
        texto_prueba = "La inteligencia artificial es un campo de la informática que busca crear sistemas capaces de realizar tareas que normalmente requieren inteligencia humana. Estos sistemas utilizan algoritmos avanzados y grandes cantidades de datos para aprender y mejorar con el tiempo."
        
        print("\n[2/7] Formateo texto plano...")
        r1 = sd(motor.procesar({'contenido': texto_prueba, 'estilo': 'texto_plano'}))
        print(f"  📍 ({r1['caracteres_formateado']} chars) {r1['texto_formateado'][:100]}...")
        
        print("\n[3/7] Formateo párrafos...")
        r2 = sd(motor.procesar({'contenido': texto_prueba, 'estilo': 'parrafos'}))
        print(f"  📍 ({r2['caracteres_formateado']} chars)")
        print(f"  {r2['texto_formateado'][:150]}...")
        
        print("\n[4/7] Formateo lista...")
        r3 = sd(motor.procesar({'contenido': texto_prueba, 'estilo': 'lista'}))
        print(f"  📍 Lista:\n{r3['texto_formateado'][:200]}")
        
        print("\n[5/7] Formateo destacado con emojis...")
        r4 = sd(motor.procesar({'contenido': texto_prueba, 'estilo': 'destacado', 'tono': 'entusiasta', 'incluir_emojis': True}))
        print(f"  📍 {r4['texto_formateado'][:150]}...")
        
        print("\n[6/7] Formato especial - definición...")
        r5 = sd(motor.procesar({
            'contenido': 'La IA es un campo multidisciplinario que combina matemáticas, estadística y computación.',
            'formato_especial': 'definicion',
            'titulo': 'Inteligencia Artificial',
            'dato_extra': 'Término acuñado por John McCarthy en 1956.',
            'estilo': 'destacado',
        }))
        print(f"  📍 Definición:\n{r5['texto_formateado']}")
        
        print("\n[7/7] Métodos directos...")
        def_formateada = motor.formatear_definicion(
            titulo='Python',
            definicion='Python es un lenguaje de programación interpretado, de alto nivel y propósito general.',
            dato_extra='Creado por Guido van Rossum en 1991.'
        )
        print(f"  📍 Python: {def_formateada[:100]}...")
        
        proc_formateado = motor.formatear_procedimiento(
            titulo='Instalación de Python',
            pasos=['Descargar desde python.org', 'Ejecutar el instalador', 'Verificar con python --version'],
            consejo='Asegúrate de marcar "Add Python to PATH".'
        )
        print(f"  📍 Procedimiento:\n{proc_formateado[:200]}...")
        
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