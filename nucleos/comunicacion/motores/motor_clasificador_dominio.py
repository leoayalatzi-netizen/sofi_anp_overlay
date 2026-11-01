#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Clasificador de Dominio (Red Neuronal Entrenada)
# =====================================================================
# Carga la red neuronal profunda entrenada en entrenamiento/entrenar_clasificador.py
# (TF-IDF -> MLP 4 capas con BatchNorm/Dropout/AdamW) y la usa para predecir
# a qué dominio de conocimiento (ciencia, tecnologia, cultura, ...) pertenece
# un texto de entrada. Se usa para enrutar mejor las búsquedas en la
# biblioteca de conocimiento y como demostración de un modelo real,
# complejo y entrenado integrado en ANP.
# =====================================================================

import json
import math
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    NUMPY_DISPONIBLE = False
    np = None

try:
    from ....nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
except ImportError:
    try:
        from nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
    except ImportError:
        from abc import ABC, abstractmethod
        from enum import Enum
        from dataclasses import dataclass

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
            def estado(self):
                return self._estado

            def inicializar(self, contexto=None):
                self._estado = EstadoMotor.ACTIVO
                return True

            def detener(self):
                self._estado = EstadoMotor.ERROR
                return True

            @abstractmethod
            def _procesar_impl(self, entrada, contexto=None):
                pass

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

try:
    from .motor_neuronal import RedNeuronalOptima
except ImportError:
    try:
        from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima
    except ImportError:
        RedNeuronalOptima = None

STOPWORDS_ES = set("""
de la que el en y a los del se las por un para con no una su al lo como mas
pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me
hasta hay donde quien desde todo nos durante todos uno les ni contra otros
ese eso ante ellos e esto mi antes algunos que unos yo otro otras otra el
tanto esa estos mucho quienes nada muchos cual poco ella estar estas algunas
algo nosotros mi mis tu tus te ti tuyo ellas nosotras vosotros vosotras os
mio mia mios mias tuya tuyos tuyas suyo suya suyos suyas nuestro nuestra
nuestros nuestras vuestro vuestra vuestros vuestras esos esas es soy eres
somos sois son fue fui fuiste fuimos fueron ser
""".split())


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _tokenizar(texto: str) -> List[str]:
    texto = _normalizar(texto)
    tokens = re.findall(r"[a-z]{3,}", texto)
    tokens = [t for t in tokens if t not in STOPWORDS_ES]
    bigramas = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return tokens + bigramas


RUTA_MODELOS = Path(__file__).resolve().parents[3] / "almacenamiento" / "modelos"
RUTA_GRUPO_PESOS = RUTA_MODELOS / "clasificador_grupo.anp"
RUTA_GRUPO_VOCAB = RUTA_MODELOS / "clasificador_grupo_vocab.json"


class MotorClasificadorDominio(MotorBase):
    """Motor JERÁRQUICO de 2 etapas (Nevula 1.1): primero predice el GRUPO
    temático (stem/sociedad/cotidiano/ocio) con una red, luego un
    clasificador especializado por grupo predice el dominio exacto.
    Validado por 4-fold CV: 57.7% de precisión en el holdout final,
    contra ~43% del clasificador plano de una sola etapa (Nevula 1.0).
    No usa embeddings preentrenados: este entorno no tiene acceso a
    internet para descargarlos. La mejora viene de la arquitectura de
    dos etapas, no de una representación léxica distinta."""

    def __init__(self, config=None):
        super().__init__(config)
        self._red_grupo: Optional["RedNeuronalOptima"] = None
        self._vocab_grupo: Dict[str, int] = {}
        self._idf_grupo = None
        self._grupos: List[str] = []
        self._modelos_grupo: Dict[str, Dict[str, Any]] = {}  # g -> {red, vocab, idf, dominios}
        self._cargado = False
        self._precision_total = None
        self._evolucionado = False
        self._vectorizador_evolucionado = None
        self._red_grupo_legacy = None
        self._modelos_grupo_legacy = {}
        self._vectorizador_grupo_legacy = None
        self._cargar_modelo()

    def _cargar_modelo(self):
        if RedNeuronalOptima is None or not NUMPY_DISPONIBLE:
            return
        # Nevula 1.2 es una capa evolutiva aditiva. Si existe, se usa como
        # backend preferente; ante cualquier fallo se conserva el pipeline 1.1.
        try:
            from evolucion.vectorizador_hibrido import VectorizadorHibrido
            ruta_evo = RUTA_MODELOS / 'evolucionado'
            pesos_evo = ruta_evo / 'clasificador_grupo.anp'
            vocab_evo = ruta_evo / 'clasificador_grupo_vocab.json'
            if pesos_evo.exists() and vocab_evo.exists():
                meta_evo = json.loads(vocab_evo.read_text(encoding='utf-8'))
                red_evo = RedNeuronalOptima.cargar(str(pesos_evo))
                vec_evo = VectorizadorHibrido.cargar(vocab_evo)
                modelos_evo = {}
                for g in meta_evo.get('clases', []):
                    b = ruta_evo / f'grupo_{g}'
                    vp = Path(str(b) + '_vocab.json')
                    if b.with_suffix('.anp').exists() and vp.exists():
                        mm = json.loads(vp.read_text(encoding='utf-8'))
                        modelos_evo[g] = {'red': RedNeuronalOptima.cargar(str(b.with_suffix('.anp'))), 'vec': VectorizadorHibrido.cargar(vp), 'dominios': mm['clases']}
                if red_evo is not None and len(modelos_evo) == len(meta_evo.get('clases', [])):
                    self._red_grupo = red_evo; self._vectorizador_evolucionado = vec_evo
                    self._grupos = meta_evo['clases']; self._modelos_grupo = modelos_evo
                    # Conservamos el backend 1.1 cargado en paralelo para
                    # validación de regresiones: si 1.2 contradice al modelo
                    # estable en la primera decisión, se conserva 1.1.
                    legacy_meta_path = RUTA_MODELOS / 'clasificador_grupo_vocab.json'
                    legacy_weights = RUTA_MODELOS / 'clasificador_grupo.anp'
                    if legacy_meta_path.exists() and legacy_weights.exists():
                        lm = json.loads(legacy_meta_path.read_text(encoding='utf-8'))
                        self._red_grupo_legacy = RedNeuronalOptima.cargar(str(legacy_weights))
                        self._vectorizador_grupo_legacy = {'vocab': lm['vocabulario'], 'idf': np.array(lm['idf'], dtype=np.float64), 'grupos': lm['clases']}
                        for lg in lm.get('clases', []):
                            lb = RUTA_MODELOS / f'grupo_{lg}.anp'; lv = RUTA_MODELOS / f'grupo_{lg}_vocab.json'
                            if lb.exists() and lv.exists():
                                lmm=json.loads(lv.read_text(encoding='utf-8'))
                                self._modelos_grupo_legacy[lg]={'red':RedNeuronalOptima.cargar(str(lb)),'vocab':lmm['vocabulario'],'idf':np.array(lmm['idf'],dtype=np.float64),'dominios':lmm['clases']}
                    resumen = ruta_evo / 'resultado.json'
                    if resumen.exists(): self._precision_total = json.loads(resumen.read_text(encoding='utf-8')).get('precision_holdout')
                    self._evolucionado = True; self._cargado = True; return
        except Exception:
            self._evolucionado = False
        if not RUTA_GRUPO_PESOS.exists() or not RUTA_GRUPO_VOCAB.exists():
            return
        try:
            self._red_grupo = RedNeuronalOptima.cargar(str(RUTA_GRUPO_PESOS))
            meta_g = json.loads(RUTA_GRUPO_VOCAB.read_text(encoding="utf-8"))
            self._vocab_grupo = meta_g["vocabulario"]
            self._idf_grupo = np.array(meta_g["idf"], dtype=np.float64)
            self._grupos = meta_g["clases"]

            for g in self._grupos:
                ruta_pesos = RUTA_MODELOS / f"grupo_{g}.anp"
                ruta_vocab = RUTA_MODELOS / f"grupo_{g}_vocab.json"
                if not ruta_pesos.exists():
                    continue
                red = RedNeuronalOptima.cargar(str(ruta_pesos))
                meta = json.loads(ruta_vocab.read_text(encoding="utf-8"))
                self._modelos_grupo[g] = {
                    "red": red, "vocab": meta["vocabulario"],
                    "idf": np.array(meta["idf"], dtype=np.float64), "dominios": meta["clases"],
                }
            resumen_path = RUTA_MODELOS / "jerarquico_resumen.json"
            if resumen_path.exists():
                self._precision_total = json.loads(resumen_path.read_text(encoding="utf-8")).get("precision_total_jerarquico")
            self._cargado = bool(self._modelos_grupo)
        except Exception:
            self._cargado = False

    @staticmethod
    def _vectorizar_con(texto: str, vocabulario: Dict[str, int], idf: "np.ndarray"):
        vec = np.zeros((len(vocabulario), 1), dtype=np.float64)
        toks = _tokenizar(texto)
        if not toks:
            return vec
        tf = Counter(toks)
        total = len(toks)
        for w, c in tf.items():
            idx = vocabulario.get(w)
            if idx is not None:
                vec[idx, 0] = (c / total) * idf[idx]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def clasificar(self, texto: str) -> Dict[str, Any]:
        """Etapa 1: predice el grupo. Etapa 2: predice el dominio exacto
        dentro de ese grupo. Devuelve dominio, confianza combinada
        (prob. grupo × prob. dominio dentro del grupo) y un top-3."""
        if not self._cargado:
            return {"exito": False, "error": "modelo_no_cargado", "dominio": None}

        if self._evolucionado:
            x1 = self._vectorizador_evolucionado.transformar([texto]).T
            probs_grupo = self._red_grupo.predecir(x1).flatten()
            orden_grupo = np.argsort(-probs_grupo)
            grupo_top = self._grupos[int(orden_grupo[0])]; conf_grupo = float(probs_grupo[orden_grupo[0]])
            # Guardia de regresión: el 1.2 solo sustituye la decisión de
            # grupo cuando coincide con el backend 1.1 ya validado.
            if self._red_grupo_legacy is not None and self._vectorizador_grupo_legacy is not None:
                lx = self._vectorizar_con(texto, self._vectorizador_grupo_legacy['vocab'], self._vectorizador_grupo_legacy['idf'])
                lp = self._red_grupo_legacy.predecir(lx).flatten(); li=int(np.argmax(lp)); lg=self._vectorizador_grupo_legacy['grupos'][li]
                if lg != grupo_top:
                    grupo_top=lg; conf_grupo=float(lp[li]); info=self._modelos_grupo_legacy.get(grupo_top)
                    if info is None: return {'exito':False,'error':'grupo_sin_modelo','dominio':None}
                    x2=self._vectorizar_con(texto,info['vocab'],info['idf']); probs_dom=info['red'].predecir(x2).flatten(); orden_dom=np.argsort(-probs_dom); dominios_grupo=info['dominios']
                    return {'exito':True,'dominio':dominios_grupo[int(orden_dom[0])],'confianza':round(conf_grupo*float(probs_dom[orden_dom[0]]),4),'grupo':grupo_top,'confianza_grupo':round(conf_grupo,4),'top3':[{'dominio':dominios_grupo[int(i)],'confianza':round(conf_grupo*float(probs_dom[int(i)]),4)} for i in orden_dom[:min(3,len(dominios_grupo))]],'motor':'nevula_1.1_guardia_regresion'}
            info = self._modelos_grupo.get(grupo_top)
            if info is None: return {'exito': False, 'error': 'grupo_sin_modelo', 'dominio': None}
            probs_dom = info['red'].predecir(info['vec'].transformar([texto]).T).flatten(); orden_dom=np.argsort(-probs_dom); dominios_grupo=info['dominios']
            top3=[{'dominio':dominios_grupo[int(i)],'confianza':round(conf_grupo*float(probs_dom[int(i)]),4)} for i in orden_dom[:min(3,len(dominios_grupo))]]
            return {'exito':True,'dominio':dominios_grupo[int(orden_dom[0])],'confianza':round(conf_grupo*float(probs_dom[orden_dom[0]]),4),'grupo':grupo_top,'confianza_grupo':round(conf_grupo,4),'top3':top3,'motor':'nevula_1.2_evolucionada'}

        x1 = self._vectorizar_con(texto, self._vocab_grupo, self._idf_grupo)
        probs_grupo = self._red_grupo.predecir(x1).flatten()
        orden_grupo = np.argsort(-probs_grupo)
        grupo_top = self._grupos[int(orden_grupo[0])]
        conf_grupo = float(probs_grupo[orden_grupo[0]])

        info = self._modelos_grupo.get(grupo_top)
        if info is None:
            return {"exito": False, "error": "grupo_sin_modelo", "dominio": None}

        x2 = self._vectorizar_con(texto, info["vocab"], info["idf"])
        probs_dom = info["red"].predecir(x2).flatten()
        orden_dom = np.argsort(-probs_dom)
        dominios_grupo = info["dominios"]

        top3 = [{"dominio": dominios_grupo[i], "confianza": round(float(probs_dom[i]) * conf_grupo, 4)}
                for i in orden_dom[:min(3, len(dominios_grupo))]]
        return {
            "exito": True,
            "dominio": dominios_grupo[int(orden_dom[0])],
            "confianza": round(float(probs_dom[orden_dom[0]]) * conf_grupo, 4),
            "grupo": grupo_top, "confianza_grupo": conf_grupo,
            "top3": top3,
        }

    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if isinstance(entrada, dict):
            texto = entrada.get("texto", "")
        else:
            texto = str(entrada)
        if not texto.strip():
            return {"exito": False, "error": "texto vacío"}
        return self.clasificar(texto)

    def info(self) -> Dict[str, Any]:
        return {
            "cargado": self._cargado,
            "grupos": self._grupos,
            "dominios_por_grupo": {g: v["dominios"] for g, v in self._modelos_grupo.items()},
            "precision_total_pipeline": self._precision_total,
        }


if __name__ == "__main__":
    print("=" * 70)
    print("DIAGNÓSTICO — MotorClasificadorDominio (jerárquico, 2 etapas)")
    print("=" * 70)
    motor = MotorClasificadorDominio()
    motor.inicializar()
    info = motor.info()
    print(f"\nModelo cargado: {info['cargado']}")
    if info["cargado"]:
        print(f"Grupos: {info['grupos']}")
        for g, ds in info["dominios_por_grupo"].items():
            print(f"  {g}: {ds}")
        if info["precision_total_pipeline"] is not None:
            print(f"Precisión total del pipeline (holdout): {info['precision_total_pipeline']:.1%}")
        pruebas = [
            "¿Cuál es la fórmula de la segunda ley de Newton?",
            "¿Cómo declaro una función lambda en Python?",
            "¿Quién pintó la Mona Lisa?",
            "¿Qué corriente filosófica defendía Sócrates?",
            "dime un sinonimo de la palabra alegre",
            "cuales son las capitales de europa",
            "¿qué es un robot?", "¿cuál es la regla del fuera de juego en fútbol?",
        ]
        print("\nPruebas de clasificación:")
        for p in pruebas:
            r = motor.clasificar(p)
            print(f"  '{p[:50]}' -> {r['dominio']} ({r['confianza']:.1%}) [grupo: {r['grupo']}]")
    else:
        print("⚠️  No se encontró el modelo entrenado. Ejecuta primero:")
        print("    python3 entrenamiento/entrenar_clasificador_jerarquico.py")
    print("\n" + "=" * 70)
