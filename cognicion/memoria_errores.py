#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Memoria de Errores
# =====================================================================
# Guarda cada vez que el VerificadorRespuesta rechaza una respuesta:
# pregunta, dominio detectado, respuesta descartada, confianza y motivo.
# Esta tabla es la materia prima para un futuro pipeline de aprendizaje
# (reentrenar el clasificador de dominio, ajustar el planificador, etc.)
# pero ese pipeline en sí (ETAPA 6 del plan completo) no forma parte de
# este cambio: aquí solo se recolecta la experiencia.
# =====================================================================
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class GestorMemoriaErrores:
    def __init__(self, base_dir: Path):
        self.db = Path(base_dir) / "almacenamiento" / "cerebro_anp.db"
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute('''CREATE TABLE IF NOT EXISTS errores_experiencia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, pregunta TEXT, dominio TEXT,
                intencion TEXT, respuesta TEXT, confianza REAL, motivo TEXT
            )''')
            conn.commit()
            conn.close()
        except Exception:
            pass

    def registrar(self, pregunta: str, dominio: Optional[str], intencion: str,
                   respuesta: str, confianza: float, motivo: str):
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute(
                "INSERT INTO errores_experiencia VALUES (NULL, datetime('now'), ?, ?, ?, ?, ?, ?)",
                (pregunta[:300], dominio or "desconocido", intencion, respuesta[:300], confianza, motivo),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def registrar_experiencia(self, dominio: Optional[str], intencion: str, aprobado: bool,
                               confianza: float, texto: str = ""):
        """Registra TODO intento (aprobado o no), a diferencia de `registrar`
        que solo guarda los rechazados. Esta tabla alimenta dos cosas:
        ModeloCapacidades (tasa de aprobación por dominio) y, cuando
        aprobado=True con confianza alta, el pipeline de aprendizaje puede
        usar (texto, dominio) como ejemplo adicional para reentrenar el
        clasificador de dominio (auto-entrenamiento semi-supervisado:
        ver aprendizaje/colector_experiencias.py)."""
        try:
            conn = sqlite3.connect(str(self.db))
            conn.execute('''CREATE TABLE IF NOT EXISTS experiencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
                dominio TEXT, intencion TEXT, aprobado INTEGER, confianza REAL, texto TEXT
            )''')
            cols = [r[1] for r in conn.execute("PRAGMA table_info(experiencias)")]
            if "texto" not in cols:
                conn.execute("ALTER TABLE experiencias ADD COLUMN texto TEXT DEFAULT ''")
            conn.execute("INSERT INTO experiencias VALUES (NULL, datetime('now'), ?, ?, ?, ?, ?)",
                         (dominio or "desconocido", intencion, 1 if aprobado else 0, confianza, texto[:300]))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def experiencias_aprobadas(self, min_confianza: float = 0.65):
        """Pares (texto, dominio) de intentos que el verificador aprobó con
        buena confianza. Materia prima para reentrenar el clasificador."""
        try:
            conn = sqlite3.connect(str(self.db))
            cols = [r[1] for r in conn.execute("PRAGMA table_info(experiencias)")]
            if "texto" not in cols:
                conn.close()
                return []
            c = conn.cursor()
            c.execute("SELECT texto, dominio FROM experiencias WHERE aprobado=1 AND confianza>=? "
                      "AND dominio != 'desconocido' AND texto != ''", (min_confianza,))
            filas = c.fetchall()
            conn.close()
            return [(t, d) for t, d in filas if t]
        except Exception:
            return []

    def perfil_dominios(self) -> Dict[str, Dict[str, float]]:
        """Tasa de aprobación del verificador por dominio: la aproximación
        más honesta que tenemos hoy a un 'ModeloDeCapacidades' -- no son
        benchmarks externos, son los propios intentos reales de Nevula."""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT dominio, COUNT(*), SUM(aprobado), AVG(confianza) FROM experiencias GROUP BY dominio")
            filas = c.fetchall()
            conn.close()
            return {d: {"intentos": n, "aprobados": ap or 0, "tasa": (ap or 0) / n, "confianza_media": round(conf or 0, 3)}
                    for d, n, ap, conf in filas}
        except Exception:
            return {}

    def recientes(self, n: int = 10) -> List[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT timestamp, pregunta, dominio, confianza, motivo FROM errores_experiencia "
                      "ORDER BY id DESC LIMIT ?", (n,))
            filas = c.fetchall()
            conn.close()
            return [{"timestamp": f[0], "pregunta": f[1], "dominio": f[2], "confianza": f[3], "motivo": f[4]} for f in filas]
        except Exception:
            return []

    def total(self) -> int:
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM errores_experiencia")
            n = c.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0

    def dominios_debiles(self, n: int = 5) -> List[Dict[str, Any]]:
        """Dominios donde más veces falló la verificación: pista de dónde
        el sistema necesita más datos o mejores motores."""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT dominio, COUNT(*) as n FROM errores_experiencia "
                      "GROUP BY dominio ORDER BY n DESC LIMIT ?", (n,))
            filas = c.fetchall()
            conn.close()
            return [{"dominio": f[0], "fallos": f[1]} for f in filas]
        except Exception:
            return []
