#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Modelo de Capacidades
# =====================================================================
# Perfil dinámico "DOMINIO -> score" calculado a partir de la tasa real
# de respuestas aprobadas por el verificador en ese dominio. No son
# benchmarks externos curados (eso sería la ETAPA 6 completa, con
# evaluador_modelos.py); es la aproximación honesta que se puede tener
# hoy con los datos que Nevula ya genera en cada conversación.
# =====================================================================
from typing import Dict, Optional


class ModeloCapacidades:
    def __init__(self, memoria_errores):
        self.memoria_errores = memoria_errores

    def perfil(self) -> Dict[str, Dict[str, float]]:
        if self.memoria_errores is None:
            return {}
        return self.memoria_errores.perfil_dominios()

    def resumen(self, min_intentos: int = 1) -> str:
        perfil = self.perfil()
        if not perfil:
            return "📈 Todavía no hay suficientes intentos registrados para estimar capacidades por dominio."
        filas = [(d, s) for d, s in perfil.items() if s["intentos"] >= min_intentos]
        filas.sort(key=lambda x: -x[1]["tasa"])
        lineas = ["📈 **Capacidades estimadas por dominio** (tasa de aprobación del verificador):\n"]
        for dominio, s in filas:
            barra_n = round(s["tasa"] * 10)
            barra = "█" * barra_n + "░" * (10 - barra_n)
            lineas.append(f"  {dominio:<22} {barra} {s['tasa']:.0%}  ({s['aprobados']}/{s['intentos']} intentos)")
        return "\n".join(lineas)
