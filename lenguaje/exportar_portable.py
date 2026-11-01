from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import torch
from .modelo import NevulaLanguageModel
from .tokenizador import TokenizadorNevula

def export(checkpoint, tokenizer, outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    model,ck=NevulaLanguageModel.load_checkpoint(checkpoint,'cpu'); state=model.state_dict()
    arrays={}
    arrays['tok']=state['tok.weight'].detach().numpy().astype('float32'); arrays['pos']=state['pos.weight'].detach().numpy().astype('float32')
    for i,b in enumerate(model.blocks):
        arrays[f'b{i}.n1']=state[f'blocks.{i}.n1.w'].detach().numpy().astype('float32'); arrays[f'b{i}.qkv']=state[f'blocks.{i}.attn.qkv.weight'].detach().numpy().astype('float32'); arrays[f'b{i}.proj']=state[f'blocks.{i}.attn.proj.weight'].detach().numpy().astype('float32'); arrays[f'b{i}.n2']=state[f'blocks.{i}.n2.w'].detach().numpy().astype('float32'); arrays[f'b{i}.w1']=state[f'blocks.{i}.ff.w1.weight'].detach().numpy().astype('float32'); arrays[f'b{i}.w2']=state[f'blocks.{i}.ff.w2.weight'].detach().numpy().astype('float32'); arrays[f'b{i}.out']=state[f'blocks.{i}.ff.out.weight'].detach().numpy().astype('float32')
    arrays['norm']=state['norm.w'].detach().numpy().astype('float32'); arrays['lm_head']=state['lm_head.weight'].detach().numpy().astype('float32')
    np.savez_compressed(out/'language_core_numpy.npz',**arrays)
    tok=TokenizadorNevula(tokenizer); pieces=[tok.sp.id_to_piece(i) for i in range(tok.vocab_size)]
    (out/'tokenizer_portable.json').write_text(json.dumps({'pieces':pieces,'unk_id':tok.unk_id,'bos_id':tok.bos_id,'eos_id':tok.eos_id},ensure_ascii=False),encoding='utf-8')
    cfg=ck.get('config',{}); meta={'format':'nevula-portable-numpy-1','parametros':sum(p.numel() for p in model.parameters()),'block_size':model.block_size,'d_model':model.d_model,'n_layers':len(model.blocks),'n_heads':cfg.get('n_heads'),'vocab_size':model.vocab_size}
    (out/'language_core_portable.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--checkpoint',required=True); ap.add_argument('--tokenizer',required=True); ap.add_argument('--outdir',required=True); a=ap.parse_args(); print(json.dumps(export(a.checkpoint,a.tokenizer,a.outdir),indent=2))
