"""Entrena (SFT + LoRA) el LLM con lo que Sofi aprendió. Ejecutar en una máquina con GPU (Colab/Kaggle), NO en Render gratis.
Uso: python entrenar_llm.py --dataset dataset_sofi.jsonl --model Qwen/Qwen3-4B"""
import argparse, subprocess, sys
p=argparse.ArgumentParser(); p.add_argument("--dataset",required=True); p.add_argument("--model",default="Qwen/Qwen3-4B")
p.add_argument("--epochs",default="2"); p.add_argument("--min-examples",default="100"); a=p.parse_args()
def run(*c): print(">"," ".join(c),flush=True); subprocess.run([sys.executable,*c],check=True)
D="entrenamiento/llm_moderno/"
run(D+"preparar_datos.py","--input",a.dataset,"--min-examples",a.min_examples)
run(D+"entrenar_sft.py","--model",a.model,"--epochs",a.epochs)
run(D+"evaluar.py","--input",D+"data/validation.jsonl","--model",a.model)
run(D+"fusionar_adaptador.py","--model",a.model)
print("Listo: modelo fusionado en almacenamiento/modelos/nevula_qwen3_8b_merged. Sírvelo (Ollama/vLLM) y pon su URL en SOFI_LLM_URL.")
