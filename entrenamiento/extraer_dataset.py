#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae un dataset etiquetado (texto -> dominio) a partir de la biblioteca de
conocimiento JSON en datos/. Cada carpeta de primer nivel dentro de datos/
es una clase de dominio (ciencia, tecnologia, cultura, etc.). Se descarta
'anp_interno' porque no es un dominio de conocimiento consultable.
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
DATOS = BASE / "datos"
CAMPOS_TEXTO = [
    "definicion", "descripcion", "ejemplo", "titulo",
    "significado", "frase", "cita", "pregunta", "respuesta",
    "animal", "emocion", "corriente", "sesgo", "sistema", "organo", "evento",
    "personaje", "genero", "obra", "curiosidad", "dato", "texto",
]
# Nota: "concepto"/"nombre"/"palabra" y similares se excluyen como texto
# EXTRA por separado (son slugs o etiquetas cortas de 1-4 palabras, casi
# sin contenido semántico por sí solos: "Tabla hash (hash map)" aporta
# poca señal como fila de entrenamiento aislada). Sí se usan combinados
# con la definición ("Tabla hash: estructura que asocia claves...") más
# abajo, que es donde de verdad ayudan al clasificador.
EXCLUIR_DOMINIOS = {"anp_interno"}


def extraer_textos_de_item(item) -> list:
    """Devuelve fragmentos de texto útiles de un item (dict, str o list)."""
    textos = []
    if isinstance(item, str):
        if len(item) > 8:
            textos.append(item)
    elif isinstance(item, dict):
        for campo in CAMPOS_TEXTO:
            v = item.get(campo)
            if isinstance(v, str) and len(v) > 8:
                textos.append(v)
        # también combinaciones campo compuestas (ej: nombre + definicion)
        nombre = item.get("nombre") or item.get("concepto") or item.get("palabra")
        definicion = item.get("definicion") or item.get("descripcion") or item.get("significado")
        if nombre and definicion:
            textos.append(f"{nombre}: {definicion}")
    elif isinstance(item, list):
        for sub in item:
            textos.extend(extraer_textos_de_item(sub))
    return textos


def recolectar_json(ruta: Path) -> list:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return []
    contenedor = datos.get("datos", datos) if isinstance(datos, dict) else datos
    textos = []
    if isinstance(contenedor, list):
        for item in contenedor:
            textos.extend(extraer_textos_de_item(item))
    elif isinstance(contenedor, dict):
        for v in contenedor.values():
            textos.extend(extraer_textos_de_item(v))
    return textos


def limpiar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def construir_dataset(min_len_palabras: int = 3):
    ejemplos = []  # (texto, dominio)
    dominios = sorted([d.name for d in DATOS.iterdir() if d.is_dir() and d.name not in EXCLUIR_DOMINIOS])
    for dominio_dir in DATOS.iterdir():
        if not dominio_dir.is_dir() or dominio_dir.name in EXCLUIR_DOMINIOS:
            continue
        dominio = dominio_dir.name
        for jf in dominio_dir.rglob("*.json"):
            for t in recolectar_json(jf):
                t = limpiar(t)
                if len(t.split()) >= min_len_palabras:
                    ejemplos.append((t, dominio))
    return ejemplos, dominios


if __name__ == "__main__":
    ejemplos, dominios = construir_dataset()
    print(f"Dominios ({len(dominios)}): {dominios}")
    print(f"Total ejemplos extraídos: {len(ejemplos)}")
    from collections import Counter
    conteo = Counter(d for _, d in ejemplos)
    for dom in dominios:
        print(f"  {dom}: {conteo.get(dom, 0)}")
    out = BASE / "entrenamiento" / "dataset_dominios.json"
    out.write_text(json.dumps({"dominios": dominios, "ejemplos": ejemplos}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Guardado en {out}")
