from __future__ import annotations
import re, sqlite3, time, math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

class MemoriaJerarquica:
    """Memoria en cuatro capas: trabajo, episódica, semántica y procedural.

    La capa de trabajo vive en RAM; las otras tres son persistentes. Solo se
    almacenan datos entregados explícitamente o resultados generados por el
    propio sistema con fuente/confianza trazables.
    """
    VERSION = "2.5-APEX-memory"
    CAPAS = ("episodica", "semantica", "procedural")

    def __init__(self, path: Path, working_max: int = 32, max_items: int = 12000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_items = int(max_items)
        self.working: List[Dict[str, Any]] = []
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capa TEXT NOT NULL,
                tipo TEXT NOT NULL,
                clave TEXT NOT NULL,
                valor TEXT NOT NULL,
                peso REAL DEFAULT 1.0,
                confianza REAL DEFAULT 0.5,
                fuente TEXT DEFAULT 'sistema',
                tags TEXT DEFAULT '',
                ts REAL NOT NULL
            )"""
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_memoria_clave ON memoria(clave)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_memoria_capa ON memoria(capa)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_memoria_ts ON memoria(ts)")
        self.db.commit()
        self._migrar_memoria_antigua()
        self.working_max = int(working_max)

    def _norm(self, s: Any) -> str:
        return re.sub(r"\s+", " ", str(s)).strip()

    def _tokens(self, s: str) -> set[str]:
        return set(re.findall(r"[a-záéíóúüñ0-9]{3,}", s.lower()))

    def _migrar_memoria_antigua(self) -> None:
        """Importa recuerdos de la tabla 2.4 una sola vez, sin borrarlos."""
        try:
            cols = {r[1] for r in self.db.execute("PRAGMA table_info(recuerdos)").fetchall()}
            if not {"tipo", "clave", "valor"}.issubset(cols):
                return
            old_count = self.db.execute("SELECT COUNT(*) FROM memoria").fetchone()[0]
            if old_count:
                return
            rows = self.db.execute("SELECT tipo,clave,valor,peso,fuente,ts FROM recuerdos ORDER BY ts DESC LIMIT 3000").fetchall()
            for tipo, clave, valor, peso, fuente, ts in rows:
                self.guardar("episodica", tipo or "recuerdo", clave, valor, fuente or "migracion", float(peso or 1.0), 0.7, ts=ts)
        except Exception:
            return

    def guardar(self, capa: str, tipo: str, clave: str, valor: str, fuente: str = "sistema",
                peso: float = 1.0, confianza: float = 0.5, tags: str = "", ts: Optional[float] = None) -> bool:
        capa = str(capa).lower()
        if capa not in self.CAPAS:
            raise ValueError(f"capa de memoria inválida: {capa}")
        clave = self._norm(clave).lower()
        valor = self._norm(valor)
        if not clave or not valor:
            return False
        try:
            existing = self.db.execute(
                "SELECT id,peso,confianza FROM memoria WHERE capa=? AND clave=? AND valor=? LIMIT 1",
                (capa, clave, valor),
            ).fetchone()
            now = float(ts or time.time())
            if existing:
                new_weight = min(4.0, max(float(existing[1]), float(peso)) + 0.05)
                new_conf = max(float(existing[2]), float(confianza))
                self.db.execute("UPDATE memoria SET peso=?,confianza=?,ts=?,fuente=?,tags=? WHERE id=?",
                                (new_weight, new_conf, now, fuente, tags, existing[0]))
            else:
                self.db.execute(
                    "INSERT INTO memoria(capa,tipo,clave,valor,peso,confianza,fuente,tags,ts) VALUES(?,?,?,?,?,?,?,?,?)",
                    (capa, tipo, clave, valor, float(peso), float(confianza), fuente, tags, now),
                )
            self.db.commit()
            self._purgar()
            return True
        except Exception:
            return False

    def trabajar(self, tipo: str, contenido: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self.working.append({"tipo": tipo, "contenido": contenido, "meta": meta or {}, "ts": time.time()})
        if len(self.working) > self.working_max:
            del self.working[: len(self.working) - self.working_max]

    def trabajar_contexto(self) -> str:
        return "\n".join(f"[{x['tipo']}] {x['contenido']}" for x in self.working[-8:])

    def recordar(self, consulta: str, capas: Optional[List[str]] = None, k: int = 8) -> List[Dict[str, Any]]:
        capas = capas or list(self.CAPAS)
        tokens = self._tokens(consulta)
        if not tokens:
            return []
        placeholders = ",".join("?" for _ in capas)
        params = list(capas)
        try:
            rows = self.db.execute(
                f"SELECT id,capa,tipo,clave,valor,peso,confianza,fuente,tags,ts FROM memoria WHERE capa IN ({placeholders}) ORDER BY ts DESC LIMIT 3000",
                params,
            ).fetchall()
        except Exception:
            return []
        now = time.time()
        scored = []
        for row in rows:
            _id, capa, tipo, clave, valor, peso, confianza, fuente, tags, ts = row
            words = self._tokens(f"{clave} {valor} {tags}")
            overlap = len(tokens & words)
            if overlap <= 0:
                continue
            jaccard = overlap / max(1, len(tokens | words))
            recency = 1.0 / (1.0 + (now - float(ts or now)) / 86400.0)
            score = 0.50 * jaccard + 0.20 * min(1.0, float(confianza)) + 0.15 * min(1.0, float(peso) / 2.0) + 0.15 * recency
            scored.append((score, {
                "id": _id, "capa": capa, "tipo": tipo, "clave": clave,
                "valor": valor, "peso": float(peso), "confianza": float(confianza),
                "fuente": fuente, "tags": tags, "ts": float(ts), "score": round(score, 4)
            }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:k]]

    def contexto(self, consulta: str, k: int = 8) -> str:
        rows = self.recordar(consulta, k=k)
        return "\n".join(f"[{r['capa']}/{r['tipo']}] {r['clave']}: {r['valor']}" for r in rows)

    def aprender_explicito(self, texto: str) -> int:
        patterns = [
            ("preferencia", r"\b(?:prefiero|me gusta|me gustan|prefiero que)\s+(.+)"),
            ("nombre", r"\b(?:me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,50})"),
            ("objetivo", r"\b(?:mi objetivo es|quiero lograr|quiero conseguir)\s+(.+)")
        ]
        n = 0
        for tipo, pat in patterns:
            m = re.search(pat, texto, re.IGNORECASE)
            if m:
                val = self._norm(m.group(1).strip(" .,!"))
                if val and self.guardar("semantica", tipo, tipo, val, "usuario", 1.5, 0.95):
                    n += 1
        return n

    def registrar_episodio(self, clave: str, valor: str, fuente: str = "sistema", confianza: float = 0.6) -> bool:
        return self.guardar("episodica", "episodio", clave, valor, fuente, 0.7, confianza)

    def registrar_semantica(self, clave: str, valor: str, fuente: str = "usuario", confianza: float = 0.9) -> bool:
        return self.guardar("semantica", "hecho", clave, valor, fuente, 1.2, confianza)

    def registrar_procedimiento(self, clave: str, valor: str, fuente: str = "sistema", confianza: float = 0.8) -> bool:
        return self.guardar("procedural", "procedimiento", clave, valor, fuente, 1.0, confianza)

    def total(self, capa: Optional[str] = None) -> int:
        if capa:
            return int(self.db.execute("SELECT COUNT(*) FROM memoria WHERE capa=?", (capa,)).fetchone()[0])
        return int(self.db.execute("SELECT COUNT(*) FROM memoria").fetchone()[0])

    def estadisticas(self) -> Dict[str, int]:
        out = {c: self.total(c) for c in self.CAPAS}
        out["trabajo"] = len(self.working)
        return out

    def _purgar(self) -> None:
        self.db.execute(
            "DELETE FROM memoria WHERE id NOT IN (SELECT id FROM memoria ORDER BY ts DESC LIMIT ?)",
            (self.max_items,),
        )
        self.db.commit()
