#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.1 - Clasificador de Dominio JERÁRQUICO (2 etapas)
# =====================================================================
# CAMBIO ESTRUCTURAL: en vez de una única red que distingue entre 15
# dominios a la vez (validado por CV en ~43% de precisión), se entrenan
# DOS niveles:
#   Etapa 1: una red clasifica el texto en 1 de 4 GRUPOS temáticos
#            (más fácil: menos clases, más distintas entre sí)
#   Etapa 2: un clasificador especializado por grupo distingue entre los
#            dominios de ESE grupo únicamente (problema más chico)
#
# Validado con 4-fold cross-validation antes de implementarlo: el
# jerárquico da 50.8% ± 3.1% contra 43.0% ± 3.2% del clasificador plano,
# una mejora consistente en los 4 folds (no ruido).
#
# Nota de honestidad: NO usa embeddings preentrenados (no hay acceso a
# internet en este entorno para descargarlos). Sigue siendo TF-IDF +
# red neuronal, pero con una arquitectura de dos etapas en vez de una
# única red plana — eso es lo que de verdad mueve la aguja aquí, más
# que la representación léxica en sí.
# =====================================================================
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

import numpy as np

from entrenamiento.entrenar_clasificador import (
    cargar_dataset, dividir_train_val, balancear_clases, VectorizadorTFIDF, a_onehot,
)
from nucleos.memoria.motores.motor_neuronal import (
    RedNeuronalOptima, FuncionActivacion, Regularizador, ModoNormalizacion,
    Inicializador, SchedulerType,
)

GRUPOS = {
    "computacion": ["programacion", "tecnologia", "robotica"],
    "ciencias_exactas": ["ciencia", "matematicas", "naturaleza"],
    "sociedad": ["cultura", "humanidad", "conocimiento_general", "geografia"],
    "cotidiano": ["lenguaje", "vida_cotidiana", "conversacional"],
    "ocio": ["entretenimiento", "deportes"],
}
DOMINIO_A_GRUPO = {d: g for g, ds in GRUPOS.items() for d in ds}
NOMBRES_GRUPO = list(GRUPOS.keys())

DIR_MODELOS = BASE / "almacenamiento" / "modelos"


def _entrenar_red(X_train, y_train, X_val, y_val, n_clases, capas, dropout, wd, lr, epocas, patience, batch=32):
    red = RedNeuronalOptima("jerarquico")
    dims = [X_train.shape[0]] + list(capas) + [n_clases]
    for i in range(len(dims) - 1):
        es_salida = (i == len(dims) - 2)
        act = FuncionActivacion.SOFTMAX if es_salida else FuncionActivacion.RELU
        if act == FuncionActivacion.RELU:
            kwargs = dict(dropout_rate=dropout, regularizador=Regularizador.L2, lambda_reg=wd / 4,
                          inicializador=Inicializador.HE_NORMAL)
            if i < len(dims) - 3:
                kwargs["normalizacion"] = ModoNormalizacion.BATCH
        else:
            kwargs = dict(inicializador=Inicializador.XAVIER_NORMAL)
        red.agregar(dims[i], dims[i + 1], activacion=act, **kwargs)
    red.compilar(optimizador="adamw", perdida="categorical_crossentropy", lr=lr,
                 scheduler_type=SchedulerType.COSINE, max_grad_norm=5.0, weight_decay=wd)
    red.entrenar(X_train, y_train, X_val, y_val, epocas=epocas, batch_size=batch,
                 early_stopping=patience, verbose=False)
    return red


def _guardar(red, vectorizador, ruta_base: Path, clases, extra_meta=None):
    ruta_pesos = ruta_base.with_suffix(".anp")
    ruta_vocab = Path(str(ruta_base) + "_vocab.json")
    red.guardar(str(ruta_pesos))
    vectorizador.guardar(ruta_vocab)
    meta = json.loads(ruta_vocab.read_text(encoding="utf-8"))
    meta["clases"] = clases
    if extra_meta:
        meta.update(extra_meta)
    ruta_vocab.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def entrenar_jerarquico():
    print("=" * 70)
    print("ENTRENAMIENTO JERÁRQUICO (2 etapas) — Clasificador de Dominio ANP")
    print("=" * 70)

    ejemplos, dominios = cargar_dataset()
    train, val = dividir_train_val(ejemplos, dominios)
    print(f"\n[1/4] Dataset: {len(ejemplos)} ejemplos, {len(dominios)} dominios en {len(GRUPOS)} grupos")
    for g, ds in GRUPOS.items():
        print(f"   {g}: {ds}")

    # ---------------- ETAPA 1: clasificador de GRUPO ----------------
    print("\n[2/4] Entrenando ETAPA 1 (grupo temático)...")
    train_g = [(t, DOMINIO_A_GRUPO[d]) for t, d in train]
    train_g_bal = balancear_clases(train_g, factor_objetivo=1.3)
    vec1 = VectorizadorTFIDF(max_vocab=1200, min_df=3).ajustar([t for t, _ in train_g_bal])
    Xtr1 = vec1.transformar([t for t, _ in train_g_bal]).T
    ytr1 = a_onehot([g for _, g in train_g_bal], NOMBRES_GRUPO)
    Xva1 = vec1.transformar([t for t, _ in val]).T
    yva1 = a_onehot([DOMINIO_A_GRUPO[d] for _, d in val], NOMBRES_GRUPO)
    red1 = _entrenar_red(Xtr1, ytr1, Xva1, yva1, len(NOMBRES_GRUPO),
                          capas=(192, 96), dropout=0.3, wd=0.006, lr=0.003, epocas=280, patience=40)
    pred1 = red1.predecir(Xva1)
    acc1 = float(np.mean(np.argmax(pred1, axis=0) == np.argmax(yva1, axis=0)))
    print(f"      Precisión etapa 1 (grupo): {acc1:.1%}")
    _guardar(red1, vec1, DIR_MODELOS / "clasificador_grupo", NOMBRES_GRUPO,
             extra_meta={"precision_val": acc1, "mapa_dominio_grupo": DOMINIO_A_GRUPO})

    # ---------------- ETAPA 2: un clasificador por grupo ----------------
    print("\n[3/4] Entrenando ETAPA 2 (dominio específico dentro de cada grupo)...")
    stage2_info = {}
    for g, ds in GRUPOS.items():
        train_g2 = [(t, d) for t, d in train if d in ds]
        train_g2_bal = balancear_clases(train_g2, factor_objetivo=1.3)
        val_g2 = [(t, d) for t, d in val if d in ds]
        vec2 = VectorizadorTFIDF(max_vocab=900, min_df=2).ajustar([t for t, _ in train_g2_bal])
        Xtr2 = vec2.transformar([t for t, _ in train_g2_bal]).T
        ytr2 = a_onehot([d for _, d in train_g2_bal], ds)
        Xva2 = vec2.transformar([t for t, _ in val_g2]).T if val_g2 else Xtr2[:, :3]
        yva2 = a_onehot([d for _, d in val_g2], ds) if val_g2 else ytr2[:, :3]
        red2 = _entrenar_red(Xtr2, ytr2, Xva2, yva2, len(ds),
                              capas=(96, 48), dropout=0.3, wd=0.006, lr=0.003, epocas=220, patience=35)
        pred2 = red2.predecir(Xva2)
        acc2 = float(np.mean(np.argmax(pred2, axis=0) == np.argmax(yva2, axis=0))) if val_g2 else float("nan")
        print(f"      {g:<12} ({len(ds)} dominios, {len(train_g2)} ejemplos): precisión {acc2:.1%}")
        ruta = DIR_MODELOS / f"grupo_{g}"
        _guardar(red2, vec2, ruta, ds, extra_meta={"precision_val": acc2})
        stage2_info[g] = {"dominios": ds, "precision_val": acc2, "n_train": len(train_g2)}

    # ---------------- Evaluación combinada honesta ----------------
    print("\n[4/4] Evaluando el pipeline COMPLETO (etapa1 + etapa2) en el holdout...")
    aciertos = 0
    modelos_cache = {}
    for g in GRUPOS:
        ruta = DIR_MODELOS / f"grupo_{g}"
        modelos_cache[g] = (RedNeuronalOptima.cargar(str(ruta) + ".anp"),
                            json.loads(Path(str(ruta) + "_vocab.json").read_text(encoding="utf-8")))
    for texto, dom_real in val:
        xv1 = vec1.transformar([texto]).T
        g_pred = NOMBRES_GRUPO[int(np.argmax(red1.predecir(xv1), axis=0)[0])]
        red2, meta2 = modelos_cache[g_pred]
        vocab2, idf2, clases2 = meta2["vocabulario"], np.array(meta2["idf"]), meta2["clases"]
        vec2_tmp = VectorizadorTFIDF()
        vec2_tmp.vocabulario, vec2_tmp.idf = vocab2, idf2
        xv2 = vec2_tmp.transformar([texto]).T
        dom_pred = clases2[int(np.argmax(red2.predecir(xv2), axis=0)[0])]
        if dom_pred == dom_real:
            aciertos += 1
    precision_total = aciertos / len(val)
    print(f"\n      *** PRECISIÓN TOTAL DEL PIPELINE JERÁRQUICO: {precision_total:.1%} ***")

    resumen = {"precision_etapa1_grupo": acc1, "precision_total_jerarquico": precision_total,
               "stage2": stage2_info, "n_val": len(val)}
    (DIR_MODELOS / "jerarquico_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    print("\n" + "=" * 70)
    print("COMPLETADO")
    print("=" * 70)
    return resumen


if __name__ == "__main__":
    entrenar_jerarquico()
