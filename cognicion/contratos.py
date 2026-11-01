#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Contratos del subsistema cognitivo
# =====================================================================
# Estructuras de datos compartidas entre AnalizadorEntrada, Planificador,
# GrafoTareas, MotorEvidencia/Consenso, VerificadorRespuesta y
# GestorMemoriaErrores. Mantenerlas separadas evita imports circulares.
# =====================================================================
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class AnalisisEntrada:
    """Salida del AnalizadorEntrada: NO decide qué motor usar, solo
    describe probabilísticamente el problema. La decisión es del
    PlanificadorCognitivo."""
    texto: str
    dominio: Optional[str] = None
    confianza_dominio: float = 0.0
    intencion: str = "factual"  # factual|explicacion|calculo|creatividad|comparacion|conversacional
    complejidad: float = 0.2       # 0..1
    ambiguedad: float = 0.0        # 0..1
    requiere_memoria: bool = True
    requiere_busqueda: bool = True
    requiere_razonamiento: bool = False
    requiere_calculo: bool = False
    requiere_creatividad: bool = False
    requiere_verificacion: bool = True


class EstadoTarea(Enum):
    PENDIENTE = "pendiente"
    EJECUTADA = "ejecutada"
    FALLIDA = "fallida"
    OMITIDA = "omitida"


@dataclass
class Task:
    id: str
    objetivo: str
    motor_requerido: str
    dependencias: List[str] = field(default_factory=list)
    estado: EstadoTarea = EstadoTarea.PENDIENTE
    resultado: Any = None
    confianza: float = 0.0


@dataclass
class Candidato:
    """Una respuesta candidata producida por una tarea/motor, antes del
    consenso y la verificación."""
    texto: str
    fuente: str
    confianza: float


@dataclass
class Veredicto:
    """Salida del VerificadorRespuesta."""
    factualidad: float
    coherencia: float
    relevancia: float
    completitud: float
    confianza_total: float
    aprobado: bool
    motivo: str = ""


@dataclass
class MotorCapability:
    nombre: str
    capacidades: List[str]
    coste: float = 0.3
    fiabilidad: float = 0.7
