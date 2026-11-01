#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Grafo de Tareas
# =====================================================================
# Nota de alcance: esta versión resuelve las dependencias con un orden
# topológico simple y ejecución secuencial (no hay concurrencia real).
# Es suficiente para el número de tareas que genera el planificador hoy
# (típicamente 2-5); paralelismo real de motores queda para una
# siguiente iteración si el número de tareas por consulta crece.
# =====================================================================
from typing import Dict, List

from .contratos import EstadoTarea, Task


class GrafoTareas:
    def __init__(self):
        self.tareas: Dict[str, Task] = {}

    def agregar(self, task: Task) -> "GrafoTareas":
        self.tareas[task.id] = task
        return self

    def orden_topologico(self) -> List[Task]:
        visitadas, orden = set(), []

        def visitar(tid: str, pila: set):
            if tid in visitadas or tid not in self.tareas:
                return
            if tid in pila:
                return  # ciclo: se ignora la dependencia repetida
            pila.add(tid)
            for dep in self.tareas[tid].dependencias:
                visitar(dep, pila)
            pila.discard(tid)
            visitadas.add(tid)
            orden.append(self.tareas[tid])

        for tid in self.tareas:
            visitar(tid, set())
        return orden

    def resumen(self) -> str:
        return " -> ".join(f"{t.id}({t.motor_requerido})" for t in self.orden_topologico())
