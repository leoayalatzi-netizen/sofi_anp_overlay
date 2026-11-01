# Nevula 1.2 — Evolución neuronal

Esta carpeta es **aditiva**: el proyecto 1.1 y sus modelos originales no se eliminan ni se reemplazan físicamente.

## Entrenar de nuevo

```bash
PYTHONPATH=ANP python ANP/evolucion/entrenamiento_masivo.py
```

El entrenamiento escribe únicamente en `ANP/almacenamiento/modelos/evolucionado/` y genera `ANP/entrenamiento/dataset_dominios_masivo_v12.json`.

## Arquitectura

- representación híbrida: TF-IDF de palabras/bigramas + caracteres 3–5;
- clasificación jerárquica en 5 grupos;
- MLPs con ReLU, BatchNorm, Dropout, AdamW, cosine LR, clipping y early stopping;
- aumento y balanceo de datos;
- evaluación independiente;
- guardia de regresión 1.1 cuando 1.2 contradice al backend estable.

## Continuidad

El formato `.anp` histórico sigue siendo compatible. `checkpoint.py` aporta un formato de checkpoint ampliado para futuras fases de reanudación y metadatos.
