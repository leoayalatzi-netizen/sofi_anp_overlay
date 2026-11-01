# Nevula APEX — Entrenamiento con un LLM moderno

Se agregó un módulo independiente en `entrenamiento/llm_moderno/` para adaptar un LLM preentrenado con SFT + LoRA/QLoRA, evaluar base frente a adaptador y usarlo desde Python o terminal.

**Inicio rápido:** consulta [`entrenamiento/llm_moderno/README.md`](entrenamiento/llm_moderno/README.md) para requisitos, preparación de datos, comandos y límites de hardware.

El núcleo portátil anterior no se modifica. El adaptador no incluye los pesos de la base: al usarlo, Transformers descarga o carga `Qwen/Qwen3-8B`. No se ha realizado entrenamiento en este paquete.
