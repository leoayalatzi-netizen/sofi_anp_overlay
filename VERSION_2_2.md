# ANP Nevula 2.2 — Multiplataforma

## Objetivo
El Language Core deja de depender de un único runtime. Nevula selecciona automáticamente el backend disponible:

1. **PyTorch** — entrenamiento e inferencia completa en PC/GPU.
2. **NumPy Portable** — inferencia autónoma con el mismo checkpoint exportado, pensada para ARM64/Pydroid y otros Python sin PyTorch.
3. **Fallback** — capa lingüística ligera si tampoco existe NumPy/modelo portable.

## Artefactos portables
En `almacenamiento/modelos/lenguaje/` se incluyen:
- `language_core_numpy.npz`
- `language_core_portable.json`
- `tokenizer_portable.json`

El exportador se ejecuta con PyTorch en la máquina de entrenamiento:
```bash
python -m lenguaje.exportar_portable --checkpoint almacenamiento/modelos/lenguaje/language_core.pt --tokenizer almacenamiento/modelos/lenguaje/tokenizer.model --outdir almacenamiento/modelos/lenguaje
```

## Arquitectura
`principal.py -> LanguageCore -> Torch | NumPy Portable | Fallback`

La ruta portátil no requiere PyTorch ni SentencePiece para cargar el modelo. El tokenizador portátil reproduce una segmentación compatible aproximada a partir de las piezas exportadas.

## Limitación honesta
El checkpoint bootstrap incluido sigue siendo pequeño y poco entrenado. La portabilidad no convierte ese checkpoint en un modelo de frontera. El siguiente salto de calidad requiere mucho más entrenamiento, corpus de alta calidad e instruction tuning.
