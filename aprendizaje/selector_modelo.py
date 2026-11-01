#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.1 - Selector de Modelo (pipeline JERÁRQUICO)
# =====================================================================
# Igual que en Nevula 1.0: nunca se promueve un candidato sin evaluarlo
# contra el mismo holdout fijo que la producción. Ahora "promover"
# significa copiar TANTO el clasificador de grupo (etapa 1) COMO los
# cuatro clasificadores especializados (etapa 2), ya que son un pipeline
# indivisible -- promover solo una etapa dejaría el sistema inconsistente.
# =====================================================================
import json
import shutil
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from aprendizaje import registro_versiones
from aprendizaje.entrenador import entrenar
from aprendizaje.evaluador_modelos import comparar
from aprendizaje.generador_dataset import construir_dataset_candidato

MARGEN_MINIMO_MEJORA = 0.02


def ejecutar_ciclo(margen_minimo: float = MARGEN_MINIMO_MEJORA) -> dict:
    ejemplos, dominios, n_nuevos = construir_dataset_candidato()
    id_version = time.strftime("%Y%m%d_%H%M%S")

    resultado_entrenamiento = entrenar(ejemplos, dominios, id_version)
    comparacion = comparar(resultado_entrenamiento["dir_candidato"])

    promovido = comparacion["mejora"] >= margen_minimo
    entrada_registro = {
        "id_version": id_version, "n_ejemplos_totales": len(ejemplos), "n_ejemplos_nuevos": n_nuevos,
        "precision_etapa1_candidato": resultado_entrenamiento["precision_etapa1"],
        "precision_holdout_actual": comparacion["precision_actual"],
        "precision_holdout_candidato": comparacion["precision_candidato"],
        "mejora": comparacion["mejora"], "margen_requerido": margen_minimo, "promovido": promovido,
        "motivo": ("mejora >= margen: promovido a producción" if promovido else
                   f"mejora {comparacion['mejora']:.1%} < margen {margen_minimo:.1%}: se descarta, "
                   "producción no cambia"),
    }

    if promovido:
        dir_prod = BASE / "almacenamiento" / "modelos"
        dir_cand = Path(resultado_entrenamiento["dir_candidato"])
        for archivo in dir_cand.glob("*"):
            shutil.copy(archivo, dir_prod / archivo.name)
        # Recalcular y guardar el resumen jerárquico oficial en producción
        holdout_info = {"precision_total_jerarquico": comparacion["precision_candidato"],
                         "precision_etapa1_grupo": resultado_entrenamiento["precision_etapa1"]}
        (dir_prod / "jerarquico_resumen.json").write_text(json.dumps(holdout_info, ensure_ascii=False, indent=1),
                                                           encoding="utf-8")

    registro_versiones.registrar(entrada_registro)
    return entrada_registro


if __name__ == "__main__":
    r = ejecutar_ciclo()
    print(json.dumps(r, ensure_ascii=False, indent=2))
