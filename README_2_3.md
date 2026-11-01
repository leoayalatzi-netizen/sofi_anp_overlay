# ANP Nevula 2.3

Universal Cognitive Runtime. Nevula selecciona automáticamente PyTorch, ONNX, NumPy portable o fallback.

## Comandos
- `python principal.py`
- `python -m lenguaje.entrenar --help`
- `python -m lenguaje.exportar_onnx --help`
- `python -m lenguaje.exportar_portable --help`

## Android/Pydroid
La ruta NumPy no depende de PyTorch. Para una aplicación Android nativa se recomienda ONNX Runtime Android; el proyecto oficial ofrece AAR para Android y soporte ARM64. Para Pydroid, si no existe un wheel ORT compatible, Nevula conserva su backend NumPy.
