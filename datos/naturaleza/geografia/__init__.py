#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Biblioteca de datos ANP - naturaleza / geografia
Datos curados para alimentar el conocimiento de ANP Nevula v0.0.1
"""
from pathlib import Path
import json

def cargar_datos(nombre_archivo):
    """Carga un archivo JSON de esta carpeta"""
    ruta = Path(__file__).parent / nombre_archivo
    if ruta.exists():
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def listar_archivos():
    """Lista todos los archivos JSON en esta carpeta"""
    return [f.name for f in Path(__file__).parent.glob("*.json")]
