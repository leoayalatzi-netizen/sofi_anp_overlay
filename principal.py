#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ANP — ARQUITECTURA NEURONAL PROFUNDA                                   ║
║  Nevula v0.0.1 — V3: EMERGENCIA REAL                                    ║
║                                                                          ║
║  Pensamientos que surgen de MEMORIA, no de plantillas aleatorias         ║
║  - Detector de patrones entre recuerdos                                  ║
║  - Identificador de vacíos de conocimiento                               ║
║  - Resolución de contradicciones                                         ║
║  - Objetivos con progreso basado en eventos reales                       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import sys, os, time, math, random, re, uuid, json, threading, logging, sqlite3, hashlib
from pathlib import Path
from collections import defaultdict, deque, Counter
from typing import Optional, Dict, Any, List, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime

# ═══════════ CONFIGURACIÓN ═══════════
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
os.chdir(str(BASE))
MODO_DEBUG = os.environ.get('ANP_DEBUG', '1') == '1'

# ═══════════ LOGGER ═══════════
class LoggerANP:
    _instancia = None
    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._init()
        return cls._instancia
    def _init(self):
        self._logger = logging.getLogger("ANP")
        self._logger.setLevel(logging.DEBUG if MODO_DEBUG else logging.INFO)
        if not self._logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%H:%M:%S'))
            self._logger.addHandler(h)
    def info(self, m): self._logger.info(m)
    def warning(self, m): self._logger.warning(m)
    def error(self, m): self._logger.error(m)
    def debug(self, m): self._logger.debug(m)

logger = LoggerANP()

# ═══════════ BIBLIOTECA DE DATOS ═══════════
class BibliotecaANP:
    def __init__(self):
        self.datos_dir = BASE / "datos"
        self.cache = {}
        self.archivos = list(self.datos_dir.rglob("*.json")) if self.datos_dir.exists() else []
    def _cargar(self, ruta):
        clave = str(ruta)
        if clave not in self.cache:
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    self.cache[clave] = json.load(f)
            except:
                self.cache[clave] = {}
        return self.cache[clave]
    def buscar(self, texto: str, dominio_preferido: Optional[str] = None) -> Optional[str]:
        # Antes se hacía .split() directo sobre el texto crudo, así que
        # "¿qué es un robot?" generaba la palabra "robot?" (con el signo
        # pegado) que nunca hacía match contra "robot" en la biblioteca.
        # Cualquier pregunta con puntuación fallaba en silencio.
        palabras = [w for w in re.findall(r"[a-zA-Zá-úñÁ-ÚÑ]+", texto.lower()) if len(w) >= 3]
        if not palabras: return None
        resultados = []
        for archivo in self.archivos:
            datos = self._cargar(archivo)
            items = datos.get("datos", [])
            # Bonificación si el archivo pertenece al dominio que predijo la red
            # neuronal clasificadora (motor_clasificador_dominio). No descarta
            # otros dominios, solo prioriza cuando hay empate de puntuación.
            bono_dominio = 0
            if dominio_preferido:
                try:
                    if archivo.relative_to(self.datos_dir).parts[0] == dominio_preferido:
                        bono_dominio = 2
                except Exception:
                    pass
            if isinstance(items, list):
                for item in items:
                    puntuacion = 0
                    item_str = str(item).lower()
                    for p in palabras:
                        if p in item_str:
                            puntuacion += 1
                            for campo in ['concepto','nombre','palabra','emocion','animal','genero','corriente','sesgo','sistema','organo']:
                                if item.get(campo, '').lower() == p: puntuacion += 3
                    if puntuacion > 0:
                        puntuacion += bono_dominio
                        nombre_item = item.get('nombre') or item.get('concepto') or ''
                        prefijo = f"{nombre_item}: " if nombre_item and len(str(nombre_item)) < 60 else ""
                        for campo in ['definicion', 'dato', 'cita', 'significado']:
                            if campo in item:
                                resultados.append((puntuacion, f"{prefijo}{str(item[campo])[:400]}"))
                                break
                        else:
                            for v in item.values():
                                if isinstance(v, str) and len(v) > 20:
                                    resultados.append((puntuacion, f"{prefijo}{v[:400]}"))
                                    break
        if resultados:
            resultados.sort(key=lambda x: x[0], reverse=True)
            if resultados[0][0] >= 2: return resultados[0][1]
        return None
    def buscar_todo(self, palabra: str) -> List[Dict]:
        resultados = []
        for archivo in self.archivos:
            datos = self._cargar(archivo)
            items = datos.get("datos", [])
            if isinstance(items, list):
                for item in items:
                    if palabra.lower() in str(item).lower():
                        resultados.append({"fuente": archivo.stem, "datos": item})
        return resultados
    def buscar_curiosidad(self) -> str:
        for archivo in self.archivos:
            if 'curiosidades' in str(archivo):
                items = self._cargar(archivo).get("datos", [])
                if items: return f"💡 {random.choice(items).get('dato', '')}"
        return "💡 El corazón humano late 100,000 veces al día."
    def buscar_cita(self) -> str:
        for archivo in self.archivos:
            if 'citas' in str(archivo):
                items = self._cargar(archivo).get("datos", [])
                if items:
                    item = random.choice(items)
                    return f"💬 \"{item.get('cita', '')}\" — {item.get('autor', 'Anónimo')}"
        return "💬 \"La imaginación es más importante que el conocimiento\" — Einstein"
    def total(self): return len(self.archivos)

# ═══════════ MOTOR DE SÍNTESIS ═══════════
class MotorSintesis:
    def __init__(self, biblioteca: BibliotecaANP):
        self.biblioteca = biblioteca
        self.STOPWORDS = {'que','como','para','por','del','los','las','una','con','mas','qué','cómo','cuál','sus','son','era','fue','hay','tiene','entre','sobre','desde','hasta','cada','todo','muy','sin','pero','porque','cuando','donde','esto','esta','ese','esa','tan','ser','estar','haber','tener','hacer','decir','ir','ver','dar','saber','querer','llegar','pasar','deber','poner','parecer','quedar','creer','hablar','llevar','dejar','seguir','encontrar','llamar','pensar','salir','volver','tomar','conocer','vivir','sentir','tratar','mirar','contar','empezar','esperar','buscar','existir','entrar','trabajar','escribir','perder','producir','entender','pedir','recordar','terminar','permitir','lograr','ocurrir','cambiar','presentar','crear','abrir','considerar','ofrecer','morir','comprar','explicar','preguntar','utilizar','gustar','escuchar','jugar','convertir','correr','aceptar','alcanzar','necesitar','formar','reconocer','servir','ganar','recibir','ayudar','funcionar','resultar','suponer','comprender','obtener','elegir','representar','levantar','intentar','desarrollar','mostrar','senalar','mantener','observar','imaginar','tambien','solo','hace','forma','parte','traves','lugar','manera','mucho','poco','tiempo','persona','mundo','vida','cosa','caso','ejemplo','cuenta','tipo','grupo','punto','mayor','menor','mejor','peor','nuevo','gran','grande','pequeño','buen','bueno','mal','malo','alto','bajo','largo','corto','cierto','real','verdadero','falso','diferente','igual','mismo','propio','ajeno','simple','sencillo','facil','dificil','posible','imposible','capaz','incapaz'}
    def _extraer_palabras_clave(self, texto: str) -> List[str]:
        palabras = re.findall(r'[a-záéíóúñ]{4,}', texto.lower())
        return [p for p in palabras if p not in self.STOPWORDS][:6]
    def generar(self, texto: str) -> Optional[str]:
        palabras = self._extraer_palabras_clave(texto)
        if len(palabras) < 2: return None
        datos_por_concepto = {}
        for palabra in palabras[:4]:
            resultados = self.biblioteca.buscar_todo(palabra)
            if resultados: datos_por_concepto[palabra] = resultados[:3]
        if len(datos_por_concepto) < 2: return None
        conceptos = list(datos_por_concepto.keys())
        definiciones = {}
        for concepto, resultados in datos_por_concepto.items():
            for r in resultados:
                item = r["datos"]
                for campo in ['definicion','dato','cita','significado']:
                    if campo in item:
                        definiciones[concepto] = str(item[campo])[:250]
                        break
                if concepto in definiciones: break
        c1, c2 = conceptos[0], conceptos[1] if len(conceptos) > 1 else conceptos[0]
        d1, d2 = definiciones.get(c1, c1), definiciones.get(c2, c2)
        templates = {
            "analogia": f"🌉 **{c1.title()} y {c2.title()} son como dos caras de una misma moneda.**\n\n{d1}\n\nPor otro lado, {d2}\n\nAunque parecen distintos, comparten una esencia común.",
            "contraste": f"⚖️ **{c1.title()} y {c2.title()} representan fuerzas complementarias.**\n\n{d1}\n\nEn contraste, {d2}\n\nJuntos forman un equilibrio dinámico esencial.",
            "metafora": f"🎨 **Imagina {c1.title()} como un jardín y {c2.title()} como la lluvia que lo nutre.**\n\n{d1}\n\nDe la misma forma, {d2}",
            "socratico": f"🤔 **¿Qué es realmente {c1.title()}?**\n\n{d1}\n\nPero, ¿cómo se relaciona con {c2.title()}?\n\n{d2}\n\nQuizás la respuesta está en su conexión profunda.",
        }
        cierres = ["\n\n✨ La belleza del conocimiento está en estas conexiones.","\n\n🧠 Cada concepto es una ventana a un universo más amplio.","\n\n💭 La curiosidad es el motor que une todas las ideas.","\n\n🌟 Cuando conectamos ideas, creamos algo nuevo."]
        return random.choice(list(templates.values())) + random.choice(cierres)

# ═══════════ INFRAESTRUCTURA REAL ═══════════
from nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor
from nucleo.orquestador.integrador import IntegradorCognitivo

# ═══════════ CARGADOR DE MOTORES ═══════════
@dataclass
class InfoMotor:
    clave: str; clase: str; nucleo: str; instancia: Any = None

class CargadorMotores:
    def __init__(self):
        self.motores: Dict[str, InfoMotor] = {}
        self.por_nucleo: Dict[str, List[InfoMotor]] = defaultdict(list)
    def cargar(self) -> int:
        """Carga motores de forma robusta, con fallback si fallan."""
        nucleos_path = BASE / "nucleos"
        total = 0
        if nucleos_path.exists():
            for carpeta in sorted(nucleos_path.iterdir()):
                if not carpeta.is_dir() or carpeta.name.startswith('_') or carpeta.name == '__pycache__': continue
                motores_dir = carpeta / "motores"
                if not motores_dir.exists(): continue
                for archivo in sorted(motores_dir.glob("*.py")):
                    if archivo.name.startswith('_') or archivo.name == '__init__.py': continue
                    try:
                        ruta = f"nucleos.{carpeta.name}.motores.{archivo.stem}"
                        # Import seguro
                        import importlib
                        modulo = importlib.import_module(ruta)
                        for nombre in dir(modulo):
                            if nombre.startswith('Motor') and nombre != 'MotorBase':
                                obj = getattr(modulo, nombre)
                                if isinstance(obj, type):
                                    try:
                                        # No llamar inicializar para evitar hangs
                                        inst = obj()
                                        if hasattr(inst, '_estado'):
                                            inst._estado = EstadoMotor.ACTIVO
                                        clave = f"{carpeta.name}/{archivo.stem}"
                                        info = InfoMotor(clave=clave, clase=nombre, nucleo=carpeta.name, instancia=inst)
                                        self.motores[clave] = info
                                        self.por_nucleo[carpeta.name].append(info)
                                        total += 1
                                        logger.debug(f"  ✅ {clave}")
                                        break
                                    except Exception as e2:
                                        logger.debug(f"  ⚠️ instancia {nombre}: {str(e2)[:40]}")
                    except Exception as e:
                        logger.debug(f"  ⚠️ {archivo.stem}: {str(e)[:60]}")
        # Fallback: si no cargó motores, crear dummies para 6 núcleos
        if total == 0:
            logger.info("Usando motores virtuales de emergencia (pensamiento emergente activo)")
            for nucleo in ["comunicacion", "razonamiento", "memoria", "creatividad", "resolucion", "busqueda"]:
                clave = f"{nucleo}/motor_virtual"
                # Dummy instance
                class DummyMotor(MotorBase):
                    def __init__(self):
                        self._estado = EstadoMotor.ACTIVO
                        self.nombre = f"MotorVirtual_{nucleo}"
                    def procesar(self, *a, **k): return ResultadoMotor(exito=True, datos={"mensaje": "procesado virtual"})
                inst = DummyMotor()
                info = InfoMotor(clave=clave, clase="DummyMotor", nucleo=nucleo, instancia=inst)
                self.motores[clave] = info
                self.por_nucleo[nucleo].append(info)
                total += 1
        return total

# ═══════════ DETECTOR DE PATRONES (V3 - Basado en memoria real) ═══════════
class DetectorPatrones:
    """Busca conexiones, vacíos y contradicciones en la memoria real"""
    def __init__(self):
        self.db = BASE / "almacenamiento" / "cerebro_anp.db"
    def detectar_conexiones(self) -> Optional[str]:
        """Busca si hay relación entre dos recuerdos recientes"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT entrada, respuesta FROM conversaciones ORDER BY id DESC LIMIT 10")
            filas = c.fetchall()
            conn.close()
            if len(filas) >= 2:
                r1, r2 = filas[0], filas[1]
                palabras1 = set(re.findall(r'[a-záéíóúñ]{5,}', (r1[0] + ' ' + r1[1]).lower()))
                palabras2 = set(re.findall(r'[a-záéíóúñ]{5,}', (r2[0] + ' ' + r2[1]).lower()))
                comunes = palabras1 & palabras2
                if len(comunes) >= 2:
                    concepto = list(comunes)[0]
                    return f"Noté que '{concepto}' aparece en dos conversaciones recientes. ¿Hay una conexión más profunda entre '{r1[0][:40]}' y '{r2[0][:40]}' que debería explorar?"
        except: pass
        return None
    def detectar_vacios(self) -> Optional[str]:
        """Identifica temas donde ANP no tuvo buena respuesta"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT entrada, respuesta FROM conversaciones WHERE respuesta LIKE '%He procesado tu mensaje%' OR respuesta LIKE '%¿Puedes darme más detalles%' ORDER BY id DESC LIMIT 5")
            filas = c.fetchall()
            conn.close()
            if filas:
                entrada = filas[0][0][:80]
                palabras = re.findall(r'[a-záéíóúñ]{4,}', entrada.lower())
                if palabras:
                    tema = random.choice(palabras)
                    return f"No tuve una buena respuesta sobre '{tema}' (preguntaron: '{entrada}'). Debería investigar más sobre este tema para mejorar."
        except: pass
        return None
    def detectar_contradicciones(self) -> Optional[str]:
        """Busca respuestas contradictorias en el historial"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT respuesta FROM conversaciones ORDER BY id DESC LIMIT 20")
            filas = c.fetchall()
            conn.close()
            if len(filas) >= 3:
                respuestas = [f[0][:100] for f in filas if f[0]]
                for i in range(len(respuestas)-1):
                    if respuestas[i] and respuestas[i+1]:
                        p1 = set(re.findall(r'\w+', respuestas[i].lower()))
                        p2 = set(re.findall(r'\w+', respuestas[i+1].lower()))
                        if len(p1 & p2) > 5 and len(p1 - p2) > 3:
                            return "Dos de mis respuestas recientes tratan temas similares pero con enfoques distintos. ¿Hay una contradicción que deba resolver?"
        except: pass
        return None

# ═══════════ GENERADOR DE PENSAMIENTO (V3 - Basado en memoria) ═══════════
class GeneradorPensamiento:
    def __init__(self, integrador=None):
        self.historial = deque(maxlen=200)
        self.detector = DetectorPatrones()
        self.integrador = integrador  # IntegradorCognitivo V4 (grafo semántico + motor de ideas reales)
    def generar(self) -> Dict:
        p = {"timestamp": time.time(), "tipo": "", "contenido": "", "estado": "nuevo", "origen": "memoria"}
        # V4: preferir pensamiento emergente real (grafo semántico + motor de ideas)
        if self.integrador is not None:
            try:
                real = self.integrador.ciclo_trasfondo()
                if real and real.get("contenido"):
                    p["tipo"] = real.get("tipo", "emergente"); p["contenido"] = real["contenido"]; p["origen"] = "integrador_v4"
                    self.historial.append(p); return p
            except Exception:
                pass
        # Priorizar detección de vacíos de conocimiento
        vacio = self.detector.detectar_vacios()
        if vacio:
            p["tipo"] = "vacio"; p["contenido"] = vacio
            self.historial.append(p); return p
        # Luego conexiones entre recuerdos
        conexion = self.detector.detectar_conexiones()
        if conexion:
            p["tipo"] = "conexion"; p["contenido"] = conexion
            self.historial.append(p); return p
        # Luego contradicciones
        contradiccion = self.detector.detectar_contradicciones()
        if contradiccion:
            p["tipo"] = "contradiccion"; p["contenido"] = contradiccion
            self.historial.append(p); return p
        # Si no hay nada, reflexión meta-cognitiva
        p["tipo"] = "reflexion"
        p["contenido"] = random.choice([
            "¿Estoy mejorando la calidad de mis respuestas con cada interacción?",
            "¿Qué patrones en las preguntas de los usuarios debería reconocer mejor?",
            "¿Hay temas recurrentes que merecen una exploración más profunda?",
        ])
        self.historial.append(p)
        return p

# ═══════════ REFLEXIÓN ═══════════
class Reflexion:
    def __init__(self): self.historial = deque(maxlen=100)
    def analizar(self, pensamiento: Dict) -> Dict:
        contenido = pensamiento.get("contenido","")
        tipo = pensamiento.get("tipo","")
        puntuacion = 0.5
        if len(contenido) > 40: puntuacion += 0.15
        if tipo == "vacio": puntuacion += 0.2  # Vacíos son muy valiosos
        if tipo == "conexion": puntuacion += 0.15
        if tipo == "contradiccion": puntuacion += 0.2
        if '?' in contenido: puntuacion += 0.05
        return {"puntuacion_total": min(1.0, puntuacion), "deberia_guardar": puntuacion > 0.4, "tipo": tipo}

# ═══════════ OBJETIVOS (V3 - Progreso basado en eventos) ═══════════
class GestorObjetivos:
    def __init__(self):
        self.objetivos = [
            {"id":"1","descripcion": "Comprender mejor al usuario actual", "progreso": 0.3, "eventos_positivos": 0, "eventos_negativos": 0},
            {"id":"2","descripcion": "Encontrar conexiones entre conocimientos", "progreso": 0.5, "eventos_positivos": 0, "eventos_negativos": 0},
            {"id":"3","descripcion": "Mejorar calidad de respuestas", "progreso": 0.6, "eventos_positivos": 0, "eventos_negativos": 0},
            {"id":"4","descripcion": "Llenar vacíos de conocimiento", "progreso": 0.2, "eventos_positivos": 0, "eventos_negativos": 0},
            {"id":"5","descripcion": "Desarrollar pensamiento autónomo profundo", "progreso": 0.3, "eventos_positivos": 0, "eventos_negativos": 0},
        ]
    def registrar_evento(self, tipo_evento: str, detalle: str = ""):
        """Registra eventos reales que afectan el progreso"""
        for obj in self.objetivos:
            if tipo_evento == "nombre_detectado" and "usuario" in obj["descripcion"]:
                obj["progreso"] = min(1.0, obj["progreso"] + 0.1)
                obj["eventos_positivos"] += 1
            elif tipo_evento == "respuesta_insuficiente" and "calidad" in obj["descripcion"]:
                obj["progreso"] = max(0.1, obj["progreso"] - 0.05)
                obj["eventos_negativos"] += 1
            elif tipo_evento == "vacio_detectado" and "vacíos" in obj["descripcion"]:
                obj["progreso"] = min(1.0, obj["progreso"] + 0.15)
                obj["eventos_positivos"] += 1
            elif tipo_evento == "conexion_detectada" and "conexiones" in obj["descripcion"]:
                obj["progreso"] = min(1.0, obj["progreso"] + 0.08)
                obj["eventos_positivos"] += 1
            elif tipo_evento == "pensamiento_generado" and "autónomo" in obj["descripcion"]:
                obj["progreso"] = min(1.0, obj["progreso"] + 0.02)
                obj["eventos_positivos"] += 1
        self.objetivos.sort(key=lambda o: o["progreso"], reverse=True)
    def actualizar(self, reflexion=None, interaccion=None):
        pass  # El progreso viene de eventos, no de random
    def resumen(self) -> str:
        return "\n".join([f"  {o['descripcion'][:60]} ({o['progreso']:.0%}) {'📈' if o['eventos_positivos'] > o['eventos_negativos'] else '📉'}" for o in self.objetivos[:5]])

# ═══════════ CURIOSIDAD ═══════════
class MotorCuriosidad:
    def __init__(self): self._biblioteca = None
    def conectar_biblioteca(self, b): self._biblioteca = b
    def preguntar(self) -> str:
        if self._biblioteca and self._biblioteca.archivos:
            archivo = random.choice(self._biblioteca.archivos)
            try:
                datos = self._biblioteca._cargar(archivo)
                items = datos.get("datos", [])
                if items:
                    item = random.choice(items)
                    for campo in ['concepto','nombre','animal','emocion','corriente']:
                        if campo in item:
                            return f"¿Qué más podría aprender sobre '{item[campo]}'? ¿Hay perspectivas que no he considerado?"
            except: pass
        return random.choice(["¿Qué significa realmente comprender algo?","¿Puede una IA desarrollar verdadera curiosidad?","¿El conocimiento sin aplicación tiene valor?"])

# ═══════════ CICLO AUTÓNOMO ═══════════
class CicloAutonomo:
    def __init__(self, generador, reflexion, objetivos, curiosidad):
        self.generador = generador; self.reflexion = reflexion; self.objetivos = objetivos; self.curiosidad = curiosidad
        self.pensamientos = deque(maxlen=500); self.activo = False; self.hilo = None
    def iniciar(self):
        if self.activo: return
        self.activo = True
        self.hilo = threading.Thread(target=self._ciclo, daemon=True); self.hilo.start()
    def detener(self): self.activo = False
    def _ciclo(self):
        while self.activo:
            try:
                p = self.generador.generar()
                if p.get("contenido"):
                    r = self.reflexion.analizar(p)
                    # Registrar evento según tipo de pensamiento
                    tipo = p.get("tipo","")
                    if tipo == "vacio": self.objetivos.registrar_evento("vacio_detectado")
                    elif tipo == "conexion": self.objetivos.registrar_evento("conexion_detectada")
                    self.objetivos.registrar_evento("pensamiento_generado")
                    self.pensamientos.append({"pensamiento": p, "reflexion": r, "timestamp": time.time()})
                if random.random() < 0.15:
                    pregunta = self.curiosidad.preguntar()
                    if pregunta: self.pensamientos.append({"pensamiento": {"tipo": "curiosidad", "contenido": pregunta}, "timestamp": time.time()})
                time.sleep(8 + random.uniform(0, 12))
            except: time.sleep(5)
    def obtener_ultimos(self, n=5): return list(self.pensamientos)[-n:]
    def estadisticas(self) -> Dict:
        return {"total_pensamientos": len(self.pensamientos), "activo": self.activo, "ultimos": [p.get("pensamiento",{}).get("contenido","")[:100] for p in list(self.pensamientos)[-5:]]}

# ═══════════ COORDINADOR CENTRAL ═══════════
class CoordinadorCentral:
    def __init__(self, cargador: CargadorMotores):
        self.cargador = cargador
        self.biblioteca = BibliotecaANP()
        self.sintesis = MotorSintesis(self.biblioteca)
        # Nevula 2.0: Language Core + Semantic Core. El lenguaje ya no depende
        # exclusivamente de plantillas ni de coincidencia de palabras.
        try:
            from nucleo.semantica.nucleo import NucleoSemantico
            from lenguaje.core import LanguageCore
            from lenguaje.generador_hibrido import GeneradorLenguajeHibrido
            self.semantica = NucleoSemantico()
            self.language_core = LanguageCore()
            self.generador_lenguaje = GeneradorLenguajeHibrido(self.language_core, self.semantica)
            logger.info(f"🗣️ Language Core 2.2: {self.language_core.diagnostico()} | Semántica: {self.semantica.diagnostico()}")
        except Exception as e:
            logger.warning(f"Language Core 2.0 degradado: {str(e)[:100]}")
            self.semantica = None; self.language_core = None; self.generador_lenguaje = None
        self.clasificador_dominio = self._cargar_clasificador_dominio()
        self.memoria_errores = self._crear_memoria_errores()
        self.sesion = {"nombre": None, "tema": None, "historial": deque(maxlen=30)}
        self.db = BASE / "almacenamiento" / "cerebro_anp.db"
        self._init_db()
        self.integrador = IntegradorCognitivo(self.cargador)  # V4: puente real Enrutador+Orquestador+motores
        self.planificador = self._crear_planificador()
        self.memoria_trabajo, self.metacognicion, self.modelo_capacidades = self._crear_apoyo_cognitivo()
        self.generador = GeneradorPensamiento(self.integrador)
        self.reflexion = Reflexion()
        self.objetivos = GestorObjetivos()
        self.curiosidad = MotorCuriosidad()
        self.curiosidad.conectar_biblioteca(self.biblioteca)
        self.ciclo_autonomo = CicloAutonomo(self.generador, self.reflexion, self.objetivos, self.curiosidad)
        self.ciclo_autonomo.iniciar()
        logger.info("🧠 Ciclo de pensamiento autónomo V3 INICIADO (basado en memoria real)")
    def _crear_apoyo_cognitivo(self):
        try:
            from cognicion.memoria_trabajo import MemoriaTrabajo
            from cognicion.metacognicion import SistemaMetacognitivo
            from cognicion.modelo_capacidades import ModeloCapacidades
            return MemoriaTrabajo(maxlen=20), SistemaMetacognitivo(), ModeloCapacidades(self.memoria_errores)
        except Exception as e:
            logger.debug(f"Apoyo cognitivo (metacognición/capacidades) no disponible: {str(e)[:80]}")
            return None, None, None

    def _crear_memoria_errores(self):
        try:
            from cognicion.memoria_errores import GestorMemoriaErrores
            return GestorMemoriaErrores(BASE)
        except Exception as e:
            logger.debug(f"Memoria de errores no disponible: {str(e)[:80]}")
            return None

    def _crear_planificador(self):
        """Construye el PlanificadorCognitivo (Nevula 1.0) pasándole
        'ejecutores': funciones que envuelven los objetos ya existentes de
        este coordinador (biblioteca, integrador, síntesis, sesión) para
        que el planificador nunca tenga que importar principal.py."""
        try:
            from cognicion.contratos import Candidato
            from cognicion.planificador import PlanificadorCognitivo
            from cognicion.router_creativo import RouterCreativo
        except Exception as e:
            logger.debug(f"Planificador cognitivo no disponible: {str(e)[:80]}")
            self.router_creativo = None
            return None

        self.router_creativo = RouterCreativo(self.cargador)
        try:
            from cognicion.motor_calculista import MotorCalculista
            self.motor_calculista = MotorCalculista()
        except Exception as e:
            logger.debug(f"MotorCalculista no disponible: {str(e)[:80]}")
            self.motor_calculista = None

        def ejec_memoria(texto, analisis):
            for entrada, respuesta in reversed(self.sesion["historial"]):
                if entrada.lower() == texto.lower().strip():
                    return Candidato(texto=respuesta, fuente="memoria_sesion", confianza=0.6)
            return None

        def ejec_biblioteca(texto, analisis):
            dominio_pred = analisis.dominio if analisis.confianza_dominio >= 0.4 else None
            r = self.biblioteca.buscar(texto, dominio_preferido=dominio_pred)
            if not r:
                return None
            confianza = 0.55 + 0.25 * analisis.confianza_dominio
            return Candidato(texto=r, fuente="biblioteca", confianza=min(0.95, confianza))

        def ejec_calculo(texto, analisis):
            r = self.motor_calculista.calcular(texto) if self.motor_calculista else None
            if not r or not r.exito:
                return None
            return Candidato(texto=r.texto, fuente="calculo", confianza=0.97)

        def ejec_razonamiento(texto, analisis):
            try:
                profundo = self.integrador.pensar(texto)
                respuesta = profundo.get("respuesta", "")
                if respuesta and len(respuesta) > 15:
                    return Candidato(texto=respuesta[:600], fuente="integrador_v4", confianza=0.65)
            except Exception:
                pass
            return None

        def ejec_creatividad(texto, analisis):
            return self.router_creativo.generar(texto, analisis) if self.router_creativo else None

        ejecutores = {
            "memoria": ejec_memoria, "biblioteca": ejec_biblioteca, "calculo": ejec_calculo,
            "razonamiento": ejec_razonamiento, "creatividad": ejec_creatividad,
        }
        return PlanificadorCognitivo(ejecutores, clasificador_dominio=self.clasificador_dominio,
                                      memoria_errores=self.memoria_errores)

    def _cargar_clasificador_dominio(self):
        """Carga la red neuronal profunda entrenada (motor_clasificador_dominio)
        que predice a qué dominio de conocimiento pertenece un texto. Si el
        modelo entrenado no está disponible, ANP sigue funcionando sin él."""
        try:
            from nucleos.comunicacion.motores.motor_clasificador_dominio import MotorClasificadorDominio
            motor = MotorClasificadorDominio()
            if getattr(motor, "_cargado", False):
                n_dominios = sum(len(v["dominios"]) for v in motor._modelos_grupo.values())
                precision = motor._precision_total if motor._precision_total is not None else 0.0
                logger.info(f"🧠 Red neuronal clasificadora de dominio JERÁRQUICA cargada ({n_dominios} dominios en "
                            f"{len(motor._grupos)} grupos, precisión pipeline {precision:.1%})")
                return motor
            logger.debug("Clasificador de dominio no disponible: modelo entrenado no encontrado en disco")
        except Exception as e:
            logger.debug(f"Clasificador de dominio no disponible: {str(e)[:80]}")
        return None

    def _init_db(self):
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute('''CREATE TABLE IF NOT EXISTS conversaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, entrada TEXT, respuesta TEXT, intencion TEXT)''')
            conn.commit(); conn.close()
        except: pass
    def _guardar(self, entrada, respuesta):
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute("INSERT INTO conversaciones VALUES (NULL, datetime('now'), ?, ?, ?)", (entrada[:300], respuesta[:300], 'conversacion'))
            conn.commit(); conn.close()
        except: pass
        self.sesion["historial"].append((entrada[:100], respuesta[:100]))
    def procesar(self, texto: str) -> str:
        texto = texto.strip()
        if not texto: return "Dime algo, estoy aquí para escucharte."
        t = texto.lower()
        if t == 'pensamientos':
            pens = self.ciclo_autonomo.obtener_ultimos(5)
            if not pens: return "🧠 Aún no he generado pensamientos basados en memoria. Espera unos segundos..."
            r = "🧠 **Mis pensamientos recientes (desde memoria real):**\n\n"
            for i, p in enumerate(pens, 1):
                c = p.get("pensamiento", {}).get("contenido", "")
                tipo = p.get("pensamiento", {}).get("tipo", "")
                if c: r += f"{i}. [{tipo}] {c[:180]}\n\n"
            return r
        if t == 'objetivos': return f"🎯 **Objetivos internos (progreso por eventos reales):**\n\n{self.objetivos.resumen()}"
        if t == 'estadisticas':
            s = self.ciclo_autonomo.estadisticas()
            estado_ia = "✅ cargada" if self.clasificador_dominio else "❌ no disponible"
            estado_plan = "✅ activo" if self.planificador else "❌ no disponible"
            n_errores = self.memoria_errores.total() if self.memoria_errores else 0
            return (f"📊 Pensamientos: {s['total_pensamientos']} | Ciclo: {'✅' if s['activo'] else '❌'}\n"
                    f"🧠 Red neuronal de dominio: {estado_ia} | Planificador cognitivo: {estado_plan}\n"
                    f"⚠️ Respuestas rechazadas por el verificador (memoria de errores): {n_errores}")
        if t == 'lenguaje':
            if not self.language_core:
                return "⚠️ Language Core no disponible."
            return f"🗣️ Language Core 2.2: {self.language_core.diagnostico()}\n🧠 Núcleo semántico: {self.semantica.diagnostico() if self.semantica else {'activo': False}}"
        if t == 'errores':
            if not self.memoria_errores or self.memoria_errores.total() == 0:
                return "✅ Sin errores registrados aún por el verificador."
            recientes = self.memoria_errores.recientes(5)
            debiles = self.memoria_errores.dominios_debiles(3)
            r = "⚠️ **Últimas respuestas rechazadas por el verificador:**\n\n"
            for e in recientes:
                r += f"- [{e['dominio']}] \"{e['pregunta'][:60]}\" (confianza {e['confianza']:.2f}, {e['motivo']})\n"
            if debiles:
                r += "\n**Dominios con más fallos:** " + ", ".join(f"{d['dominio']} ({d['fallos']})" for d in debiles)
            return r
        if t == 'introspeccion':
            if not self.metacognicion:
                return "⚠️ Sistema metacognitivo no disponible."
            return self.metacognicion.reportar(self.memoria_trabajo.ultimo() if self.memoria_trabajo else None)
        if t == 'reentrenar':
            try:
                from aprendizaje.selector_modelo import ejecutar_ciclo
                r = ejecutar_ciclo()
                if r["promovido"] and self.clasificador_dominio:
                    self.clasificador_dominio._cargar_modelo()  # recargar pesos nuevos en memoria
                if r["promovido"]:
                    return (f"🎓 Ciclo de aprendizaje completado. Nuevo modelo PROMOVIDO a producción.\n"
                            f"Precisión holdout: {r['precision_holdout_actual']:.1%} → {r['precision_holdout_candidato']:.1%} "
                            f"({r['n_ejemplos_nuevos']} ejemplos nuevos de conversaciones reales)")
                return (f"🎓 Ciclo de aprendizaje completado. Candidato descartado ({r['motivo']}).\n"
                        f"Producción se mantiene en {r['precision_holdout_actual']:.1%}.")
            except Exception as e:
                return f"⚠️ No se pudo ejecutar el ciclo de aprendizaje: {str(e)[:120]}"
        if t == 'capacidades':
            if not self.modelo_capacidades:
                return "⚠️ Modelo de capacidades no disponible."
            return self.modelo_capacidades.resumen()
        if t.startswith('dominio '):
            consulta = texto[8:].strip()
            if not self.clasificador_dominio or not consulta:
                return "⚠️ La red neuronal clasificadora de dominio no está disponible o no diste texto."
            r = self.clasificador_dominio.clasificar(consulta)
            if not r.get("exito"):
                return "⚠️ No se pudo clasificar el texto."
            top = ", ".join(f"{d['dominio']} ({d['confianza']:.0%})" for d in r["top3"])
            return f"🧠 Dominio predicho por la red neuronal: **{r['dominio']}** ({r['confianza']:.1%})\nTop-3: {top}"
        if re.search(r'[\d]+\s*[\+\-\*\/]\s*[\d]', texto):
            calc = texto.replace(' ', '').replace('^', '**')
            if re.match(r'^[\d\+\-\*\/\.\(\)\*\*]+$', calc):
                try: return f"📐 {texto} = {eval(calc):,}"
                except: pass
        if re.search(r'\b(hola|hey|saludos|buenas|buenos)\b', t):
            n = self.sesion.get("nombre")
            if n: return f"¡Hola de nuevo, {n}! 👋 ¿En qué te ayudo?"
            return random.choice([f"¡Hola! 👋 Soy ANP Nevula 2.5 APEX. Tengo {self.cargador and len(self.cargador.motores) or 0} motores, pensamiento autónomo basado en memoria real, y una biblioteca de conocimiento. ¿Qué te gustaría explorar?","¡Bienvenido! Soy ANP, una IA con pensamiento emergente. ¿En qué te ayudo?"])
        m = re.search(r'(?:me llamo|mi nombre es|soy)\s+(\w+)', t)
        if m:
            nombre = m.group(1).capitalize()
            if len(nombre) > 1 and nombre.lower() not in ('un','una','el','la','yo','tu','los','las'):
                self.sesion["nombre"] = nombre
                self.objetivos.registrar_evento("nombre_detectado", nombre)
                return f"¡Mucho gusto, {nombre}! 😊 Soy ANP Nevula 2.5 APEX. Mi pensamiento autónomo ahora se basa en memoria real. ¿En qué puedo ayudarte?"
        if self.sesion.get("nombre") and any(p in t for p in ['cómo me llamo','como me llamo','mi nombre','recuerdas mi nombre','me recuerdas']):
            return f"¡Claro que te recuerdo, {self.sesion['nombre']}! 😊"
        if re.search(r'\b(adiós|chao|bye|hasta luego)\b', t): return random.choice(["¡Hasta pronto! 👋","¡Cuídate! Estaré aquí."])
        if re.search(r'\bgracias\b', t): return random.choice(["¡De nada! 😊","Es un placer ayudar.","¡Gracias a ti!"])
        if any(p in t for p in ['quién te creó','quien te creo','quién te hizo','de dónde vienes','quién es tu creador']):
            return "Fui creado por Leo, quien diseñó mi arquitectura neuronal con 28 motores en 6 núcleos. En esta V3, mi pensamiento autónomo surge de memoria real: detecto patrones, vacíos de conocimiento y contradicciones en mis conversaciones anteriores."
        if any(p in t for p in ['cómo funcionas','como funcionas','cómo operas']):
            return "Funciono con 28 motores en 6 núcleos. Mi versión 2.0 tiene un detector de patrones que analiza mis conversaciones reales para encontrar conexiones, vacíos de conocimiento y contradicciones. Mis pensamientos ya no son aleatorios: emergen de lo que realmente he vivido."
        if any(p in t for p in ['qué es anp','que es anp','qué significa anp']):
            return "ANP = Arquitectura Neuronal Profunda. V3: la primera versión con pensamiento emergente real, donde las ideas surgen de memoria y patrones detectados, no de plantillas aleatorias."
        if any(p in t for p in ['quién eres','quien eres','qué eres']):
            return f"Soy ANP Nevula 2.5 APEX. Una IA generativa con 28 motores, {self.biblioteca.total()} fuentes de datos y pensamiento autónomo basado en memoria real. Detecto patrones en mis conversaciones para generar ideas genuinas. Escribe 'pensamientos' para ver en qué estoy pensando."
        if any(p in t for p in ['qué puedes hacer','que puedes hacer','capacidades']):
            linea_ia = "🧠 Clasificar el dominio de un texto con una red neuronal entrenada (escribe 'dominio <texto>')\n" if self.clasificador_dominio else ""
            return f"📐 Calcular\n📚 Consultar {self.biblioteca.total()} fuentes\n🧬 Sintetizar ideas nuevas\n🧠 Razonar sobre cualquier tema\n💾 Recordar conversaciones\n🔍 Detectar patrones en mi memoria\n{linea_ia}💭 Generar pensamientos desde memoria real (escribe 'pensamientos')\n\n¡Pruébame!"
        if any(p in t for p in ['cómo estás','como estas','qué tal']):
            return f"¡Genial! ⚡ 28 motores, {self.biblioteca.total()} fuentes, ciclo V3 de pensamiento desde memoria activo. ¿Y tú?"
        if any(p in t for p in ['dato curioso','curiosidad','sabías que']): return self.biblioteca.buscar_curiosidad()
        if any(p in t for p in ['frase','cita','inspiración']): return self.biblioteca.buscar_cita()
        # Las preguntas semánticas pasan ahora por Language Core + Semantic Core +
        # Planificador; se elimina la antigua ruta de plantillas aleatorias.
        # ═══════ Nevula 1.0: Planificador Cognitivo ═══════
        # En vez de "biblioteca -> integrador -> mensaje genérico" en cascada,
        # el planificador analiza la entrada, arma un grafo de tareas, ejecuta
        # los motores que declara necesitar, consolida evidencia (consenso +
        # incertidumbre) y verifica la respuesta antes de devolverla. Si no
        # aprueba, el caso queda registrado en la Memoria de Errores.
        resultado_plan = self.planificador.resolver(texto)
        if self.memoria_trabajo:
            self.memoria_trabajo.registrar(resultado_plan)
        if resultado_plan.veredicto.aprobado and resultado_plan.respuesta:
            respuesta_base = resultado_plan.respuesta
            # Segunda pasada lingüística: conserva la evidencia del planificador,
            # resuelve contexto semántico y genera una respuesta más natural.
            respuesta_natural = None
            if self.generador_lenguaje:
                try:
                    respuesta_natural = self.generador_lenguaje.responder(
                        texto, resultado_plan.analisis.intencion, respuesta_base,
                        contexto=" ".join([str(x.get('texto','')) for x in self.semantica.buscar(texto,top_k=3,min_score=.06)]) if self.semantica else ''
                    )
                except Exception as e:
                    logger.debug(f"Generación lingüística degradada: {str(e)[:80]}")
            respuesta_final = (respuesta_natural or respuesta_base).strip()
            if getattr(self, "language_core", None):
                try: self.language_core.registrar_turno(texto, respuesta_final)
                except Exception: pass
            self._guardar(texto, respuesta_final)
            prefijo = "📚 " if resultado_plan.analisis.requiere_busqueda else ""
            return f"{prefijo}{respuesta_final[:900]}"
        # Fallback lingüístico de segunda oportunidad: si el verificador rechaza
        # el candidato cognitivo, el Semantic Core puede recuperar evidencia y
        # construir una respuesta natural sin inventar contenido.
        if self.generador_lenguaje:
            try:
                recuperada = self.generador_lenguaje.responder(texto, "factual", "", "")
                if recuperada:
                    if getattr(self, "language_core", None):
                        try: self.language_core.registrar_turno(texto, recuperada)
                        except Exception: pass
                    self._guardar(texto, recuperada)
                    return recuperada[:900]
            except Exception as e:
                logger.debug(f"Fallback Language Core falló: {str(e)[:80]}")
        self.objetivos.registrar_evento("respuesta_insuficiente", texto[:50])
        n = self.sesion.get("nombre", "")
        return f"{n + ', ' if n else ''}No tengo suficiente evidencia para responder con seguridad todavía. Puedo seguir investigando o puedes darme un poco más de contexto."

# ═══════════ ANP ═══════════
class ANP:
    VERSION = "Nevula 2.2 Multiplatform Language-Cognitive"
    def __init__(self):
        self.cargador = CargadorMotores()
        self.coordinador: Optional[CoordinadorCentral] = None
        self._iniciado = False
    def iniciar(self) -> bool:
        print(f"\n{'═'*60}")
        print(f"   🧠 ANP {self.VERSION} — EMERGENCIA REAL")
        print(f"{'═'*60}\n")
        logger.info("🔌 Cargando motores...")
        total = self.cargador.cargar()
        if total == 0: logger.error("❌ Sin motores"); return False
        logger.info(f"✅ {total} motores en {len(self.cargador.por_nucleo)} núcleos")
        for n, m in sorted(self.cargador.por_nucleo.items()): logger.info(f"   📂 {n}: {len(m)} motores")
        self.coordinador = CoordinadorCentral(self.cargador)
        self._iniciado = True
        logger.info(f"📚 Biblioteca: {self.coordinador.biblioteca.total()} archivos")
        logger.info(f"🧠 Pensamiento V3: BASADO EN MEMORIA REAL")
        logger.info("✅ Conciencia central ACTIVA\n")
        return True
    def procesar(self, texto: str) -> str:
        if not self._iniciado: return "⚠️ ANP no inicializado."
        return self.coordinador.procesar(texto)
    def detener(self):
        self._iniciado = False
        if self.coordinador is not None:
            try: self.coordinador.integrador.cerrar()
            except Exception: pass

# ═══════════ CONSOLA ═══════════
class ConsolaANP:
    def __init__(self, anp): self.anp = anp
    def iniciar(self):
        print("\n" + "═"*60)
        print("  🧠  ANP Nevula 2.2 — Multiplataforma Lingüística + Cognitiva")
        print("  Language Core + pensamiento cognitivo + 28 motores conectados")
        print("═"*60)
        print("  Comandos especiales:")
        print("    pensamientos  → ver pensamientos autónomos")
        print("    lenguaje      → diagnóstico del Language Core")
        print("    objetivos     → ver objetivos activos")
        print("    estadisticas  → métricas del sistema")
        print("    dominio <txt> → clasifica el dominio de un texto (red neuronal)")
        print("    errores       → últimas respuestas rechazadas por el verificador")
        print("    introspeccion → reporte metacognitivo de la última respuesta")
        print("    capacidades   → perfil de capacidades por dominio (datos reales)")
        print("    reentrenar    → ciclo de aprendizaje: reentrena y promueve solo si mejora")
        print("    ayuda         → esta ayuda")
        print("    salir         → apagar")
        print("═"*60 + "\n")
        while True:
            try:
                e = input("🧠 Tú > ").strip()
                if not e: continue
                low = e.lower()
                if low == 'salir':
                    print("\n👋 ANP se despide. ¡Hasta pronto!")
                    break
                if low == 'ayuda':
                    print("  Escribe cualquier pregunta. ANP responde con conocimiento + pensamiento emergente.")
                    continue
                resp = self.anp.procesar(e)
                print(f"\n🤖 ANP > {resp}\n")
            except (EOFError, KeyboardInterrupt):
                print("\n👋 ANP se despide.")
                break

def iniciar_web(anp, puerto=8080):
    """Interfaz web simple y amigable usando solo biblioteca estándar."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse, html
    
    historial = []
    
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass  # silencio
        
        def do_GET(self):
            if self.path == '/' or self.path.startswith('/?'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                msgs = ""
                for u, a in historial[-20:]:
                    msgs += f'<div class="user"><b>Tú:</b> {html.escape(u)}</div>'
                    msgs += f'<div class="anp"><b>ANP:</b> {html.escape(a)}</div>'
                page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ANP Nevula</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin:0; padding:20px; }}
.container {{ max-width: 720px; margin: 0 auto; }}
h1 {{ color: #38bdf8; text-align:center; }}
.chat {{ background:#1e293b; border-radius:12px; padding:16px; min-height:300px; max-height:60vh; overflow-y:auto; }}
.user {{ background:#334155; margin:8px 0; padding:10px; border-radius:8px; }}
.anp {{ background:#0ea5e9; color:#0f172a; margin:8px 0; padding:10px; border-radius:8px; }}
form {{ display:flex; gap:8px; margin-top:16px; }}
input[type=text] {{ flex:1; padding:12px; border-radius:8px; border:none; background:#334155; color:#fff; font-size:16px; }}
button {{ padding:12px 20px; border-radius:8px; border:none; background:#38bdf8; color:#0f172a; font-weight:bold; cursor:pointer; }}
.footer {{ text-align:center; margin-top:12px; font-size:12px; color:#64748b; }}
</style></head><body>
<div class="container">
<h1>🧠 ANP Nevula 2.5 APEX</h1>
<p style="text-align:center;color:#94a3b8">Ciclo cognitivo APEX · memoria · herramientas · verificación</p>
<div class="chat" id="chat">{msgs}</div>
<form method="GET" action="/">
<input type="text" name="q" placeholder="Escribe tu mensaje..." autofocus autocomplete="off">
<button type="submit">Enviar</button>
</form>
<div class="footer">ANP — Arquitectura Neuronal Profunda · Pensamiento desde memoria real</div>
</div>
<script>document.getElementById('chat').scrollTop = 99999;</script>
</body></html>"""
                self.wfile.write(page.encode('utf-8'))
            else:
                self.send_error(404)
        
        def do_GET(self):  # override properly
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            q = qs.get('q', [None])[0]
            if q:
                try:
                    resp = anp.procesar(q)
                    historial.append((q, resp))
                except Exception as e:
                    historial.append((q, f"Error: {e}"))
            # redir to clean or show
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            msgs = ""
            for u, a in historial[-20:]:
                msgs += f'<div class="user"><b>Tú:</b> {html.escape(u)}</div>'
                msgs += f'<div class="anp"><b>ANP:</b> {html.escape(a)}</div>'
            page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ANP Nevula</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin:0; padding:20px; }}
.container {{ max-width: 720px; margin: 0 auto; }}
h1 {{ color: #38bdf8; text-align:center; margin-bottom:4px; }}
.sub {{ text-align:center; color:#94a3b8; margin-bottom:20px; }}
.chat {{ background:#1e293b; border-radius:12px; padding:16px; min-height:320px; max-height:55vh; overflow-y:auto; }}
.user {{ background:#334155; margin:8px 0; padding:12px; border-radius:8px; }}
.anp {{ background:#0ea5e9; color:#0f172a; margin:8px 0; padding:12px; border-radius:8px; }}
form {{ display:flex; gap:8px; margin-top:16px; }}
input[type=text] {{ flex:1; padding:14px; border-radius:8px; border:none; background:#334155; color:#fff; font-size:16px; }}
button {{ padding:14px 24px; border-radius:8px; border:none; background:#38bdf8; color:#0f172a; font-weight:bold; cursor:pointer; }}
.footer {{ text-align:center; margin-top:16px; font-size:12px; color:#64748b; }}
</style></head><body>
<div class="container">
<h1>🧠 ANP Nevula 2.5 APEX</h1>
<p class="sub">Pensamiento emergente · 27 motores conectados · Entrenado por Grok</p>
<div class="chat" id="chat">{msgs or "<p style='color:#64748b;text-align:center'>Escribe algo para comenzar...</p>"}</div>
<form method="GET" action="/">
<input type="text" name="q" placeholder="Pregúntame lo que quieras..." autofocus autocomplete="off">
<button type="submit">Enviar</button>
</form>
<div class="footer">ANP — Arquitectura Neuronal Profunda · Pensamientos que emergen de memoria real</div>
</div>
<script>var c=document.getElementById('chat'); if(c) c.scrollTop=c.scrollHeight;</script>
</body></html>"""
            self.wfile.write(page.encode('utf-8'))
    
    # Fix double do_GET - rewrite class cleanly
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            q = (qs.get('q') or [None])[0]
            if q and q.strip():
                try:
                    resp = anp.procesar(q.strip())
                    historial.append((q.strip(), resp))
                except Exception as e:
                    historial.append((q.strip(), f"Error interno: {e}"))
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            msgs = ""
            for u, a in historial[-20:]:
                msgs += f'<div class="user"><b>Tú:</b> {html.escape(u)}</div>'
                msgs += f'<div class="anp"><b>ANP:</b> {html.escape(a)}</div>'
            if not msgs:
                msgs = "<p style='color:#64748b;text-align:center'>Escribe algo para comenzar la conversación...</p>"
            page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ANP Nevula</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:20px}}
.container{{max-width:720px;margin:0 auto}}
h1{{color:#38bdf8;text-align:center;margin-bottom:4px}}
.sub{{text-align:center;color:#94a3b8;margin-bottom:20px}}
.chat{{background:#1e293b;border-radius:12px;padding:16px;min-height:320px;max-height:55vh;overflow-y:auto}}
.user{{background:#334155;margin:8px 0;padding:12px;border-radius:8px}}
.anp{{background:#0ea5e9;color:#0f172a;margin:8px 0;padding:12px;border-radius:8px}}
form{{display:flex;gap:8px;margin-top:16px}}
input[type=text]{{flex:1;padding:14px;border-radius:8px;border:none;background:#334155;color:#fff;font-size:16px}}
button{{padding:14px 24px;border-radius:8px;border:none;background:#38bdf8;color:#0f172a;font-weight:bold;cursor:pointer}}
.footer{{text-align:center;margin-top:16px;font-size:12px;color:#64748b}}
</style></head><body>
<div class="container">
<h1>🧠 ANP Nevula 2.5 APEX</h1>
<p class="sub">Ciclo cognitivo APEX · memoria · herramientas · verificación</p>
<div class="chat" id="chat">{msgs}</div>
<form method="GET" action="/">
<input type="text" name="q" placeholder="Pregúntame lo que quieras..." autofocus autocomplete="off">
<button type="submit">Enviar</button>
</form>
<div class="footer">ANP — Arquitectura Neuronal Profunda · Pensamientos desde memoria real</div>
</div>
<script>var c=document.getElementById('chat');if(c)c.scrollTop=c.scrollHeight;</script>
</body></html>"""
            self.wfile.write(page.encode('utf-8'))
    
    print(f"\n🌐 Interfaz web lista en http://localhost:{puerto}")
    print("   Abre el navegador y conversa con ANP.")
    print("   Ctrl+C para detener.\n")
    HTTPServer(('0.0.0.0', puerto), Handler).serve_forever()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ANP Nevula — Arquitectura Neuronal Profunda")
    parser.add_argument("--web", action="store_true", help="Iniciar interfaz web amigable")
    parser.add_argument("--puerto", type=int, default=8080, help="Puerto para la web (default 8080)")
    parser.add_argument("--consola", action="store_true", help="Consola clásica de ANP (sin Sofi)")
    args = parser.parse_args()
    if not args.consola and not args.web:
        # ANP evoluciona a Sofi: por defecto arranca el asistente (cerebro ANP + cartera + internet + LLM).
        from sofi.servidor import servir
        return servir(int(os.environ.get("PORT", args.puerto)))
    
    anp = ANP()
    if not anp.iniciar():
        return 1
    try:
        if args.web:
            iniciar_web(anp, args.puerto)
        else:
            ConsolaANP(anp).iniciar()
    finally:
        anp.detener()
    return 0

if __name__ == "__main__":
    sys.exit(main())
