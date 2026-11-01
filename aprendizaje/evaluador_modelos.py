#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.1 - Evaluador de Modelos (pipeline JERÁRQUICO)
# =====================================================================
import json
import random as random_stdlib
import sys
from pathlib import Path
from typing import List, Tuple

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

import numpy as np

from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima
from nucleos.comunicacion.motores.motor_clasificador_dominio import _tokenizar
from entrenamiento.entrenar_clasificador import VectorizadorTFIDF
from collections import Counter


def construir_holdout_fijo(frac: float = 0.2, seed: int = 12345) -> List[Tuple[str, str]]:
    from entrenamiento.extraer_dataset import construir_dataset
    ejemplos, dominios = construir_dataset()
    rng = random_stdlib.Random(seed)
    por_clase = {d: [] for d in dominios}
    for t, d in ejemplos:
        por_clase[d].append(t)
    holdout = []
    for d, textos in por_clase.items():
        textos = list(textos)
        rng.shuffle(textos)
        n = max(1, int(len(textos) * frac))
        holdout += [(t, d) for t in textos[:n]]
    return holdout


def _vectorizar(texto: str, vocabulario, idf) -> np.ndarray:
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


def _cargar_pipeline(dir_modelos: Path):
    meta_g = json.loads((dir_modelos / "clasificador_grupo_vocab.json").read_text(encoding="utf-8"))
    red_g = RedNeuronalOptima.cargar(str(dir_modelos / "clasificador_grupo.anp"))
    grupos = meta_g["clases"]
    modelos_grupo = {}
    for g in grupos:
        ruta_pesos = dir_modelos / f"grupo_{g}.anp"
        if not ruta_pesos.exists():
            continue
        meta2 = json.loads((dir_modelos / f"grupo_{g}_vocab.json").read_text(encoding="utf-8"))
        modelos_grupo[g] = {
            "red": RedNeuronalOptima.cargar(str(ruta_pesos)),
            "vocab": meta2["vocabulario"], "idf": np.array(meta2["idf"]), "dominios": meta2["clases"],
        }
    return {"red_grupo": red_g, "vocab_grupo": meta_g["vocabulario"], "idf_grupo": np.array(meta_g["idf"]),
            "grupos": grupos, "modelos_grupo": modelos_grupo}


def evaluar_pipeline(dir_modelos: Path, holdout: List[Tuple[str, str]]) -> dict:
    pl = _cargar_pipeline(dir_modelos)
    aciertos = 0
    por_dominio = {}
    for texto, dom_real in holdout:
        x1 = _vectorizar(texto, pl["vocab_grupo"], pl["idf_grupo"])
        g_pred = pl["grupos"][int(np.argmax(pl["red_grupo"].predecir(x1), axis=0)[0])]
        info = pl["modelos_grupo"].get(g_pred)
        pred_dom = None
        if info is not None:
            x2 = _vectorizar(texto, info["vocab"], info["idf"])
            pred_dom = info["dominios"][int(np.argmax(info["red"].predecir(x2), axis=0)[0])]
        por_dominio.setdefault(dom_real, {"n": 0, "aciertos": 0})
        por_dominio[dom_real]["n"] += 1
        if pred_dom == dom_real:
            aciertos += 1
            por_dominio[dom_real]["aciertos"] += 1
    return {"precision": aciertos / len(holdout) if holdout else 0.0, "n_holdout": len(holdout),
            "por_dominio": por_dominio}


def comparar(dir_candidato: str) -> dict:
    dir_prod = BASE / "almacenamiento" / "modelos"
    holdout = construir_holdout_fijo()
    actual = evaluar_pipeline(dir_prod, holdout)
    candidato = evaluar_pipeline(Path(dir_candidato), holdout)
    return {"precision_actual": actual["precision"], "precision_candidato": candidato["precision"],
            "mejora": candidato["precision"] - actual["precision"], "n_holdout": actual["n_holdout"]}


if __name__ == "__main__":
    dir_prod = BASE / "almacenamiento" / "modelos"
    holdout = construir_holdout_fijo()
    r = evaluar_pipeline(dir_prod, holdout)
    print(json.dumps({"precision_produccion": r["precision"], "n_holdout": r["n_holdout"]}, ensure_ascii=False, indent=2))
