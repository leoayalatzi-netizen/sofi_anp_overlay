#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Router Creativo
# =====================================================================
# Antes, "relacionar/comparar" pasaba por MotorSintesis (que en realidad
# es un motor de síntesis conceptual, no de creatividad) y los motores
# reales de creatividad (motor_ideas.py, motor_imaginacion.py) nunca se
# usaban desde principal.py pese a existir y funcionar. Este router los
# activa, pero SOLO cuando AnalizadorEntrada marcó intencion=="creatividad":
# así no pueden colarse en una pregunta factual (el problema de
# "respuestas absurdas" que ya atajó el VerificadorRespuesta se ataca acá
# desde el origen, no solo al final).
# =====================================================================
import re
from typing import Any, Optional

from .contratos import Candidato

_STOP_INSTRUCCION = {
    "imagina", "imaginate", "imagínate", "escribe", "dime", "crea", "una", "un", "sobre",
    "de", "poema", "poesia", "poesía", "historia", "cuento", "corto", "corta", "metafora",
    "metáfora", "por", "favor", "hazme", "genera", "invéntame", "inventame",
    "inventa", "para", "con", "que", "trate", "cuentame", "cuéntame", "cuenta",
    "dame", "ideas", "idea", "sobre", "acerca", "del", "los", "las", "tienes",
}


def _extraer_concepto(texto: str) -> str:
    palabras = [w for w in re.findall(r"[a-záéíóúñ]+", texto.lower()) if w not in _STOP_INSTRUCCION and len(w) > 2]
    return " ".join(palabras) or "un concepto abstracto"


class RouterCreativo:
    def __init__(self, cargador):
        self.motor_imaginacion = self._obtener(cargador, "creatividad/motor_imaginacion")
        self.motor_ideas = self._obtener(cargador, "creatividad/motor_ideas")

    @staticmethod
    def _obtener(cargador, clave: str):
        info = cargador.motores.get(clave)
        return info.instancia if info else None

    def generar(self, texto: str, analisis) -> Optional[Candidato]:
        tl = texto.lower()
        concepto = _extraer_concepto(texto)

        if "idea" in tl or "brainstorm" in tl:
            if self.motor_ideas is None:
                return None
            r = self.motor_ideas.procesar({"operacion": "brainstorm", "tema": concepto, "cantidad": 3})
            if not getattr(r, "exito", False) or not r.datos.get("ideas"):
                return None
            ideas = "; ".join(i["texto"] for i in r.datos["ideas"][:3])
            return Candidato(texto=f"💡 {ideas}", fuente="motor_ideas", confianza=0.55)

        if self.motor_imaginacion is None:
            return None
        if "metafora" in tl or "metáfora" in tl:
            op, extra, campo = "metafora", {"concepto": concepto}, "metaforas"
        elif "historia" in tl or "cuento" in tl:
            op, extra, campo = "historia", {"tema": concepto}, "historia"
        elif "poema" in tl or "poesia" in tl or "poesía" in tl:
            op, extra, campo = "poema", {"tema": concepto}, "poema"
        else:
            op, extra, campo = "imaginar", {"concepto": concepto}, "visualizacion"

        r = self.motor_imaginacion.procesar({"operacion": op, **extra})
        if not getattr(r, "exito", False) or not r.datos:
            return None
        d = r.datos
        salida = d.get(campo)
        if isinstance(salida, list):
            salida = "\n".join(salida)
        if not salida:
            return None
        return Candidato(texto=f"🎨 {salida}", fuente="motor_imaginacion", confianza=0.55)
