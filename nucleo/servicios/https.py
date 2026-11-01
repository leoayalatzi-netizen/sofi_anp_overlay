#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Servicio HTTP (Cliente HTTP Cuántico)
# =====================================================================
# Versión: 0.0.1-NEBULA
# =====================================================================
# ADVERTENCIA: Este módulo implementa un cliente HTTP de nivel
# empresarial con pool de conexiones, rate limiting, rotación de
# User-Agent, circuit breaker, caché, reintentos, y soporte para
# scraping avanzado.
# =====================================================================

import sys
import os
import time
import threading
import json
import gzip
import zlib
import random
import hashlib
import socket
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict, deque
from functools import wraps
from contextlib import contextmanager
from urllib.parse import urlparse, urlencode
from http.cookiejar import CookieJar
import traceback
import re
import math

# Dependencias opcionales
try:
    import brotli
    BROTLI_DISPONIBLE = True
except ImportError:
    brotli = None
    BROTLI_DISPONIBLE = False

try:
    import certifi
    CERTIFI_DISPONIBLE = True
except ImportError:
    certifi = None
    CERTIFI_DISPONIBLE = False

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    from requests.exceptions import RequestException, Timeout, ConnectionError as ReqConnectionError
    REQUESTS_DISPONIBLE = True
except ImportError:
    REQUESTS_DISPONIBLE = False
    requests = None

try:
    import aiohttp
    AIOHTTP_DISPONIBLE = True
except ImportError:
    AIOHTTP_DISPONIBLE = False

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback elegante)
# =====================================================================

try:
    from .cache import obtener_cache
except ImportError:
    def obtener_cache(nombre=""):
        return None

try:
    from .registro import obtener_logger
except ImportError:
    def obtener_logger(nombre=""):
        return None

try:
    from ..metricas import contador, histograma, medidor
except ImportError:
    def contador(nombre, descripcion="", **kwargs):
        return None
    def histograma(nombre, descripcion="", **kwargs):
        return None
    def medidor(nombre, descripcion="", **kwargs):
        return None

# =====================================================================
# ENUMERACIONES
# =====================================================================

class MetodoHTTP(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"

class EstadoRespuesta(Enum):
    EXITO = "exito"
    REDIRECCION = "redireccion"
    ERROR_CLIENTE = "error_cliente"
    ERROR_SERVIDOR = "error_servidor"
    ERROR_RED = "error_red"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    BLOQUEADO = "bloqueado"
    DESCONOCIDO = "desconocido"

class PoliticaReintento(Enum):
    FIJO = "fijo"
    EXPONENCIAL = "exponencial"
    EXPONENCIAL_JITTER = "exponencial_jitter"
    NUNCA = "nunca"

class EstadoCircuitBreaker(Enum):
    CERRADO = "cerrado"
    ABIERTO = "abierto"
    SEMI_ABIERTO = "semi_abierto"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class RespuestaHTTP:
    url: str
    metodo: MetodoHTTP
    status_code: int
    headers: Dict[str, str]
    contenido: bytes
    texto: str = ""
    json_data: Any = None
    tiempo_respuesta_ms: float = 0.0
    intentos: int = 1
    desde_cache: bool = False
    cookies: Dict[str, str] = field(default_factory=dict)
    historial_redirecciones: List[str] = field(default_factory=list)
    encoding: str = "utf-8"
    
    def __post_init__(self):
        if self.contenido and not self.texto:
            try:
                self.texto = self.contenido.decode(self.encoding, errors='replace')
            except Exception:
                self.texto = self.contenido.decode('utf-8', errors='replace')
    
    @property
    def exito(self) -> bool:
        return 200 <= self.status_code < 300
    
    @property
    def estado(self) -> EstadoRespuesta:
        if 200 <= self.status_code < 300:
            return EstadoRespuesta.EXITO
        elif 300 <= self.status_code < 400:
            return EstadoRespuesta.REDIRECCION
        elif 400 <= self.status_code < 500:
            if self.status_code == 429:
                return EstadoRespuesta.RATE_LIMITED
            elif self.status_code == 403:
                return EstadoRespuesta.BLOQUEADO
            return EstadoRespuesta.ERROR_CLIENTE
        elif 500 <= self.status_code < 600:
            return EstadoRespuesta.ERROR_SERVIDOR
        return EstadoRespuesta.DESCONOCIDO
    
    def json(self) -> Any:
        if self.json_data is None:
            try:
                self.json_data = json.loads(self.texto)
            except Exception:
                self.json_data = None
        return self.json_data
    
    def soup(self, parser: str = "html.parser"):
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(self.texto, parser)
        except ImportError:
            return None

@dataclass
class EstadisticasHTTP:
    total_peticiones: int = 0
    exitos: int = 0
    fallos: int = 0
    timeouts: int = 0
    reintentos: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bytes_descargados: int = 0
    tiempo_total_ms: float = 0.0
    
    @property
    def tasa_exito(self) -> float:
        return self.exitos / max(1, self.total_peticiones)
    
    @property
    def tiempo_promedio_ms(self) -> float:
        return self.tiempo_total_ms / max(1, self.total_peticiones)

# =====================================================================
# ROTADOR DE USER-AGENTS
# =====================================================================

class UserAgentRotator:
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    ]
    
    def __init__(self, tipo: str = "aleatorio"):
        self.tipo = tipo
        self._indice = 0
        self._lock = threading.RLock()
    
    def obtener(self) -> str:
        with self._lock:
            if self.tipo == "rotatorio":
                ua = self.USER_AGENTS[self._indice]
                self._indice = (self._indice + 1) % len(self.USER_AGENTS)
                return ua
            else:
                return random.choice(self.USER_AGENTS)

# =====================================================================
# RATE LIMITER
# =====================================================================

class RateLimiter:
    
    def __init__(self, peticiones_por_segundo: float = 10.0):
        self.tasa = peticiones_por_segundo
        self.intervalo = 1.0 / peticiones_por_segundo
        self._ultima_peticion: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def esperar(self, dominio: str):
        with self._lock:
            ahora = time.time()
            ultima = self._ultima_peticion.get(dominio, 0)
            tiempo_espera = ultima + self.intervalo - ahora
            if tiempo_espera > 0:
                time.sleep(tiempo_espera)
                ahora = time.time()
            self._ultima_peticion[dominio] = ahora

# =====================================================================
# CIRCUIT BREAKER
# =====================================================================

class CircuitBreakerHTTP:
    
    def __init__(self, umbral_fallos: int = 5, timeout_recuperacion: float = 60.0):
        self.umbral_fallos = umbral_fallos
        self.timeout_recuperacion = timeout_recuperacion
        self._fallos: Dict[str, int] = defaultdict(int)
        self._estado: Dict[str, EstadoCircuitBreaker] = defaultdict(lambda: EstadoCircuitBreaker.CERRADO)
        self._abierto_hasta: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def permitir(self, dominio: str) -> bool:
        with self._lock:
            estado = self._estado[dominio]
            if estado == EstadoCircuitBreaker.CERRADO:
                return True
            elif estado == EstadoCircuitBreaker.ABIERTO:
                if time.time() >= self._abierto_hasta[dominio]:
                    self._estado[dominio] = EstadoCircuitBreaker.SEMI_ABIERTO
                    return True
                return False
            elif estado == EstadoCircuitBreaker.SEMI_ABIERTO:
                return True
            return True
    
    def registrar_exito(self, dominio: str):
        with self._lock:
            self._fallos[dominio] = 0
            if self._estado[dominio] == EstadoCircuitBreaker.SEMI_ABIERTO:
                self._estado[dominio] = EstadoCircuitBreaker.CERRADO
    
    def registrar_fallo(self, dominio: str):
        with self._lock:
            self._fallos[dominio] += 1
            if self._estado[dominio] == EstadoCircuitBreaker.CERRADO:
                if self._fallos[dominio] >= self.umbral_fallos:
                    self._estado[dominio] = EstadoCircuitBreaker.ABIERTO
                    self._abierto_hasta[dominio] = time.time() + self.timeout_recuperacion
            elif self._estado[dominio] == EstadoCircuitBreaker.SEMI_ABIERTO:
                self._estado[dominio] = EstadoCircuitBreaker.ABIERTO
                self._abierto_hasta[dominio] = time.time() + self.timeout_recuperacion

# =====================================================================
# POOL DE CONEXIONES
# =====================================================================

class PoolConexionesHTTP:
    
    def __init__(self, max_conexiones: int = 50, max_por_host: int = 10):
        self.max_conexiones = max_conexiones
        self.max_por_host = max_por_host
        self._session = None
        
        if REQUESTS_DISPONIBLE:
            try:
                self._session = requests.Session()
                adapter = HTTPAdapter(
                    pool_connections=max_conexiones,
                    pool_maxsize=max_conexiones,
                    max_retries=Retry(total=0),
                    pool_block=False
                )
                self._session.mount('http://', adapter)
                self._session.mount('https://', adapter)
            except Exception:
                self._session = None
        
        self._lock = threading.RLock()
    
    def obtener_session(self):
        return self._session
    
    def cerrar(self):
        if self._session:
            self._session.close()
            self._session = None

# =====================================================================
# CLIENTE HTTP PRINCIPAL
# =====================================================================


class ClienteHTTP:
    
    _instancias: Dict[str, 'ClienteHTTP'] = {}
    _lock_instancias = threading.RLock()
    
    def __init__(self, nombre: str = "default",
                 timeout: float = 30.0,
                 max_reintentos: int = 3,
                 politica_reintento: PoliticaReintento = PoliticaReintento.EXPONENCIAL_JITTER,
                 rate_limit: float = 10.0,
                 user_agent_tipo: str = "aleatorio",
                 cache_ttl: int = 300,
                 verificar_ssl: bool = True,
                 seguir_redirecciones: bool = True,
                 max_redirecciones: int = 5,
                 proxy: Optional[str] = None,
                 headers_default: Dict[str, str] = None):
        
        self.nombre = nombre
        self.timeout = timeout
        self.max_reintentos = max_reintentos
        self.politica_reintento = politica_reintento
        self.verificar_ssl = verificar_ssl
        self.seguir_redirecciones = seguir_redirecciones
        self.max_redirecciones = max_redirecciones
        self.proxy = proxy
        self.headers_default = headers_default or {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.user_agent_rotator = UserAgentRotator(tipo=user_agent_tipo)
        self.rate_limiter = RateLimiter(rate_limit)
        self.circuit_breaker = CircuitBreakerHTTP()
        self.pool = PoolConexionesHTTP()
        
        self.cache = obtener_cache(f"http_{nombre}")
        self.cache_ttl = cache_ttl
        
        self.estadisticas = EstadisticasHTTP()
        self._estadisticas_lock = threading.RLock()
        
        self._logger = obtener_logger(f"HTTP.{nombre}")
        
        try:
            self._metrica_peticiones = contador("http.peticiones")
            self._metrica_exitos = contador("http.exitos")
            self._metrica_fallos = contador("http.fallos")
            self._metrica_latencia = histograma("http.latencia")
        except Exception:
            self._metrica_peticiones = None
            self._metrica_exitos = None
            self._metrica_fallos = None
            self._metrica_latencia = None
        
        self.cookie_jar = CookieJar()
    
    @classmethod
    def obtener(cls, nombre: str = "default", **kwargs) -> 'ClienteHTTP':
        with cls._lock_instancias:
            if nombre not in cls._instancias:
                cls._instancias[nombre] = ClienteHTTP(nombre=nombre, **kwargs)
            return cls._instancias[nombre]
    
    def _obtener_headers(self, extra_headers: Dict[str, str] = None) -> Dict[str, str]:
        headers = self.headers_default.copy()
        headers['User-Agent'] = self.user_agent_rotator.obtener()
        if extra_headers:
            headers.update(extra_headers)
        return headers
    
    def _calcular_retraso(self, intento: int) -> float:
        if self.politica_reintento == PoliticaReintento.FIJO:
            return 1.0
        elif self.politica_reintento == PoliticaReintento.EXPONENCIAL:
            return 2 ** intento
        elif self.politica_reintento == PoliticaReintento.EXPONENCIAL_JITTER:
            return (2 ** intento) + random.uniform(0, 0.5)
        else:
            return 0.0
    
    def _peticion_cruda(self, metodo: MetodoHTTP, url: str,
                        headers: Dict[str, str] = None,
                        datos: Any = None,
                        json_data: Dict = None,
                        params: Dict = None,
                        timeout: float = None,
                        stream: bool = False) -> RespuestaHTTP:
        
        if not REQUESTS_DISPONIBLE:
            raise RuntimeError("Requests no está instalado")
        
        timeout = timeout or self.timeout
        headers = self._obtener_headers(headers)
        dominio = urlparse(url).netloc
        
        if not self.circuit_breaker.permitir(dominio):
            raise Exception(f"Circuit breaker abierto para {dominio}")
        
        self.rate_limiter.esperar(dominio)
        
        session = self.pool.obtener_session()
        if session is None:
            raise RuntimeError("No hay sesión HTTP disponible")
        
        kwargs = {
            'method': metodo.value,
            'url': url,
            'headers': headers,
            'params': params,
            'timeout': timeout,
            'verify': self.verificar_ssl,
            'allow_redirects': self.seguir_redirecciones,
            'stream': stream,
        }
        
        if json_data:
            kwargs['json'] = json_data
        elif datos:
            kwargs['data'] = datos
        
        if self.proxy:
            kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
        
        try:
            response = session.request(**kwargs)
            contenido = response.content if not stream else b''
            
            resp = RespuestaHTTP(
                url=url,
                metodo=metodo,
                status_code=response.status_code,
                headers=dict(response.headers),
                contenido=contenido,
                encoding=response.encoding or 'utf-8',
                tiempo_respuesta_ms=response.elapsed.total_seconds() * 1000,
                historial_redirecciones=[r.url for r in response.history] if response.history else []
            )
            
            for cookie in response.cookies:
                resp.cookies[cookie.name] = cookie.value
                self.cookie_jar.set_cookie(cookie)
            
            self.circuit_breaker.registrar_exito(dominio)
            return resp
            
        except Exception as e:
            self.circuit_breaker.registrar_fallo(dominio)
            raise e
    
    def _reintentar_peticion(self, metodo: MetodoHTTP, url: str, **kwargs) -> RespuestaHTTP:
        ultimo_error = None
        
        for intento in range(self.max_reintentos + 1):
            try:
                inicio = time.time()
                resp = self._peticion_cruda(metodo, url, **kwargs)
                tiempo_ms = (time.time() - inicio) * 1000
                
                with self._estadisticas_lock:
                    self.estadisticas.total_peticiones += 1
                    self.estadisticas.tiempo_total_ms += tiempo_ms
                    self.estadisticas.bytes_descargados += len(resp.contenido)
                    
                    if resp.exito:
                        self.estadisticas.exitos += 1
                        if self._metrica_exitos:
                            self._metrica_exitos.inc()
                    else:
                        self.estadisticas.fallos += 1
                        if self._metrica_fallos:
                            self._metrica_fallos.inc()
                
                if self._metrica_peticiones:
                    self._metrica_peticiones.inc()
                if self._metrica_latencia:
                    self._metrica_latencia.observar(tiempo_ms)
                
                resp.intentos = intento + 1
                return resp
                
            except Exception as e:
                ultimo_error = e
                self.estadisticas.fallos += 1
                
                if intento < self.max_reintentos:
                    retraso = self._calcular_retraso(intento)
                    self.estadisticas.reintentos += 1
                    time.sleep(retraso)
        
        raise ultimo_error
    
    # ===== MÉTODOS PÚBLICOS =====
    
    def get(self, url: str, params: Dict = None, headers: Dict = None,
            timeout: float = None, usar_cache: bool = False,
            cache_ttl: int = None) -> RespuestaHTTP:
        
        if usar_cache and self.cache:
            clave = f"GET:{url}:{json.dumps(params or {})}"
            cached = self.cache.obtener(clave)
            if cached is not None:
                self.estadisticas.cache_hits += 1
                resp = RespuestaHTTP(**cached)
                resp.desde_cache = True
                return resp
            self.estadisticas.cache_misses += 1
        
        resp = self._reintentar_peticion(
            MetodoHTTP.GET, url, headers=headers, params=params, timeout=timeout
        )
        
        if usar_cache and self.cache and resp.exito:
            self.cache.guardar(
                f"GET:{url}:{json.dumps(params or {})}",
                asdict(resp),
                ttl=cache_ttl or self.cache_ttl
            )
        
        return resp
    
    def post(self, url: str, data: Dict = None, json: Dict = None,
             headers: Dict = None, timeout: float = None) -> RespuestaHTTP:
        return self._reintentar_peticion(
            MetodoHTTP.POST, url, headers=headers, datos=data, json_data=json, timeout=timeout
        )
    
    def get_json(self, url: str, **kwargs) -> Optional[Any]:
        resp = self.get(url, **kwargs)
        if resp.exito:
            return resp.json()
        return None
    
    def get_soup(self, url: str, parser: str = "html.parser", **kwargs):
        resp = self.get(url, **kwargs)
        if resp.exito:
            return resp.soup(parser)
        return None
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        with self._estadisticas_lock:
            return {
                'nombre': self.nombre,
                'total_peticiones': self.estadisticas.total_peticiones,
                'exitos': self.estadisticas.exitos,
                'fallos': self.estadisticas.fallos,
                'tasa_exito': self.estadisticas.tasa_exito,
                'reintentos': self.estadisticas.reintentos,
                'cache_hits': self.estadisticas.cache_hits,
                'cache_misses': self.estadisticas.cache_misses,
                'tiempo_promedio_ms': self.estadisticas.tiempo_promedio_ms,
            }
    
    def __repr__(self) -> str:
        return f"ClienteHTTP({self.nombre}, peticiones={self.estadisticas.total_peticiones})"

# =====================================================================
# FUNCIONES DE CONVENIENCIA
# =====================================================================

def obtener_cliente(nombre: str = "default") -> ClienteHTTP:
    return ClienteHTTP.obtener(nombre)

def get(url: str, **kwargs) -> RespuestaHTTP:
    return obtener_cliente().get(url, **kwargs)

def get_json(url: str, **kwargs) -> Optional[Any]:
    return obtener_cliente().get_json(url, **kwargs)

def get_soup(url: str, **kwargs):
    return obtener_cliente().get_soup(url, **kwargs)

# =====================================================================
# DIAGNÓSTICO Y PRUEBAS
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL CLIENTE HTTP CUÁNTICO")
    print("=" * 70)
    
    cliente = None
    
    try:
        print("\n[1/6] Inicializando cliente HTTP...")
        cliente = ClienteHTTP("test", timeout=10, max_reintentos=2)
        print(f"  ✅ Cliente inicializado: {cliente}")
        
        print("\n[2/6] Probando GET a httpbin.org...")
        try:
            resp = cliente.get("https://httpbin.org/get", params={"test": "ANP"})
            print(f"  📍 Status: {resp.status_code}")
            print(f"  📍 Tiempo: {resp.tiempo_respuesta_ms:.2f}ms")
            if resp.exito:
                data = resp.json()
                print(f"  ✅ Args recibidos: {data.get('args', {})}")
        except Exception as e:
            print(f"  ⚠️ Sin conexión o error: {e}")
        
        print("\n[3/6] Probando User-Agent rotator...")
        for i in range(3):
            ua = cliente.user_agent_rotator.obtener()
            print(f"  📍 UA {i+1}: {ua[:60]}...")
        
        print("\n[4/6] Probando caché (simulado)...")
        print(f"  📍 Cache TTL: {cliente.cache_ttl}s")
        
        print("\n[5/6] Estadísticas del cliente...")
        stats = cliente.obtener_estadisticas()
        print(f"  📊 Total peticiones: {stats['total_peticiones']}")
        print(f"  📊 Éxitos: {stats['exitos']}")
        print(f"  📊 Tasa éxito: {stats['tasa_exito']:.1%}")
        
        print("\n[6/6] Componentes activos...")
        print(f"  ✅ User-Agent Rotator: {len(cliente.user_agent_rotator.USER_AGENTS)} UAs")
        print(f"  ✅ Rate Limiter: {cliente.rate_limiter.tasa} req/s")
        print(f"  ✅ Requests disponible: {REQUESTS_DISPONIBLE}")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("   El Cliente HTTP Cuántico está VIVO.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        
    finally:
        if cliente and cliente.pool:
            cliente.pool.cerrar()
    
    print("\n" + "=" * 70 + "\n")