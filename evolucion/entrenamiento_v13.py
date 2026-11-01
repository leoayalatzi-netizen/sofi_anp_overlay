#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entrenamiento Nevula 1.3: segunda gran pasada, preservando 1.2.
Crea modelos en almacenamiento/modelos/evolucionado_v13.
"""
import json, random, time, sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from entrenamiento.entrenar_clasificador import cargar_dataset, balancear_clases, a_onehot
from evolucion.entrenamiento_masivo import augmentation, stratified_split, train_net, save_model, GRUPOS
from evolucion.vectorizador_hibrido import VectorizadorHibrido

OUT=BASE/'almacenamiento'/'modelos'/'evolucionado_v13'; OUT.mkdir(parents=True,exist_ok=True)
DOM_A_GRUPO={d:g for g,ds in GRUPOS.items() for d in ds}
def main():
    random.seed(20260908); np.random.seed(20260908)
    raw,domains=cargar_dataset(); train,val=stratified_split(raw,.15,20260909)
    bal=balancear_clases(train,1.55)
    aug=augmentation(bal,5,20260909)
    (BASE/'entrenamiento'/'dataset_masivo_v13.json').write_text(json.dumps({
        'version':'1.3','base':len(raw),'train':len(train),'val':len(val),
        'balanced':len(bal),'augmented':len(aug),'domains':domains
    },ensure_ascii=False,indent=2),encoding='utf-8')
    report={'version':'1.3','timestamp':time.time(),'base':len(raw),'train':len(train),'val':len(val),'augmented':len(aug),'groups':{}}
    tg=[(t,DOM_A_GRUPO[d]) for t,d in aug]; tv=[(t,DOM_A_GRUPO[d]) for t,d in val]
    vec=VectorizadorHibrido(2600,2,.62,1.0).ajustar([t for t,_ in tg])
    X=vec.transformar([t for t,_ in tg]).T; Y=a_onehot([d for _,d in tg],list(GRUPOS))
    XV=vec.transformar([t for t,_ in tv]).T; YV=a_onehot([d for _,d in tv],list(GRUPOS))
    rg,b,h=train_net('nevula13_grupo',X,Y,XV,YV,list(GRUPOS),(256,128,64),70,128,.0014,.18)
    acc=float(np.mean(np.argmax(rg.predecir(XV),axis=0)==np.argmax(YV,axis=0)))
    save_model(rg,vec,OUT/'clasificador_grupo',list(GRUPOS),{'precision_val':acc,'version':'1.3','arquitectura':[X.shape[0],256,128,64,len(GRUPOS)]})
    report['precision_grupo']=acc
    for g,ds in GRUPOS.items():
        tr=[x for x in aug if x[1] in ds]; va=[x for x in val if x[1] in ds]
        v=VectorizadorHibrido(2200,2,.62,1.0).ajustar([t for t,_ in tr])
        a=v.transformar([t for t,_ in tr]).T; y=a_onehot([d for _,d in tr],ds)
        av=v.transformar([t for t,_ in va]).T; yv=a_onehot([d for _,d in va],ds)
        rr,bb,hh=train_net('nevula13_'+g,a,y,av,yv,ds,(256,128,64),65,128,.0014,.18)
        ac=float(np.mean(np.argmax(rr.predecir(av),axis=0)==np.argmax(yv,axis=0))) if va else 0.0
        save_model(rr,v,OUT/f'grupo_{g}',ds,{'precision_val':ac,'version':'1.3','arquitectura':[a.shape[0],256,128,64,len(ds)]})
        report['groups'][g]={'precision_val':ac,'n_train':len(tr),'n_val':len(va),'epochs':len(h)}
    (BASE/'almacenamiento'/'auditoria'/'entrenamiento_v13_resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
