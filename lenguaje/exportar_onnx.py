from __future__ import annotations
import argparse
from pathlib import Path
import torch
from .modelo import NevulaLanguageModel

class Wrapper(torch.nn.Module):
    def __init__(self,m): super().__init__(); self.m=m
    def forward(self,ids): return self.m(ids)[0]

def export(checkpoint,out):
    model,_=NevulaLanguageModel.load_checkpoint(checkpoint,'cpu'); model.eval(); w=Wrapper(model)
    dummy=torch.ones((1,min(16,model.block_size)),dtype=torch.long)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    torch.onnx.export(w,dummy,out,input_names=['input_ids'],output_names=['logits'],dynamic_axes={'input_ids':{1:'sequence'},'logits':{1:'sequence'}},opset_version=17)
    return {'path':str(out),'block_size':model.block_size,'vocab_size':model.vocab_size}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();print(export(a.checkpoint,a.out))
