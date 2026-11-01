# API Nevula 1.3

## Arranque
`python api/server.py`

Variables:
- `NEVULA_HOST` (por defecto 127.0.0.1)
- `NEVULA_PORT` (por defecto 8080)
- `NEVULA_LLM_URL` opcional: endpoint base compatible con `/chat/completions`
- `NEVULA_LLM_API_KEY` opcional
- `NEVULA_LLM_MODEL` opcional

## Endpoints
- GET `/health`
- GET `/info`
- GET `/v1/models`
- GET `/v1/memory?session_id=...`
- POST `/chat` con `{"texto":"...", "session_id":"...", "generativo":true}`
- POST `/predict` con `{"texto":"..."}`
- POST `/v1/chat/completions` con formato OpenAI-compatible y `session_id` opcional.

El estado conversacional se guarda en `almacenamiento/conversaciones/` para poder recuperar una sesión después de reiniciar el proceso.
