#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor de Entidades (El Cartógrafo de la Realidad)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Comunicación
# =====================================================================

import sys, os, re, time, json, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
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
                self._id = str(__import__('uuid').uuid4())
                self.nombre = self.__class__.__name__
                self._estado = EstadoMotor.NO_INICIALIZADO
                self.config = config or ConfiguracionMotor()
            @property
            def estado(self): return self._estado
            def inicializar(self):
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

class TipoEntidad(Enum):
    PERSONA = "persona"
    ORGANIZACION = "organizacion"
    LUGAR = "lugar"
    FECHA = "fecha"
    HORA = "hora"
    DINERO = "dinero"
    PORCENTAJE = "porcentaje"
    EMAIL = "email"
    URL = "url"
    TELEFONO = "telefono"
    IP = "ip"
    DNI = "dni"
    ISBN = "isbn"
    COLOR_HEX = "color_hex"
    DESCONOCIDO = "desconocido"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class EntidadDetectada:
    texto: str
    tipo: TipoEntidad
    posicion_inicio: int
    posicion_fin: int
    confianza: float = 1.0
    normalizado: str = ""
    metadatos: Dict[str, Any] = field(default_factory=dict)

# =====================================================================
# MOTOR DE ENTIDADES PRINCIPAL
# =====================================================================

class MotorEntidades(MotorBase):
    """Motor de Extracción de Entidades Nombradas de ANP."""
    
    # ===== PATRONES (VERIFICADOS - SIN ERRORES DE SINTAXIS) =====
    
    def _compilar_patrones(self):
        """Compila todos los patrones regex. Se llama en inicializar."""
        self._patrones_compilados = {}
        
        # Email
        self._patrones_compilados[TipoEntidad.EMAIL] = {
            'patron': re.compile(r'\b([A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.[A-Za-z]{2,})\b'),
            'confianza': 0.99,
            'normalizar': lambda x: x.lower(),
        }
        
        # URL
        self._patrones_compilados[TipoEntidad.URL] = {
            'patron': re.compile(r'(https?://[^\s<>\"\'\[\]{}|\\^`]+|www\.[^\s<>\"\'\[\]{}|\\^`]+)'),
            'confianza': 0.95,
            'normalizar': lambda x: x.lower().rstrip('.,;:!?()[]\'\"'),
        }
        
        # IP
        self._patrones_compilados[TipoEntidad.IP] = {
            'patron': re.compile(r'\b((?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?))\b'),
            'confianza': 0.98,
            'normalizar': lambda x: x,
        }
        
        # Fechas
        self._patrones_compilados[TipoEntidad.FECHA] = {
            'patrones': [
                re.compile(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b'),
                re.compile(r'\b(\d{4}-\d{1,2}-\d{1,2})\b'),
            ],
            'confianza': 0.95,
            'normalizar': lambda x: x,
        }
        
        # Hora
        self._patrones_compilados[TipoEntidad.HORA] = {
            'patron': re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\b'),
            'confianza': 0.93,
            'normalizar': lambda x: x.upper().strip(),
        }
        
        # Dinero
        self._patrones_compilados[TipoEntidad.DINERO] = {
            'patron': re.compile(r'([\$\€\£\¥]\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?\s*(?:USD|EUR|GBP|MXN|ARS)?)'),
            'confianza': 0.88,
            'normalizar': lambda x: re.sub(r'\s+', ' ', x).strip(),
        }
        
        # Porcentaje
        self._patrones_compilados[TipoEntidad.PORCENTAJE] = {
            'patron': re.compile(r'\b(\d{1,3}(?:[.,]\d{1,2})?\s*%)\b'),
            'confianza': 0.96,
            'normalizar': lambda x: x.replace(' ', ''),
        }
        
        # Teléfono
        self._patrones_compilados[TipoEntidad.TELEFONO] = {
            'patron': re.compile(r'(\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9})'),
            'confianza': 0.85,
            'normalizar': lambda x: re.sub(r'[\s.-]', '', x),
        }
        
        # DNI
        self._patrones_compilados[TipoEntidad.DNI] = {
            'patron': re.compile(r'\b(\d{8}[A-Za-z])\b'),
            'confianza': 0.80,
            'normalizar': lambda x: x.upper(),
        }
        
        # ISBN
        self._patrones_compilados[TipoEntidad.ISBN] = {
            'patron': re.compile(r'\b(ISBN(?:-13|-10)?\s*:?\s*(?:\d[- ]?){9,12}[\dXx])\b'),
            'confianza': 0.90,
            'normalizar': lambda x: re.sub(r'\s+', ' ', x).upper(),
        }
        
        # Color HEX
        self._patrones_compilados[TipoEntidad.COLOR_HEX] = {
            'patron': re.compile(r'(#[A-Fa-f0-9]{3,8})\b'),
            'confianza': 0.97,
            'normalizar': lambda x: x.upper(),
        }
    
    # ===== DICCIONARIOS =====
    
    NOMBRES_PROPIOS = {
        'Juan', 'María', 'José', 'Luis', 'Carlos', 'Ana', 'Pedro', 'Miguel',
        'Laura', 'Carmen', 'Francisco', 'Jesús', 'David', 'Javier', 'Sofía',
        'Diego', 'Alejandro', 'Adriana', 'Fernando', 'Gabriela', 'Ricardo',
        'Patricia', 'Roberto', 'Daniela', 'Elon Musk', 'Satya Nadella',
        'Bill Gates', 'Steve Jobs', 'Barack Obama', 'Joe Biden',
    }
    
    ORGANIZACIONES = {
        'Microsoft', 'Apple', 'Google', 'Amazon', 'Facebook', 'Twitter',
        'NASA', 'ONU', 'UNESCO', 'OTAN', 'Tesla', 'OpenAI', 'Anthropic',
        'Netflix', 'Spotify', 'YouTube', 'Instagram', 'WhatsApp',
        'Banco Mundial', 'Naciones Unidas', 'Cruz Roja', 'Unión Europea',
    }
    
    LUGARES = {
        'Madrid', 'Barcelona', 'México', 'España', 'Argentina', 'Lima',
        'Bogotá', 'Santiago', 'Buenos Aires', 'París', 'Londres',
        'Nueva York', 'Tokyo', 'Berlín', 'Roma', 'Brasil', 'Chile',
        'Colombia', 'Perú', 'Francia', 'Alemania', 'Italia', 'Japón',
    }
    
    FALSOS_NOMBRES = {
        'el', 'la', 'los', 'las', 'un', 'una', 'the', 'a', 'an', 'in',
        'on', 'at', 'of', 'and', 'or', 'but', 'with', 'for', 'from', 'to',
        'by', 'is', 'are', 'was', 'were', 'this', 'that', 'these', 'those',
        'it', 'he', 'she', 'they', 'we', 'you', 'i', 'me', 'my', 'no', 'not',
        'que', 'qué', 'cual', 'cuál', 'quien', 'quién', 'como', 'cómo',
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        self._patrones_compilados = {}
    
    def inicializar(self):
        """Inicializa el motor y compila patrones."""
        self._compilar_patrones()
        return super().inicializar()
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        """Extrae entidades nombradas del texto."""
        try:
            if isinstance(entrada, str):
                texto = entrada
            elif isinstance(entrada, dict):
                texto = entrada.get('texto', entrada.get('text', ''))
            else:
                texto = str(entrada)
            
            if not texto or not texto.strip():
                return self._resultado_vacio(texto or '')
            
            entidades = []
            posiciones_ocupadas = set()
            
            # Extraer por patrones regex
            for tipo, datos in self._patrones_compilados.items():
                if 'patron' in datos:
                    self._extraer_patron(texto, tipo, datos['patron'], 
                                        datos['confianza'], datos.get('normalizar'),
                                        entidades, posiciones_ocupadas)
                elif 'patrones' in datos:
                    for p in datos['patrones']:
                        self._extraer_patron(texto, tipo, p, datos['confianza'],
                                            datos.get('normalizar'), entidades, posiciones_ocupadas)
            
            # Extraer nombres propios
            self._extraer_nombres(texto, entidades, posiciones_ocupadas)
            
            # Ordenar
            entidades.sort(key=lambda e: (e.posicion_inicio, -e.confianza))
            
            # Agrupar por tipo
            por_tipo = defaultdict(list)
            for e in entidades:
                por_tipo[e.tipo.value].append(e.texto)
            
            # Resumen
            partes = []
            for t in sorted(por_tipo):
                unicos = list(dict.fromkeys(por_tipo[t]))[:3]
                partes.append(f"{t}: {', '.join(unicos)}")
            
            return {
                'texto_original': texto,
                'entidades': [{
                    'texto': e.texto, 'tipo': e.tipo.value,
                    'posicion_inicio': e.posicion_inicio,
                    'posicion_fin': e.posicion_fin,
                    'confianza': e.confianza,
                    'normalizado': e.normalizado,
                } for e in entidades],
                'total_entidades': len(entidades),
                'por_tipo': {k: len(list(dict.fromkeys(v))) for k, v in por_tipo.items()},
                'resumen': ' | '.join(partes) if partes else 'Sin entidades detectadas',
            }
        except Exception as e:
            return self._resultado_vacio(str(entrada)[:100], str(e))
    
    def _resultado_vacio(self, texto='', error=''):
        return {
            'texto_original': texto,
            'entidades': [], 'total_entidades': 0, 'por_tipo': {},
            'resumen': f'Error: {error}' if error else 'Sin entidades detectadas',
        }
    
    def _extraer_patron(self, texto, tipo, patron, confianza, normalizar, entidades, ocupadas):
        for m in patron.finditer(texto):
            inicio, fin = m.start(), m.end()
            if any(not (fin <= oi or inicio >= of) for oi, of in ocupadas):
                continue
            valor = m.group(1) if m.groups() else m.group(0)
            entidades.append(EntidadDetectada(
                texto=valor, tipo=tipo, posicion_inicio=inicio, posicion_fin=fin,
                confianza=confianza, normalizado=normalizar(valor) if normalizar else valor
            ))
            ocupadas.add((inicio, fin))
    
    def _extraer_nombres(self, texto, entidades, ocupadas):
        patron = re.compile(
            r'(?<![.!?]\s)(?<!\A)'
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+(?:de|del|la|las|el|los|y|e)\s+)?'
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+)*)'
        )
        for m in patron.finditer(texto):
            inicio, fin = m.start(), m.end()
            valor = m.group(1).strip()
            if any(not (fin <= oi or inicio >= of) for oi, of in ocupadas):
                continue
            
            palabras = valor.split()
            if all(p.lower() in self.FALSOS_NOMBRES for p in palabras):
                continue
            
            if any(p in self.ORGANIZACIONES for p in palabras):
                tipo, conf = TipoEntidad.ORGANIZACION, 0.90
            elif any(p in self.LUGARES for p in palabras):
                tipo, conf = TipoEntidad.LUGAR, 0.90
            elif any(p in self.NOMBRES_PROPIOS for p in palabras):
                tipo, conf = TipoEntidad.PERSONA, 0.85
            elif len(palabras) >= 2:
                tipo, conf = TipoEntidad.PERSONA, 0.60
            else:
                tipo, conf = TipoEntidad.DESCONOCIDO, 0.40
            
            entidades.append(EntidadDetectada(
                texto=valor, tipo=tipo, posicion_inicio=inicio, posicion_fin=fin,
                confianza=conf, normalizado=valor
            ))
            ocupadas.add((inicio, fin))

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR DE ENTIDADES")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor...")
        motor = MotorEntidades()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return {'entidades': [], 'total_entidades': 0, 'por_tipo': {}, 'resumen': 'Error'}
        
        print("\n[2/6] Extracción básica...")
        t1 = "Contacta a Juan García en juan.garcia@example.com o visita https://anp.ai. Tel: +34 612 345 678. Precio: $1,234.56 USD. Fecha: 15/06/2026. Color: #FF5733. IP: 192.168.1.1."
        d1 = sd(motor.procesar(t1))
        print(f"  📊 Total: {d1['total_entidades']}")
        for e in d1['entidades'][:8]:
            print(f"     - [{e['tipo']}] {e['texto']} ({e['confianza']})")
        
        print("\n[3/6] Por tipo...")
        print(f"  📊 {d1['por_tipo']}")
        
        print("\n[4/6] Nombres propios...")
        t2 = "Microsoft anunció que Satya Nadella visitará Madrid con Elon Musk para la NASA en Nueva York."
        d2 = sd(motor.procesar(t2))
        print(f"  📊 Total: {d2['total_entidades']}")
        for e in d2['entidades']:
            if e['tipo'] in ('persona', 'organizacion', 'lugar'):
                print(f"     - [{e['tipo']}] {e['texto']} ({e['confianza']})")
        
        print("\n[5/6] Resúmenes...")
        print(f"  📍 1: {d1['resumen']}")
        print(f"  📍 2: {d2['resumen']}")
        
        print("\n[6/6] Estadísticas...")
        print(f"  📊 Tipos de patrones: {len(motor._patrones_compilados)}")
        print(f"  📊 Nombres propios: {len(motor.NOMBRES_PROPIOS)}")
        print(f"  📊 Organizaciones: {len(motor.ORGANIZACIONES)}")
        print(f"  📊 Lugares: {len(motor.LUGARES)}")
        
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