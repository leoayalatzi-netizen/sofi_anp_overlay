from __future__ import annotations
import re, math, unicodedata
from collections import Counter
class GuardasLenguaje:
    VERSION='2.4-OMEGA-quality'
    def __init__(self,lexicon=None): self.lexicon=set(lexicon or ())
    def _words(self,t): return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}",t.lower())
    def evaluar(self,texto,consulta='',evidencia=''):
        if not texto:return 0.0
        t=re.sub(r'\s+',' ',texto).strip(); w=self._words(t)
        if len(t)<12 or len(t)>5000 or len(w)<4:return 0.0
        if any(x in t for x in ('<|user|>','<|assistant|>','<|context|>','▁','�')):return 0.0
        alpha=sum(c.isalpha() for c in t); printable=sum(c.isprintable() for c in t); alpha_ratio=alpha/max(1,len(t))
        known=sum(x in self.lexicon for x in w)/max(1,len(w)) if self.lexicon else .7
        unique=len(set(w))/max(1,len(w)); bigr=list(zip(w,w[1:])); big_unique=len(set(bigr))/max(1,len(bigr))
        repeated=max((n for n in Counter(w).values()),default=1); repetition=1-min(1,(repeated-2)/8)
        q=set(self._words(consulta)); e=set(self._words(evidencia)); overlap=len(set(w)&(q|e))/max(1,len(set(w)))
        punct=sum(c in '.!?;:' for c in t); sentence_bonus=min(1,punct/3)
        gibberish_penalty=0 if unique>=.35 and big_unique>=.45 and alpha_ratio>=.45 else .45
        score=.20*min(1,unique/.65)+.20*min(1,big_unique/.75)+.15*repetition+.15*min(1,alpha_ratio/.75)+.10*sentence_bonus+.10*overlap+.10*(printable/len(t))+.10*known-gibberish_penalty
        return max(0,min(1,score))
    def aceptar(self,texto,consulta,evidencia='',umbral=.58): return self.evaluar(texto,consulta,evidencia)>=umbral
