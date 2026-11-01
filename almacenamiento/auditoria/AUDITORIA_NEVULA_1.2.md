# Auditoría y evolución — Nevula 1.1 → 1.2

## Principio de conservación
No se eliminaron artefactos del proyecto original. Los modelos 1.1 y sus vocabularios permanecen en `almacenamiento/modelos/`. La evolución se añadió bajo `evolucion/`, `api/` y `almacenamiento/modelos/evolucionado/`.

## Hallazgos críticos
1. El clasificador 1.1 usa TF-IDF de palabras/bigramas, adecuado como baseline pero limitado ante variaciones morfológicas y ortográficas.
2. El motor 1.1 conserva pesos, pero su `.anp` no conserva estado completo de AdamW/scheduler para reanudación exacta.
3. La pérdida de entropía cruzada ya entrega el gradiente normalizado por lote y `compute_gradients()` vuelve a dividir por el tamaño del lote. La generación 1.2 compensa esto localmente durante entrenamiento sin cambiar el motor histórico.
4. BatchNorm actualiza gamma/beta con una ruta distinta al optimizador. La generación 1.2 no reescribe ese comportamiento histórico; los nuevos modelos se entrenan de forma compatible con el motor existente.
5. El holdout original podía solaparse con el split de entrenamiento porque se construía con otra semilla. La evaluación 1.2 conserva ese indicador histórico y además documenta un split estratificado separado para el entrenamiento.

## Evolución aplicada
- Vectorizador híbrido: palabras, bigramas y caracteres 3–5.
- Balanceo de clases.
- Aumento controlado por dropout de palabras.
- Arquitectura jerárquica de 2 etapas, 5 grupos.
- Red de grupo: 1400 features → 128 → 64 → 32 → 5.
- Redes especializadas: 1200 features → 128 → 64 → 32 → clases del grupo.
- AdamW, cosine LR, clipping y early stopping.
- Artefactos de modelo separados para poder comparar/promover sin destruir producción.
- API opcional con biblioteca estándar.

## Resultado del entrenamiento ejecutado
- Dataset original: 1,617 ejemplos.
- Train base: 1,378.
- Validación: 239.
- Train balanceado: 1,783.
- Train aumentado: 4,570.
- Precisión etapa 1: 64.85%.
- Holdout independiente: 79.87% (318 ejemplos).
- Especializados: computación 87.93%, ciencias exactas 88.46%, sociedad 82.46%, cotidiano 97.56%, ocio 93.55%.

La cifra de holdout es una medición experimental del clasificador de dominio, no una afirmación de capacidad general de razonamiento o comprensión lingüística.
