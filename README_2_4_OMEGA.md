# Nevula 2.4 OMEGA

Esta versión introduce una ruta de evolución lingüístico-cognitiva entrenada y verificable.

### Uso rápido
```bash
python principal.py
```

Diagnóstico:
```text
lenguaje
```

Entrenamiento OMEGA reproducible:
```bash
python -m lenguaje.entrenar_omega_lite --steps 1800
```

Generación del corpus:
```bash
python -m lenguaje.corpus_omega
```

Benchmark:
```bash
python -m lenguaje.benchmark_24
```

### Backends
1. OMEGA + PyTorch cuando existe el checkpoint compatible.
2. PyTorch Nevula 2.3.x como respaldo.
3. NumPy portable heredado.
4. Fallback Python.

En Android/Pydroid 3, PyTorch puede no estar disponible; en ese caso Nevula conserva el backend portátil anterior. El checkpoint OMEGA se entrega listo para equipos Python/PyTorch compatibles.
