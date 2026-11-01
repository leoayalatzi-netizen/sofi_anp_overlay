#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Planificador Cognitivo
# =====================================================================
# El componente #1 que faltaba: convierte los motores de "especialistas
# sueltos donde gana el primero que responde" a "herramientas que el
# planificador elige y coordina según lo que el problema necesita".
#
# Cómo se conecta con el resto del sistema (para no crear imports
# circulares con principal.py): recibe un diccionario de "ejecutores",
# funciones callable(texto, analisis) -> Candidato, una por cada motor
# lógico declarado en registro_herramientas. principal.py las construye
# a partir de sus propios objetos (biblioteca, integrador, sintesis...)
# y se las pasa al planificador en el arranque.
# =====================================================================
import time
from typing import Callable, Dict, List, Optional

from .analizador_entrada import AnalizadorEntrada
from .contratos import AnalisisEntrada, Candidato, EstadoTarea, Task, Veredicto
from .evidencia import MotorConsenso, MotorIncertidumbre
from .grafo_tareas import GrafoTareas
from .memoria_errores import GestorMemoriaErrores
from .registro_herramientas import buscar_por_capacidad
from .verificador import VerificadorRespuesta

Ejecutor = Callable[[str, AnalisisEntrada], Optional[Candidato]]


class ResultadoPlanificacion:
    def __init__(self, respuesta: str, veredicto: Veredicto, incertidumbre: MotorIncertidumbre,
                 analisis: AnalisisEntrada, grafo: GrafoTareas, candidatos: List[Candidato]):
        self.respuesta = respuesta
        self.veredicto = veredicto
        self.incertidumbre = incertidumbre
        self.analisis = analisis
        self.grafo = grafo
        self.candidatos = candidatos


class PlanificadorCognitivo:
    def __init__(self, ejecutores: Dict[str, Ejecutor], clasificador_dominio=None,
                 memoria_errores: Optional[GestorMemoriaErrores] = None):
        self.ejecutores = ejecutores
        self.analizador = AnalizadorEntrada(clasificador_dominio)
        self.memoria_errores = memoria_errores

    def _construir_grafo(self, analisis: AnalisisEntrada) -> GrafoTareas:
        g = GrafoTareas()
        g.agregar(Task(id="percepcion", objetivo="interpretar la entrada", motor_requerido="percepcion"))
        deps_integracion = []

        if analisis.requiere_calculo:
            g.agregar(Task(id="calculo", objetivo="resolver operación", motor_requerido="calculo",
                            dependencias=["percepcion"]))
            deps_integracion.append("calculo")
        if analisis.requiere_memoria:
            g.agregar(Task(id="memoria", objetivo="consultar sesión/historial", motor_requerido="memoria",
                            dependencias=["percepcion"]))
            deps_integracion.append("memoria")
        if analisis.requiere_busqueda:
            g.agregar(Task(id="busqueda", objetivo="consultar biblioteca de conocimiento", motor_requerido="biblioteca",
                            dependencias=["percepcion"]))
            deps_integracion.append("busqueda")
        if analisis.requiere_razonamiento:
            g.agregar(Task(id="razonamiento", objetivo="razonar/sintetizar relación", motor_requerido="razonamiento",
                            dependencias=[d for d in deps_integracion] or ["percepcion"]))
            deps_integracion.append("razonamiento")
        if analisis.requiere_creatividad:
            g.agregar(Task(id="creatividad", objetivo="generar contenido creativo", motor_requerido="creatividad",
                            dependencias=["percepcion"]))
            deps_integracion.append("creatividad")

        if not deps_integracion:
            deps_integracion = ["percepcion"]
        g.agregar(Task(id="sintesis", objetivo="consolidar respuesta final", motor_requerido="sintesis",
                        dependencias=deps_integracion))
        return g

    def _ejecutar_tarea(self, task: Task, texto: str, analisis: AnalisisEntrada) -> List[Candidato]:
        if task.motor_requerido in ("percepcion", "sintesis"):
            return []  # no producen candidato propio; percepción ya ocurrió, síntesis se resuelve en consenso
        ejecutor = self.ejecutores.get(task.motor_requerido)
        if ejecutor is None:
            task.estado = EstadoTarea.OMITIDA
            return []
        try:
            candidato = ejecutor(texto, analisis)
            if candidato is None:
                task.estado = EstadoTarea.OMITIDA
                return []
            task.estado = EstadoTarea.EJECUTADA
            task.resultado, task.confianza = candidato.texto, candidato.confianza
            return [candidato]
        except Exception as e:
            task.estado = EstadoTarea.FALLIDA
            task.resultado = f"error: {e}"
            return []

    def resolver(self, texto: str) -> ResultadoPlanificacion:
        analisis = self.analizador.analizar(texto)
        grafo = self._construir_grafo(analisis)

        candidatos: List[Candidato] = []
        for task in grafo.orden_topologico():
            candidatos.extend(self._ejecutar_tarea(task, texto, analisis))

        mejor, incertidumbre = MotorConsenso.consolidar(candidatos)
        veredicto = VerificadorRespuesta.verificar(texto, mejor.texto, fuente=mejor.fuente)

        if self.memoria_errores is not None:
            self.memoria_errores.registrar_experiencia(analisis.dominio, analisis.intencion,
                                                         veredicto.aprobado, veredicto.confianza_total, texto=texto)
        if not veredicto.aprobado and self.memoria_errores is not None:
            self.memoria_errores.registrar(
                pregunta=texto, dominio=analisis.dominio, intencion=analisis.intencion,
                respuesta=mejor.texto, confianza=veredicto.confianza_total, motivo=veredicto.motivo,
            )

        return ResultadoPlanificacion(mejor.texto, veredicto, incertidumbre, analisis, grafo, candidatos)
