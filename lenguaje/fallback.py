from __future__ import annotations
import json,re,random
from pathlib import Path
from collections import defaultdict,Counter

class FallbackLanguageCore:
    """Generador lingüístico mínimo sin PyTorch/SentencePiece. No pretende sustituir
    el Transformer; garantiza que Nevula conserve una capa lingüística offline."""
    VERSION='2.2-fallback'
    def __init__(self, corpus_path):
        self.path=Path(corpus_path); self.next=defaultdict(Counter); self.ready=False; self.vocab=0
        try:
            text=self.path.read_text(encoding='utf8',errors='ignore')
            # Sólo aprende continuaciones de frases; no ejecuta ni interpreta el corpus.
            for line in text.splitlines():
                words=re.findall(r'[\wáéíóúüñÁÉÍÓÚÜÑ]+|[.,!?;:]',line)
                if len(words)<3: continue
                for a,b,c in zip(words,words[1:],words[2:]): self.next[(a.lower(),b.lower())][c.lower()]+=1
            self.vocab=len({x for k in self.next for x in k}); self.ready=bool(self.next)
        except Exception: pass
    def diagnostico(self): return {'activo':self.ready,'version':self.VERSION,'parametros':0,'vocabulario':self.vocab,'modo':'sin_torch'}
    def responder(self,consulta,contexto='',max_new_tokens=80):
        if not self.ready: return None
        words=re.findall(r'[\wáéíóúüñÁÉÍÓÚÜÑ]+', (consulta+' '+contexto))
        if len(words)>=2: pair=(words[-2].lower(),words[-1].lower())
        else: pair=('<|assistant|>','<|assistant|>')
        # Buscar un par aprendido cercano si el par exacto no existe.
        if pair not in self.next:
            candidates=[k for k in self.next if any(w in k for w in pair if w)]
            pair=random.choice(candidates) if candidates else random.choice(list(self.next))
        out=[]
        for _ in range(max_new_tokens):
            choices=self.next.get(pair)
            if not choices: break
            toks=list(choices); weights=list(choices.values()); nxt=random.choices(toks,weights=weights,k=1)[0]
            if nxt in ('<|user|>','<|context|>','<|assistant|>'): break
            out.append(nxt)
            if nxt in '.!?': break
            pair=(pair[1],nxt)
        text=' '.join(out); text=re.sub(r'\s+([.,!?;:])',r'\1',text).strip()
        return text if len(text)>=8 else None
