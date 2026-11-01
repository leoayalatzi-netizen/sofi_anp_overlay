"""Genera comparaciones base vs. adaptador para un conjunto de evaluación JSONL.
Cada línea puede usar {"prompt":"..."} o {"question":"..."}.
Esto guarda respuestas para revisión; no pretende puntuar automáticamente la verdad.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--model",default="Qwen/Qwen3-8B")
    ap.add_argument("--adapter",default="almacenamiento/modelos/nevula_qwen3_8b_lora")
    ap.add_argument("--out",default="entrenamiento/llm_moderno/salidas/comparacion.jsonl")
    ap.add_argument("--limit",type=int,default=200)
    args=ap.parse_args()
    rows=[]
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj=json.loads(line); prompt=obj.get("prompt",obj.get("question"))
            if prompt: rows.append({"prompt":str(prompt),"reference":obj.get("reference",obj.get("answer"))})
        if len(rows)>=args.limit: break
    if not rows: raise SystemExit("No se encontraron prompts en el archivo JSONL.")
    tok=AutoTokenizer.from_pretrained(args.model,use_fast=True)
    dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (torch.float16 if torch.cuda.is_available() else torch.float32)
    base=AutoModelForCausalLM.from_pretrained(args.model,torch_dtype=dtype,device_map="auto" if torch.cuda.is_available() else None).eval()
    adapted=PeftModel.from_pretrained(base,args.adapter).eval()
    device=next(adapted.parameters()).device
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as f:
        for i,row in enumerate(rows,1):
            messages=[{"role":"user","content":row["prompt"]}]
            prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            inputs=tok(prompt,return_tensors="pt"); inputs={k:v.to(device) for k,v in inputs.items()}
            with torch.inference_mode():
                with adapted.disable_adapter():
                    base_out=adapted.generate(**inputs,max_new_tokens=256,do_sample=False,pad_token_id=tok.eos_token_id)
                tuned_out=adapted.generate(**inputs,max_new_tokens=256,do_sample=False,pad_token_id=tok.eos_token_id)
            n=inputs["input_ids"].shape[1]
            result={**row,"base_response":tok.decode(base_out[0][n:],skip_special_tokens=True).strip(),"nevula_response":tok.decode(tuned_out[0][n:],skip_special_tokens=True).strip()}
            f.write(json.dumps(result,ensure_ascii=False)+"\n")
            print(f"{i}/{len(rows)}")
    print(f"Comparación guardada en: {out}")
if __name__=="__main__": main()
