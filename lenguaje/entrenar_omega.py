from __future__ import annotations
import argparse,json,math,random,time
from pathlib import Path
import sentencepiece as spm, torch
from .corpus_omega import build_omega_corpus
from .modelo_evolucion import NevulaEvolutionModel
BASE=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--steps',type=int,default=1200); ap.add_argument('--batch',type=int,default=2); ap.add_argument('--grad-accum',type=int,default=4); ap.add_argument('--block',type=int,default=256); ap.add_argument('--dmodel',type=int,default=256); ap.add_argument('--layers',type=int,default=6); ap.add_argument('--heads',type=int,default=8); ap.add_argument('--kv-heads',type=int,default=4); ap.add_argument('--vocab',type=int,default=8192); ap.add_argument('--lr',type=float,default=3e-4); ap.add_argument('--out',default='almacenamiento/modelos/lenguaje/omega'); ap.add_argument('--resume',action='store_true'); a=ap.parse_args()
 random.seed(20260911); torch.manual_seed(20260911)
 out=BASE/a.out; out.mkdir(parents=True,exist_ok=True); corpus=BASE/'almacenamiento/modelos/lenguaje/corpus_omega.txt'; manifest=build_omega_corpus(corpus)
 tok=out/'tokenizer.model'
 if not tok.exists():
  spm.SentencePieceTrainer.Train(input=str(corpus),model_prefix=str(out/'tokenizer'),vocab_size=a.vocab,model_type='bpe',character_coverage=1.0,unk_id=0,pad_id=1,bos_id=2,eos_id=3,user_defined_symbols=['<|user|>','<|context|>','<|assistant|>','<|tool|>','<|system|>'],hard_vocab_limit=False)
 sp=spm.SentencePieceProcessor(model_file=str(tok)); ids=sp.encode(corpus.read_text(encoding='utf8'),out_type=int)+[sp.eos_id()]
 # Hold-out contiguous tail: deterministic and leak-resistant enough for local corpus.
 cut=int(len(ids)*.95); train_ids=ids[:cut]; val_ids=ids[cut:]
 def batch(data):
  xs=[];ys=[]
  for _ in range(a.batch):
   i=random.randrange(0,len(data)-a.block-1); z=data[i:i+a.block+1];xs.append(z[:-1]);ys.append(z[1:])
  return torch.tensor(xs,dtype=torch.long),torch.tensor(ys,dtype=torch.long)
 device='cuda' if torch.cuda.is_available() else 'cpu';cfg=dict(vocab_size=sp.get_piece_size(),block_size=a.block,d_model=a.dmodel,n_layers=a.layers,n_heads=a.heads,kv_heads=a.kv_heads,ff_mult=2.75)
 m=NevulaEvolutionModel(**cfg).to(device); opt=torch.optim.AdamW(m.parameters(),lr=a.lr,betas=(.9,.95),weight_decay=.1); warm=max(50,int(a.steps*.05))
 def lr_lambda(s): return min(1.0,(s+1)/warm)*0.5*(1+math.cos(math.pi*max(0,s-warm)/max(1,a.steps-warm)))
 sch=torch.optim.lr_scheduler.LambdaLR(opt,lr_lambda);scaler=torch.amp.GradScaler('cuda',enabled=device=='cuda'); start=0;best=1e9;ck=out/'latest.pt'
 if a.resume and ck.exists():
  d=torch.load(ck,map_location=device,weights_only=False);m.load_state_dict(d['model']);opt.load_state_dict(d['optimizer']);sch.load_state_dict(d['scheduler']);start=d['step'];best=d.get('best_val_loss',best)
 m.train();history=[];t0=time.time()
 for step in range(start+1,a.steps+1):
  opt.zero_grad(set_to_none=True);acc=0.0
  for _ in range(a.grad_accum):
   x,y=batch(train_ids);x=x.to(device);y=y.to(device)
   with torch.autocast(device_type='cuda',dtype=torch.float16,enabled=device=='cuda'):
    _,loss,_=m(x,y); loss=loss/a.grad_accum
   scaler.scale(loss).backward();acc+=float(loss.item())
  scaler.unscale_(opt);torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);scaler.step(opt);scaler.update();sch.step()
  if step%100==0 or step==a.steps:
   m.eval(); vals=[]
   with torch.no_grad():
    for _ in range(12):
     x,y=batch(val_ids);x=x.to(device);y=y.to(device);_,z,_=m(x,y);vals.append(float(z.item()))
   vl=sum(vals)/len(vals);best=min(best,vl);rec={'step':step,'train_loss':acc,'val_loss':vl,'ppl':math.exp(min(20,vl)),'lr':opt.param_groups[0]['lr'],'elapsed_s':time.time()-t0};history.append(rec)
   torch.save({'config':cfg,'model':m.state_dict(),'optimizer':opt.state_dict(),'scheduler':sch.state_dict(),'step':step,'best_val_loss':best},ck);print(json.dumps(rec))
   m.train()
 m.eval();final=out/'language_omega.pt';torch.save({'config':cfg,'model':m.state_dict(),'steps':a.steps,'best_val_loss':best,'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'corpus_manifest':manifest},final)
 report={'version':'2.4-OMEGA','config':cfg,'steps':a.steps,'best_val_loss':best,'best_ppl':math.exp(min(20,best)),'parameters':sum(p.numel() for p in m.parameters()),'corpus_tokens':len(ids),'train_tokens':len(train_ids),'validation_tokens':len(val_ids),'device':device,'history':history,'seconds':time.time()-t0}
 (out/'training_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
