# ANP Nevula 1.2 — Informe de evolución

Se conserva íntegramente la base 1.1 y se añade una segunda generación neuronal sin destruir la anterior.

### Cambios
- Motor de representación híbrida.
- Dataset balanceado y aumentado: 1,617 → 4,570 ejemplos efectivos de entrenamiento.
- MLPs jerárquicos más robustos.
- Entrenamiento con gradiente correctamente escalado para la CE en la ruta nueva.
- Holdout separado de 318 ejemplos.
- Backend 1.2 preferente con guardia automática de regresión hacia 1.1.
- API HTTP opcional sin dependencias externas.
- Auditoría técnica y documentación.

### Resultado observado
- Grupo: 64.85% en validación.
- Pipeline en holdout: 79.87%.
- Computación: 87.93%.
- Ciencias exactas: 88.46%.
- Sociedad: 82.46%.
- Cotidiano: 97.56%.
- Ocio: 93.55%.

Estas métricas miden clasificación de dominio; no equivalen a comprensión general ni a inteligencia general.
