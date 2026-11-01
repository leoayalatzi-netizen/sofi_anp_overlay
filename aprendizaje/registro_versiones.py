#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Registro de Versiones
# =====================================================================
import json
import time
from pathlib import Path
from typing import Any, Dict, List

RUTA = Path(__file__).parent.parent / "almacenamiento" / "modelos" / "versiones" / "registro.json"


def _cargar() -> List[Dict[str, Any]]:
    if RUTA.exists():
        try:
            return json.loads(RUTA.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def registrar(entrada: Dict[str, Any]) -> None:
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    historial = _cargar()
    entrada = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), **entrada}
    historial.append(entrada)
    RUTA.write_text(json.dumps(historial, ensure_ascii=False, indent=1), encoding="utf-8")


def historial() -> List[Dict[str, Any]]:
    return _cargar()


def version_activa() -> Dict[str, Any]:
    h = _cargar()
    promovidas = [v for v in h if v.get("promovido")]
    return promovidas[-1] if promovidas else {}
