#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.1 - Entrenador (candidato versionado, JERÁRQUICO)
# =====================================================================
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

import numpy as np

from entrenamiento.entrenar_clasificador import VectorizadorTFIDF, dividir_train_val, balancear_clases, a_onehot
from entrenamiento.entrenar_clasificador_jerarquico import (
    GRUPOS, DOMINIO_A_GRUPO, NOMBRES_GRUPO, _entrenar_red, _guardar,
)


def entrenar(ejemplos, dominios, id_version: str, dir_salida: Path = None):
    """Entrena el pipeline jerárquico COMPLETO (etapa 1 + etapa 2 por grupo)
    y lo guarda en una carpeta de candidato versionado, sin tocar los
    modelos en producción (eso lo decide selector_modelo.py después de
    evaluar contra el holdout fijo)."""
    dir_salida = dir_salida or (BASE / "almacenamiento" / "modelos" / "versiones" / id_version)
    dir_salida.mkdir(parents=True, exist_ok=True)

    train, val = dividir_train_val(ejemplos, dominios)

    train_g = [(t, DOMINIO_A_GRUPO[d]) for t, d in train]
    train_g_bal = balancear_clases(train_g, factor_objetivo=1.3)
    vec1 = VectorizadorTFIDF(max_vocab=1200, min_df=3).ajustar([t for t, _ in train_g_bal])
    Xtr1 = vec1.transformar([t for t, _ in train_g_bal]).T
    ytr1 = a_onehot([g for _, g in train_g_bal], NOMBRES_GRUPO)
    Xva1 = vec1.transformar([t for t, _ in val]).T
    yva1 = a_onehot([DOMINIO_A_GRUPO[d] for _, d in val], NOMBRES_GRUPO)
    red1 = _entrenar_red(Xtr1, ytr1, Xva1, yva1, len(NOMBRES_GRUPO),
                          capas=(192, 96), dropout=0.3, wd=0.006, lr=0.003, epocas=280, patience=40)
    acc1 = float(np.mean(np.argmax(red1.predecir(Xva1), axis=0) == np.argmax(yva1, axis=0)))
    _guardar(red1, vec1, dir_salida / "clasificador_grupo", NOMBRES_GRUPO,
             extra_meta={"precision_val": acc1, "mapa_dominio_grupo": DOMINIO_A_GRUPO})

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
        acc2 = float(np.mean(np.argmax(red2.predecir(Xva2), axis=0) == np.argmax(yva2, axis=0))) if val_g2 else float("nan")
        _guardar(red2, vec2, dir_salida / f"grupo_{g}", ds, extra_meta={"precision_val": acc2})

    return {"dir_candidato": str(dir_salida), "n_train": len(train), "n_val": len(val),
            "precision_etapa1": acc1}


if __name__ == "__main__":
    import time
    from entrenamiento.entrenar_clasificador import cargar_dataset
    ejemplos, dominios = cargar_dataset()
    version = time.strftime("%Y%m%d_%H%M%S")
    resultado = entrenar(ejemplos, dominios, version)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
