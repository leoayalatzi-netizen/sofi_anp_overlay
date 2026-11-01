# Nevula 1.4 — Salto evolutivo semántico + neuronal

## Cambios principales

1. **Modelo del mundo**: nuevo `nucleo/semantica/modelo_mundo.py` que convierte relaciones declaradas en los datos en un grafo con fuente y estado `extraida`.
2. **Núcleo semántico**: recuperación híbrida TF-IDF + n-gramas + coincidencia conceptual, con índice local de 700+ documentos.
3. **Estado cognitivo**: `EstadoCognitivo` mantiene objetivo, hipótesis, evidencia, contradicciones, decisiones e incertidumbre.
4. **Síntesis fundamentada**: el motor de síntesis deja de elegir plantillas al azar como vía principal y responde desde evidencia recuperada.
5. **Pensamiento autónomo**: las conexiones espontáneas se generan desde conceptos/relaciones reales de la biblioteca y se expresan como hipótesis verificables.
6. **Router neuronal 1.4 grande**: MLP `900 → 1024 → 512 → 256 → 5`, 1,580,037 parámetros.
7. **Entrenamiento**: 3,254 ejemplos efectivos para el router, incluyendo consultas naturales generadas a partir del corpus original.
8. **Integración**: el cerebro conversacional prioriza el router 1.4 y conserva especialistas 1.3 como segunda etapa.
9. **Corrección de intención**: el cerebro ahora lee correctamente `intencion_principal.categoria` y su confianza.
10. **Motor neuronal**: BatchNorm ya no actualiza gamma/beta con una tasa fija oculta; sus gradientes pasan por AdamW. Se añadieron derivadas para LeakyReLU, Swish, GELU y Mish y se corrigió la escala de gradiente de las pérdidas.

## Evaluación independiente

- Router de grupo 1.3: **82.04%** en holdout independiente de 323 ejemplos.
- Router de grupo 1.4: **97.52%** en el mismo holdout.
- Mejora absoluta: **+15.48 puntos porcentuales**.
- Mejora relativa: **~18.9%**.
- Pipeline conversacional 1.4 (router + especialistas + prior semántico): **99.07%** en el mismo holdout para dominio final.

La cifra de 80% solicitada no se presenta como una mejora de precisión: no sería científicamente correcto prometerla. El salto estructural de la red es superior al 80% en parámetros respecto al router 1.3 (1.58 M frente a ~707 k; **+123%**), mientras que la precisión del router mejoró de forma medible y reproducible.

## Nota sobre “cuántica”

Esta versión no se presenta como computación cuántica física. La arquitectura conserva el nombre experimental, pero la capa nueva es clásica y probabilística. Si se incorpora una capa quantum-like en el futuro, deberá especificar formalmente su representación matemática y distinguirla de hardware/cómputo cuántico real.
