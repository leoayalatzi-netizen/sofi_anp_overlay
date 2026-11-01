from __future__ import annotations
import math,re
from pathlib import Path
import torch
from .modelo_evolucion import NevulaEvolutionModel
import sentencepiece as spm
BASE=Path(__file__).resolve().parents[1]
class OmegaCore:
 VERSION='2.4-OMEGA'
 def __init__(self,root=None,device=None):
  self.root=Path(root or BASE/'almacenamiento/modelos/lenguaje/omega_mobile');self.VERSION='2.5-APEX' if self.root.name=='apex_mobile' else '2.4-OMEGA';self.device=device or ('cuda' if torch.cuda.is_available() else 'cpu');self.ready=False
  ck=(self.root/'language_apex_mobile.pt') if (self.root/'language_apex_mobile.pt').exists() else (self.root/'language_omega_mobile.pt');tok=self.root/'tokenizer.model'
  if ck.exists() and tok.exists():
   d=torch.load(ck,map_location=self.device,weights_only=False);self.config=d['config'];self.model=NevulaEvolutionModel(**self.config).to(self.device);self.model.load_state_dict(d['model']);self.model.eval();self.tok=spm.SentencePieceProcessor(model_file=str(tok));self.ready=True;self.steps=d.get('steps',0);self.best_val_loss=d.get('best_val_loss')
 def diagnostico(self):
  if not self.ready:return {'activo':False,'version':self.VERSION}
  return {'activo':True,'version':self.VERSION,'device':self.device,'vocabulario':self.tok.get_piece_size(),'parametros':sum(p.numel() for p in self.model.parameters()),'contexto':self.config['block_size'],'steps':self.steps,'best_val_loss':self.best_val_loss}
 @torch.no_grad()
 def generate(self,prompt,max_new_tokens=120,temperature=.68,top_p=.90,repetition_penalty=1.12):
  if not self.ready:return None
  ids=self.tok.encode(prompt,out_type=int);ids=ids[-self.config['block_size']+1:];x=torch.tensor([ids],dtype=torch.long,device=self.device);past=None;pieces=[]
  for _ in range(max_new_tokens):
   inp=x if past is None else x[:,-1:]
   logits,_,past=self.model(inp,past=past,use_cache=True);z=logits[0,-1]/max(.05,temperature)
   if x.shape[1]:
    recent=x[0,-min(80,x.shape[1]):].tolist()
    for tid in set(recent): z[tid]/=repetition_penalty
   vals,inds=torch.sort(z,descending=True);probs=torch.softmax(vals,dim=-1);cum=torch.cumsum(probs,0);keep=cum<=top_p;keep[0]=True;vals=vals[keep];inds=inds[keep];nxt=inds[torch.multinomial(torch.softmax(vals,0),1)]
   x=torch.cat((x,nxt.view(1,1)),1);piece=self.tok.decode([int(nxt)]);pieces.append(piece)
   if int(nxt) in (self.tok.eos_id(),self.tok.pad_id()) or '<|' in piece or x.shape[1] >= self.config['block_size']:break
  return re.sub(r'\s+',' ',self.tok.decode(x[0].tolist()).split('<|assistant|>',1)[-1].split('<|user|>',1)[0]).strip()
