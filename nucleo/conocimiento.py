
#!/usr/bin/env python3
"""Módulo de acceso a la base de conocimiento ANP"""
import sqlite3, json, re, random
from pathlib import Path
from typing import Optional, List, Dict, Any

BASE = Path(__file__).parent.parent
ALMACEN = BASE / "almacenamiento"
DB_PATH = ALMACEN / "conocimiento.db"

class BaseConocimiento:
    """Acceso unificado a toda la base de conocimiento de ANP"""
    
    def __init__(self):
        self.db = DB_PATH
    
    def buscar_concepto(self, palabra: str) -> Optional[Dict]:
        """Busca un concepto en la base de datos"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT * FROM conceptos WHERE nombre LIKE ? OR definicion LIKE ?", 
                     (f"%{palabra}%", f"%{palabra}%"))
            row = c.fetchone()
            conn.close()
            if row:
                return {"nombre": row[1], "definicion": row[2], "categoria": row[3], "ejemplos": row[4]}
            return None
        except:
            return None
    
    def buscar_hecho(self, tema: str) -> Optional[str]:
        """Busca un hecho sobre un tema"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT hecho FROM hechos WHERE tema LIKE ? ORDER BY confianza DESC LIMIT 1", 
                     (f"%{tema}%",))
            row = c.fetchone()
            conn.close()
            return row[0] if row else None
        except:
            return None
    
    def buscar_regla(self, texto: str) -> Optional[str]:
        """Busca una regla de respuesta que coincida con el texto"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT patron, respuesta FROM reglas ORDER BY prioridad")
            for patron, respuesta in c.fetchall():
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    # Reemplazar grupos en la respuesta
                    for i, group in enumerate(match.groups(), 1):
                        respuesta = respuesta.replace(f"{{{i}}}", group)
                    # También reemplazar nombres detectados
                    nombre_match = re.search(r"(?:me llamo|soy|mi nombre es)\s+(\w+)", texto, re.IGNORECASE)
                    if nombre_match:
                        respuesta = respuesta.replace("{nombre}", nombre_match.group(1).capitalize())
                    conn.close()
                    return respuesta
            conn.close()
            return None
        except:
            return None
    
    def buscar_similares(self, palabra: str) -> List[str]:
        """Busca sinónimos en datos semánticos"""
        try:
            with open(ALMACEN / "semantica" / "datos_semanticos.json", 'r') as f:
                datos = json.load(f)
            return datos.get("sinonimos", {}).get(palabra.lower(), [])
        except:
            return []
    
    def calcular(self, expresion: str) -> Optional[str]:
        """Evalúa una expresión matemática simple"""
        try:
            # Limpiar expresión
            expr = expresion.replace('+', ' + ').replace('-', ' - ').replace('*', ' * ').replace('/', ' / ')
            # Evaluar de forma segura (solo números y operadores básicos)
            if re.match(r'^[\d\s\+\-\*\/\.\(\)]+$', expr):
                resultado = eval(expr)
                return f"{expresion.strip()} = {resultado}"
            return None
        except:
            return None
    
    def obtener_contexto_conversacion(self, ultimas: int = 3) -> str:
        """Obtiene el contexto de conversaciones recientes"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT usuario, respuesta FROM conversaciones ORDER BY id DESC LIMIT ?", (ultimas,))
            rows = c.fetchall()
            conn.close()
            if rows:
                return " | ".join([f"U:{r[0][:50]} R:{r[1][:50]}" for r in reversed(rows)])
            return ""
        except:
            return ""
    
    def guardar_conversacion(self, usuario: str, respuesta: str, intencion: str = "", sentimiento: str = ""):
        """Guarda una interacción en la base de datos"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("INSERT INTO conversaciones VALUES (NULL, datetime('now'), ?, ?, ?, ?)",
                     (usuario, respuesta, intencion, sentimiento))
            conn.commit()
            conn.close()
        except:
            pass

# Instancia global
conocimiento = BaseConocimiento()
