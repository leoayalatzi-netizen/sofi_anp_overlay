# ANP Nevula 1.3 — Auditoría y evolución

## Principio
Nevula 1.3 es una evolución aditiva de 1.2. No se eliminan los módulos históricos ni los modelos 1.2.

## Evoluciones
- Cerebro conversacional multi-turno (`evolucion/cerebro_conversacional.py`).
- Memoria de sesión persistente y resumen automático.
- Resolución contextual de referencias: esto/eso/lo anterior/ese modelo/esa versión.
- Seguimiento de tema, entidades y hechos explícitos.
- Clasificación de intención heredada y clasificación neuronal de dominio.
- Modelos de clasificación afinados en `evolucionado_v13`.
- Dataset masivo reproducible y segunda pasada de fine-tuning.
- API nueva, conservando `api/server_legacy_v12.py`.
- API compatible con envoltorio OpenAI `/v1/chat/completions`.
- Adaptador opcional a un proveedor LLM compatible mediante variables de entorno.
- `/v1/memory` para inspección de una sesión.
- `/v1/models` para descubrimiento del modelo.

## Entrenamiento
La pasada 1.2 utilizó 4,570 ejemplos efectivos y un holdout independiente de 318 ejemplos.
La 1.3 conserva esos modelos y ejecuta una pasada adicional de fine-tuning sobre el conjunto balanceado/aumentado.
Se incluye además un clasificador neuronal experimental de intención (`clasificador_intencion.anp`); quedó deliberadamente fuera del camino crítico porque su holdout sintético no justificó reemplazar el motor de intención existente.

## Limitaciones honestas
Esta arquitectura no se convierte mágicamente en un LLM sólo por aumentar la red. La generación lingüística profunda está desacoplada y puede conectarse a un proveedor LLM mediante `NEVULA_LLM_URL`. Sin ese proveedor, Nevula conserva un modo local determinista/contextual.

## Compatibilidad
Los modelos 1.2 siguen en `almacenamiento/modelos/evolucionado`.
Los candidatos 1.3 están en `almacenamiento/modelos/evolucionado_v13`.
