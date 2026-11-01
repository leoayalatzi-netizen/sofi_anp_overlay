#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Colector de Experiencias
# =====================================================================
# Recoge ejemplos (texto, dominio) de las conversaciones reales que el
# VerificadorRespuesta ya aprobó con buena confianza. Es auto-entrenamiento
# semi-supervisado: la etiqueta viene de la propia predicción del
# clasificador + confirmación de que la biblioteca encontró algo útil en
# ese dominio, no de un humano revisando cada caso. Por eso el selector de
# modelo (selector_modelo.py) NUNCA promueve un modelo nuevo sin medir su
# precisión contra un holdout fijo: si el auto-entrenamiento empezara a
# reforzar errores sistemáticos, el benchmark lo detendría.
# =====================================================================
from pathlib import Path
from typing import List, Tuple


def recolectar(memoria_errores, min_confianza: float = 0.65) -> List[Tuple[str, str]]:
    if memoria_errores is None:
        return []
    return memoria_errores.experiencias_aprobadas(min_confianza=min_confianza)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cognicion.memoria_errores import GestorMemoriaErrores
    ge = GestorMemoriaErrores(Path(__file__).parent.parent)
    ejemplos = recolectar(ge)
    print(f"Ejemplos nuevos recolectados de experiencias reales: {len(ejemplos)}")
    for t, d in ejemplos[:10]:
        print(f"  [{d}] {t[:60]}")
