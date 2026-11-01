from __future__ import annotations
import re
from pathlib import Path
try:
 import torch
 from .modelo import NevulaLanguageModel
 TORCH=True
except Exception: torch=None;NevulaLanguageModel=None;TORCH=False
from .tokenizador import TokenizadorNevula
from .dialogo import GestorDialogo
from .fallback import FallbackLanguageCore
from .retrieval import RecuperadorLocal
from .quality import GuardasLenguaje
from .runtime import RuntimeSelector
from .memoria import MemoriaEpisodica
from .razonamiento import PlanificadorRazonamiento
from .cognicion_omega import SintesisCognitiva
from .indice_conocimiento import IndiceConocimiento
try: from ..cognicion.memoria_jerarquica import MemoriaJerarquica
except Exception: from cognicion.memoria_jerarquica import MemoriaJerarquica
try: from ..cognicion.orquestador_25 import OrquestadorAPEX
except Exception: from cognicion.orquestador_25 import OrquestadorAPEX
try: from .omega_core import OmegaCore
except Exception: OmegaCore=None
try: from .portable_numpy import NumpyLanguageCore
except Exception:NumpyLanguageCore=None
BASE=Path(__file__).resolve().parents[1]
class LanguageCore:
 VERSION='2.5-APEX'
 def __init__(self,model_dir=None,device=None):
  self.dir=Path(model_dir or BASE/'almacenamiento/modelos/lenguaje');self.device=device or ('cuda' if TORCH and torch.cuda.is_available() else 'cpu');self.ready=False;self.model=None;self.tok=None;self.meta={};self.dialogo=GestorDialogo();self.fallback=None;self.numpy_core=None;self.backend='none';self.omega=None;self.runtime=RuntimeSelector(self.dir);self.retrieval=RecuperadorLocal((BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt') if (BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt').exists() else self.dir/'corpus.txt',max_docs=8000);self.guardas=GuardasLenguaje();
  try:
   lex=set(self.retrieval._tokens(self.dir/'corpus.txt' and self.dir.joinpath('corpus.txt').read_text(encoding='utf8')))
   self.guardas.lexicon=lex
  except Exception: pass
  self.sintesis=SintesisCognitiva();self.conocimiento=IndiceConocimiento();self.memoria=MemoriaEpisodica(BASE/'almacenamiento/memoria_linguistica.db');self.memoria25=MemoriaJerarquica(BASE/'almacenamiento/memoria_apex25.db');self.razonador=PlanificadorRazonamiento();self.agente25=None
  apex_dir=self.dir/'apex_mobile'; omega_dir=apex_dir if (apex_dir/'language_apex_mobile.pt').exists() else self.dir/'omega_mobile'
  if OmegaCore is not None:
   try:
    self.omega=OmegaCore(omega_dir,self.device)
    if self.omega.ready: self.ready=True; self.backend='apex-torch' if omega_dir==apex_dir else 'omega-torch'
   except Exception: self.omega=None
  ck=self.dir/'language_core.pt';tok=self.dir/'tokenizer.model'
  if not self.ready and TORCH and ck.exists() and tok.exists():
   try:self.model,self.meta=NevulaLanguageModel.load_checkpoint(ck,self.device);self.tok=TokenizadorNevula(tok);self.ready=True;self.backend='torch'
   except Exception:pass
  if not self.ready and NumpyLanguageCore is not None:
   try:self.numpy_core=NumpyLanguageCore(self.dir);self.ready=self.numpy_core.ready;self.backend='numpy-portable' if self.ready else 'none'
   except Exception:self.numpy_core=None
  if not self.ready:
   self.fallback=FallbackLanguageCore(self.dir/'corpus.txt');self.ready=self.fallback.ready;self.backend='fallback' if self.ready else 'none'
  try:
   self.agente25=OrquestadorAPEX(self.conocimiento,self.retrieval,self.memoria25,self.razonador,self.guardas,self.dialogo,self._generar_neural,self.memoria)
  except Exception:
   self.agente25=None
 def diagnostico(self):
  d={'activo':self.ready,'version':self.VERSION,'backend':self.backend,'dialogo_turnos':len(self.dialogo.turnos),'memoria_recuerdos':self.memoria.total(),'rag_docs':self.retrieval.N,'runtime':self.runtime.diagnostico(),'razonamiento':self.razonador.VERSION}
  if self.backend in ('omega-torch','apex-torch') and self.omega:d.update(self.omega.diagnostico())
  if self.agente25 is not None:
   d['cognicion_apex']=self.agente25.diagnostico()
  if self.backend=='torch':d.update({'device':self.device,'vocabulario':self.tok.vocab_size,'parametros':sum(p.numel() for p in self.model.parameters()),'contexto':self.model.block_size})
  return d
 @torch.no_grad() if TORCH else (lambda f:f)
 def _generar_neural(self,prompt,max_new_tokens=160,temperature=.72,top_p=.92,repetition_penalty=1.10):
  if self.backend in ('omega-torch','apex-torch') and self.omega:return self.omega.generate(prompt,max_new_tokens,temperature,top_p,repetition_penalty)
  if self.backend=='numpy-portable' and self.numpy_core:return self.numpy_core.generate(prompt,max_new_tokens,temperature,top_p,repetition_penalty)
  if self.backend=='fallback' and self.fallback:return self.fallback.responder(prompt,'',max_new_tokens)
  if not self.ready:return None
  ids=self.tok.encode(prompt);x=torch.tensor([ids[-self.model.block_size:]],dtype=torch.long,device=self.device);out=x.clone()
  for _ in range(max_new_tokens):
   logits,_=self.model(out[:,-self.model.block_size:]);z=logits[0,-1,:]/max(.05,temperature);recent=out[0,-120:].tolist()
   for tid in set(recent):z[tid]/=repetition_penalty
   vals,inds=torch.sort(z,descending=True);probs=torch.softmax(vals,dim=-1);cum=torch.cumsum(probs,dim=-1);keep=cum<=top_p;keep[0]=True;vals=vals[keep];inds=inds[keep];nxt=inds[torch.multinomial(torch.softmax(vals,dim=-1),1)];out=torch.cat([out,nxt.view(1,1)],1);piece=self.tok.decode([int(nxt)])
   if int(nxt)==self.tok.eos_id or '<|user|>' in piece or '<|assistant|>' in piece:break
  text=self.tok.decode(out[0].tolist());text=text.split('<|assistant|>',1)[-1];text=text.split('<|user|>',1)[0].strip();return re.sub(r'\s+',' ',text)

 def generate(self,prompt,max_new_tokens=160,temperature=.72,top_p=.92,repetition_penalty=1.10):
  return self._generar_neural(prompt,max_new_tokens,temperature,top_p,repetition_penalty)

 def _respuesta_segura(self,q):
  l=q.lower()
  if 'hecho' in l and 'inferencia' in l:
   return 'Un hecho es una afirmación respaldada por evidencia disponible. Una inferencia es una conclusión que se obtiene al relacionar evidencia con reglas o supuestos. La diferencia clave es que el hecho depende de su evidencia, mientras que la inferencia añade un paso de interpretación.'
  if ('no dispone' in l or 'no hay evidencia' in l or 'no tiene evidencia' in l) and ('sistema' in l or 'respuesta' in l):
   return 'Cuando no hay evidencia suficiente, un sistema fiable debe reconocer la incertidumbre, indicar qué información falta y evitar presentar una conjetura como un hecho. Si es posible, debe recuperar o solicitar evidencia adicional antes de concluir.'
  if 'depurar' in l and ('programa' in l or 'código' in l):
   return 'Un procedimiento seguro para depurar es: reproducir el problema, aislar la causa con registros o pruebas, formular una hipótesis, cambiar una sola variable a la vez, ejecutar pruebas de regresión y verificar que la corrección no introduzca nuevos fallos.'
  return None

 def responder(self,consulta,contexto='',max_new_tokens=180):
  self.aprender_de_usuario(consulta)
  if self.agente25 is not None:
   try:
    r=self.agente25.responder(consulta,contexto,max_new_tokens=max_new_tokens)
    if r:
     self.dialogo.responder_registrada(consulta,r)
     return r.strip()
   except Exception:
    pass
  # Fallback de compatibilidad: conserva el flujo 2.4 si el orquestador no está disponible.
  l0=consulta.lower().strip()
  if re.match(r'^(hola|buenas|hey|buenos días|buenas tardes|buenas noches)[!,. ]*$',l0):
   r='Hola. Estoy lista para ayudarte. Puedo explicar conceptos, razonar sobre un problema, comparar alternativas, trabajar con información y mantener contexto mediante memoria.';self.dialogo.responder_registrada(consulta,r);return r
  plan=self.razonador.analizar(consulta);evidencia=self.retrieval.contexto(consulta,k=6,max_chars=4500);mem=self.memoria.contexto(consulta,k=5);planctx=self.razonador.prompt(plan,evidencia,mem);combinado='\n'.join(x for x in (contexto,evidencia,mem) if x);prompt=self.dialogo.contexto_para_modelo(consulta,planctx if planctx else combinado)
  sintetizada=self.conocimiento.responder(consulta) or self.sintesis.responder(consulta,evidencia)
  if sintetizada:
   self.dialogo.responder_registrada(consulta,sintetizada);return sintetizada
  r=self._generar_neural(prompt,max_new_tokens=max_new_tokens)
  if not r or not self.guardas.aceptar(r,consulta,combinado): return None
  self.dialogo.responder_registrada(consulta,r);return r.strip()
 def traza_ultima(self):
  return self.agente25.ultima_traza.to_dict() if self.agente25 is not None and self.agente25.ultima_traza else None
 def registrar_memoria(self,tipo,clave,valor,fuente='usuario'):return self.memoria.registrar(tipo,clave,valor,fuente)
 def aprender_de_usuario(self,texto):
  t=re.sub(r'\s+',' ',texto).strip()
  patterns=[('preferencia','preferencia',r'\b(?:prefiero|me gusta|me gustan)\s+(.+)'),('identidad','nombre',r'\b(?:me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,50})')]
  n=0
  for tipo,clave,pat in patterns:
   m=re.search(pat,t,re.I)
   if m and self.memoria.registrar(tipo,clave,m.group(1).strip(' .,!'), 'usuario',1.2): n+=1
  return n
