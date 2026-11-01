#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Registro de Herramientas
# =====================================================================
# Punto único donde se declara qué sabe hacer cada motor. El planificador
# nunca importa un motor por su nombre de archivo: pregunta "¿quién sabe
# hacer esto?" y el registro responde. Así el sistema puede crecer de
# 28 a 50 motores sin tocar el cerebro central.
#
# Nota de alcance: para esta primera versión (Nevula 1.0) las capacidades
# están declaradas a mano con valores de fiabilidad razonables, no
# calculadas por benchmark automático (eso es la ETAPA 6 del plan,
# "aprendizaje continuo", que queda fuera de este cambio).
# =====================================================================
from typing import Dict, List, Optional

from .contratos import MotorCapability

_CAPACIDADES: List[MotorCapability] = [
    MotorCapability("memoria", ["recordar", "historial", "sesion", "contexto"], coste=0.1, fiabilidad=0.9),
    MotorCapability("biblioteca", ["buscar", "conocimiento", "hechos", "definicion"], coste=0.15, fiabilidad=0.75),
    MotorCapability("razonamiento", ["razonar", "causal", "logico", "comparar", "por_que"], coste=0.4, fiabilidad=0.7),
    MotorCapability("calculo", ["calcular", "aritmetica", "ecuacion", "matematicas"], coste=0.1, fiabilidad=0.97),
    MotorCapability("sintesis", ["relacionar", "conectar", "sintetizar", "combinar"], coste=0.35, fiabilidad=0.6),
    MotorCapability("creatividad", ["imaginar", "idea", "creativo", "inventar"], coste=0.3, fiabilidad=0.55),
    MotorCapability("clasificador_dominio", ["dominio", "clasificar", "enrutar"], coste=0.05, fiabilidad=0.5),
]

_INDICE: Dict[str, MotorCapability] = {c.nombre: c for c in _CAPACIDADES}


def obtener(nombre: str) -> Optional[MotorCapability]:
    return _INDICE.get(nombre)


def listar() -> List[MotorCapability]:
    return list(_CAPACIDADES)


def buscar_por_capacidad(capacidad: str) -> List[MotorCapability]:
    """Devuelve los motores que declaran una capacidad, ordenados por
    fiabilidad descendente."""
    coincidencias = [c for c in _CAPACIDADES if capacidad in c.capacidades]
    coincidencias.sort(key=lambda c: -c.fiabilidad)
    return coincidencias
