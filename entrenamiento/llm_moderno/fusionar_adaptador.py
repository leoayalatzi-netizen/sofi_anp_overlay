"""Fusiona el adaptador LoRA con los pesos base para exportar un modelo independiente."""
from __future__ import annotations
import argparse
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="Qwen/Qwen3-8B")
    ap.add_argument("--adapter",default="almacenamiento/modelos/nevula_qwen3_8b_lora")
    ap.add_argument("--out",default="almacenamiento/modelos/nevula_qwen3_8b_merged")
    args=ap.parse_args()
    if not Path(args.adapter).exists(): raise SystemExit(f"No existe el adaptador: {args.adapter}")
    dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (torch.float16 if torch.cuda.is_available() else torch.float32)
    base=AutoModelForCausalLM.from_pretrained(args.model,torch_dtype=dtype,device_map="auto" if torch.cuda.is_available() else None)
    tuned=PeftModel.from_pretrained(base,args.adapter)
    merged=tuned.merge_and_unload()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    merged.save_pretrained(out,safe_serialization=True, max_shard_size="5GB")
    AutoTokenizer.from_pretrained(args.adapter,use_fast=True).save_pretrained(out)
    print(f"Modelo fusionado guardado en {out}. Comprueba el espacio libre: el modelo completo puede ocupar muchos GB.")
if __name__=="__main__": main()
