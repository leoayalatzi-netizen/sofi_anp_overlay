#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nevula 1.3 - Cerebro Conversacional.

Capa incremental sobre Nevula 1.2:
- memoria multi-turno por sesión
- resolución de referencias (esto/eso/lo anterior/ese modelo...)
- continuidad temática
- resumen automático de contexto
- extracción conservadora de hechos/preferencias explícitas
- clasificación de intención heredada
- clasificación de dominio neuronal heredada
- integración opcional con cualquier proveedor LLM compatible con OpenAI API
No reemplaza los motores anteriores.
"""
from __future__ import annotations
import json, os, re, time, uuid, threading
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = Path(__file__).resolve().parents[1]
STORE = BASE / "almacenamiento" / "conversaciones"
STORE.mkdir(parents=True, exist_ok=True)

STOP = set("""el la los las un una unos unas de del al y o u que en por para con sin sobre como es son fue era me te se mi tu su tus mis esto eso este esta estos estas ese esa esos esas lo la le les yo tú usted una""".split())
REFS = re.compile(r"\b(esto|eso|este|esta|estos|estas|ese|esa|esos|esas|lo anterior|la anterior|el anterior|la última|lo último|ese modelo|esa versión|ahí|allí|aquello)\b", re.I)
FACT_PATTERNS = [
    (re.compile(r"\b(?:mi nombre es|me llamo)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][\wÁÉÍÓÚÜÑáéíóúüñ-]{1,30})",re.I),"nombre"),
    (re.compile(r"\b(?:prefiero|me gusta|me gustan)\s+(.{2,100})$",re.I),"preferencia"),
    (re.compile(r"\b(?:no me gusta|odio|prefiero no)\s+(.{2,100})$",re.I),"aversión"),
]

@dataclass
class Turn:
    role: str
    text: str
    timestamp: float = field(default_factory=time.time)
    intent: str = "desconocido"
    domain: str = ""
    entities: List[str] = field(default_factory=list)

@dataclass
class Session:
    id: str
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    turns: deque = field(default_factory=lambda: deque(maxlen=80))
    topic: str = ""
    topics: deque = field(default_factory=lambda: deque(maxlen=20))
    facts: Dict[str, Any] = field(default_factory=dict)
    last_entities: List[str] = field(default_factory=list)
    summary: str = ""

class ConversationBrain:
    def __init__(self, max_sessions: int = 500):
        self.sessions: Dict[str, Session] = {}
        self.lock = threading.RLock()
        self.max_sessions = max_sessions
        self._intent = None
        self._domain_models = None
        self._semantica = None
        self._modelo_mundo = None
        try:
            from nucleo.semantica import NucleoSemantico, ModeloMundo
            self._semantica = NucleoSemantico()
            self._modelo_mundo = ModeloMundo(self._semantica)
        except Exception:
            self._semantica = self._modelo_mundo = None
        self._load_neural_components()

    def _load_neural_components(self):
        try:
            from nucleos.comunicacion.motores.intencion import MotorIntencion
            self._intent=MotorIntencion(); self._intent.inicializar()
        except Exception:
            self._intent=None
        try:
            from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima
            from evolucion.vectorizador_hibrido import VectorizadorHibrido
            new=BASE/'almacenamiento'/'modelos'/'evolucionado_v14'
            old=BASE/'almacenamiento'/'modelos'/'evolucionado_v13'
            route_dir=new if (new/'clasificador_grupo.anp').exists() else old
            vocab=route_dir/'clasificador_grupo_vocab.json'; model=route_dir/'clasificador_grupo.anp'
            if not (vocab.exists() and model.exists()): self._domain_models=None; return
            meta=json.loads(vocab.read_text(encoding='utf-8'))
            router=(RedNeuronalOptima.cargar(str(model)),VectorizadorHibrido.cargar(vocab),meta['clases'],{})
            for g in meta['clases']:
                for od in (old,BASE/'almacenamiento'/'modelos'/'evolucionado'):
                    b=od/f'grupo_{g}'; vm=Path(str(b)+'_vocab.json'); mm=b.with_suffix('.anp')
                    if vm.exists() and mm.exists():
                        rr=RedNeuronalOptima.cargar(str(mm)); vv=VectorizadorHibrido.cargar(vm)
                        if rr is not None: router[3][g]=(rr,vv,json.loads(vm.read_text(encoding='utf-8'))['clases']); break
            self._domain_models=router
        except Exception:
            self._domain_models=None

    def new_session(self) -> str:
        with self.lock:
            sid=str(uuid.uuid4())
            self.sessions[sid]=Session(sid)
            self._trim()
            return sid

    def _session_path(self,sid:str)->Path:
        return STORE / f"{sid}.json"

    def _load_session(self,sid:str)->Optional[Session]:
        p=self._session_path(sid)
        if not p.exists(): return None
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            s=Session(d["id"],d.get("created",time.time()),d.get("updated",time.time()))
            s.topic=d.get("topic",""); s.topics=deque(d.get("topics",[]),maxlen=20)
            s.facts=d.get("facts",{}); s.last_entities=d.get("last_entities",[]); s.summary=d.get("summary","")
            for t in d.get("turns",[]):
                s.turns.append(Turn(t.get("role","user"),t.get("text",""),t.get("timestamp",time.time()),t.get("intent","desconocido"),t.get("domain",""),t.get("entities",[])))
            return s
        except Exception: return None

    def _persist(self,s:Session):
        try:
            payload={"id":s.id,"created":s.created,"updated":s.updated,"topic":s.topic,
                     "topics":list(s.topics),"facts":s.facts,"last_entities":s.last_entities,
                     "summary":s.summary,"turns":[asdict(t) for t in s.turns]}
            tmp=self._session_path(s.id).with_suffix(".tmp")
            tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8"); tmp.replace(self._session_path(s.id))
        except Exception: pass

    def get(self, sid: Optional[str]) -> Session:
        with self.lock:
            if not sid:
                sid=self.new_session()
            if sid not in self.sessions:
                self.sessions[sid]=self._load_session(sid) or Session(sid)
                self._trim()
            s=self.sessions[sid]
            s.updated=time.time()
            return s

    def _trim(self):
        if len(self.sessions)>self.max_sessions:
            for sid in sorted(self.sessions, key=lambda x:self.sessions[x].updated)[:len(self.sessions)-self.max_sessions]:
                del self.sessions[sid]

    def _classify(self,text:str)->Tuple[str,float]:
        if not self._intent: return "desconocido",0.0
        try:
            r=self._intent.procesar({"texto":text})
            d=r.datos if hasattr(r,"datos") else r
            intent=d.get("intencion_principal",{}) if isinstance(d,dict) else {}
            cat=intent.get("categoria",d.get("categoria","desconocido")) if isinstance(intent,dict) else intent
            conf=float(intent.get("confianza",d.get("confianza_global",d.get("confianza",0.0))) if isinstance(intent,dict) else d.get("confianza_global",0.0))
            return str(cat),conf
        except Exception:
            return "desconocido",0.0

    def _domain(self,text:str)->Tuple[str,float]:
        # Atajos semánticos de alta precisión para operaciones matemáticas explícitas.
        low=text.lower()
        if re.search(r"(?:\d\s*[+\-*/^]\s*\d)|\b(calcula|calcular|suma|resta|multiplica|multiplicar|divide|dividir|ecuacion|ecuación|integral|derivada)\b", low):
            return "matematicas",0.99
        # Intenciones puramente conversacionales no deben ser forzadas a un dominio técnico.
        intent,_=self._classify(text)
        if intent in {"saludo","despedida","agradecimiento","disculpa"}: return "conversacional",0.98
        if not self._domain_models: return "",0.0
        try:
            rg,vg,groups,special=self._domain_models
            p=rg.predecir(vg.transformar([text]).T).flatten()
            gi=int(p.argmax()); g=groups[gi]; gc=float(p[gi])
            # El modelo semántico puede corregir un router léxico cuando existe
            # evidencia local fuerte para otro grupo.
            if self._semantica:
                hits=self._semantica.buscar(text,top_k=3,min_score=.16)
                aliases={'ciencia':'ciencias_exactas','matematicas':'ciencias_exactas','naturaleza':'ciencias_exactas','programacion':'computacion','tecnologia':'computacion','robotica':'computacion','cultura':'sociedad','humanidad':'sociedad','conocimiento_general':'sociedad','geografia':'sociedad','lenguaje':'cotidiano','vida_cotidiana':'cotidiano','conversacional':'cotidiano','entretenimiento':'ocio','deportes':'ocio'}
                if hits:
                    hinted=aliases.get(hits[0]['fuente'].split('/')[0])
                    if hinted in groups and (hits[0]['score'] >= .30 or gc < .75):
                        g=hinted; gc=max(gc, min(.94, hits[0]['score']))
                    # Si la evidencia local es fuerte, su dominio de origen tiene
                    # prioridad sobre el especialista entrenado con vocabulario menor.
                    if hits[0]['score'] >= .28:
                        parts=hits[0]['fuente'].split('/')
                        source_domain=parts[0]
                        # Subdominios explícitos tienen prioridad (p.ej. tecnologia/programacion).
                        if 'programacion' in parts: source_domain='programacion'
                        elif 'matematicas' in parts: source_domain='matematicas'
                        elif 'fisica' in parts and source_domain=='ciencia': source_domain='ciencia'
                        if source_domain in {'ciencia','conocimiento_general','conversacional','cultura','deportes','entretenimiento','geografia','humanidad','lenguaje','matematicas','naturaleza','programacion','robotica','tecnologia','vida_cotidiana'}:
                            return source_domain, min(1.0, 0.70 + hits[0]['score'])
            if g in special:
                rr,vv,ds=special[g]; q=rr.predecir(vv.transformar([text]).T).flatten()
                di=int(q.argmax()); domain=ds[di]; confidence=gc*float(q[di])
            else:
                domain=g; confidence=gc
            if self._semantica:
                hits=self._semantica.buscar(text,top_k=3,min_score=.08)
                if hits:
                    path=hits[0]['fuente'].split('/')[0]
                    aliases={'ciencia':'ciencias_exactas','matematicas':'ciencias_exactas','naturaleza':'ciencias_exactas','programacion':'computacion','tecnologia':'computacion','robotica':'computacion','cultura':'sociedad','humanidad':'sociedad','conocimiento_general':'sociedad','geografia':'sociedad','lenguaje':'cotidiano','vida_cotidiana':'cotidiano','conversacional':'cotidiano','entretenimiento':'ocio','deportes':'ocio'}
                    hinted=aliases.get(path)
                    if hinted==g: confidence=min(1.0,confidence+0.08*hits[0]['score'])
            return domain,confidence
        except Exception:
            return "",0.0

    def _entities(self,text:str)->List[str]:
        # Entidades conservadoras: comillas, nombres de archivos, URLs y tokens capitalizados.
        found=[]
        found += re.findall(r'["“]([^"”]{2,80})["”]',text)
        found += re.findall(r'\b[\w.-]+\.(?:zip|py|json|md|txt|csv|pdf)\b',text,re.I)
        found += re.findall(r'\b(?:https?://|www\.)\S+',text,re.I)
        for x in re.findall(r'\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{2,}\b',text):
            if x not in found: found.append(x)
        return list(dict.fromkeys(found))[:12]

    def _resolve(self,s:Session,text:str)->str:
        if not REFS.search(text): return text
        recent=[t.text for t in list(s.turns)[-8:] if t.role=="user"]
        anchor = recent[-1] if recent else (s.topic or "")
        if not anchor: return text
        # No sustituimos literalmente todo: añadimos contexto para evitar alterar la frase original.
        return f"[Contexto conversacional relevante: {anchor}] {text}"

    def _extract_facts(self,s:Session,text:str):
        for pat,key in FACT_PATTERNS:
            m=pat.search(text.strip())
            if m:
                val=m.group(1).strip().rstrip(".")
                s.facts[key]=val

    def _update_topic(self,s:Session,text:str,domain:str):
        ents=self._entities(text)
        if ents: s.last_entities=ents
        topic=domain or (ents[0] if ents else "")
        if topic and topic!=s.topic:
            if s.topic: s.topics.append(s.topic)
            s.topic=topic

    def _make_summary(self,s:Session)->str:
        users=[t.text for t in list(s.turns) if t.role=="user"][-8:]
        if not users: return ""
        compact=[]
        for x in users:
            x=re.sub(r"\s+"," ",x).strip()
            compact.append(x[:220])
        topic=s.topic or "sin tema dominante"
        facts=", ".join(f"{k}: {v}" for k,v in s.facts.items())
        return f"Tema actual: {topic}. " + (f"Datos explícitos: {facts}. " if facts else "") + "Conversación reciente: " + " | ".join(compact)

    def context_messages(self,s:Session,limit:int=18)->List[Dict[str,str]]:
        msgs=[]
        for t in list(s.turns)[-limit:]:
            msgs.append({"role":t.role,"content":t.text})
        return msgs

    def process(self,sid:Optional[str],text:str)->Dict[str,Any]:
        text=str(text or "").strip()
        if not text: raise ValueError("texto_vacio")
        s=self.get(sid)
        with self.lock:
            resolved=self._resolve(s,text)
            intent,ic=self._classify(text)
            domain,dc=self._domain(text)
            ents=self._entities(text)
            s.turns.append(Turn("user",text,intent,domain,ents))
            self._extract_facts(s,text)
            # En referencias anafóricas, la continuidad conversacional tiene prioridad
            # sobre una clasificación de dominio aislada.
            if REFS.search(text) and s.topic:
                s.updated=time.time()
                ents=self._entities(text)
                if ents: s.last_entities=ents
            else:
                self._update_topic(s,text,domain)
            s.summary=self._make_summary(s)
            semantic_hits=self._semantica.buscar(resolved,top_k=5,min_score=.05) if self._semantica else []
            semantic_concepts=self._semantica.conceptos(resolved,top_k=8) if self._semantica else []
            world_evidence=self._modelo_mundo.evidencias(resolved,top_k=3) if self._modelo_mundo else []
            self._persist(s)
            return {
                "session_id":s.id,"texto":text,"texto_con_contexto":resolved,
                "intencion":intent,"confianza_intencion":round(ic,4),
                "dominio":domain,"confianza_dominio":round(dc,4),
                "tema_actual":s.topic,"temas_anteriores":list(s.topics)[-8:],
                "entidades":s.last_entities,"hechos_explicitos":dict(s.facts),
                "conceptos_semanticos":semantic_concepts,
                "evidencia_semantica":[{"score":h["score"],"fuente":h["fuente"],"datos":h["datos"]} for h in semantic_hits],
                "evidencia_modelo_mundo":world_evidence,
                "resumen":s.summary,"turnos":len(s.turns)
            }

    def add_assistant(self,sid:str,text:str):
        s=self.get(sid)
        with self.lock:
            s.turns.append(Turn("assistant",text))
            s.updated=time.time()
            s.summary=self._make_summary(s)
            self._persist(s)

    def history(self,sid:str)->Dict[str,Any]:
        s=self.get(sid)
        return {"session_id":s.id,"summary":s.summary,"topic":s.topic,"facts":s.facts,
                "turns":[asdict(t) for t in list(s.turns)],"topics":list(s.topics)}

    def llm(self,sid:str,text:str)->Optional[str]:
        base=os.getenv("NEVULA_LLM_URL","").strip()
        if not base: return None
        key=os.getenv("NEVULA_LLM_API_KEY","").strip()
        model=os.getenv("NEVULA_LLM_MODEL","gpt-4o-mini")
        s=self.get(sid)
        system=("Eres el componente generativo de Nevula. Mantén continuidad natural. "
                "Usa el resumen y los turnos previos. No inventes recuerdos. "
                f"Resumen: {s.summary or 'ninguno'}.")
        payload={"model":model,"messages":[{"role":"system","content":system}]+self.context_messages(s,18)+[{"role":"user","content":text}]}
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers={"Content-Type":"application/json"}
        if key: headers["Authorization"]="Bearer "+key
        try:
            req=Request(base.rstrip("/")+"/chat/completions",data=data,headers=headers,method="POST")
            with urlopen(req,timeout=45) as r:
                obj=json.loads(r.read().decode("utf-8"))
            return obj["choices"][0]["message"]["content"]
        except Exception:
            return None
