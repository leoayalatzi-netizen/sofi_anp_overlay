import json, random, sys, time
from pathlib import Path
import numpy as np
from sklearn.neural_network import MLPClassifier
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from entrenamiento.entrenar_clasificador import cargar_dataset, balancear_clases
from evolucion.entrenamiento_masivo import GRUPOS,DOM_A_GRUPO,stratified_split
from evolucion.vectorizador_hibrido import VectorizadorHibrido
from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima,FuncionActivacion,Regularizador,ModoNormalizacion,Inicializador
from aprendizaje.evaluador_modelos import construir_holdout_fijo
OUT=BASE/'almacenamiento/modelos/evolucionado_v14'; OUT.mkdir(parents=True,exist_ok=True)

def export(clf,vec,classes):
 r=RedNeuronalOptima('nevula14_router_grande'); dims=[clf.coefs_[0].shape[0]]+[w.shape[1] for w in clf.coefs_]
 for i,(a,b) in enumerate(zip(dims[:-1],dims[1:])):
  r.agregar(a,b,activacion=FuncionActivacion.SOFTMAX if i==len(dims)-2 else FuncionActivacion.RELU,regularizador=Regularizador.NINGUNO,normalizacion=ModoNormalizacion.NINGUNO,inicializador=Inicializador.HE_NORMAL)
  r.capas[-1].pesos=np.asarray(clf.coefs_[i].T,dtype=np.float64); r.capas[-1].sesgos=np.asarray(clf.intercepts_[i],dtype=np.float64).reshape(-1,1)
 r._entrenada=True; r.epocas_entrenadas=int(clf.n_iter_); r.compilar(optimizador='adamw',perdida='categorical_crossentropy',lr=.001)
 r.guardar(str(OUT/'clasificador_grupo.anp')); vec.guardar(OUT/'clasificador_grupo_vocab.json'); p=OUT/'clasificador_grupo_vocab.json'; d=json.loads(p.read_text()); d.update({'clases':classes,'version':'1.4-grande','arquitectura':dims,'parametros':sum(a*b+b for a,b in zip(dims[:-1],dims[1:])),'trainer':'sklearn.MLPClassifier'}); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)); return r

def main():
 t=time.time(); random.seed(20260910); np.random.seed(20260910); raw,domains=cargar_dataset(); train,val=stratified_split(raw,.15,424242); train=balancear_clases(train,1.2)
 labels=list(GRUPOS); examples=[]
 for text,d in train:
  g=DOM_A_GRUPO[d]; examples.append((text,g)); examples.append((f'Explícame {text[:140]}',g))
 vec=VectorizadorHibrido(900,2,.38,1.0,True).ajustar([x[0] for x in examples],[x[1] for x in examples]); X=vec.transformar([x[0] for x in examples]); y=np.array([labels.index(x[1]) for x in examples])
 clf=MLPClassifier(hidden_layer_sizes=(1024,512,256),activation='relu',solver='adam',alpha=1e-4,batch_size=128,learning_rate_init=.001,max_iter=6,early_stopping=False,shuffle=True,random_state=20260910,verbose=False); clf.fit(X,y); r=export(clf,vec,labels)
 # independent holdout group accuracy through exported custom model
 hold=construir_holdout_fijo(.2,12345); correct=0
 for text,real in hold:
  p=r.predecir(vec.transformar([text]).T).argmax(); correct += labels[int(p)]==DOM_A_GRUPO[real]
 report={'version':'1.4-grande','base':len(raw),'train':len(examples),'features':X.shape[1],'arquitectura':[X.shape[1],1024,512,256,len(labels)],'parametros':sum(a*b+b for a,b in zip([X.shape[1],1024,512,256],[1024,512,256,len(labels)])),'precision_holdout_grupo':correct/len(hold),'epocas':int(clf.n_iter_),'tiempo_segundos':round(time.time()-t,2)}
 (BASE/'almacenamiento/auditoria/entrenamiento_v14_grande_resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
