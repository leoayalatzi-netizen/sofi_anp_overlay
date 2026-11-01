from __future__ import annotations
from pathlib import Path
import re, math
from collections import Counter
class RecuperadorLocal:
    VERSION='2.4-OMEGA-rag'
    def __init__(self, corpus_path, max_docs=5000):
        self.path=Path(corpus_path); self.docs=[]; self.df=Counter(); self.N=0
        if not self.path.exists(): return
        try:
            for line in self.path.read_text(encoding='utf8').splitlines():
                t=re.sub(r'\s+',' ',line).strip()
                if len(t)<35: continue
                # cada ejemplo se mantiene como unidad, pero eliminamos etiquetas para scoring
                clean=re.sub(r'<\|(?:user|assistant|context)\|>',' ',t)
                toks=self._tokens(clean)
                if len(toks)<5: continue
                self.docs.append((t,toks)); self.df.update(set(toks))
                if len(self.docs)>=max_docs: break
            self.N=len(self.docs)
        except Exception: self.docs=[]
    def _tokens(self,s): return re.findall(r'[a-záéíóúüñ0-9]{3,}',s.lower())
    def buscar(self,query,k=6):
        q=self._tokens(query); qc=Counter(q)
        if not q or not self.docs:return []
        scored=[]
        for text,toks in self.docs:
            c=Counter(toks); score=0.0
            for w,fq in qc.items():
                if c[w]: score += (1+math.log(c[w]))*(math.log((self.N+1)/(self.df[w]+1))+1)*min(2,fq)
            norm=math.sqrt(max(5,len(toks))); score/=norm
            # bonus por coincidencia de bigramas
            if len(q)>1:
                pairs=set(zip(q,q[1:])); dp=set(zip(toks,toks[1:])); score += .35*len(pairs&dp)
            if score>0: scored.append((score,text))
        scored.sort(reverse=True)
        return [{'score':round(s,6),'text':t} for s,t in scored[:k]]
    def contexto(self,query,k=6,max_chars=4500):
        rows=self.buscar(query,k); out=[]; n=0
        for r in rows:
            if n+len(r['text'])>max_chars: break
            out.append(r['text']); n+=len(r['text'])
        return '\n'.join(out)
