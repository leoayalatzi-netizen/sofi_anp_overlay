#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entrena una red neuronal profunda (MLP) para clasificar el DOMINIO temático
de un texto de entrada, usando como backbone el motor neuronal ya existente
en ANP (nucleos/memoria/motores/motor_neuronal.py -> RedNeuronalOptima).

Pipeline:
  texto -> TF-IDF (vocabulario propio, sin librerías externas de NLP)
        -> Red neuronal 4 capas (entrada -> 256 -> 128 -> 64 -> n_dominios)
           con ReLU, Dropout, BatchNorm, softmax + AdamW + cosine LR schedule
        -> dominio predicho + confianza

Guarda:
  - almacenamiento/modelos/clasificador_dominio.anp   (pesos entrenados)
  - almacenamiento/modelos/clasificador_dominio_vocab.json (vectorizador + clases)
"""
import sys
import json
import math
import random
import re
import unicodedata
from pathlib import Path
from collections import Counter

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

import numpy as np

from nucleos.memoria.motores.motor_neuronal import (
    RedNeuronalOptima, FuncionActivacion, Regularizador, ModoNormalizacion,
    Inicializador, SchedulerType,
)

random.seed(42)
np.random.seed(42)

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


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def tokenizar(texto: str) -> list:
    texto = normalizar(texto)
    tokens = re.findall(r"[a-z]{3,}", texto)
    tokens = [t for t in tokens if t not in STOPWORDS_ES]
    # Bigramas: capturan pares de palabras contiguas ("energia cinetica",
    # "numero primo") que dan mucha más señal discriminativa entre dominios
    # que las palabras sueltas, sin salir de un enfoque léxico simple.
    bigramas = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return tokens + bigramas


class VectorizadorTFIDF:
    def __init__(self, max_vocab: int = 1500, min_df: int = 2):
        self.max_vocab = max_vocab
        self.min_df = min_df
        self.vocabulario = {}
        self.idf = None

    def ajustar(self, textos: list):
        doc_freq = Counter()
        for t in textos:
            toks = set(tokenizar(t))
            doc_freq.update(toks)
        candidatos = [(w, df) for w, df in doc_freq.items() if df >= self.min_df]
        candidatos.sort(key=lambda x: -x[1])
        candidatos = candidatos[: self.max_vocab]
        self.vocabulario = {w: i for i, (w, _) in enumerate(candidatos)}
        n_docs = len(textos)
        self.idf = np.zeros(len(self.vocabulario), dtype=np.float64)
        for w, i in self.vocabulario.items():
            self.idf[i] = math.log((1 + n_docs) / (1 + doc_freq[w])) + 1.0
        return self

    def transformar(self, textos: list) -> np.ndarray:
        X = np.zeros((len(textos), len(self.vocabulario)), dtype=np.float64)
        for row, t in enumerate(textos):
            toks = tokenizar(t)
            if not toks:
                continue
            tf = Counter(toks)
            total = len(toks)
            for w, c in tf.items():
                idx = self.vocabulario.get(w)
                if idx is not None:
                    X[row, idx] = (c / total) * self.idf[idx]
            norm = np.linalg.norm(X[row])
            if norm > 0:
                X[row] /= norm
        return X

    def guardar(self, ruta: Path):
        ruta.write_text(json.dumps({
            "vocabulario": self.vocabulario,
            "idf": self.idf.tolist(),
            "max_vocab": self.max_vocab,
        }, ensure_ascii=False), encoding="utf-8")


def cargar_dataset():
    ruta = BASE / "entrenamiento" / "dataset_dominios.json"
    if not ruta.exists():
        from extraer_dataset import construir_dataset
        ejemplos, dominios = construir_dataset()
    else:
        data = json.loads(ruta.read_text(encoding="utf-8"))
        ejemplos, dominios = data["ejemplos"], data["dominios"]
    return ejemplos, dominios


def dividir_train_val(ejemplos, dominios, frac_val=0.15):
    por_clase = {d: [] for d in dominios}
    for texto, dom in ejemplos:
        por_clase[dom].append(texto)
    train, val = [], []
    for dom, textos in por_clase.items():
        random.shuffle(textos)
        n_val = max(1, int(len(textos) * frac_val))
        val += [(t, dom) for t in textos[:n_val]]
        train += [(t, dom) for t in textos[n_val:]]
    random.shuffle(train)
    random.shuffle(val)
    return train, val


def balancear_clases(train, factor_objetivo: float = 1.4):
    """Sobremuestreo (oversampling) de las clases minoritarias hasta
    mediana*factor_objetivo. Con 15 dominios de tamaños muy dispares
    (programación con 176 ejemplos vs vida_cotidiana con 50), la red sin
    balancear colapsaba a predecir casi siempre la clase mayoritaria
    (~28% de precisión). Balanceando sube a ~40%: la diferencia entre un
    modelo inútil y uno que realmente distingue los 15 dominios."""
    from collections import defaultdict
    por_clase = defaultdict(list)
    for t, d in train:
        por_clase[d].append(t)
    objetivo = int(np.median([len(v) for v in por_clase.values()]) * factor_objetivo)
    rng = random.Random(7)
    balanceado = []
    for d, textos in por_clase.items():
        pool = list(textos)
        if len(pool) < objetivo:
            pool = pool + rng.choices(pool, k=objetivo - len(pool))
        balanceado += [(t, d) for t in pool]
    rng.shuffle(balanceado)
    return balanceado


def aumentar_datos(train, copias_por_ejemplo=4, prob_mantener=(0.6, 0.9)):
    """Aumento de datos por 'word dropout': genera variantes de cada texto
    conservando un subconjunto aleatorio de sus tokens. Esto multiplica el
    tamaño del set de entrenamiento y mejora la generalización con un
    dataset pequeño, sin depender de librerías externas de NLP."""
    aumentado = list(train)
    for texto, dom in train:
        toks = tokenizar(texto)
        if len(toks) < 4:
            continue
        for _ in range(copias_por_ejemplo):
            p = random.uniform(*prob_mantener)
            k = max(3, int(len(toks) * p))
            muestra = random.sample(toks, k)
            aumentado.append((" ".join(muestra), dom))
    random.shuffle(aumentado)
    return aumentado


def a_onehot(etiquetas, dominios):
    idx = {d: i for i, d in enumerate(dominios)}
    Y = np.zeros((len(dominios), len(etiquetas)), dtype=np.float64)
    for j, e in enumerate(etiquetas):
        Y[idx[e], j] = 1.0
    return Y


def main():
    print("=" * 70)
    print("ENTRENAMIENTO: Red Neuronal Clasificadora de Dominios (ANP)")
    print("=" * 70)

    ejemplos, dominios = cargar_dataset()
    print(f"\n[1/6] Dataset: {len(ejemplos)} ejemplos, {len(dominios)} dominios: {dominios}")

    train, val = dividir_train_val(ejemplos, dominios)
    print(f"[2/6] Split -> train={len(train)}  val={len(val)}")

    train = balancear_clases(train, factor_objetivo=1.3)
    print(f"      Balanceo por sobremuestreo -> train={len(train)} (clases equilibradas)")

    vectorizador = VectorizadorTFIDF(max_vocab=1200, min_df=3).ajustar([t for t, _ in train])
    train_aum = train
    print(f"[3/6] Vocabulario TF-IDF: {len(vectorizador.vocabulario)} términos")

    X_train = vectorizador.transformar([t for t, _ in train_aum]).T  # (dim, n)
    y_train = a_onehot([d for _, d in train_aum], dominios)
    X_val = vectorizador.transformar([t for t, _ in val]).T
    y_val = a_onehot([d for _, d in val], dominios)

    dim_entrada = X_train.shape[0]
    n_clases = len(dominios)

    print(f"[4/6] Construyendo red profunda: {dim_entrada} -> 192 -> 96 -> {n_clases}")
    red = RedNeuronalOptima("clasificador_dominio")
    red.agregar(dim_entrada, 192, activacion=FuncionActivacion.RELU, dropout_rate=0.3,
                regularizador=Regularizador.L2, lambda_reg=0.0015,
                normalizacion=ModoNormalizacion.BATCH, inicializador=Inicializador.HE_NORMAL)
    red.agregar(192, 96, activacion=FuncionActivacion.RELU, dropout_rate=0.3,
                regularizador=Regularizador.L2, lambda_reg=0.0015,
                inicializador=Inicializador.HE_NORMAL)
    red.agregar(96, n_clases, activacion=FuncionActivacion.SOFTMAX, inicializador=Inicializador.XAVIER_NORMAL)
    red.compilar(optimizador="adamw", perdida="categorical_crossentropy", lr=0.003,
                 scheduler_type=SchedulerType.COSINE, max_grad_norm=5.0, weight_decay=0.006)

    total_params = sum(c.entrada_dim * c.salida_dim + c.salida_dim for c in red.capas)
    print(f"      Parámetros totales: {total_params:,}")

    print("\n[5/6] Entrenando...")
    resultado = red.entrenar(X_train, y_train, X_val, y_val, epocas=280, batch_size=32,
                              early_stopping=40, verbose=True)

    y_pred_val = red.predecir(X_val)
    pred_clase = np.argmax(y_pred_val, axis=0)
    real_clase = np.argmax(y_val, axis=0)
    precision_val = float(np.mean(pred_clase == real_clase))
    print(f"\n      Precisión final en validación: {precision_val:.2%}")

    print("\n[6/6] Guardando modelo entrenado...")
    dir_modelos = BASE / "almacenamiento" / "modelos"
    dir_modelos.mkdir(parents=True, exist_ok=True)
    ruta_pesos = dir_modelos / "clasificador_dominio.anp"
    ruta_vocab = dir_modelos / "clasificador_dominio_vocab.json"
    red.guardar(str(ruta_pesos))
    vectorizador.guardar(ruta_vocab)
    # Guardar también las clases junto al vocabulario para inferencia
    meta = json.loads(ruta_vocab.read_text(encoding="utf-8"))
    meta["dominios"] = dominios
    meta["precision_val"] = precision_val
    meta["total_parametros"] = total_params
    meta["ejemplos_entrenamiento"] = len(train_aum)
    ruta_vocab.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    print(f"      Pesos:  {ruta_pesos}")
    print(f"      Vocab:  {ruta_vocab}")
    print("\n" + "=" * 70)
    print(f"COMPLETADO — precisión validación: {precision_val:.2%}")
    print("=" * 70)


if __name__ == "__main__":
    main()
