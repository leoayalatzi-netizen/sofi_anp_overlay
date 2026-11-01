"""Bucle de aprendizaje de Sofi: guarda interacciones, recibe 👍/👎 y exporta un dataset SFT listo para entrenar el LLM."""
import json, threading, time, uuid
from pathlib import Path
class Aprendizaje:
    def __init__(self, d):
        self.f=Path(d)/"interacciones.jsonl"; self.lock=threading.Lock(); self.r={}
        try:
            for l in self.f.read_text(encoding="utf8").splitlines():
                e=json.loads(l)
                if e["op"]=="n": self.r[e["id"]]=e
                elif e["op"]=="fb" and e["id"] in self.r: self.r[e["id"]]["v"]=e["v"]
        except Exception: pass
    def _w(self,e):
        try:
            with self.lock, open(self.f,"a",encoding="utf8") as fh: fh.write(json.dumps(e,ensure_ascii=False)+"\n")
        except Exception: pass
    def registrar(self,q,a,via):
        i=uuid.uuid4().hex[:10]; e={"op":"n","id":i,"t":int(time.time()),"q":q,"a":a,"via":via,"v":0}; self.r[i]=e; self._w(e); return i
    def feedback(self,i,v):
        if i not in self.r: return None
        self.r[i]["v"]=v; self._w({"op":"fb","id":i,"v":v}); return self.r[i]
    def stats(self):
        v=[x["v"] for x in self.r.values()]; return {"total":len(v),"buenas":v.count(1),"malas":v.count(-1),"minimo_entrenar":100}
    def dataset(self,system):
        out=[json.dumps({"messages":[{"role":"system","content":system},{"role":"user","content":x["q"]},{"role":"assistant","content":x["a"]}]},ensure_ascii=False) for x in self.r.values() if x["v"]==1 and len(x["a"])>20]
        return "\n".join(out)+("\n" if out else "")
