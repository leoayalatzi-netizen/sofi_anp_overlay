# Nevula 2.2 — Instalación multiplataforma

## PC / Linux / Windows
Instala las dependencias del Language Core:
```bash
pip install -r requirements-lenguaje.txt
```
Aquí se recomienda PyTorch para entrenamiento e inferencia.

## Android / Pydroid 3
No dependas de `pip install torch`: si no existe una rueda compatible con tu combinación Android/ARM64/Python, Nevula 2.2 **no se detiene**.

El paquete ya contiene el backend `NumPy Portable`. Instala NumPy en Pydroid si está disponible para tu versión de Python y ejecuta:
```bash
python principal.py
```
Nevula intentará usar, en orden:
1. PyTorch
2. NumPy Portable
3. Fallback Python

## Diagnóstico
Usa el comando:
```text
lenguaje
```
Debe mostrar `backend: torch`, `backend: numpy-portable` o `backend: fallback`.
