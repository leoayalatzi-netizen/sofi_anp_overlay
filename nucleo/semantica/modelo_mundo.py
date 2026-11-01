#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modelo de mundo relacional derivado de la biblioteca de Nevula.

No afirma que las relaciones sean verdades universales: las etiqueta como
"extraidas" y conserva la fuente para permitir verificación posterior.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List, Tuple

class ModeloMundo:
    REL_KEYS = ("relacionado_con","relaciones","tipo","categoria","causa","causas","efecto","efectos","depende_de","depende","parte_de","es_un")
    def __init__(self, semantica):
        self.semantica=semantica
        self.grafo=defaultdict(list)
        self._construir()

    def _add(self,a,r,b,fuente):
        a=str(a).strip(); b=str(b).strip()
        if not a or not b or a==b: return
        self.grafo[a].append({"relacion":r,"objetivo":b,"fuente":fuente,"estado":"extraida"})

    def _construir(self):
        for d in self.semantica.documentos:
            item=d["item"]; base=item.get("concepto") or item.get("nombre")
            if not base: continue
            for k in self.REL_KEYS:
                if k not in item: continue
                v=item[k]
                vals=v if isinstance(v,list) else [v]
                for x in vals:
                    if isinstance(x,dict):
                        for kk,vv in x.items(): self._add(base,kk,vv,d["fuente"])
                    else: self._add(base,k,x,d["fuente"])

    def vecinos(self, concepto: str, limite: int=12)->List[Dict[str,Any]]:
        c=str(concepto).strip(); exact=self.grafo.get(c,[])
        if exact: return exact[:limite]
        cn=c.lower()
        for k,v in self.grafo.items():
            if k.lower()==cn or cn in k.lower() or k.lower() in cn: return v[:limite]
        return []

    def ruta(self, origen: str, destino: str, profundidad: int=3):
        objetivo=destino.lower(); q=[(origen,[])]; seen={origen}
        while q:
            actual,path=q.pop(0)
            if actual.lower()==objetivo: return path
            if len(path)>=profundidad: continue
            for e in self.vecinos(actual):
                nxt=e["objetivo"]
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt,path+[e]))
        return []

    def evidencias(self, consulta: str, top_k=5):
        resultados=self.semantica.buscar(consulta,top_k=top_k)
        out=[]
        for r in resultados:
            item=r["datos"]; concepto=item.get("concepto") or item.get("nombre")
            out.append({"score":r["score"],"concepto":concepto,"fuente":r["fuente"],"datos":item,"relaciones":self.vecinos(concepto or "")})
        return out

    def diagnostico(self):
        return {"nodos":len(self.grafo),"aristas":sum(len(v) for v in self.grafo.values())}
