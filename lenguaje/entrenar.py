from __future__ import annotations
import argparse, json, math, random, time
from pathlib import Path
import sentencepiece as spm
import torch
from torch.utils.data import Dataset, DataLoader
from .corpus import build_corpus
from .modelo import NevulaLanguageModel

BASE=Path(__file__).resolve().parents[1]

class SeqDataset(Dataset):
    def __init__(self, ids, block):
        self.ids=ids; self.block=block; self.n=max(0,(len(ids)-1)//block)
    def __len__(self): return self.n
    def __getitem__(self,i):
        s=i*self.block; a=self.ids[s:s+self.block+1]
        return torch.tensor(a[:-1],dtype=torch.long),torch.tensor(a[1:],dtype=torch.long)

def save_checkpoint(path, model, opt, scheduler, scaler, step, best, history, cfg, corpus_chars):
    tmp=Path(str(path)+'.tmp')
    torch.save({'config':cfg,'model':model.state_dict(),'optimizer':opt.state_dict(),'scheduler':scheduler.state_dict(),'scaler':scaler.state_dict(),'step':step,'best_loss':best,'history_tail':history[-200:],'corpus_chars':corpus_chars,'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S')},tmp)
    tmp.replace(path)

def main():
    ap=argparse.ArgumentParser(description='Nevula 2.1 — preentrenamiento lingüístico reanudable')
    ap.add_argument('--steps',type=int,default=10000); ap.add_argument('--batch',type=int,default=8); ap.add_argument('--grad-accum',type=int,default=4)
    ap.add_argument('--block',type=int,default=512); ap.add_argument('--dmodel',type=int,default=512); ap.add_argument('--layers',type=int,default=8); ap.add_argument('--heads',type=int,default=8); ap.add_argument('--vocab',type=int,default=8192)
    ap.add_argument('--lr',type=float,default=3e-4); ap.add_argument('--warmup',type=int,default=500); ap.add_argument('--out',default='almacenamiento/modelos/lenguaje'); ap.add_argument('--resume',action='store_true')
    args=ap.parse_args(); random.seed(20260911); torch.manual_seed(20260911)
    out=BASE/args.out; out.mkdir(parents=True,exist_ok=True); corpus=BASE/'almacenamiento/modelos/lenguaje/corpus.txt'; build_corpus(corpus)
    prefix=str(out/'tokenizer')
    if not (out/'tokenizer.model').exists():
        spm.SentencePieceTrainer.Train(input=str(corpus),model_prefix=prefix,vocab_size=args.vocab,model_type='bpe',character_coverage=1.0,unk_id=0,pad_id=1,bos_id=2,eos_id=3,user_defined_symbols=['<|user|>','<|context|>','<|assistant|>'],hard_vocab_limit=False)
    sp=spm.SentencePieceProcessor(model_file=str(out/'tokenizer.model')); ids=sp.encode(corpus.read_text(encoding='utf8'),out_type=int)+[sp.eos_id()]
    ds=SeqDataset(ids,args.block); loader=DataLoader(ds,batch_size=args.batch,shuffle=True,drop_last=True,pin_memory=torch.cuda.is_available())
    device='cuda' if torch.cuda.is_available() else 'cpu'; cfg=dict(vocab_size=sp.get_piece_size(),block_size=args.block,d_model=args.dmodel,n_layers=args.layers,n_heads=args.heads,ff_mult=2.75,dropout=.08,tie_embeddings=True)
    model=NevulaLanguageModel(**cfg).to(device); opt=torch.optim.AdamW(model.parameters(),lr=args.lr,betas=(.9,.95),weight_decay=.1)
    scheduler=torch.optim.lr_scheduler.LambdaLR(opt,lambda s: min(1.0,(s+1)/max(1,args.warmup)))
    scaler=torch.amp.GradScaler('cuda',enabled=device=='cuda'); start_step=0; best=float('inf'); history=[]
    ckpt=out/'language_core_latest.pt'
    if args.resume and ckpt.exists():
        ck=torch.load(ckpt,map_location=device,weights_only=False); model.load_state_dict(ck['model']); opt.load_state_dict(ck['optimizer']); scheduler.load_state_dict(ck['scheduler']); scaler.load_state_dict(ck.get('scaler',{})); start_step=int(ck.get('step',0)); best=float(ck.get('best_loss',best)); history=list(ck.get('history_tail',[])); print(f'Reanudando desde step {start_step}')
    model.train(); it=iter(loader); start=time.time(); tokens_seen=0
    for step in range(start_step+1,args.steps+1):
        opt.zero_grad(set_to_none=True); loss_acc=0.0
        for _ in range(args.grad_accum):
            try: x,y=next(it)
            except StopIteration: it=iter(loader); x,y=next(it)
            x=x.to(device,non_blocking=True); y=y.to(device,non_blocking=True); tokens_seen += x.numel()
            with torch.autocast(device_type='cuda',dtype=torch.float16,enabled=device=='cuda'):
                _,loss=model(x,y); loss=loss/args.grad_accum
            scaler.scale(loss).backward(); loss_acc += float(loss.item())
        scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); scaler.step(opt); scaler.update(); scheduler.step()
        lv=loss_acc; history.append(lv)
        if lv<best: best=lv
        if step%100==0:
            ppl=math.exp(min(20,lv)); print(f'step {step}/{args.steps} loss={lv:.4f} ppl={ppl:.1f} lr={scheduler.get_last_lr()[0]:.2e} tokens={tokens_seen} elapsed={time.time()-start:.1f}s')
            save_checkpoint(ckpt,model,opt,scheduler,scaler,step,best,history,cfg,len(corpus.read_text(encoding='utf8')))
    save_checkpoint(ckpt,model,opt,scheduler,scaler,args.steps,best,history,cfg,len(corpus.read_text(encoding='utf8')))
    torch.save({'config':cfg,'model':model.state_dict(),'steps':args.steps,'best_loss':best,'history_tail':history[-200:],'corpus_chars':len(corpus.read_text(encoding='utf8')),'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S')},out/'language_core.pt')
    (out/'training_report.json').write_text(json.dumps({'version':'2.1','steps':args.steps,'best_loss':best,'perplexity':math.exp(min(20,best)),'device':device,'parameters':sum(p.numel() for p in model.parameters()),'tokens_seen':tokens_seen,'context':args.block,'vocab':sp.get_piece_size()},ensure_ascii=False,indent=2),encoding='utf8')
    print('saved',out/'language_core.pt','params',sum(p.numel() for p in model.parameters()))
if __name__=='__main__': main()
