# ANP Nevula 2.3.1 — Salto de Calidad Lingüística

Esta versión conserva el runtime multiplataforma 2.3 y añade una capa cognitiva enfocada en **calidad de lenguaje, razonamiento, memoria y datos de entrenamiento**.

## Cambios principales
- Guardas lingüísticas 2.3.1: detección de fragmentación, repetición, baja diversidad, símbolos corruptos y texto no lingüístico.
- RAG local ampliado a 5.000 unidades con scoring TF-IDF ligero + coincidencias de bigramas.
- Memoria episódica persistente SQLite: solo guarda elementos explícitamente registrados por el sistema.
- Planificador de razonamiento: clasifica intención y construye un plan antes de generar.
- Corpus de evolución separado, deduplicado y con tareas de explicación, resumen, instrucciones, diálogo y razonamiento.
- Arquitectura de entrenamiento 2.3.1: RoPE + Grouped Query Attention + KV cache + SwiGLU + RMSNorm + weight tying.
- Entrenamiento con train/validation split, cosine schedule, acumulación de gradiente, AMP CUDA y checkpoints reanudables.
- Benchmark reproducible de lenguaje/razonamiento/memoria.

## Escalas
`mobile` 4k/128/192/4; `small` 8k/256/384/8; `evolution` 16k/512/512/12; `large` 32k/1024/768/16; `xlarge` 32k/2048/1024/24.

## Importante
El paquete **no afirma estar preentrenado a escala masiva**. La mejora arquitectónica y del pipeline permite entrenar un modelo mucho más capaz, pero la capacidad final depende de datos, pasos y hardware reales.
