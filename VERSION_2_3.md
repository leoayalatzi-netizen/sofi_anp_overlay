# ANP Nevula 2.3 — Universal Cognitive Runtime

## Salto respecto a 2.2

### Runtime multiplataforma
1. PyTorch: entrenamiento e inferencia de máxima capacidad en PC/GPU.
2. ONNX Runtime: ruta portable para despliegues nativos y Android.
3. NumPy: inferencia autónoma en ARM/Pydroid cuando no existe PyTorch/ORT.
4. Fallback Python: arranque de emergencia.

### Cognición lingüística
- RAG local ligero para aportar evidencia del corpus antes de generar.
- Guardas de calidad para rechazar salidas corruptas.
- Memoria conversacional preservada.
- Diagnóstico ampliado del backend, corpus y runtime.

### Escalabilidad
- `mobile`: checkpoint actual compatible con dispositivos modestos.
- `small`: 8k vocab / 384d / 8 capas.
- `evolution`: 16k vocab / 512d / 12 capas / contexto 512.
- `large`: 32k vocab / 768d / 16 capas.
- `xlarge`: 32k vocab / 1024d / 24 capas.

## Estado honesto
El checkpoint incluido continúa siendo el bootstrap de 2.1/2.2: 4,096 tokens de vocabulario, contexto 128 y 2,619,072 parámetros, entrenado durante 30 pasos. La arquitectura 2.3 permite entrenar modelos considerablemente mayores, pero no se presenta como si ya hubieran sido preentrenados masivamente.
