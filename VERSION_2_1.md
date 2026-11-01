# Nevula 2.1 — Language Focus

## Objetivo
El salto 2.1 cambia el centro de gravedad de Nevula: **el lenguaje deja de ser sólo una capa de presentación y pasa a ser un subsistema entrenable con memoria conversacional, corpus, tokenizer, preentrenamiento y generación.**

### Implementado
1. **Language Core 2.1**: Transformer causal configurable y runtime tolerante a ausencia de PyTorch.
2. **Memoria dialogal**: conserva turnos recientes, tema y contexto separado de la evidencia factual.
3. **Entrenamiento reanudable**: checkpoints periódicos, gradient accumulation, AMP CUDA, warm-up, clipping, perplexity y tokens vistos.
4. **Corpus 2.1**: deduplicación, limpieza y manifest con hash/procedencia; integra conocimiento local, conversaciones y web cacheada.
5. **Curriculum**: separa diálogo, conocimiento, razonamiento y textos largos.
6. **Internet controlado**: URLs explícitas, cache local y comprobación de robots.txt; todo puede reconstruirse offline.
7. **Fallback lingüístico**: si el equipo de ejecución no tiene PyTorch, Nevula no declara muerto el lenguaje; usa un generador n-gram mínimo mientras conserva la ruta cognitiva/semántica.
8. **Integración**: las respuestas aceptadas y recuperadas alimentan la memoria de trabajo lingüística.

## Qué NO se afirma
El checkpoint bootstrap incluido sigue siendo pequeño y fue entrenado con un corpus local reducido. No es comparable a un LLM de frontera. La infraestructura para crecer está preparada; la calidad de conversación crecerá al entrenar con muchos más tokens y realizar instruction tuning/dialogue tuning.

## Ruta de escalado
- **2.1-A**: corpus de millones de documentos/tokens, validación y filtros de calidad.
- **2.1-B**: preentrenamiento continuo con reanudación y evaluación de perplexity.
- **2.1-C**: SFT de instrucciones y diálogo multivuelta.
- **2.1-D**: preferencias, rechazo de alucinaciones y evaluación automática/humana.
- **2.1-E**: contexto largo + recuperación semántica + herramientas sin romper la identidad conversacional.

El sistema sigue siendo offline-first: Internet es una fuente opcional de datos, no una dependencia de ejecución.
