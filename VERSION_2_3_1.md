# ANP Nevula 2.3.1 — Calidad Cognitivo-Lingüística

**Objetivo:** convertir el 2.3 en una plataforma de lenguaje verificable, con separación explícita entre generación, razonamiento, memoria, recuperación y control de calidad.

### Capas nuevas
1. **Lenguaje:** guardas anti-gibberish y scoring de diversidad/repetición.
2. **Razonamiento:** planificador de intención y pasos antes de generar.
3. **Memoria:** memoria episódica SQLite persistente y explícita.
4. **Conocimiento:** RAG local de hasta 5.000 unidades, TF-IDF ligero y bigramas.
5. **Entrenamiento:** corpus evolución deduplicado + tareas de explicación, resumen, instrucciones y razonamiento.
6. **Arquitectura futura:** RoPE + GQA + KV-cache + SwiGLU + RMSNorm para el nuevo checkpoint de evolución.
7. **Evaluación:** benchmark reproducible y `doctor` multiplataforma.

La arquitectura nueva no se presenta como un modelo ya entrenado a escala de frontera. El código, corpus y pipeline quedan preparados para que el entrenamiento real sea el siguiente multiplicador de capacidad.
