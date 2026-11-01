"""Backend opcional de Transformers para integrar el LLM moderno en Nevula APEX.

Este backend no reemplaza el runtime portable existente: requiere PyTorch,
Transformers y suficiente memoria para el modelo elegido.
"""
from __future__ import annotations
from pathlib import Path

class NevulaHFBackend:
    def __init__(self, model_id="Qwen/Qwen3-8B", adapter_dir=None, device_map="auto", dtype=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch=torch
        self.model_id=model_id
        self.adapter_dir=str(adapter_dir) if adapter_dir else None
        source=self.adapter_dir if self.adapter_dir and Path(self.adapter_dir).exists() else model_id
        self.tokenizer=AutoTokenizer.from_pretrained(source,use_fast=True)
        if dtype is None:
            dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (torch.float16 if torch.cuda.is_available() else torch.float32)
        self.model=AutoModelForCausalLM.from_pretrained(model_id,torch_dtype=dtype,device_map=device_map if torch.cuda.is_available() else None)
        if self.adapter_dir:
            if not Path(self.adapter_dir).exists(): raise FileNotFoundError(f"No existe el adaptador: {self.adapter_dir}")
            from peft import PeftModel
            self.model=PeftModel.from_pretrained(self.model,self.adapter_dir)
        self.model.eval()

    def generate(self, messages, max_new_tokens=512, temperature=0.0):
        if isinstance(messages,str): messages=[{"role":"user","content":messages}]
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        inputs=self.tokenizer(prompt,return_tensors="pt")
        device=next(self.model.parameters()).device
        inputs={k:v.to(device) for k,v in inputs.items()}
        kwargs={"max_new_tokens":max_new_tokens,"do_sample":temperature>0,"pad_token_id":self.tokenizer.eos_token_id}
        if temperature>0: kwargs.update({"temperature":temperature,"top_p":0.9,"repetition_penalty":1.08})
        with self.torch.inference_mode(): out=self.model.generate(**inputs,**kwargs)
        return self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],skip_special_tokens=True).strip()
