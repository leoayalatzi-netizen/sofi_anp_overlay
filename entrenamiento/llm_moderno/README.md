# Nevula APEX — Modern LLM Upgrade

Este módulo añade un camino opcional de entrenamiento e inferencia con un modelo fundacional establecido. No borra ni reemplaza los componentes portables existentes de Nevula.

## Diseño

- **Base inicial:** `Qwen/Qwen3-8B` (aprox. 8.2B parámetros; licencia Apache 2.0 en el repositorio oficial).
- **Adaptación:** SFT (supervised fine-tuning) con LoRA/QLoRA. Los pesos generales del modelo base permanecen congelados y se guarda un adaptador para Nevula.
- **Datos:** ejemplos conversacionales curados, separados en entrenamiento y validación, deduplicados y reportados.
- **Evaluación:** comparación de respuestas base vs. adaptadas con un conjunto de prueba que no se usó para entrenar.
- **Integración:** `runtime_hf.py` expone una clase Python opcional. El runtime portátil original continúa disponible como fallback.

La técnica PEFT/LoRA entrena una pequeña cantidad de parámetros adicionales en lugar de actualizar todos los pesos del modelo, reduciendo sustancialmente la memoria necesaria. QLoRA cuantiza la base a 4 bits durante el ajuste. Referencias: [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B), [documentación PEFT/TRL](https://huggingface.co/docs/trl/main/en/peft_integration).

## Importante antes de entrenar

El corpus de Nevula puede incluir texto libre y ejemplos sintéticos repetidos. **No se debe asumir que millones de caracteres equivalen a un buen dataset de instrucciones.** El preparador solo transforma formatos reconocibles y elimina duplicados; no inventa pares pregunta/respuesta a partir de prosa sin estructura. Inspecciona `dataset_report.json` y las muestras antes de gastar recursos.

Para una adaptación de calidad, crea un conjunto grande y diverso de conversaciones correctas, con:

- preguntas y respuestas naturales en español, además de otros idiomas que Nevula deba manejar;
- razonamiento explicado de forma breve y verificable, matemáticas y código con respuestas comprobadas;
- uso correcto de herramientas, recuperación de información y reconocimiento de incertidumbre;
- conversaciones de varios turnos y casos donde la respuesta correcta es pedir aclaración;
- ejemplos negativos corregidos, sin duplicar variantes triviales;
- licencias y procedencia de datos documentadas.

Reserva un conjunto de evaluación independiente. No entrenes con él ni lo uses para seleccionar ejemplos durante el ajuste.

## Requisitos y hardware

1. Usa preferentemente Linux o WSL2 con una GPU NVIDIA compatible con CUDA. QLoRA de un modelo 8B puede requerir alrededor de 10–16 GB de VRAM o más, según longitud de contexto, versiones, lote y memoria adicional; no es una garantía. Más VRAM permite entrenar con secuencias/lotes mayores.
2. Instala PyTorch siguiendo las instrucciones adecuadas a tu versión de CUDA: <https://pytorch.org/get-started/locally/>.
3. Instala el resto de dependencias:

```bash
pip install -r entrenamiento/llm_moderno/requirements-llm.txt
```

En Windows nativo, `bitsandbytes`/CUDA puede ser menos sencillo; WSL2 o Linux suele ser una ruta más reproducible. En CPU, el entrenamiento de un 8B es normalmente impráctico.

## Flujo de trabajo

Ejecuta desde la raíz del repositorio.

### 1. Preparar el dataset conversacional

El script acepta JSONL, JSON y TXT/MD con las etiquetas `<|user|>` y `<|assistant|>`.

```bash
python entrenamiento/llm_moderno/preparar_datos.py \
  --input entrenamiento/llm_moderno/data/mi_dataset.jsonl \
  --out entrenamiento/llm_moderno/data/procesado
```

El JSONL debe contener un objeto por línea. Formato recomendado:

```json
{"messages":[{"role":"system","content":"Eres Nevula, un asistente preciso."},{"role":"user","content":"¿Qué es una variable en Python?"},{"role":"assistant","content":"Una variable es un nombre asociado a un valor..."}]}
```

También acepta `instruction`/`input`/`output`, `prompt`/`completion` o `question`/`answer`.

### 2. Revisar y entrenar

Inspecciona `dataset_report.json`, `train.jsonl` y `validation.jsonl`. Después:

```bash
python entrenamiento/llm_moderno/entrenar_sft.py \
  --train entrenamiento/llm_moderno/data/procesado/train.jsonl \
  --validation entrenamiento/llm_moderno/data/procesado/validation.jsonl \
  --model Qwen/Qwen3-8B \
  --out almacenamiento/modelos/nevula_qwen3_8b_lora \
  --epochs 2 --max-length 2048
```

El primer uso descargará los pesos del modelo base (varios GB). Los checkpoints y el adaptador ocupan espacio adicional. Para continuar desde un checkpoint del entrenador, añade `--resume`.

Para probar otra base compatible, cambia `--model`, verifica su licencia y asegúrate de que su arquitectura funcione con la versión instalada de Transformers/PEFT.

### 3. Conversar con Nevula

```bash
python entrenamiento/llm_moderno/chat_nevula.py \
  --adapter almacenamiento/modelos/nevula_qwen3_8b_lora
```

Para probar el modelo base sin el adaptador:

```bash
python entrenamiento/llm_moderno/chat_nevula.py --base-only
```

### 4. Comparar base y adaptador

Prepara un archivo JSONL de prueba con campos `prompt` y opcionalmente `reference`:

```json
{"prompt":"Explica la diferencia entre correlación y causalidad.","reference":"La correlación describe asociación; no demuestra por sí sola causalidad."}
```

Luego ejecuta:

```bash
python entrenamiento/llm_moderno/evaluar.py \
  --input entrenamiento/llm_moderno/data/evaluacion.jsonl \
  --adapter almacenamiento/modelos/nevula_qwen3_8b_lora \
  --out entrenamiento/llm_moderno/salidas/comparacion.jsonl
```

Evalúa las salidas a ciegas con criterios definidos: exactitud, cumplimiento de instrucciones, utilidad, seguridad, citas/evidencia y consistencia en turnos. La pérdida de validación es útil para detectar sobreajuste, pero no prueba por sí sola que el asistente sea mejor.

## Integración en Python

```python
from entrenamiento.llm_moderno.runtime_hf import NevulaHFBackend

llm = NevulaHFBackend(
    model_id="Qwen/Qwen3-8B",
    adapter_dir="almacenamiento/modelos/nevula_qwen3_8b_lora",
)
respuesta = llm.generate([
    {"role": "system", "content": "Eres Nevula APEX."},
    {"role": "user", "content": "Resume este texto: ..."},
])
print(respuesta)
```

## Hoja de ruta para mejorar más

1. Curar datos y crear evaluación fija.
2. Ejecutar SFT/QLoRA y comparar con la base.
3. Añadir recuperación RAG para conocimiento privado/actualizable en lugar de intentar memorizar todo en los pesos.
4. Recopilar pares de preferencias de alta calidad y probar DPO si existe suficiente señal fiable.
5. Evaluar llamadas a herramientas y flujos APEX en un entorno de pruebas antes de permitir acciones reales.
6. Considerar un modelo mayor o entrenamiento completo solo cuando haya datos, presupuesto computacional y evaluación que justifiquen ese coste.

**Este paquete prepara el pipeline; no incluye pesos de Qwen ni afirma haber entrenado un modelo.** El entrenamiento real requiere descargar la base, contar con hardware compatible y aportar datos de calidad.
