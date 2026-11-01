#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Núcleo semántico local y determinista para Nevula 1.4.

Construye un índice conceptual sobre los JSON de conocimiento y combina:
- normalización lingüística
- coincidencia léxica
- TF-IDF/coseno
- entidades y conceptos explícitos
- relaciones del modelo del mundo

No pretende ser un LLM: es una capa de representación/recuperación que evita
que el orquestador dependa de palabras aisladas o plantillas aleatorias.
"""
from __future__ import annotations
import json, math, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE = Path(__file__).resolve().parents[2]
STOP = set("de la que el en y a los del se las por un para con no una su al lo como mas pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos esto mi mis tu tus te ti son fue fui ser es".split())

def normalizar(s: Any) -> str:
    x = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in x if not unicodedata.combining(c))

def tokens(s: Any) -> List[str]:
    ws = [w for w in re.findall(r"[a-z0-9áéíóúüñ]{2,}", normalizar(s)) if w not in STOP]
    out = list(dict.fromkeys(ws))
    out += [f"{ws[i]}_{ws[i+1]}" for i in range(len(ws)-1)]
    out += [f"{ws[i]}_{ws[i+1]}_{ws[i+2]}" for i in range(len(ws)-2)]
    return list(dict.fromkeys(out))

class NucleoSemantico:
    def __init__(self, datos_dir: Optional[Path] = None):
        self.datos_dir = Path(datos_dir or BASE / "datos")
        self.documentos: List[Dict[str, Any]] = []
        self.df = Counter(); self.idf: Dict[str,float] = {}; self.vocab = set()
        self._matrices: List[Dict[str,float]] = []
        self._cargado = False
        self._cargar()

    def _texto_item(self, item: Dict[str, Any]) -> str:
        parts=[]
        for k,v in item.items():
            if k in {"metadata"}: continue
            if isinstance(v, (str,int,float,bool)): parts.append(f"{k} {v}")
            elif isinstance(v,list): parts.extend(str(z) for z in v)
            elif isinstance(v,dict): parts.append(json.dumps(v, ensure_ascii=False))
        return " ".join(parts)

    def _cargar(self):
        if not self.datos_dir.exists(): return
        for path in sorted(self.datos_dir.rglob("*.json")):
            try:
                data=json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for item in data.get("datos",[]) if isinstance(data,dict) else []:
                if not isinstance(item,dict): continue
                texto=self._texto_item(item)
                if not texto: continue
                tok=tokens(texto); tf=Counter(tok)
                self.documentos.append({"fuente":str(path.relative_to(self.datos_dir)),"item":item,"texto":texto,"tokens":tok})
                self.df.update(set(tok))
        n=max(1,len(self.documentos))
        self.idf={t:math.log((1+n)/(1+df))+1.0 for t,df in self.df.items()}
        self.vocab=set(self.idf)
        self._matrices=[self._vector(d["tokens"]) for d in self.documentos]
        self._cargado=True

    def _vector(self, toks: List[str]) -> Dict[str,float]:
        c=Counter(toks); total=max(1,len(toks)); v={}
        for t,n in c.items():
            if t in self.idf: v[t]=(n/total)*self.idf[t]
        norm=math.sqrt(sum(x*x for x in v.values())) or 1.0
        return {k:x/norm for k,x in v.items()}

    def buscar(self, consulta: str, top_k: int=5, min_score: float=0.05) -> List[Dict[str,Any]]:
        q=tokens(consulta); qv=self._vector(q); qc=set(q)
        if not qv: return []
        qraw=normalizar(consulta)
        scored=[]
        for i,d in enumerate(self.documentos):
            dv=self._matrices[i]; dt=set(d["tokens"])
            cos=sum(qv.get(t,0.0)*dv.get(t,0.0) for t in qv)
            overlap=len(qc & dt) / max(1,len(qc))
            concept=normalizar(str(d["item"].get("concepto", "")))
            name=normalizar(str(d["item"].get("nombre", "")))
            exact=0.0
            for qt in qc:
                if qt in concept.split('_') or qt == concept:
                    exact=max(exact,1.0)
                elif qt == name or qt in name.split():
                    exact=max(exact,0.85)
            score=0.62*cos+0.13*overlap+0.25*exact
            if score>=min_score: scored.append((score,i))
        scored.sort(reverse=True)
        out=[]
        for score,i in scored[:top_k]:
            d=self.documentos[i]
            out.append({"score":round(float(score),6),"fuente":d["fuente"],"datos":d["item"],"texto":d["texto"]})
        return out

    def conceptos(self, consulta: str, top_k: int=8) -> List[str]:
        res=self.buscar(consulta, top_k=top_k, min_score=0.08); out=[]
        for r in res:
            item=r["datos"]
            for k in ("concepto","nombre","titulo"):
                if item.get(k): out.append(str(item[k]))
        return list(dict.fromkeys(out))[:top_k]

    def diagnostico(self) -> Dict[str,Any]:
        return {"documentos":len(self.documentos),"terminos":len(self.vocab),"cargado":self._cargado}
