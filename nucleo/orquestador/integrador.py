#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ANP — INTEGRADOR COGNITIVO (V4)                                        ║
║  Puente real entre Enrutador/Orquestador y los motores existentes        ║
║                                                                          ║
║  Qué resuelve respecto a V3:                                             ║
║  1. Orquestador._ejecutar_en_nucleo() era un stub (sleep + eco).         ║
║     Aquí se sobreescribe para llamar al motor REAL vía CargadorMotores.  ║
║  2. Los núcleos nacían INACTIVOS -> nunca había ruta "saludable".        ║
║     Aquí se registran como ACTIVOS al iniciar y antes de cada consulta.  ║
║  3. CacheRutas cachea la RUTA, no el resultado -> en cache-hit no se     ║
║     ejecutaba nada. Aquí se desactiva cacheable en todas las rutas       ║
║     propias (el pensamiento profundo no debe servir respuestas rancias). ║
║  4. motor_atencion y motor_trabajo viven en nucleo/ (infraestructura),  ║
║     no en nucleos/*/motores/, así que el CargadorMotores nunca los      ║
║     cargaba. Aquí se instancian explícitamente como memoria de trabajo  ║
║     y atención compartidas por todo el sistema.                         ║
║  5. La síntesis ya no es "el primer hilo que responde": varios núcleos  ║
║     se consultan en paralelo, sus resultados compiten por foco          ║
║     atencional real (spreading activation) y, si hay ≥2 focos, se       ║
║     combinan con el motor de ideas o el grafo semántico -> ahí es       ║
║     donde aparece algo parecido a pensamiento emergente real.           ║
╚══════════════════════════════════════════════════════════════════════════╝

UBICACIÓN REQUERIDA: nucleo/orquestador/integrador.py
(debe vivir junto a maestro.py y enrutador.py para que los imports
relativos `.maestro` / `.enrutador` funcionen, igual que ya hace
enrutador.py al importar de maestro.py)
"""

import re
import time
import random
import hashlib
import threading
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ═══════════ IMPORTS DEL SISTEMA (con fallback para pruebas sueltas) ═══════════
try:
    from .maestro import Orquestador, TipoTarea, PrioridadTarea, ModoOrquestacion, Ruta
except ImportError:
    from maestro import Orquestador, TipoTarea, PrioridadTarea, ModoOrquestacion, Ruta

try:
    from .enrutador import Enrutador, EstrategiaEnrutamiento
except ImportError:
    from enrutador import Enrutador, EstrategiaEnrutamiento

try:
    from nucleo.motor_atencion import MotorAtencion
    from nucleo.motor_trabajo import MotorTrabajo
except ImportError:
    from motor_atencion import MotorAtencion
    from motor_trabajo import MotorTrabajo

try:
    from nucleo.bus_eventos.bus import obtener_bus
except ImportError:
    try:
        from bus import obtener_bus
    except ImportError:
        obtener_bus = None


# ═══════════════════════════════════════════════════════════════
# EMBEDDING LIGERO (hashing trick) — sin dependencias externas,
# determinista, y con señal real de contenido (no ruido aleatorio):
# textos que comparten palabras producen vectores más parecidos,
# que es justo lo que MotorAtencion necesita para discriminar.
# ═══════════════════════════════════════════════════════════════
_RE_PALABRAS = re.compile(r'[a-záéíóúñ]{4,}', re.IGNORECASE)
_STOPWORDS_BASICAS = {
    'que', 'como', 'para', 'por', 'del', 'los', 'las', 'una', 'con', 'mas',
    'qué', 'cómo', 'cuál', 'sus', 'son', 'era', 'fue', 'hay', 'tiene', 'entre',
    'sobre', 'desde', 'hasta', 'cada', 'todo', 'muy', 'sin', 'pero', 'porque',
    'cuando', 'donde', 'esto', 'esta', 'ese', 'esa', 'relacion', 'relación',
}

def _palabras_clave(texto: str, max_n: int = 3) -> List[str]:
    """Extrae las palabras más significativas de un texto para consultar
    el grafo semántico (que busca por substring, no por similitud)."""
    palabras = [p for p in _RE_PALABRAS.findall((texto or '').lower()) if p not in _STOPWORDS_BASICAS]
    palabras_unicas = sorted(set(palabras), key=len, reverse=True)
    return palabras_unicas[:max_n]

def generar_embedding(texto: str, dim: int = 256) -> List[float]:
    vector = [0.0] * dim
    palabras = _RE_PALABRAS.findall((texto or "").lower())
    if not palabras:
        return vector
    for palabra in palabras:
        h = hashlib.sha256(palabra.encode('utf-8')).digest()
        idx = int.from_bytes(h[:4], 'big') % dim
        signo = 1.0 if h[4] % 2 == 0 else -1.0
        vector[idx] += signo
    norma = sum(v * v for v in vector) ** 0.5
    if norma > 0:
        vector = [v / norma for v in vector]
    return vector


def _buscar_semantica_por_palabras(instancia, texto: str) -> Dict[str, Any]:
    """La memoria semántica busca por substring literal, no por similitud:
    pasarle la pregunta completa nunca encuentra nada. Se consulta por
    palabras clave y se fusionan los resultados. Reutilizada tanto por
    OrquestadorANP (camino enrutado) como por el fan-out total."""
    claves = _palabras_clave(texto, 3) or [texto[:40]]
    acumulado, vistos = [], set()
    tiempo_total = 0.0
    for clave in claves:
        r = instancia.procesar({'accion': 'buscar', 'texto': clave, 'limite': 3})
        tiempo_total += r.tiempo_ejecucion_ms
        if r.exito and isinstance(r.datos, dict):
            for item in r.datos.get('resultados', []):
                if item.get('id') not in vistos:
                    vistos.add(item.get('id'))
                    acumulado.append(item)
    return {'exito': True, 'total': len(acumulado), 'resultados': acumulado[:5]}, tiempo_total


# ═══════════════════════════════════════════════════════════════
# ORQUESTADOR REAL: sobreescribe el stub para llamar a los motores
# cargados de verdad, y desactiva el bug de caché-sin-ejecución.
# Se mantiene disponible para enrutamiento selectivo con circuit
# breaker; el fan-out total (IntegradorCognitivo._ejecutar_todos)
# no depende de esta clase.
# ═══════════════════════════════════════════════════════════════
class OrquestadorANP(Orquestador):

    # (nucleo, nombre_corto_de_ruta) -> constructor de entrada según el
    # contrato REAL de cada motor (verificado leyendo cada archivo).
    # Para los motores que no pude inspeccionar directamente se usa el
    # contrato genérico {'texto', 'operacion':'analizar'} como mejor esfuerzo.
    _CONSTRUCTORES = {
        ('creatividad', 'ideas'): lambda t: {'operacion': 'brainstorm', 'tema': t, 'cantidad': 3},
    }

    def __init__(self, cargador_motores, modo: ModoOrquestacion = ModoOrquestacion.NORMAL):
        super().__init__(modo)
        self._cargador = cargador_motores

    def _inicializar_rutas(self):
        """Igual que la base, pero con cacheable=False: el pensamiento
        profundo no debe servir un eco de ruta cacheada en vez de ejecutar."""
        rutas = super()._inicializar_rutas()
        nuevas = {}
        for tipo, lista in rutas.items():
            nuevas[tipo] = [
                Ruta(
                    nucleo_principal=r.nucleo_principal,
                    nucleo_fallback=r.nucleo_fallback,
                    motor=r.motor,
                    prioridad=r.prioridad,
                    timeout=r.timeout,
                    reintentos_max=r.reintentos_max,
                    requiere_contexto=r.requiere_contexto,
                    cacheable=False,
                    ttl_cache=r.ttl_cache,
                ) for r in lista
            ]
        return nuevas

    def _buscar_motor(self, nucleo: str, motor_corto: str):
        """Resuelve (núcleo, nombre_corto) -> InfoMotor real del CargadorMotores."""
        if not motor_corto:
            return None
        candidatos = [f"{nucleo}/{motor_corto}", f"{nucleo}/motor_{motor_corto}"]
        for clave in candidatos:
            info = self._cargador.motores.get(clave)
            if info and info.instancia is not None:
                return info
        return None

    def _ejecutar_en_nucleo(self, tarea) -> Any:
        """Reemplaza el stub: llama de verdad al motor cargado."""
        nucleo = tarea.ruta.nucleo_principal
        motor_corto = tarea.ruta.motor or ''
        info_motor = self._buscar_motor(nucleo, motor_corto)
        if info_motor is None:
            raise RuntimeError(f"Motor no disponible: {nucleo}/{motor_corto}")

        texto = tarea.datos.get('texto', '') if isinstance(tarea.datos, dict) else str(tarea.datos)

        if nucleo == 'memoria' and motor_corto == 'semantica':
            datos, tiempo_total = _buscar_semantica_por_palabras(info_motor.instancia, texto)
            return {
                'status': 'success', 'nucleo': nucleo, 'motor': info_motor.clave,
                'datos': datos, 'tiempo_ms': tiempo_total,
            }

        constructor = self._CONSTRUCTORES.get((nucleo, motor_corto))
        entrada = constructor(texto) if constructor else {'texto': texto, 'operacion': 'analizar'}

        resultado = info_motor.instancia.procesar(entrada)
        if not resultado.exito:
            raise RuntimeError(resultado.error or f"Fallo en {info_motor.clave}")

        return {
            'status': 'success',
            'nucleo': nucleo,
            'motor': info_motor.clave,
            'datos': resultado.datos,
            'tiempo_ms': resultado.tiempo_ejecucion_ms,
        }


# ═══════════════════════════════════════════════════════════════
# INTEGRADOR COGNITIVO: el verdadero "pensamiento emergente"
# ═══════════════════════════════════════════════════════════════
class IntegradorCognitivo:

    NUCLEOS = ["comunicacion", "razonamiento", "memoria", "resolucion", "busqueda", "creatividad"]

    def __init__(self, cargador_motores, nucleos_excluir: Optional[set] = None):
        self.cargador = cargador_motores
        self.nucleos_excluir = nucleos_excluir or set()
        self.orquestador = OrquestadorANP(cargador_motores)
        for nombre in self.NUCLEOS:
            self.orquestador.registrar_nucleo(nombre)

        self.enrutador = Enrutador(EstrategiaEnrutamiento.CUANTICO)

        self.atencion = MotorAtencion()
        self.atencion.inicializar()
        self.trabajo = MotorTrabajo()
        self.trabajo.inicializar()

        self.bus = obtener_bus() if obtener_bus else None
        if self.bus and getattr(self.bus, 'estado', None) is not None:
            try:
                self.bus.iniciar()
            except Exception:
                pass

        self._lock = threading.RLock()

    # ───────────────────────── utilidades internas ─────────────────────────

    def _motor(self, nucleo: str, motor_corto: str):
        info = self.orquestador._buscar_motor(nucleo, motor_corto)
        return info.instancia if info else None

    def _llamar_motor(self, clave: str, info, texto: str) -> Optional[Dict[str, Any]]:
        """Llama a UN motor cargado. Usa el contrato verificado para los
        que conozco; para el resto, mejor esfuerzo con el contrato genérico
        {'texto','operacion':'analizar'} (el mismo que ya usaba V3)."""
        nucleo = info.nucleo
        try:
            if clave == 'memoria/motor_semantica':
                datos, tiempo_ms = _buscar_semantica_por_palabras(info.instancia, texto)
                return {'status': 'success', 'nucleo': nucleo, 'motor': clave, 'datos': datos, 'tiempo_ms': tiempo_ms}

            if clave == 'creatividad/motor_ideas':
                r = info.instancia.procesar({'operacion': 'brainstorm', 'tema': texto, 'cantidad': 3})
            else:
                # Contrato genérico de mejor esfuerzo — no verificado para este motor.
                r = info.instancia.procesar({'texto': texto, 'operacion': 'analizar'})

            if not r.exito:
                return None
            return {'status': 'success', 'nucleo': nucleo, 'motor': clave, 'datos': r.datos, 'tiempo_ms': r.tiempo_ejecucion_ms}
        except Exception:
            return None

    def _ejecutar_todos(self, texto: str, timeout_total: float = 6.0) -> Dict[str, Optional[Dict[str, Any]]]:
        """Dispara TODOS los motores cargados en paralelo. No espera más de
        timeout_total en total; lo que no termine a tiempo queda como None
        (el hilo sigue corriendo en segundo plano, Python no puede matarlo,
        pero no bloquea la respuesta al usuario)."""
        resultados: Dict[str, Optional[Dict[str, Any]]] = {}
        motores = [(c, i) for c, i in self.cargador.motores.items() if i.nucleo not in self.nucleos_excluir]
        if not motores:
            return resultados

        ejecutor = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, len(motores)))
        futuros = {ejecutor.submit(self._llamar_motor, clave, info, texto): clave for clave, info in motores}
        pendientes = set(futuros.keys())
        limite = time.time() + timeout_total
        while pendientes and time.time() < limite:
            terminados, pendientes = concurrent.futures.wait(pendientes, timeout=0.3)
            for f in terminados:
                clave = futuros[f]
                try:
                    resultados[clave] = f.result()
                except Exception:
                    resultados[clave] = None
        for f in pendientes:
            resultados[futuros[f]] = None
        try:
            ejecutor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            ejecutor.shutdown(wait=False)  # Python < 3.9
        return resultados

    def _extraer_texto(self, nucleo: str, datos: Any) -> str:
        if datos is None:
            return ''
        if nucleo == 'memoria' and isinstance(datos, dict):
            resultados = datos.get('resultados', [])
            if resultados:
                top = resultados[0]
                return f"{top.get('nombre','')}: {top.get('definicion','')}".strip(': ')
            return ''
        if nucleo == 'creatividad' and isinstance(datos, dict):
            ideas = datos.get('ideas', [])
            if ideas:
                mejor = max(ideas, key=lambda i: i.get('originalidad', 0))
                return mejor.get('texto', '')
            return ''
        if isinstance(datos, dict):
            for campo in ('respuesta', 'resultado', 'texto'):
                v = datos.get(campo)
                if isinstance(v, str) and len(v) > 10:
                    return v
            return ''
        if isinstance(datos, str):
            return datos
        return ''

    # ───────────────────────── API pública ─────────────────────────

    def pensar(self, texto: str, timeout_total: float = 6.0) -> Dict[str, Any]:
        """Pipeline de pensamiento profundo. Se usa cuando los atajos rápidos
        (saludo, cálculo, nombre, etc. en principal.py) no resuelven el mensaje.
        Consulta a TODOS los motores cargados (no solo uno por núcleo), y deja
        que compitan por foco real en memoria de trabajo + atención."""
        with self._lock:
            crudos = self._ejecutar_todos(texto, timeout_total=timeout_total)

            emb_consulta = generar_embedding(texto)
            self.atencion.procesar({'accion': 'alimentar', 'item': texto[:200], 'embedding': emb_consulta})

            candidatos: Dict[str, Tuple[str, str]] = {}
            for clave, crudo in crudos.items():
                if not crudo or crudo.get('status') != 'success':
                    continue
                extraido = self._extraer_texto(crudo.get('nucleo', ''), crudo.get('datos'))
                if not extraido or len(extraido) < 10:
                    continue
                emb = generar_embedding(extraido)
                ins = self.trabajo.procesar({
                    'accion': 'insertar', 'contenido': extraido, 'resumen': extraido[:100],
                    'modalidad': 'verbal',
                    'prioridad': 'alta' if crudo.get('nucleo') == 'razonamiento' else 'media',
                    'peso_atencion': 0.6, 'metadata': {'motor': clave},
                })
                self.atencion.procesar({'accion': 'alimentar', 'item': extraido[:200], 'embedding': emb})
                if ins.exito and isinstance(ins.datos, dict) and ins.datos.get('exito'):
                    candidatos[ins.datos['id']] = (clave, extraido)

            foco_res = self.trabajo.procesar({'accion': 'foco'})
            foco_ids = []
            if foco_res.exito and isinstance(foco_res.datos, dict):
                foco_ids = [f['id'] for f in foco_res.datos.get('foco', [])]

            seleccionados = [candidatos[i] for i in foco_ids if i in candidatos]
            if not seleccionados:
                seleccionados = list(candidatos.values())

            respuesta = self._sintetizar(seleccionados)

            if self.bus:
                try:
                    self.bus.publicar('pensamiento.sintesis', {
                        'consulta': texto[:150],
                        'fuentes': [c for c, _ in seleccionados],
                        'resultado': respuesta[:200],
                    }, origen='integrador')
                except Exception:
                    pass

            return {
                'respuesta': respuesta,
                'fuentes': [c for c, _ in seleccionados],
                'motores_consultados': len(crudos),
                'motores_con_señal': len(candidatos),
            }

    def _sintetizar(self, seleccionados: List[Tuple[str, str]]) -> str:
        if not seleccionados:
            return ''
        if len(seleccionados) == 1:
            return seleccionados[0][1][:600]

        (_, c1), (_, c2) = seleccionados[0], seleccionados[1]
        motor_ideas = self._motor('creatividad', 'ideas')
        if motor_ideas:
            r = motor_ideas.procesar({'operacion': 'combinar', 'idea1': c1[:200], 'idea2': c2[:200]})
            if r.exito and isinstance(r.datos, dict):
                combinado = r.datos.get('idea_combinada')
                if combinado:
                    return combinado.strip()[:700]
        return f"{c1}\n\nEsto se conecta con: {c2}"[:700]

    def ciclo_trasfondo(self) -> Optional[Dict[str, Any]]:
        """Pensamiento autónomo de fondo (V4): usa el grafo semántico real
        para encontrar vacíos de conocimiento, y el motor de ideas para
        combinar dos focos reales de la memoria de trabajo. Reemplaza al
        DetectorPatrones de V3, que solo hacía regex sobre filas de SQLite."""
        motor_sem = self._motor('memoria', 'semantica')
        motor_id = self._motor('creatividad', 'ideas')

        if motor_sem:
            busq = motor_sem.procesar({'accion': 'buscar', 'limite': 30})
            if busq.exito and isinstance(busq.datos, dict):
                candidatos = [
                    c for c in busq.datos.get('resultados', [])
                    if not c.get('definicion') or c.get('confianza', 1.0) < 0.7
                ]
                if candidatos:
                    elegido = random.choice(candidatos)
                    pensamiento = {
                        'tipo': 'vacio',
                        'contenido': f"Tengo el concepto '{elegido['nombre']}' en mi memoria semántica "
                                     f"pero con poca profundidad. Debería investigarlo más."
                    }
                    self._publicar_trasfondo(pensamiento)
                    return pensamiento

        if motor_id:
            foco = self.trabajo.procesar({'accion': 'foco'})
            items = foco.datos.get('foco', []) if foco.exito and isinstance(foco.datos, dict) else []
            if len(items) >= 2:
                r = motor_id.procesar({
                    'operacion': 'combinar',
                    'idea1': items[0]['resumen'], 'idea2': items[1]['resumen'],
                })
                if r.exito and isinstance(r.datos, dict) and r.datos.get('idea_combinada'):
                    pensamiento = {'tipo': 'conexion', 'contenido': r.datos['idea_combinada']}
                    self._publicar_trasfondo(pensamiento)
                    return pensamiento

        return None

    def _publicar_trasfondo(self, pensamiento: Dict[str, Any]):
        if self.bus:
            try:
                self.bus.publicar('pensamiento.trasfondo', pensamiento, origen='ciclo_autonomo')
            except Exception:
                pass

    def cerrar(self):
        """Persiste lo aprendido (grafo semántico y memoria de trabajo)."""
        motor_sem = self._motor('memoria', 'semantica')
        try:
            if motor_sem:
                motor_sem.procesar({'accion': 'guardar', 'ruta': 'almacenamiento/semantica/grafo.json'})
            self.trabajo.procesar({'accion': 'guardar', 'ruta': 'almacenamiento/trabajo/estado.json'})
        except Exception:
            pass
