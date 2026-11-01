#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado cognitivo explícito: hipótesis, evidencia, incertidumbre y decisiones."""
from dataclasses import dataclass, field
from typing import Any, Dict, List
import time, uuid

@dataclass
class EstadoCognitivo:
    objetivo: str = ""
    id: str = field(default_factory=lambda:str(uuid.uuid4()))
    contexto: Dict[str,Any] = field(default_factory=dict)
    hipotesis: List[Dict[str,Any]] = field(default_factory=list)
    evidencia: List[Dict[str,Any]] = field(default_factory=list)
    contradicciones: List[Dict[str,Any]] = field(default_factory=list)
    decisiones: List[Dict[str,Any]] = field(default_factory=list)
    incertidumbre: float = 1.0
    creado: float = field(default_factory=time.time)

    def agregar_hipotesis(self,texto,prior=0.5,origen="sistema"):
        h={"texto":str(texto),"prior":float(prior),"peso":float(prior),"origen":origen}
        self.hipotesis.append(h); return h
    def agregar_evidencia(self, dato, fuerza=0.5, fuente="local"):
        e={"dato":dato,"fuerza":max(0.0,min(1.0,float(fuerza))),"fuente":fuente}
        self.evidencia.append(e); self._recalcular(); return e
    def contradiccion(self,a,b,fuente="verificador"):
        self.contradicciones.append({"a":a,"b":b,"fuente":fuente}); self.incertidumbre=min(1.0,self.incertidumbre+0.12)
    def decidir(self,accion,razon,peso=0.5):
        self.decisiones.append({"accion":accion,"razon":razon,"peso":float(peso)})
    def _recalcular(self):
        if not self.evidencia: self.incertidumbre=1.0; return
        fuerza=sum(e["fuerza"] for e in self.evidencia)/len(self.evidencia)
        contrad=min(0.35,0.08*len(self.contradicciones))
        self.incertidumbre=max(0.0,min(1.0,1.0-fuerza+contrad))
    def resumen(self):
        return {"id":self.id,"objetivo":self.objetivo,"hipotesis":self.hipotesis[-8:],"evidencia":self.evidencia[-12:],"contradicciones":self.contradicciones[-8:],"decisiones":self.decisiones[-8:],"incertidumbre":round(self.incertidumbre,4)}
