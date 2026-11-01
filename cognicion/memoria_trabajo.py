#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Memoria de Trabajo
# =====================================================================
# Guarda en memoria (no en disco: es de corto plazo) las últimas N
# resoluciones del PlanificadorCognitivo: problema, subresultados,
# candidatos y veredicto. Es la base para que SistemaMetacognitivo pueda
# responder "¿qué estaba resolviendo?" y para una futura réplica de plan
# (ETAPA 2 completa) que aún no existe: por ahora es de solo lectura, no
# se usa todavía para replanificar automáticamente.
# =====================================================================
from collections import deque
from typing import Deque, List, Optional


class MemoriaTrabajo:
    def __init__(self, maxlen: int = 20):
        self._resultados: Deque = deque(maxlen=maxlen)

    def registrar(self, resultado_planificacion) -> None:
        self._resultados.append(resultado_planificacion)

    def ultimo(self):
        return self._resultados[-1] if self._resultados else None

    def ultimos(self, n: int = 5) -> List:
        return list(self._resultados)[-n:]

    def dominio_actual(self) -> Optional[str]:
        u = self.ultimo()
        return u.analisis.dominio if u else None
