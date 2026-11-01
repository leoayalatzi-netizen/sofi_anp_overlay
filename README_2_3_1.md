# Nevula 2.3.1

## Filosofía
2.3.1 separa cuatro problemas que antes estaban demasiado mezclados: **generar**, **razonar**, **recordar** y **verificar**.

Pipeline:
`consulta → intención → memoria → recuperación → plan → generación → guarda lingüística → respuesta`

## Entrenamiento de evolución
```bash
python -m lenguaje.corpus_evolucion
python -m lenguaje.entrenar_evolucion --steps 10000 --batch 4 --grad-accum 8
```
En GPU puedes subir steps/batch. Para un salto real de calidad, el cuello de botella ya no es solamente el código: es el volumen y calidad del corpus y el cómputo de entrenamiento.

## Diagnóstico
```bash
python -m lenguaje.benchmark_231
```

## Android
El runtime NumPy de 2.3 permanece como camino Python/ARM. Para una aplicación Android nativa, el proyecto deja preparada la separación de modelo/runtime para usar ONNX Runtime Mobile/Android.
