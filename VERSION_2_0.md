# Nevula 2.0 — Language-Cognitive Evolution

## Salto implementado
1. **Language Core** independiente del resto de motores.
2. **BPE/SentencePiece** para representación subléxica.
3. **Decoder Transformer causal** escalable.
4. **Generación autoregresiva** con temperatura, top-p y penalización de repetición.
5. **Semantic Core** integrado con recuperación híbrida y 773 documentos locales.
6. **World Model** y Cognitive State siguen siendo capas externas al lenguaje.
7. **Generador lingüístico híbrido**: la salida neuronal no puede degradar una respuesta respaldada por evidencia.
8. **Ingesta web con caché**: el sistema puede adquirir fuentes cuando hay Internet y continuar offline con el corpus almacenado.
9. **Pipeline de entrenamiento** reproducible.
10. **Presets escalables** hasta arquitecturas de muchos cientos de millones/miles de millones de parámetros, condicionadas al hardware.

## Entrenamiento incluido
El checkpoint distribuido es un **bootstrap real entrenado localmente** sobre el corpus disponible del proyecto. No se afirma que sea comparable a un LLM comercial: el corpus local todavía es demasiado pequeño para ese objetivo.

El diseño permite repetir el entrenamiento después de poblar `almacenamiento/web_corpus/raw/` mediante `lenguaje/ingesta_web.py` o `lenguaje/pipeline.py`.

## Principio online/offline
- **Online:** adquisición explícita de URLs y almacenamiento en caché.
- **Offline:** inferencia, recuperación semántica y entrenamiento sobre el material local ya adquirido.
- La ejecución no depende de Internet.
