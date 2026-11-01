# Nevula Language Core 2.2 — Multiplataforma

El núcleo lingüístico selecciona automáticamente el backend disponible: **PyTorch → NumPy Portable → Fallback**.

### Backends
- **PyTorch:** PC/GPU, entrenamiento e inferencia completa.
- **NumPy Portable:** inferencia en Python/ARM64 sin PyTorch ni SentencePiece.
- **Fallback:** generación ligera para entornos extremadamente limitados.

### Entrenamiento
```bash
python -m lenguaje.entrenar --steps 10000 --batch 8 --grad-accum 4 --block 512 --dmodel 512 --layers 8 --heads 8
```

### Exportación portátil
```bash
python -m lenguaje.exportar_portable --checkpoint almacenamiento/modelos/lenguaje/language_core.pt --tokenizer almacenamiento/modelos/lenguaje/tokenizer.model --outdir almacenamiento/modelos/lenguaje
```

La exportación genera `language_core_numpy.npz`, `language_core_portable.json` y `tokenizer_portable.json`.

**Importante:** el modelo bootstrap incluido sigue siendo un prototipo de ~2.6 M de parámetros y necesita mucho más entrenamiento para alcanzar una conversación avanzada. La mejora de 2.2 es principalmente de portabilidad y robustez de runtime.
