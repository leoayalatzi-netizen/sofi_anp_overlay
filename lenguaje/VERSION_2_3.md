# Nevula 2.3 — Universal Cognitive Runtime

2.3 mejora 2.2 en arquitectura de ejecución y calidad de respuesta.

- Backend selector: PyTorch → ONNX → NumPy portable → fallback.
- Recuperación local RAG ligera sin sklearn.
- Guardas de calidad lingüística.
- Exportador ONNX opcional para Android/native.
- El checkpoint bootstrap incluido sigue siendo el modelo entrenado de 2.1/2.2; 2.3 no afirma un preentrenamiento masivo inexistente.
- Se incorpora una ruta de entrenamiento evolutiva para modelos mayores.
