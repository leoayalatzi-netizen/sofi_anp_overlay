#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Verificador de Respuesta
# =====================================================================
# Antes de devolver una respuesta al usuario, se puntúa. Si la puntuación
# total cae debajo del umbral, se marca como NO aprobada: el coordinador
# puede intentar la siguiente mejor opción y se registra el caso en la
# Memoria de Errores para análisis posterior.
#
# Nota de alcance: la "factualidad" aquí es una heurística léxica
# (frases genéricas de relleno, longitud, solapamiento con la pregunta),
# no una verificación contra fuentes externas independientes. Un
# verificador con evidencia real (ETAPA 5 completa) requeriría el
# SistemaInvestigacion con fuentes web activas, que este cambio no
# implementa.
# =====================================================================
import re
import unicodedata
from typing import Set

from .contratos import Veredicto

FRASES_RELLENO = (
    "he procesado tu mensaje", "estoy aprendiendo de cada interacción",
    "puedes darme más detalles", "no tuve una buena respuesta",
)
STOP = {"que","como","para","por","del","los","las","una","con","que","el","la","de","en","y","a","un","al","su","es","que"}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _palabras(texto: str) -> Set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", _normalizar(texto)) if w not in STOP}


class VerificadorRespuesta:
    UMBRAL_APROBACION = 0.45

    @classmethod
    def verificar(cls, pregunta: str, respuesta: str, fuente: str = "") -> Veredicto:
        if not respuesta or not respuesta.strip():
            return Veredicto(0, 0, 0, 0, 0.0, False, "respuesta vacía")

        # Fuentes deterministas (cálculo exacto, recuerdo textual de la
        # sesión) no necesitan pasar el filtro de solapamiento léxico: su
        # confiabilidad viene del propio motor, no de compartir palabras
        # con la pregunta (p.ej. "cuánto es 12*8" -> "12*8 = 96").
        if fuente in ("calculo", "memoria_sesion"):
            return Veredicto(0.95, 1.0, 1.0, 1.0, 0.95, True, "fuente determinista")

        rl = respuesta.lower()
        es_relleno = any(f in rl for f in FRASES_RELLENO)

        factualidad = 0.85 if not es_relleno else 0.1
        if len(respuesta) < 12:
            factualidad *= 0.5

        coherencia = 1.0 if respuesta.strip()[-1:] in ".!?)…\"'0123456789%" or len(respuesta) > 20 else 0.6

        p_pal, r_pal = _palabras(pregunta), _palabras(respuesta)
        solapamiento = len(p_pal & r_pal) / max(1, len(p_pal))
        # Sin floor artificial: si la respuesta no comparte ni una palabra
        # clave con la pregunta, la relevancia debe caer a cero de verdad
        # (esto es lo que antes dejaba pasar "respuestas absurdas" del
        # integrador V4 con solo porque eran largas y bien formadas).
        relevancia = solapamiento if p_pal else 0.5
        if es_relleno:
            relevancia = 0.15

        completitud = min(1.0, len(respuesta) / 120.0)
        if es_relleno:
            completitud *= 0.3

        confianza_total = round(0.3 * factualidad + 0.15 * coherencia + 0.4 * relevancia + 0.15 * completitud, 3)
        # Compuerta dura: una pregunta con contenido (>=3 palabras clave) que
        # recibe una respuesta sin NINGÚN término en común probablemente no
        # está respondiendo lo que se preguntó, sin importar qué tan larga
        # o bien formada esté.
        if p_pal and len(p_pal) >= 2 and solapamiento == 0 and not es_relleno:
            confianza_total = min(confianza_total, 0.3)
        aprobado = confianza_total >= cls.UMBRAL_APROBACION
        motivo = "respuesta genérica sin contenido" if es_relleno else (
            "aprobada" if aprobado else (
                "sin relación temática con la pregunta" if (p_pal and solapamiento == 0) else "confianza insuficiente"))
        return Veredicto(factualidad, coherencia, relevancia, completitud, confianza_total, aprobado, motivo)
