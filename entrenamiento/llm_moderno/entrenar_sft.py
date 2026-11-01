"""Fine-tuning de Nevula sobre Qwen3-8B mediante SFT + LoRA/QLoRA."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--train", default="entrenamiento/llm_moderno/data/train.jsonl")
    ap.add_argument("--validation", default="entrenamiento/llm_moderno/data/validation.jsonl")
    ap.add_argument("--out", default="almacenamiento/modelos/nevula_qwen3_8b_lora")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lora-r", type=int, default=64)
    ap.add_argument("--no-qlora", action="store_true", help="Carga pesos sin cuantización; requiere mucha más VRAM")
    ap.add_argument("--resume", action="store_true")
    args=ap.parse_args()
    train_path=Path(args.train); val_path=Path(args.validation)
    if not train_path.exists() or not val_path.exists():
        raise SystemExit("No encuentro train/validation. Ejecuta primero preparar_datos.py.")
    if not torch.cuda.is_available():
        if not args.no_qlora:
            raise SystemExit("QLoRA requiere una GPU CUDA compatible. Para entrenamiento real de 8B, usa Linux/WSL2 con GPU; CPU no es práctico.")
        print("ADVERTENCIA: entrenamiento sin CUDA en un modelo de 8B puede requerir mucha RAM y ser extremadamente lento.")
    if not args.no_qlora and not torch.cuda.is_available(): raise SystemExit("QLoRA necesita CUDA.")
    use_bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    compute_dtype=torch.bfloat16 if use_bf16 else (torch.float16 if torch.cuda.is_available() else torch.float32)
    tokenizer=AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None: tokenizer.pad_token=tokenizer.eos_token
    quant_config=None
    if not args.no_qlora:
        quant_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=compute_dtype)
    model=AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=compute_dtype,
        quantization_config=quant_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if not args.no_qlora:
        from peft import prepare_model_for_kbit_training
        model=prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache=False
    data=load_dataset("json",data_files={"train":str(train_path),"validation":str(val_path)})
    if len(data["train"]) < 2 or len(data["validation"]) < 1: raise SystemExit("El dataset necesita al menos 2 ejemplos de entrenamiento y 1 de validación.")
    peft_config=LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_r*2, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM", target_modules="all-linear",
    )
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    cfg=SFTConfig(
        output_dir=str(out),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_length=args.max_length,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant":False},
        bf16=use_bf16,
        fp16=torch.cuda.is_available() and not use_bf16,
        optim="paged_adamw_8bit" if not args.no_qlora else "adamw_torch",
        report_to="none",
        seed=20261026,
        dataset_num_proc=2,
    )
    trainer=SFTTrainer(
        model=model,
        args=cfg,
        train_dataset=data["train"],
        eval_dataset=data["validation"],
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    resume=bool(args.resume and any(out.glob("checkpoint-*")))
    result=trainer.train(resume_from_checkpoint=resume)
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))
    report={"base_model":args.model,"method":"QLoRA" if not args.no_qlora else "LoRA without quantization","train_examples":len(data["train"]),"validation_examples":len(data["validation"]),"epochs":args.epochs,"max_length":args.max_length,"lora_rank":args.lora_r,"train_metrics":result.metrics,"eval_metrics":trainer.evaluate(),"adapter_dir":str(out)}
    (out/"nevula_training_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2,default=str))
if __name__=="__main__": main()
