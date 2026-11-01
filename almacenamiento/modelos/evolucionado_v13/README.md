# Nevula 1.2 — modelo evolucionado

Backend neuronal opcional y preferente sobre los modelos 1.1. Los artefactos 1.1 permanecen intactos.

- Vectorización híbrida palabra/bigrama + n-grama de caracteres.
- Entrenamiento jerárquico en 5 grupos.
- Dataset de entrenamiento aumentado y balanceado.
- Evaluación con holdout independiente.
- El motor de clasificación intenta cargar este backend y hace fallback automático al 1.1.
