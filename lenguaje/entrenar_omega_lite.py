from __future__ import annotations
import argparse,json,math,random,time
from pathlib import Path
import sentencepiece as spm, torch
from .corpus_omega import build_omega_corpus
from .modelo_evolucion import NevulaEvolutionModel
BASE=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--steps',type=int,default=1800);ap.add_argument('--out',default='almacenamiento/modelos/lenguaje/omega_mobile');a=ap.parse_args()
 random.seed(20260911);torch.manual_seed(20260911);out=BASE/a.out;out.mkdir(parents=True,exist_ok=True);corpus=BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt';manifest=build_omega_corpus(corpus);tok=out/'tokenizer.model'
 if not tok.exists():spm.SentencePieceTrainer.Train(input=str(corpus),model_prefix=str(out/'tokenizer'),vocab_size=8192,model_type='bpe',character_coverage=1.0,unk_id=0,pad_id=1,bos_id=2,eos_id=3,user_defined_symbols=['<|user|>','<|context|>','<|assistant|>','<|tool|>','<|system|>'],hard_vocab_limit=False)
 sp=spm.SentencePieceProcessor(model_file=str(tok));ids=sp.encode(corpus.read_text(encoding='utf8'),out_type=int)+[sp.eos_id()];cut=int(.93*len(ids));tr,va=ids[:cut],ids[cut:];block=128
 def batch(data,n=1):
  i=random.randrange(0,len(data)-block-1);z=data[i:i+block+1];return torch.tensor([z[:-1]]*n),torch.tensor([z[1:]]*n)
 device='cuda' if torch.cuda.is_available() else 'cpu';cfg=dict(vocab_size=sp.get_piece_size(),block_size=block,d_model=192,n_layers=4,n_heads=4,kv_heads=2,ff_mult=2.75);m=NevulaEvolutionModel(**cfg).to(device);o=torch.optim.AdamW(m.parameters(),lr=4e-4,betas=(.9,.95),weight_decay=.05);warm=100
 def lf(s):return min(1,(s+1)/warm)*.5*(1+math.cos(math.pi*max(0,s-warm)/max(1,a.steps-warm)))
 sch=torch.optim.lr_scheduler.LambdaLR(o,lf);best=99.;hist=[];t=time.time(); ck=out/'latest.pt'; start=0
 if ck.exists():
  d=torch.load(ck,map_location=device,weights_only=False); m.load_state_dict(d['model']); o.load_state_dict(d['optimizer']); sch.load_state_dict(d['scheduler']); start=int(d.get('step',0)); best=float(d.get('best_val_loss',99.))
 for step in range(start+1,a.steps+1):
  o.zero_grad(set_to_none=True);x,y=batch(tr);x=x.to(device);y=y.to(device);_,loss,_=m(x,y);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);o.step();sch.step()
  if step%100==0 or step==a.steps:
   m.eval();vs=[]
   with torch.no_grad():
    for _ in range(8):
     x,y=batch(va);_,z,_=m(x.to(device),y.to(device));vs.append(float(z))
   vl=sum(vs)/len(vs);best=min(best,vl);r={'step':step,'train_loss':float(loss),'val_loss':vl,'ppl':math.exp(min(20,vl)),'lr':o.param_groups[0]['lr'],'elapsed_s':time.time()-t};hist.append(r);print(json.dumps(r),flush=True);torch.save({'config':cfg,'model':m.state_dict(),'optimizer':o.state_dict(),'scheduler':sch.state_dict(),'step':step,'best_val_loss':best},out/'latest.pt');m.train()
 m.eval();torch.save({'config':cfg,'model':m.state_dict(),'steps':a.steps,'best_val_loss':best,'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'corpus_manifest':manifest},out/'language_omega_mobile.pt');(out/'training_report.json').write_text(json.dumps({'version':'2.4-OMEGA-MOBILE','config':cfg,'steps':a.steps,'best_val_loss':best,'best_ppl':math.exp(min(20,best)),'parameters':sum(p.numel() for p in m.parameters()),'corpus_tokens':len(ids),'device':device,'history':hist,'seconds':time.time()-t},ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
