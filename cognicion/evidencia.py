#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Evidencia / Consenso / Incertidumbre
# =====================================================================
import math
from typing import List, Tuple

from .contratos import Candidato


class MotorConsenso:
    """Dado un conjunto de respuestas candidatas (de memoria, búsqueda,
    razonamiento, síntesis...), elige la más confiable en vez de
    'gana el primer hilo que responde'."""

    @staticmethod
    def consolidar(candidatos: List[Candidato]) -> Tuple[Candidato, "MotorIncertidumbre"]:
        candidatos = [c for c in candidatos if c and c.texto and c.texto.strip()]
        if not candidatos:
            vacio = Candidato(texto="", fuente="ninguna", confianza=0.0)
            return vacio, MotorIncertidumbre.calcular([])
        candidatos.sort(key=lambda c: -c.confianza)
        return candidatos[0], MotorIncertidumbre.calcular(candidatos)


class MotorIncertidumbre:
    """Cuantifica cuánto debería 'dudar' Nevula de su propia respuesta,
    a partir de la dispersión de confianza entre los candidatos."""

    def __init__(self, epistemica: float, conflicto: float, confianza_final: float):
        self.epistemica = epistemica
        self.conflicto = conflicto
        self.confianza_final = confianza_final

    @staticmethod
    def calcular(candidatos: List[Candidato]) -> "MotorIncertidumbre":
        if not candidatos:
            return MotorIncertidumbre(epistemica=1.0, conflicto=0.0, confianza_final=0.0)
        top = candidatos[0].confianza
        epistemica = max(0.0, 1.0 - top)
        if len(candidatos) > 1:
            segundo = candidatos[1].confianza
            # Si el segundo mejor candidato está muy cerca del primero, hay
            # conflicto real entre fuentes (no un ganador claro).
            conflicto = max(0.0, 1.0 - abs(top - segundo))
        else:
            conflicto = 0.0
        confianza_final = max(0.0, top - 0.3 * conflicto)
        return MotorIncertidumbre(epistemica=epistemica, conflicto=conflicto, confianza_final=confianza_final)

    def nivel(self) -> str:
        """Nivel de INCERTIDUMBRE (no de confianza): confianza alta -> incertidumbre baja."""
        if self.confianza_final >= 0.7:
            return "baja"
        if self.confianza_final >= 0.4:
            return "media"
        return "alta"
