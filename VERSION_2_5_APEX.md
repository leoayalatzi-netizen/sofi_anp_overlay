# ANP Nevula 2.5 APEX

La 2.5 cambia la arquitectura de Nevula de un conjunto de motores coordinados parcialmente a un ciclo cognitivo explícito:

**percepción → planificación → memoria → herramientas → evidencia → síntesis → verificación → reparación → aprendizaje**.

## Salto principal
- Orquestador APEX con trazas de ejecución.
- Memoria jerárquica: trabajo, episódica, semántica y procedural.
- Verificador independiente con compuertas de relevancia, evidencia, coherencia y comprobación numérica.
- Reparación automática de respuestas rechazadas.
- Índice de conocimiento con coincidencia por tokens para evitar falsos matches por subcadenas.
- Rutas deterministas para cálculo, causalidad/correlación, memoria y manejo de evidencia insuficiente.
- Currículo APEX para planificación, herramientas, memoria, auto-verificación y razonamiento.
- Checkpoint móvil APEX continuado desde OMEGA.

## Entrenamiento real
El modelo APEX conserva la arquitectura compacta de OMEGA (3,233,472 parámetros) para mantener la posibilidad de ejecución local. Se continuó el entrenamiento sobre el corpus APEX durante 300 pasos adicionales. La mejor pérdida de validación observada fue **3.3098**, con **PPL 27.38**, frente a la mejor validación registrada por OMEGA de **3.7973 / PPL 44.58**.

Estos números son métricas internas del entrenamiento y no equivalen a un benchmark externo de modelos comerciales.
