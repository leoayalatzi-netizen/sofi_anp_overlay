# ANP Nevula 2.4 OMEGA

## Objetivo
Dar el siguiente salto real en calidad lingüística y cognitiva sin confundir tamaño de modelo con inteligencia. OMEGA combina entrenamiento prolongado, datos curriculares, memoria persistente, recuperación fundamentada, razonamiento estructurado y verificación.

## Cambios principales
- Nuevo corpus OMEGA: 16,063 registros y ~3.48 M caracteres.
- 8,192 piezas BPE entrenadas sobre el corpus OMEGA.
- Modelo OMEGA móvil/CPU: 3,233,472 parámetros.
- 1,800 pasos de entrenamiento real en CPU, con curriculum sintético y datos heredados.
- Mejor validación: pérdida mínima registrada 3.7973 (PPL 44.58) en el benchmark de validación local.
- RoPE + GQA + KV-cache + SwiGLU + RMSNorm + weight tying.
- KV-cache corregida para no duplicar cabezas dentro de la caché.
- Índice de conocimiento estructurado directamente desde `datos/*.json`.
- Síntesis cognitiva grounded para definiciones, ejemplos, comparaciones y evidencia.
- Razonamiento directo para causalidad, contradicciones, hechos/inferencias y memoria.
- Memoria episódica persistente y aprendizaje explícito de preferencias/nombre cuando el usuario lo declara.
- Guardas lingüísticas heredadas para rechazar generación degradada.
- Backend OMEGA-Torch prioritario en equipos con PyTorch; se mantienen los backends portables de Nevula 2.3.x como respaldo.

## Evaluación local
El benchmark OMEGA obtuvo una calidad media de 0.939 en 8 casos diseñados para definición, razonamiento, causalidad, comparación, procedimiento, incertidumbre y diálogo. Esto es una métrica interna, no una comparación científica con modelos comerciales.

## Entrenamiento
El checkpoint entregado es un modelo realmente entrenado, no un simple archivo de arquitectura. Aun así, el corpus local sigue siendo pequeño frente a los corpus usados para entrenar LLM de producción. Para un salto de escala auténtico, OMEGA necesita más datos diversos y muchas más actualizaciones, idealmente con GPU.
