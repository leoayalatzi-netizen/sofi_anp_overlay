#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nevula 1.4: salto neuronal y semántico.
Entrena MLP ampliado con sklearn (núcleo optimizado) y exporta a formato ANP
para que el runtime de Nevula siga usando su RedNeuronalOptima.
"""
import json, random, time, sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from sklearn.neural_network import MLPClassifier
from entrenamiento.entrenar_clasificador import cargar_dataset, balancear_clases, a_onehot
from evolucion.entrenamiento_masivo import GRUPOS, DOM_A_GRUPO, stratified_split
from evolucion.vectorizador_hibrido import VectorizadorHibrido
from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima, FuncionActivacion, Regularizador, ModoNormalizacion, Inicializador
from aprendizaje.evaluador_modelos import construir_holdout_fijo
OUT=BASE/'almacenamiento'/'modelos'/'evolucionado_v14'; OUT.mkdir(parents=True,exist_ok=True)
AUD=BASE/'almacenamiento'/'auditoria'; AUD.mkdir(parents=True,exist_ok=True)
WRAPPERS=['¿Qué es {x}?','Explícame {x}.','¿Cómo funciona {x}?','¿Por qué ocurre {x}?','Quiero aprender sobre {x}.','Dame una explicación de {x}.','¿A qué área pertenece {x}?','¿Qué sabes sobre {x}?','Necesito información sobre {x}.','Háblame de {x}.']

def naturalize(examples,seed=20260910):
    rng=random.Random(seed); out=list(examples)
    for text,label in examples:
        clean=' '.join(str(text).split()); core=' '.join(clean.split()[:18])
        for w in rng.sample(WRAPPERS,3): out.append((w.format(x=core),label))
    seen=set(); result=[]
    for t,l in out:
        k=(t.lower(),l)
        if k not in seen: seen.add(k); result.append((t,l))
    rng.shuffle(result); return result

def export_sklearn(clf,vec,base,classes,meta):
    # clf.coefs_ are [out,in], exactly the orientation used by ANP.
    r=RedNeuronalOptima('nevula14_'+base.stem)
    dims=[clf.coefs_[0].shape[1]]+[w.shape[0] for w in clf.coefs_]
    for i,(a,b) in enumerate(zip(dims[:-1],dims[1:])):
        out=i==len(dims)-2
        r.agregar(a,b,activacion=FuncionActivacion.SOFTMAX if out else FuncionActivacion.RELU,
                  dropout_rate=0.0,regularizador=Regularizador.NINGUNO,
                  normalizacion=ModoNormalizacion.NINGUNO,inicializador=Inicializador.HE_NORMAL)
        r.capas[-1].pesos=np.asarray(clf.coefs_[i].T,dtype=np.float64)
        r.capas[-1].sesgos=np.asarray(clf.intercepts_[i],dtype=np.float64).reshape(-1,1)
    r._entrenada=True; r.epocas_entrenadas=int(getattr(clf,'n_iter_',0)); r.compilar(optimizador='adamw',perdida='categorical_crossentropy',lr=0.001)
    r.guardar(str(base.with_suffix('.anp'))); vec.guardar(Path(str(base)+'_vocab.json'))
    p=Path(str(base)+'_vocab.json'); d=json.loads(p.read_text()); d.update({'clases':list(classes),**meta,'trainer':'sklearn.MLPClassifier','neural_engine_export':'2.0'}); p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
    return r

def fit(texts,labels,seed):
    clf=MLPClassifier(hidden_layer_sizes=(1024,512,256),activation='relu',solver='adam',alpha=1.5e-4,batch_size=96,learning_rate_init=0.0012,max_iter=12,early_stopping=True,validation_fraction=.12,n_iter_no_change=15,tol=1e-4,shuffle=True,random_state=seed,verbose=False)
    clf.fit(texts,labels); return clf

def acc(clf,X,y): return float(clf.score(X,y)) if len(y) else 0.0

def main():
    t0=time.time(); random.seed(20260910); np.random.seed(20260910)
    raw,domains=cargar_dataset(); train,val=stratified_split(raw,.15,424242); train=naturalize(balancear_clases(train,1.35))
    labels=list(GRUPOS); tg=[(t,DOM_A_GRUPO[d]) for t,d in train]; tv=[(t,DOM_A_GRUPO[d]) for t,d in val]
    vec=VectorizadorHibrido(800,2,.38,1.0,True).ajustar([t for t,_ in tg],[l for _,l in tg])
    X=vec.transformar([t for t,_ in tg]); Y=[l for _,l in tg]; XV=vec.transformar([t for t,_ in tv]); YV=[l for _,l in tv]
    label_to_i={x:i for i,x in enumerate(labels)}; YI=[label_to_i[x] for x in Y]; YVI=[label_to_i[x] for x in YV]
    clf=fit(X,YI,20260910); base=OUT/'clasificador_grupo'; export_sklearn(clf,vec,base,labels,{'version':'1.4','precision_val':acc(clf,XV,YVI),'arquitectura':[X.shape[1],1024,512,256,len(labels)],'parametros':sum(a*b+b for a,b in zip([X.shape[1],256,128,64],[256,128,64,len(labels)]))})
    report={'version':'1.4','base':len(raw),'train':len(train),'val':len(val),'features':X.shape[1],'precision_grupo_val':acc(clf,XV,YVI),'arquitectura':[X.shape[1],1024,512,256,len(labels)],'grupos':{}}
    # Los clasificadores especializados 1.3 se conservan; el salto 1.4 mejora el router global.
    # Holdout independiente: evaluación del router global (15 dominios -> grupo).
    hold=construir_holdout_fijo(.20,12345); correct=0; per={d:[0,0] for _,d in hold}
    for text,real in hold:
        pred_group=labels[int(clf.predict(vec.transformar([text]))[0])]
        real_group=DOM_A_GRUPO[real]; ok=pred_group==real_group; correct+=ok; per[real][0]+=1; per[real][1]+=ok
    report['precision_holdout']=correct/max(1,len(hold)); report['n_holdout']=len(hold); report['por_dominio_holdout']={d:{'n':n,'aciertos':a,'precision':a/max(1,n)} for d,(n,a) in per.items()}; report['tiempo_segundos']=round(time.time()-t0,2)
    (BASE/'entrenamiento'/'dataset_masivo_v14.json').write_text(json.dumps({'version':'1.4','train':train,'val':val,'wrappers':WRAPPERS},ensure_ascii=False),encoding='utf-8')
    (AUD/'entrenamiento_v14_resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
