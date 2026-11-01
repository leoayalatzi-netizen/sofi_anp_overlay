# Entrenar el LLM con lo que Sofi aprende
**Qué sí y qué no:** Render gratis no tiene GPU, así que ahí no se puede entrenar un LLM. Lo que hace el servidor es lo que sí se puede: guardar tus conversaciones, aprender al instante de cada 👍 (ANP lo guarda en su memoria) y preparar el dataset. El entrenamiento se corre una vez en una GPU gratuita (Colab/Kaggle) y el modelo resultante vuelve a Sofi.
1. Usa Sofi con un LLM conectado y marca 👍 las buenas respuestas (y 👎 las malas). Necesitas ~100 buenas como mínimo; más y variadas es mejor.
2. En la pestaña **Mente → Aprendizaje** pulsa **Descargar dataset** (dataset_sofi.jsonl).
3. En Colab (GPU) clona tu repo, sube el dataset e instala: `pip install torch` (según su guía) y `pip install -r entrenamiento/llm_moderno/requirements-llm.txt`.
4. Ejecuta: `python entrenar_llm.py --dataset dataset_sofi.jsonl --model Qwen/Qwen3-4B` (usa `Qwen/Qwen3-8B` si tu GPU tiene ≥16 GB). Hace: preparar datos → SFT con QLoRA → evaluación base vs. adaptado → fusión.
5. Sirve el modelo fusionado (Ollama, vLLM o un endpoint de Hugging Face) y pon su URL en `SOFI_LLM_URL` y su nombre en `SOFI_LLM_MODEL`.
Antes de entrenar revisa `dataset_report.json`: pocos ejemplos o muy repetidos dan un modelo peor que el base.
