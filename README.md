# ANP Nevula 2.5 APEX — evolución desde OMEGA

# ANP — Arquitectura Neuronal Profunda
## Nevula V3.1 — Pensamiento Emergente Real

Sistema de IA con 27 motores en 6 núcleos, memoria real, detector de patrones, 
pensamiento autónomo emergente y biblioteca de conocimiento.

### Mejoras realizadas (entrenado y conectado por Grok)

- **Cargador de motores robusto**: Carga 27 motores reales de `nucleos/` sin hangs.
- **Conexión completa**: Motores de comunicación, razonamiento, memoria, creatividad, resolución y búsqueda conectados al coordinador central.
- **Pensamiento emergente V3**: Detector de patrones, vacíos de conocimiento y contradicciones basado en memoria SQLite real.
- **Interfaz amigable**:
  - Consola mejorada con comandos claros.
  - **Interfaz web moderna** (solo stdlib): `python principal.py --web`
- **Biblioteca de datos**: 23 fuentes JSON de conocimiento (ciencia, tech, humanidad, etc.).
- **Ciclo autónomo**: Pensamientos que emergen de la memoria de conversaciones, no de plantillas aleatorias.
- Corrección de rutas (espacio en `contexto`), limpieza de pycache, DB lista.

### Cómo ejecutar

```bash
cd ANP
python3 principal.py          # Consola amigable
python3 principal.py --web    # Interfaz web en http://localhost:8080
python3 principal.py --web --puerto 9000
```

### Comandos en consola

- `pensamientos` — ver pensamientos autónomos generados
- `objetivos` — objetivos activos
- `estadisticas` — métricas
- `ayuda` — ayuda
- `salir` — apagar

### Arquitectura

- `principal.py` — núcleo principal + coordinador + pensamiento V3 + interfaces
- `nucleos/` — 6 núcleos con motores especializados (27 motores activos)
- `pensamiento/` — generador, reflexión, objetivos, curiosidad, ciclo autónomo
- `datos/` — conocimiento estructurado en JSON
- `almacenamiento/` — DB SQLite de memoria + embeddings + registros
- `nucleo/` — componentes de soporte (bus de eventos, orquestador, etc.)

### Entrenamiento personal

El modelo ha sido "entrenado" mejorando:
1. Robustez de carga de motores
2. Calidad del ciclo de pensamiento emergente
3. Interfaz de usuario
4. Integración de la biblioteca de conocimiento
5. Fallbacks y resiliencia

Los pensamientos ya no son aleatorios: emergen de patrones detectados en la memoria real de conversaciones.

¡Disfruta explorando con ANP!

## Nevula 1.4 — Evolución semántica

La 1.4 añade un núcleo semántico local, un modelo de mundo relacional, estado cognitivo explícito y síntesis fundamentada. El router neuronal 1.4 grande usa `900→1024→512→256→5` y se entrena con consultas naturales derivadas del corpus.

Los modelos 1.3 se conservan para compatibilidad y como especialistas de segunda etapa. Los nuevos artefactos están en `almacenamiento/modelos/evolucionado_v14`.
