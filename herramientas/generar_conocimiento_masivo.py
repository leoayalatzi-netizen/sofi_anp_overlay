#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from datos_generados_1 import PROGRAMACION, MATEMATICAS
from datos_generados_2 import DEPORTES, GEOGRAFIA, ROBOTICA
from datos_generados_3 import (
    CONVERSACIONAL, CULTURA_EXTRA, VIDA_COTIDIANA_EXTRA, NATURALEZA_EXTRA,
    CONOCIMIENTO_GENERAL_EXTRA, ENTRETENIMIENTO_EXTRA, TECNOLOGIA_EXTRA,
    CIENCIA_EXTRA, HUMANIDAD_EXTRA, LENGUAJE_EXTRA,
)
from datos_generados_4 import (
    CULTURA_EXTRA2, VIDA_COTIDIANA_EXTRA2, NATURALEZA_EXTRA2, CONOCIMIENTO_GENERAL_EXTRA2,
    ROBOTICA_EXTRA2, CONVERSACIONAL_EXTRA2, DEPORTES_EXTRA2, HUMANIDAD_EXTRA2, LENGUAJE_EXTRA2,
)

NUEVOS_DOMINIOS = {
    "programacion": PROGRAMACION,
    "matematicas": MATEMATICAS,
    "deportes": DEPORTES + DEPORTES_EXTRA2,
    "geografia": GEOGRAFIA,
    "robotica": ROBOTICA + ROBOTICA_EXTRA2,
    "conversacional": CONVERSACIONAL + CONVERSACIONAL_EXTRA2,
}

AMPLIACIONES_DOMINIOS_EXISTENTES = {
    "cultura": CULTURA_EXTRA + CULTURA_EXTRA2,
    "vida_cotidiana": VIDA_COTIDIANA_EXTRA + VIDA_COTIDIANA_EXTRA2,
    "naturaleza": NATURALEZA_EXTRA + NATURALEZA_EXTRA2,
    "conocimiento_general": CONOCIMIENTO_GENERAL_EXTRA + CONOCIMIENTO_GENERAL_EXTRA2,
    "entretenimiento": ENTRETENIMIENTO_EXTRA,
    "tecnologia": TECNOLOGIA_EXTRA,
    "ciencia": CIENCIA_EXTRA,
    "humanidad": HUMANIDAD_EXTRA + HUMANIDAD_EXTRA2,
    "lenguaje": LENGUAJE_EXTRA + LENGUAJE_EXTRA2,
}


def tuplas_a_items(tuplas):
    return [{"concepto": c, "nombre": n, "definicion": d, "ejemplo": e} for c, n, d, e in tuplas]


def escribir(dominio: str, nombre_archivo: str, tuplas):
    carpeta = BASE / "datos" / dominio
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo
    contenido = {
        "metadata": {"generado_por": "herramientas/generar_conocimiento_masivo.py",
                     "dominio": dominio, "n_items": len(tuplas)},
        "datos": tuplas_a_items(tuplas),
    }
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(tuplas)


def main():
    total = 0
    print("=== Nuevos dominios ===")
    for dominio, tuplas in NUEVOS_DOMINIOS.items():
        n = escribir(dominio, "general.json", tuplas)
        total += n
        print(f"  {dominio:<18} {n:>4} items nuevos")

    print("\n=== Ampliación de dominios existentes ===")
    for dominio, tuplas in AMPLIACIONES_DOMINIOS_EXISTENTES.items():
        n = escribir(dominio, "ampliacion_masiva.json", tuplas)
        total += n
        print(f"  {dominio:<18} {n:>4} items nuevos")

    print(f"\nTotal de items nuevos escritos en datos/: {total}")


if __name__ == "__main__":
    main()
