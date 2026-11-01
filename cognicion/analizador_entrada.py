#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Analizador de Entrada
# =====================================================================
# Convierte texto crudo en un AnalisisEntrada: no dice "manda esto al
# motor de ciencia", dice "81% ciencia, probablemente necesita
# razonamiento + búsqueda + verificación". La decisión de qué hacer con
# eso es del PlanificadorCognitivo.
# =====================================================================
import re
from typing import Optional

from .contratos import AnalisisEntrada

PALABRAS_CALCULO = re.compile(
    r'\d+\s*[\+\-\*\/\^]\s*\d+|cu[aá]nto es|cu[aá]nto vale|calcula|resuelve|'
    r'\d+\s*%\s*de|[a-zA-Z]\s*[\+\-\*\/\^]?\s*\d*\s*='
)
PALABRAS_COMPARACION = re.compile(r'\b(compara|diferencia|vs\.?|versus|parecido|similitud|mejor que|peor que)\b')
PALABRAS_CAUSALES = re.compile(r'\b(por qu[eé]|causa|efecto|consecuencia|implica|conllevar[ií]a)\b')
PALABRAS_CREATIVIDAD = re.compile(
    r'\b(imagina|inventa|invent[aá]me|dame ideas|ideas sobre|idea creativa|brainstorm|'
    r'(?:crea|escribe|cu[eé]ntame|cuenta)\w*\s+(?:un[a]?\s+)?(?:historia|cuento|poema|poesia|metáfora|metafora)|'
    r'poema sobre|cuento corto|micro ?historia)\b'
)
PALABRAS_CONVERSACIONAL = re.compile(r'\b(hola|gracias|ad[ií]os|c[oó]mo est[aá]s|qui[eé]n eres)\b')
CONECTORES_COMPLEJIDAD = re.compile(r'\b(y|adem[aá]s|tambi[eé]n|luego|entonces|mientras|si\b.*entonces)\b')
PRONOMBRES_AMBIGUOS = re.compile(r'\b(eso|esto|aquello|ello|lo mismo)\b')


class AnalizadorEntrada:
    def __init__(self, clasificador_dominio=None):
        self.clasificador_dominio = clasificador_dominio

    def analizar(self, texto: str) -> AnalisisEntrada:
        t = texto.strip()
        tl = t.lower()

        dominio, confianza_dominio = None, 0.0
        if self.clasificador_dominio is not None:
            try:
                r = self.clasificador_dominio.clasificar(t)
                if r.get("exito"):
                    dominio, confianza_dominio = r["dominio"], r["confianza"]
            except Exception:
                pass

        intencion = "factual"
        if PALABRAS_CALCULO.search(tl):
            intencion = "calculo"
        elif PALABRAS_COMPARACION.search(tl):
            intencion = "comparacion"
        elif PALABRAS_CAUSALES.search(tl):
            intencion = "explicacion"
        elif PALABRAS_CREATIVIDAD.search(tl):
            intencion = "creatividad"
        elif PALABRAS_CONVERSACIONAL.search(tl):
            intencion = "conversacional"

        n_palabras = len(tl.split())
        n_conectores = len(CONECTORES_COMPLEJIDAD.findall(tl))
        n_signos_pregunta = tl.count('?')
        complejidad = min(1.0, 0.15 + n_palabras / 40.0 + n_conectores * 0.15 + (0.2 if intencion == "comparacion" else 0))

        ambiguedad = 0.1
        if n_palabras <= 2:
            ambiguedad += 0.4
        if PRONOMBRES_AMBIGUOS.search(tl) and n_palabras < 8:
            ambiguedad += 0.3
        ambiguedad = min(1.0, ambiguedad)

        requiere_calculo = intencion == "calculo"
        requiere_creatividad = intencion == "creatividad"
        requiere_razonamiento = intencion in ("explicacion", "comparacion") or n_conectores > 0
        requiere_busqueda = intencion in ("factual", "explicacion", "comparacion") and not requiere_creatividad
        requiere_memoria = intencion != "creatividad"
        requiere_verificacion = intencion in ("factual", "explicacion", "comparacion", "calculo")

        return AnalisisEntrada(
            texto=t, dominio=dominio, confianza_dominio=confianza_dominio,
            intencion=intencion, complejidad=complejidad, ambiguedad=ambiguedad,
            requiere_memoria=requiere_memoria, requiere_busqueda=requiere_busqueda,
            requiere_razonamiento=requiere_razonamiento, requiere_calculo=requiere_calculo,
            requiere_creatividad=requiere_creatividad, requiere_verificacion=requiere_verificacion,
        )
