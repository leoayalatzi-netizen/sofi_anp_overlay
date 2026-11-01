#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vectorizador híbrido v2: TF-IDF + n-gramas + selección discriminativa.
Compatible con los modelos anteriores, pero permite entrenar vocabularios
orientados a clase para reducir colisiones entre dominios cercanos.
"""
import json, math, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

STOPWORDS_ES=set("de la que el en y a los del se las por un para con no una su al lo como mas pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos e esto mi mis tu tus te ti tuyo ellas nosotras vosotros vosotras os mio mia mios mias tuya tuyos tuyas suyo suya suyos suyas nuestro nuestra nuestros nuestras vuestro vuestra vuestros vuestras esos esas es soy eres somos sois son fue fui fuiste fuimos fueron ser".split())

def normalizar(texto):
    x=unicodedata.normalize('NFKD',str(texto).lower())
    return ''.join(c for c in x if not unicodedata.combining(c))

def tokenizar(texto):
    ws=[w for w in re.findall(r"[a-z0-9]{2,}",normalizar(texto)) if w not in STOPWORDS_ES]
    out=list(ws)
    out += [f"{ws[i]}_{ws[i+1]}" for i in range(len(ws)-1)]
    out += [f"{ws[i]}_{ws[i+1]}_{ws[i+2]}" for i in range(len(ws)-2)]
    return out

def char_tokens(texto,n_min=3,n_max=5):
    s=re.sub(r'\s+',' ',normalizar(texto)).strip(); padded=f' {s} '
    return [f'c{n}:{padded[i:i+n]}' for n in range(n_min,n_max+1) for i in range(max(0,len(padded)-n+1))]

class VectorizadorHibrido:
    VERSION='2.0'
    def __init__(self,max_vocab=6000,min_df=2,char_weight=.42,word_weight=1.0,discriminative=True):
        self.max_vocab=int(max_vocab); self.min_df=int(min_df); self.char_weight=float(char_weight); self.word_weight=float(word_weight); self.discriminative=bool(discriminative)
        self.vocabulario={}; self.idf=None; self.tipos={}; self.feature_scores={}
    def ajustar(self,textos,etiquetas=None):
        textos=list(textos); df=Counter(); class_df=defaultdict(Counter); classes=set(etiquetas or [])
        for i,t in enumerate(textos):
            toks=set(tokenizar(t)+char_tokens(t)); df.update(toks)
            if etiquetas is not None:
                class_df[etiquetas[i]].update(toks)
        cand=[(w,n) for w,n in df.items() if n>=self.min_df]
        scores={}
        if etiquetas is not None and classes:
            # Entropía de clase: features concentradas en pocas clases son más útiles.
            total=len(textos)
            for w,n in cand:
                probs=[]
                for c in classes:
                    pc=class_df[c][w]/max(1,sum(1 for e in etiquetas if e==c))
                    if pc>0: probs.append(pc)
                concentration=max(probs) if probs else 0.0
                scores[w]=(math.log1p(n)*0.25)+concentration
        else:
            scores={w:math.log1p(n) for w,n in cand}
        words=[x for x in cand if not x[0].startswith('c')]; chars=[x for x in cand if x[0].startswith('c')]
        words.sort(key=lambda x:(-scores.get(x[0],0),-x[1],x[0])); chars.sort(key=lambda x:(-scores.get(x[0],0),-x[1],x[0]))
        nw=min(len(words),int(self.max_vocab*.62)); nc=min(len(chars),self.max_vocab-nw); selected=words[:nw]+chars[:nc]
        self.vocabulario={w:i for i,(w,_) in enumerate(selected)}; self.tipos={w:('char' if w.startswith('c') else 'word') for w in self.vocabulario}; self.feature_scores={w:scores.get(w,0.0) for w in self.vocabulario}
        n=len(textos); self.idf=np.zeros(len(self.vocabulario),dtype=np.float64)
        for w,i in self.vocabulario.items(): self.idf[i]=math.log((1+n)/(1+df[w]))+1.0
        return self
    def transformar(self,textos):
        X=np.zeros((len(textos),len(self.vocabulario)),dtype=np.float64)
        for row,t in enumerate(textos):
            all_toks=tokenizar(t)+char_tokens(t); counts=Counter(all_toks); total=max(1,len(all_toks))
            for w,c in counts.items():
                idx=self.vocabulario.get(w)
                if idx is None: continue
                peso=self.char_weight if self.tipos.get(w)=='char' else self.word_weight
                X[row,idx]=(c/total)*self.idf[idx]*peso
            norm=np.linalg.norm(X[row]);
            if norm>0: X[row]/=norm
        return X
    def guardar(self,ruta):
        Path(ruta).write_text(json.dumps({'version':self.VERSION,'vocabulario':self.vocabulario,'idf':self.idf.tolist(),'max_vocab':self.max_vocab,'min_df':self.min_df,'char_weight':self.char_weight,'word_weight':self.word_weight,'tipos':self.tipos,'feature_scores':self.feature_scores},ensure_ascii=False),encoding='utf-8')
    @classmethod
    def cargar(cls,ruta):
        d=json.loads(Path(ruta).read_text(encoding='utf-8')); v=cls(d.get('max_vocab',3500),d.get('min_df',2),d.get('char_weight',.55),d.get('word_weight',1.0),d.get('discriminative',True)); v.vocabulario=d['vocabulario']; v.idf=np.array(d['idf'],dtype=np.float64); v.tipos=d.get('tipos',{}); v.feature_scores=d.get('feature_scores',{}); return v
