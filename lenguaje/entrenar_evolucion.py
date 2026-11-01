from __future__ import annotations
import argparse,json,math,random,time
from pathlib import Path
import sentencepiece as spm, torch
from torch.utils.data import Dataset,DataLoader,random_split
from .corpus_evolucion import build_evolution_corpus
from .modelo_evolucion import NevulaEvolutionModel
BASE=Path(__file__).resolve().parents[1]
class Stream(Dataset):
 def __init__(self,ids,b):self.ids=ids;self.b=b;self.n=max(0,(len(ids)-1)//b)
 def __len__(self):return self.n
 def __getitem__(self,i):
  s=i*self.b;a=self.ids[s:s+self.b+1];return torch.tensor(a[:-1]),torch.tensor(a[1:])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--steps',type=int,default=10000);ap.add_argument('--batch',type=int,default=4);ap.add_argument('--grad-accum',type=int,default=8);ap.add_argument('--block',type=int,default=512);ap.add_argument('--dmodel',type=int,default=512);ap.add_argument('--layers',type=int,default=12);ap.add_argument('--heads',type=int,default=8);ap.add_argument('--kv-heads',type=int,default=4);ap.add_argument('--vocab',type=int,default=16384);ap.add_argument('--lr',type=float,default=2e-4);ap.add_argument('--out',default='almacenamiento/modelos/lenguaje/evolution');ap.add_argument('--resume',action='store_true');a=ap.parse_args()
 random.seed(20260911);torch.manual_seed(20260911);out=BASE/a.out;out.mkdir(parents=True,exist_ok=True); corpus=BASE/'almacenamiento/modelos/lenguaje/corpus_evolution.txt';build_evolution_corpus(corpus)
 if not (out/'tokenizer.model').exists():spm.SentencePieceTrainer.Train(input=str(corpus),model_prefix=str(out/'tokenizer'),vocab_size=a.vocab,model_type='bpe',character_coverage=1.0,unk_id=0,pad_id=1,bos_id=2,eos_id=3,user_defined_symbols=['<|user|>','<|context|>','<|assistant|>','<|tool|>','<|system|>'],hard_vocab_limit=False)
 sp=spm.SentencePieceProcessor(model_file=str(out/'tokenizer.model'));ids=sp.encode(corpus.read_text(encoding='utf8'),out_type=int)+[sp.eos_id()]; ds=Stream(ids,a.block); nval=max(1,int(len(ds)*.05)); train,val=random_split(ds,[len(ds)-nval,nval],generator=torch.Generator().manual_seed(7)); loader=DataLoader(train,batch_size=a.batch,shuffle=True,drop_last=True);vloader=DataLoader(val,batch_size=a.batch,shuffle=False,drop_last=True)
 device='cuda' if torch.cuda.is_available() else 'cpu';cfg=dict(vocab_size=sp.get_piece_size(),block_size=a.block,d_model=a.dmodel,n_layers=a.layers,n_heads=a.heads,kv_heads=a.kv_heads,ff_mult=2.75);m=NevulaEvolutionModel(**cfg).to(device);opt=torch.optim.AdamW(m.parameters(),lr=a.lr,betas=(.9,.95),weight_decay=.1);sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,a.steps);scaler=torch.amp.GradScaler('cuda',enabled=device=='cuda');best=1e9;start=0;ck=out/'latest.pt'
 if a.resume and ck.exists():d=torch.load(ck,map_location=device,weights_only=False);m.load_state_dict(d['model']);opt.load_state_dict(d['optimizer']);sch.load_state_dict(d['scheduler']);start=d['step'];best=d['best']
 it=iter(loader)
 for step in range(start+1,a.steps+1):
  opt.zero_grad(set_to_none=True);acc=0
  for _ in range(a.grad_accum):
   try:x,y=next(it)
   except StopIteration:it=iter(loader);x,y=next(it)
   x=x.to(device);y=y.to(device)
   with torch.autocast(device_type='cuda',dtype=torch.float16,enabled=device=='cuda'):_,loss,_=m(x,y);loss=loss/a.grad_accum
   scaler.scale(loss).backward();acc+=loss.item()
  scaler.unscale_(opt);torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);scaler.step(opt);scaler.update();sch.step()
  if step%100==0:
   m.eval();vl=0;n=0
   with torch.no_grad():
    for x,y in vloader:
     x=x.to(device);y=y.to(device);_,z,_=m(x,y);vl+=z.item();n+=1
     if n>=20:break
   m.train();best=min(best,vl/max(1,n));torch.save({'config':cfg,'model':m.state_dict(),'optimizer':opt.state_dict(),'scheduler':sch.state_dict(),'step':step,'best':best},ck);print(f'step {step} train={acc:.4f} val={vl/max(1,n):.4f} ppl={math.exp(min(20,vl/max(1,n))):.1f}')
 m.eval();torch.save({'config':cfg,'model':m.state_dict(),'steps':a.steps,'best_val_loss':best,'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S')},out/'language_evolution.pt');(out/'training_report.json').write_text(json.dumps({'version':'2.3.1','config':cfg,'steps':a.steps,'best_val_loss':best,'parameters':sum(p.numel() for p in m.parameters()),'corpus_tokens':len(ids)},indent=2),encoding='utf8')
if __name__=='__main__':main()
