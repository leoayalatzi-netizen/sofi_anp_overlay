#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Generador de Dataset (candidato)
# =====================================================================
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))


def construir_dataset_candidato(min_confianza_experiencias: float = 0.65):
    from entrenamiento.extraer_dataset import construir_dataset as construir_base
    from cognicion.memoria_errores import GestorMemoriaErrores
    from aprendizaje.colector_experiencias import recolectar

    ejemplos_base, dominios = construir_base()
    memoria = GestorMemoriaErrores(BASE)
    nuevos = recolectar(memoria, min_confianza=min_confianza_experiencias)

    vistos = {t for t, _ in ejemplos_base}
    agregados = [(t, d) for t, d in nuevos if t not in vistos and d in dominios]

    return ejemplos_base + agregados, dominios, len(agregados)


if __name__ == "__main__":
    ejemplos, dominios, n_nuevos = construir_dataset_candidato()
    print(f"Dataset candidato: {len(ejemplos)} ejemplos ({n_nuevos} nuevos de conversaciones reales)")
    out = BASE / "entrenamiento" / "dataset_dominios_candidato.json"
    out.write_text(json.dumps({"dominios": dominios, "ejemplos": ejemplos}, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"Guardado en {out}")
