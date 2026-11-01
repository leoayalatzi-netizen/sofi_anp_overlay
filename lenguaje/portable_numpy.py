from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
from .tokenizador_portable import TokenizadorPortable

class NumpyLanguageCore:
    VERSION='2.2-numpy'
    def __init__(self, model_dir):
        self.dir=Path(model_dir); self.ready=False; self.meta={}; self.model=None
        self.tok=None
        mf=self.dir/'language_core_numpy.npz'; tf=self.dir/'tokenizer_portable.json'; jf=self.dir/'language_core_portable.json'
        if not (mf.exists() and tf.exists() and jf.exists()): return
        try:
            self.meta=json.loads(jf.read_text(encoding='utf-8')); self.tok=TokenizadorPortable(tf); self.model=np.load(mf,allow_pickle=False); self.ready=True
        except Exception: self.ready=False
    def diagnostico(self):
        return {'activo':self.ready,'version':self.VERSION,'backend':'numpy-portable','vocabulario':self.tok.vocab_size if self.tok else 0,'parametros':self.meta.get('parametros',0),'contexto':self.meta.get('block_size',0)}
    def _norm(self,x,w): return x/(np.sqrt(np.mean(x*x,axis=-1,keepdims=True)+1e-6))*w
    def _linear(self,x,w): return x@w.T
    def _forward(self,ids):
        x=self.model['tok'][ids]+self.model['pos'][np.arange(len(ids))]
        L=self.meta['n_layers']; h=self.meta['n_heads']; d=self.meta['d_model']; dh=d//h
        for i in range(L):
            n=self._norm(x,self.model[f'b{i}.n1']); qkv=self._linear(n,self.model[f'b{i}.qkv']); q,k,v=np.split(qkv,3,axis=-1)
            q=q.reshape(-1,h,dh).transpose(1,0,2); k=k.reshape(-1,h,dh).transpose(1,0,2); v=v.reshape(-1,h,dh).transpose(1,0,2)
            scores=(q@k.transpose(0,2,1))/math.sqrt(dh); mask=np.triu(np.ones(scores.shape[-2:],dtype=bool),1); scores=np.where(mask,-1e9,scores)
            scores=np.exp(scores-scores.max(axis=-1,keepdims=True)); scores/=scores.sum(axis=-1,keepdims=True)
            a=(scores@v).transpose(1,0,2).reshape(-1,d); x=x+self._linear(a,self.model[f'b{i}.proj'])
            n=self._norm(x,self.model[f'b{i}.n2']); a=self._linear(n,self.model[f'b{i}.w1']); b=self._linear(n,self.model[f'b{i}.w2']); ff=(a/(1+np.exp(-np.clip(a,-40,40))))*b
            x=x+self._linear(ff,self.model[f'b{i}.out'])
        x=self._norm(x,self.model['norm']); return self._linear(x,self.model['lm_head'])
    def generate(self,prompt,max_new_tokens=80,temperature=.72,top_p=.92,repetition_penalty=1.08):
        if not self.ready:return None
        ids=self.tok.encode(prompt)[-self.meta['block_size']:]
        for _ in range(max_new_tokens):
            logits=self._forward(ids)[-1].astype(np.float64)/max(.05,temperature)
            for t in set(ids[-120:]): logits[t]/=repetition_penalty
            order=np.argsort(logits)[::-1]; p=np.exp(logits[order]-np.max(logits[order])); p/=p.sum(); c=np.cumsum(p); keep=c<=top_p; keep[0]=True; order=order[keep]; p=p[keep]; p/=p.sum(); nxt=int(np.random.choice(order,p=p)); ids.append(nxt)
            if nxt==self.tok.eos_id: break
            if len(ids)>self.meta['block_size']: ids=ids[-self.meta['block_size']:]
        return self.tok.decode(ids)
    def responder(self,consulta,contexto=' ',max_new_tokens=80):
        if not self.ready:return None
        prompt=f'<|user|> {contexto}\n{consulta}\n<|assistant|>'
        r=self.generate(prompt,max_new_tokens=max_new_tokens)
        if not r:return None
        r=r.split('<|assistant|>',1)[-1].split('<|user|>',1)[0].strip()
        return r if len(r)>=8 else None
