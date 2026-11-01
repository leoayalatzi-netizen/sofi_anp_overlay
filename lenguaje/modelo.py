from __future__ import annotations
import math
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F

class RMSNorm(nn.Module):
    def __init__(self,d,eps=1e-6): super().__init__(); self.w=nn.Parameter(torch.ones(d)); self.eps=eps
    def forward(self,x): return x*torch.rsqrt(x.pow(2).mean(-1,keepdim=True)+self.eps)*self.w

class SwiGLU(nn.Module):
    def __init__(self,d,hidden): super().__init__(); self.w1=nn.Linear(d,hidden,bias=False); self.w2=nn.Linear(d,hidden,bias=False); self.out=nn.Linear(hidden,d,bias=False)
    def forward(self,x): return self.out(F.silu(self.w1(x))*self.w2(x))

class CausalSelfAttention(nn.Module):
    def __init__(self,d,n_heads,dropout=0.0):
        super().__init__(); assert d%n_heads==0
        self.h=n_heads; self.dh=d//n_heads; self.qkv=nn.Linear(d,3*d,bias=False); self.proj=nn.Linear(d,d,bias=False); self.drop=nn.Dropout(dropout)
        self.register_buffer('mask',torch.tril(torch.ones(4096,4096,dtype=torch.bool)).view(1,1,4096,4096),persistent=False)
    def forward(self,x):
        b,t,d=x.shape; q,k,v=self.qkv(x).chunk(3,-1)
        q=q.view(b,t,self.h,self.dh).transpose(1,2); k=k.view(b,t,self.h,self.dh).transpose(1,2); v=v.view(b,t,self.h,self.dh).transpose(1,2)
        y=F.scaled_dot_product_attention(q,k,v,is_causal=True,dropout_p=self.drop.p if self.training else 0.0)
        y=y.transpose(1,2).contiguous().view(b,t,d); return self.proj(y)

class Block(nn.Module):
    def __init__(self,d,h,ff,dropout=0.0):
        super().__init__(); self.n1=RMSNorm(d); self.attn=CausalSelfAttention(d,h,dropout); self.n2=RMSNorm(d); self.ff=SwiGLU(d,ff); self.drop=nn.Dropout(dropout)
    def forward(self,x): x=x+self.drop(self.attn(self.n1(x))); x=x+self.drop(self.ff(self.n2(x))); return x

class NevulaLanguageModel(nn.Module):
    """Decoder-only Transformer. Configurable from 20M to multi-billion scale."""
    def __init__(self,vocab_size,block_size=256,d_model=512,n_layers=8,n_heads=8,ff_mult=2.75,dropout=.08,tie_embeddings=True):
        super().__init__(); self.vocab_size=vocab_size; self.block_size=block_size; self.d_model=d_model
        self.tok=nn.Embedding(vocab_size,d_model); self.pos=nn.Embedding(block_size,d_model); ff=int(d_model*ff_mult)
        self.blocks=nn.ModuleList([Block(d_model,n_heads,ff,dropout) for _ in range(n_layers)]); self.norm=RMSNorm(d_model); self.lm_head=nn.Linear(d_model,vocab_size,bias=False)
        if tie_embeddings: self.lm_head.weight=self.tok.weight
        self.apply(self._init); self.lm_head.weight.data.mul_(0.7)
    def _init(self,m):
        if isinstance(m,nn.Linear): nn.init.normal_(m.weight,0,.02)
        elif isinstance(m,nn.Embedding): nn.init.normal_(m.weight,0,.02)
    def forward(self,idx,targets=None):
        b,t=idx.shape
        if t>self.block_size: idx=idx[:,-self.block_size:]; t=self.block_size
        p=torch.arange(t,device=idx.device); x=self.tok(idx)+self.pos(p)[None,:,:]
        for blk in self.blocks: x=blk(x)
        logits=self.lm_head(self.norm(x))
        loss=None
        if targets is not None:
            targets=targets[:,-t:]; loss=F.cross_entropy(logits.reshape(-1,self.vocab_size),targets.reshape(-1),ignore_index=-100)
        return logits,loss
    @classmethod
    def load_checkpoint(cls,path,device='cpu'):
        ck=torch.load(path,map_location=device,weights_only=False); cfg=ck['config']; m=cls(**cfg); m.load_state_dict(ck['model']); m.to(device); m.eval(); return m,ck
