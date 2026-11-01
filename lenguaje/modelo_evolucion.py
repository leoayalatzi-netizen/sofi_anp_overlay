from __future__ import annotations
import math, torch
from torch import nn
from torch.nn import functional as F

class RMSNorm(nn.Module):
    def __init__(self,d,eps=1e-6): super().__init__(); self.w=nn.Parameter(torch.ones(d)); self.eps=eps
    def forward(self,x): return x*torch.rsqrt(x.pow(2).mean(-1,keepdim=True)+self.eps)*self.w

def rope(x,cos,sin):
    # x [B,H,T,D]
    x1=x[...,::2]; x2=x[...,1::2]
    return torch.stack((x1*cos-x2*sin,x1*sin+x2*cos),dim=-1).flatten(-2)

class GQAAttention(nn.Module):
    def __init__(self,d,heads,kv_heads,max_seq=2048):
        super().__init__(); assert d%heads==0 and heads%kv_heads==0
        self.heads=heads; self.kv_heads=kv_heads; self.dh=d//heads; self.rep=heads//kv_heads
        self.q=nn.Linear(d,heads*self.dh,bias=False); self.k=nn.Linear(d,kv_heads*self.dh,bias=False); self.v=nn.Linear(d,kv_heads*self.dh,bias=False); self.o=nn.Linear(d,d,bias=False)
        inv=1/(10000**(torch.arange(0,self.dh,2).float()/self.dh)); pos=torch.arange(max_seq).float(); freqs=torch.outer(pos,inv)
        self.register_buffer('cos',freqs.cos()[None,None,:,:],persistent=False); self.register_buffer('sin',freqs.sin()[None,None,:,:],persistent=False)
    def forward(self,x,past=None,use_cache=False):
        b,t,_=x.shape; q=self.q(x).view(b,t,self.heads,self.dh).transpose(1,2); k=self.k(x).view(b,t,self.kv_heads,self.dh).transpose(1,2); v=self.v(x).view(b,t,self.kv_heads,self.dh).transpose(1,2)
        offset=0 if past is None else past[0].shape[2]
        q=rope(q,self.cos[:,:,offset:offset+t],self.sin[:,:,offset:offset+t]); k=rope(k,self.cos[:,:,offset:offset+t],self.sin[:,:,offset:offset+t])
        if past is not None:k=torch.cat((past[0],k),2); v=torch.cat((past[1],v),2)
        cache=(k,v) if use_cache else None
        kc,vc=k,v
        if self.rep>1:kc=kc.repeat_interleave(self.rep,1); vc=vc.repeat_interleave(self.rep,1)
        if past is None:
            y=F.scaled_dot_product_attention(q,kc,vc,is_causal=True)
        else:
            total=kc.shape[2]; mask=torch.arange(total,device=x.device)[None,:] <= (offset+torch.arange(t,device=x.device)[:,None])
            y=F.scaled_dot_product_attention(q,kc,vc,attn_mask=mask[None,None,:,:])
        y=y.transpose(1,2).contiguous().view(b,t,-1); return self.o(y),cache

class Block(nn.Module):
    def __init__(self,d,h,kv,ff,max_seq=2048):
        super().__init__(); self.n1=RMSNorm(d); self.attn=GQAAttention(d,h,kv,max_seq); self.n2=RMSNorm(d); hidden=int(d*ff); self.w1=nn.Linear(d,hidden,bias=False); self.w2=nn.Linear(d,hidden,bias=False); self.out=nn.Linear(hidden,d,bias=False)
    def forward(self,x,past=None,use_cache=False):
        a,cache=self.attn(self.n1(x),past,use_cache); x=x+a; x=x+self.out(F.silu(self.w1(self.n2(x)))*self.w2(self.n2(x))); return x,cache

class NevulaEvolutionModel(nn.Module):
    """Arquitectura OMEGA 2.4: RoPE + GQA + KV cache + SwiGLU + RMSNorm."""
    def __init__(self,vocab_size,block_size=512,d_model=512,n_layers=12,n_heads=8,kv_heads=4,ff_mult=2.75):
        super().__init__(); self.vocab_size=vocab_size; self.block_size=block_size; self.d_model=d_model; self.tok=nn.Embedding(vocab_size,d_model)
        self.blocks=nn.ModuleList([Block(d_model,n_heads,kv_heads,ff_mult,block_size) for _ in range(n_layers)]); self.norm=RMSNorm(d_model); self.lm_head=nn.Linear(d_model,vocab_size,bias=False); self.lm_head.weight=self.tok.weight
        self.apply(self._init)
    def _init(self,m):
        if isinstance(m,(nn.Linear,nn.Embedding)): nn.init.normal_(m.weight,0,.02)
    def forward(self,idx,targets=None,past=None,use_cache=False):
        x=self.tok(idx); new=[]
        for i,b in enumerate(self.blocks): x,c=b(x,None if past is None else past[i],use_cache); new.append(c) if use_cache else None
        logits=self.lm_head(self.norm(x)); loss=None
        if targets is not None: loss=F.cross_entropy(logits.reshape(-1,self.vocab_size),targets.reshape(-1))
        return logits,loss,new if use_cache else None
