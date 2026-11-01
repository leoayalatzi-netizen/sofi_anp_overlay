#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entrenamiento evolucionado de Nevula 1.2.
No reemplaza los artefactos 1.1: escribe modelos en almacenamiento/modelos/evolucionado.
"""
import json, random, time, hashlib, sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from entrenamiento.entrenar_clasificador import cargar_dataset, balancear_clases, a_onehot
from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima, FuncionActivacion, Regularizador, ModoNormalizacion, Inicializador, SchedulerType
from evolucion.vectorizador_hibrido import VectorizadorHibrido
from aprendizaje.evaluador_modelos import construir_holdout_fijo

GRUPOS={'computacion':['programacion','tecnologia','robotica'],'ciencias_exactas':['ciencia','matematicas','naturaleza'],'sociedad':['cultura','humanidad','conocimiento_general','geografia'],'cotidiano':['lenguaje','vida_cotidiana','conversacional'],'ocio':['entretenimiento','deportes']}
DOM_A_GRUPO={d:g for g,ds in GRUPOS.items() for d in ds}; GRUPOS_LIST=list(GRUPOS)
OUT=BASE/'almacenamiento'/'modelos'/'evolucionado'; CK=BASE/'almacenamiento'/'checkpoints'; OUT.mkdir(parents=True,exist_ok=True); CK.mkdir(parents=True,exist_ok=True)

def augmentation(train, copies=4, seed=20260908):
    rng=random.Random(seed); out=list(train)
    for text,label in train:
        words=text.split()
        if len(words)<6: continue
        for k in range(copies):
            # Dropout de palabras de baja intensidad; nunca elimina todo.
            keep=[]
            p=rng.uniform(.72,.92)
            for w in words:
                if rng.random()<p: keep.append(w)
            if len(keep)<4: keep=words[:max(4,int(len(words)*.65))]
            if k%3==1: keep=keep[::2]+keep[1::2]
            elif k%3==2: keep=keep[:]
            variant=' '.join(keep)
            if variant!=text: out.append((variant,label))
    # Dedupe exacto para no inflar artificialmente el gradiente.
    seen=set(); clean=[]
    for x in out:
        key=(x[0],x[1])
        if key not in seen: seen.add(key); clean.append(x)
    rng.shuffle(clean); return clean

def stratified_split(examples, frac=.15, seed=424242):
    rng=random.Random(seed); by={d:[] for _,d in examples}
    for t,d in examples: by[d].append((t,d))
    tr=[]; va=[]
    for d,items in by.items():
        items=list(items); rng.shuffle(items); n=max(1,int(len(items)*frac)); va+=items[:n]; tr+=items[n:]
    rng.shuffle(tr); rng.shuffle(va); return tr,va

def train_net(name,X,y,Xv,yv,classes,hidden=(384,192,96),epochs=180,batch=64,lr=.0012,drop=.20):
    r=RedNeuronalOptima(name)
    dims=[X.shape[0],*hidden,len(classes)]
    for i in range(len(dims)-1):
        out=i==len(dims)-2
        r.agregar(dims[i],dims[i+1],activacion=FuncionActivacion.SOFTMAX if out else FuncionActivacion.RELU,
                  dropout_rate=0 if out else drop,regularizador=Regularizador.L2,lambda_reg=.0008 if not out else .0,
                  normalizacion=ModoNormalizacion.BATCH if (not out and i<2) else ModoNormalizacion.NINGUNO,
                  inicializador=Inicializador.XAVIER_NORMAL if out else Inicializador.HE_NORMAL)
    r.compilar(optimizador='adamw',perdida='categorical_crossentropy',lr=lr,scheduler_type=SchedulerType.COSINE,max_grad_norm=3.0,weight_decay=.003)
    # El motor histórico divide dos veces el gradiente de CE. Compensamos aquí
    # de forma local para esta generación, sin modificar el motor 1.1 existente.
    old_compute=[]
    for layer in r.capas:
        old_compute.append(layer.compute_gradients)
        def make_fixed(fn):
            def fixed(dA,max_grad_norm=5.0): return fn(dA*X.shape[1] if False else dA,max_grad_norm)
            return fixed
    # Entrenamiento propio: la pérdida ya entrega dA / batch; restauramos la escala
    # correcta multiplicando por el tamaño real de cada minibatch antes de compute_gradients.
    def train_fixed(Xtr,Ytr,Xval,Yval):
        best=float('inf'); best_state=None; stale=0; hist=[]
        for ep in range(epochs):
            r.scheduler.step(best); r.optimizador.lr=r.scheduler.lr_actual
            perm=np.random.permutation(Xtr.shape[1]); total=0; nb=0
            for j in range(0,Xtr.shape[1],batch):
                idx=perm[j:j+batch]; xb=Xtr[:,idx]; yb=Ytr[:,idx]
                yp=r.forward(xb,entrenando=True); loss,dA=__import__('nucleos.memoria.motores.motor_neuronal',fromlist=['LossFunctions']).LossFunctions.softmax_crossentropy(yp,yb)
                # compute_gradients vuelve a promediar por m: deshacemos esa segunda división.
                dA=dA*len(idx)
                for layer in reversed(r.capas):
                    dW,db,dA=layer.compute_gradients(dA,r.max_grad_norm); r.optimizador.actualizar(layer,dW,db)
                total+=loss; nb+=1
            trloss=total/max(1,nb); pv= r.forward(Xval,entrenando=False); vloss,_=__import__('nucleos.memoria.motores.motor_neuronal',fromlist=['LossFunctions']).LossFunctions.softmax_crossentropy(pv,Yval)
            hist.append((trloss,float(vloss),r.scheduler.lr_actual))
            if vloss<best:
                best=float(vloss); stale=0; best_state=[(c.pesos.copy(),c.sesgos.copy(),c._batchnorm.gamma.copy() if c._batchnorm else None,c._batchnorm.beta.copy() if c._batchnorm else None,c._batchnorm.running_mean.copy() if c._batchnorm else None,c._batchnorm.running_var.copy() if c._batchnorm else None) for c in r.capas]
            else: stale+=1
            if stale>=30: break
        if best_state:
            for c,s in zip(r.capas,best_state):
                c.pesos,c.sesgos=c if False else s[0],s[1]
                if c._batchnorm and s[2] is not None: c._batchnorm.gamma,c._batchnorm.beta,c._batchnorm.running_mean,c._batchnorm.running_var=s[2],s[3],s[4],s[5]
        r._entrenada=True; r.epocas_entrenadas=len(hist); r._historial['perdida']=[x[0] for x in hist]; r._historial['val_perdida']=[x[1] for x in hist]; r._historial['lr']=[x[2] for x in hist]
        return r,best,hist
    return train_fixed(X,y,Xv,yv)

def save_model(r,v,base,classes,meta):
    r.guardar(str(base.with_suffix('.anp'))); v.guardar(Path(str(base)+'_vocab.json')); m=json.loads(Path(str(base)+'_vocab.json').read_text()); m.update({'clases':classes,**meta}); Path(str(base)+'_vocab.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')

def predict_model(r,v,text,classes):
    p=r.predecir(v.transformar([text]).T).flatten(); order=np.argsort(-p); return classes[int(order[0])],float(p[order[0]])

def evaluate_pipeline(holdout):
    mg=OUT/'clasificador_grupo.anp'; vg=OUT/'clasificador_grupo_vocab.json'
    rg=RedNeuronalOptima.cargar(str(mg)); vg=VectorizadorHibrido.cargar(vg); meta=None
    md=json.loads(vg_path.read_text(encoding='utf-8')); groups=md['clases']; total=0; correct=0; per={d:[0,0] for _,d in holdout}; cache={}
    for g in groups:
        b=OUT/f'grupo_{g}'; rv=RedNeuronalOptima.cargar(str(b.with_suffix('.anp'))); vv=VectorizadorHibrido.cargar(Path(str(b)+'_vocab.json')); mm=json.loads(Path(str(b)+'_vocab.json').read_text()); cache[g]=(rv,vv,mm['clases'])
    for text,real in holdout:
        g,pg=predict_model(rg,vg,text,groups); rd,vd,classes=cache[g]; d,pd=predict_model(rd,vd,text,classes); ok=d==real; total+=ok; per[real][0]+=1; per[real][1]+=ok
    return {'precision':correct/len(holdout) if False else total/max(1,len(holdout)),'n_holdout':len(holdout),'por_dominio':{d:{'n':n,'aciertos':a,'precision':a/max(1,n)} for d,(n,a) in per.items()}}

def main():
    random.seed(20260908); np.random.seed(20260908)
    raw_examples,domains=cargar_dataset(); train,val=stratified_split(raw_examples,.15)
    train_bal=balancear_clases(train,1.35); train_aug=augmentation(train_bal,2)
    # Guardar dataset masivo para reproducibilidad.
    ds_path=BASE/'entrenamiento'/'dataset_dominios_masivo_v12.json'; ds_path.write_text(json.dumps({'dominios':domains,'ejemplos':train_aug,'base_train':len(train),'base_val':len(val)},ensure_ascii=False),encoding='utf-8')
    report={'fecha':time.strftime('%Y-%m-%d %H:%M:%S'),'base_examples':len(raw_examples),'train_base':len(train),'val':len(val),'train_balanced':len(train_bal),'train_augmented':len(train_aug),'domains':domains,'groups':GRUPOS}
    # Stage 1
    tg=[(t,DOM_A_GRUPO[d]) for t,d in train_aug]; tv=[(t,DOM_A_GRUPO[d]) for t,d in val]
    vg=VectorizadorHibrido(1400,2).ajustar([t for t,_ in tg]); X=vg.transformar([t for t,_ in tg]).T; Y=a_onehot([d for _,d in tg],GRUPOS_LIST); XV=vg.transformar([t for t,_ in tv]).T; YV=a_onehot([d for _,d in tv],GRUPOS_LIST)
    rg,best,h=train_net('nevula12_grupo',X,Y,XV,YV,GRUPOS_LIST,(128,64,32),45,128,.0018,.16); pg=rg.predecir(XV); acc=float(np.mean(np.argmax(pg,axis=0)==np.argmax(YV,axis=0))); save_model(rg,vg,OUT/'clasificador_grupo',GRUPOS_LIST,{'precision_val':acc,'arquitectura':[X.shape[0],384,192,96,len(GRUPOS_LIST)],'version':'1.2-evolucionada'}); report['precision_grupo']=acc
    stage={}
    for g,ds in GRUPOS.items():
        tr=[(t,d) for t,d in train_aug if d in ds]; vv=[(t,d) for t,d in val if d in ds]
        vec=VectorizadorHibrido(1200,2).ajustar([t for t,_ in tr]); X=vec.transformar([t for t,_ in tr]).T; Y=a_onehot([d for _,d in tr],ds); XV=vec.transformar([t for t,_ in vv]).T; YV=a_onehot([d for _,d in vv],ds)
        rr,bb,hh=train_net('nevula12_'+g,X,Y,XV,YV,ds,(128,64,32),40,128,.0018,.16); pp=rr.predecir(XV); acc=float(np.mean(np.argmax(pp,axis=0)==np.argmax(YV,axis=0))) if vv else 0
        save_model(rr,vec,OUT/f'grupo_{g}',ds,{'precision_val':acc,'arquitectura':[X.shape[0],256,128,64,len(ds)],'version':'1.2-evolucionada'}); stage[g]={'precision_val':acc,'n_train':len(tr),'n_val':len(vv),'epochs':len(h)}
    report['stage2']=stage
    # Holdout independiente y sin tocar producción.
    hold=construir_holdout_fijo(.20,12345); report['holdout_independiente_note']='Holdout generado con semilla separada; no modifica modelos 1.1.'
    # manual evaluation avoiding fragile helper imports
    rg=RedNeuronalOptima.cargar(str(OUT/'clasificador_grupo.anp')); vg=VectorizadorHibrido.cargar(OUT/'clasificador_grupo_vocab.json'); gm=json.loads((OUT/'clasificador_grupo_vocab.json').read_text()); cache={}
    for g in GRUPOS_LIST:
        b=OUT/f'grupo_{g}'; cache[g]=(RedNeuronalOptima.cargar(str(b.with_suffix('.anp'))),VectorizadorHibrido.cargar(Path(str(b)+'_vocab.json')),json.loads(Path(str(b)+'_vocab.json').read_text())['clases'])
    correct=0
    for text,real in hold:
        gp=int(np.argmax(rg.predecir(vg.transformar([text]).T),axis=0)[0]); g=gm['clases'][gp]; rr,vv,ds=cache[g]; dp=int(np.argmax(rr.predecir(vv.transformar([text]).T),axis=0)[0]); correct += ds[dp]==real
    report['precision_holdout']=correct/max(1,len(hold)); report['n_holdout']=len(hold)
    report['modelo_no_promovido_automaticamente']=True
    (BASE/'almacenamiento'/'auditoria'/'entrenamiento_v12_resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2)); return report
if __name__=='__main__': main()
