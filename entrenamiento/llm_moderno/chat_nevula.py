"""Chat de terminal con el LLM base y, opcionalmente, el adaptador entrenado."""
from __future__ import annotations
import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="Qwen/Qwen3-8B")
    ap.add_argument("--adapter",default="almacenamiento/modelos/nevula_qwen3_8b_lora")
    ap.add_argument("--base-only",action="store_true",help="Probar el modelo base sin adaptador")
    ap.add_argument("--max-new-tokens",type=int,default=512)
    ap.add_argument("--temperature",type=float,default=0.7)
    args=ap.parse_args()
    adapter=None if args.base_only else args.adapter
    tokenizer=AutoTokenizer.from_pretrained(adapter or args.model, use_fast=True)
    dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (torch.float16 if torch.cuda.is_available() else torch.float32)
    model=AutoModelForCausalLM.from_pretrained(args.model,torch_dtype=dtype,device_map="auto" if torch.cuda.is_available() else None)
    if adapter:
        from pathlib import Path
        if not Path(adapter).exists(): raise SystemExit(f"No existe el adaptador: {adapter}")
        model=PeftModel.from_pretrained(model,adapter)
    model.eval(); history=[]
    print("Nevula LLM listo. Escribe /salir para terminar; /limpiar borra el historial.")
    while True:
        try: user=input("\nTú: ").strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if user=="/salir": break
        if user=="/limpiar": history=[]; print("Historial borrado."); continue
        if not user: continue
        history.append({"role":"user","content":user})
        messages=[{"role":"system","content":"Eres Nevula, un asistente útil, preciso y honesto. Responde en español salvo que el usuario prefiera otro idioma. Si no sabes algo, dilo claramente."}]+history
        prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        inputs=tokenizer(prompt,return_tensors="pt")
        device=next(model.parameters()).device
        inputs={k:v.to(device) for k,v in inputs.items()}
        kwargs={"max_new_tokens":args.max_new_tokens,"do_sample":args.temperature>0,"pad_token_id":tokenizer.eos_token_id}
        if args.temperature>0: kwargs.update({"temperature":args.temperature,"top_p":0.9,"repetition_penalty":1.08})
        with torch.inference_mode(): output=model.generate(**inputs,**kwargs)
        new=output[0][inputs["input_ids"].shape[1]:]
        answer=tokenizer.decode(new,skip_special_tokens=True).strip()
        print("Nevula:",answer)
        history.append({"role":"assistant","content":answer})
if __name__=="__main__": main()
