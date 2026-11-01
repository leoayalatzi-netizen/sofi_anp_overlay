# Nevula 2.5 APEX

## Qué cambia
Nevula 2.5 añade un coordinador cognitivo que utiliza el modelo neuronal como una herramienta dentro de un pipeline verificable. El objetivo es reducir respuestas irrelevantes y convertir memoria, conocimiento, RAG, cálculo y generación en un único sistema.

### Pipeline
1. Analizar intención y complejidad.
2. Construir un plan de tareas.
3. Recuperar memoria jerárquica.
4. Ejecutar herramientas deterministas cuando corresponda.
5. Recuperar evidencia local.
6. Sintetizar una respuesta grounded o generar con APEX.
7. Verificar.
8. Reparar si falla.
9. Persistir solo resultados suficientemente fiables.

## Archivos principales
- `cognicion/orquestador_25.py`
- `cognicion/memoria_jerarquica.py`
- `cognicion/verificador_25.py`
- `lenguaje/corpus_apex.py`
- `lenguaje/entrenar_apex.py`
- `lenguaje/benchmark_25.py`
- `almacenamiento/modelos/lenguaje/apex_mobile/language_apex_mobile.pt`

## Uso
```bash
python -m lenguaje.benchmark_25
```

## Limitación honesta
APEX sigue siendo un modelo local pequeño. El gran salto de esta versión es sistémico: coordinación y verificación, no una afirmación de nivel frontera.
