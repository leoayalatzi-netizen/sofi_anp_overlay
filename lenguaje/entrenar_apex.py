from __future__ import annotations
import argparse,json,math,random,time,shutil
from pathlib import Path
import sentencepiece as spm, torch
from .corpus_apex import build_apex_corpus
from .modelo_evolucion import NevulaEvolutionModel
BASE=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--steps',type=int,default=1200);ap.add_argument('--out',default='almacenamiento/modelos/lenguaje/apex_mobile');ap.add_argument('--base',default='almacenamiento/modelos/lenguaje/omega_mobile/language_omega_mobile.pt');args=ap.parse_args()
    random.seed(20260917);torch.manual_seed(20260917)
    out=BASE/args.out;out.mkdir(parents=True,exist_ok=True)
    corpus=BASE/'almacenamiento/modelos/lenguaje/corpus_apex.txt';manifest=build_apex_corpus(corpus)
    src_tok=BASE/'almacenamiento/modelos/lenguaje/omega_mobile/tokenizer.model'; tok=out/'tokenizer.model'
    if not tok.exists(): shutil.copy2(src_tok,tok)
    sp=spm.SentencePieceProcessor(model_file=str(tok));ids=sp.encode(corpus.read_text(encoding='utf8'),out_type=int)+[sp.eos_id()]
    cut=int(.93*len(ids));tr,va=ids[:cut],ids[cut:];block=128
    def batch(data,n=1):
        i=random.randrange(0,len(data)-block-1);z=data[i:i+block+1];return torch.tensor([z[:-1]]*n),torch.tensor([z[1:]]*n)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    base=BASE/args.base; d=torch.load(base,map_location=device,weights_only=False); cfg=d['config']
    m=NevulaEvolutionModel(**cfg).to(device);m.load_state_dict(d['model']);m.train()
    o=torch.optim.AdamW(m.parameters(),lr=1.0e-4,betas=(.9,.95),weight_decay=.05)
    target=args.steps; warm=80
    def lf(s):
        return min(1,(s+1)/warm)*.5*(1+math.cos(math.pi*max(0,s-warm)/max(1,target-warm)))
    sch=torch.optim.lr_scheduler.LambdaLR(o,lf)
    latest=out/'latest.pt';start=0;best=99.0;hist=[]
    if latest.exists():
        r=torch.load(latest,map_location=device,weights_only=False);m.load_state_dict(r['model']);o.load_state_dict(r['optimizer']);sch.load_state_dict(r['scheduler']);start=int(r.get('step',0));best=float(r.get('best_val_loss',99.0))
    t=time.time()
    for step in range(start+1,target+1):
        o.zero_grad(set_to_none=True);x,y=batch(tr);x=x.to(device);y=y.to(device);_,loss,_=m(x,y);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);o.step();sch.step()
        if step%100==0 or step==target:
            m.eval();vals=[]
            with torch.no_grad():
                for _ in range(8):
                    x,y=batch(va);_,z,_=m(x.to(device),y.to(device));vals.append(float(z))
            vl=sum(vals)/len(vals);best=min(best,vl);row={'step':step,'train_loss':float(loss),'val_loss':vl,'ppl':math.exp(min(20,vl)),'lr':o.param_groups[0]['lr']};hist.append(row);print(json.dumps(row),flush=True)
            torch.save({'config':cfg,'model':m.state_dict(),'optimizer':o.state_dict(),'scheduler':sch.state_dict(),'step':step,'best_val_loss':best},latest);m.train()
    m.eval();payload={'config':cfg,'model':m.state_dict(),'steps':target,'base_checkpoint':str(args.base),'best_val_loss':best,'trained_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'corpus_manifest':manifest}
    torch.save(payload,out/'language_apex_mobile.pt')
    (out/'training_report.json').write_text(json.dumps({'version':'2.5-APEX-MOBILE','config':cfg,'steps':target,'best_val_loss':best,'best_ppl':math.exp(min(20,best)),'parameters':sum(p.numel() for p in m.parameters()),'corpus_tokens':len(ids),'device':device,'history':hist,'seconds':time.time()-t},ensure_ascii=False,indent=2),encoding='utf8')
    shutil.copy2(src_tok,out/'tokenizer.model')
if __name__=='__main__':main()
