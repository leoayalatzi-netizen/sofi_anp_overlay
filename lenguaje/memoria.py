from __future__ import annotations
import json, re, sqlite3, time
from pathlib import Path
from collections import Counter

class MemoriaEpisodica:
    """Memoria persistente ligera: hechos declarados, preferencias y episodios.
    No inventa recuerdos: solo almacena lo que entra explícitamente por registrar()."""
    VERSION='2.4-OMEGA-memory'
    def __init__(self, path: Path, max_items=5000):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.max_items=max_items
        self.db=sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS recuerdos (id INTEGER PRIMARY KEY, tipo TEXT, clave TEXT, valor TEXT, peso REAL, ts REAL, fuente TEXT)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_recuerdos_clave ON recuerdos(clave)')
        self.db.commit()
    def registrar(self, tipo, clave, valor, fuente='dialogo', peso=1.0):
        clave=re.sub(r'\s+',' ',str(clave)).strip().lower(); valor=re.sub(r'\s+',' ',str(valor)).strip()
        if not clave or not valor: return False
        self.db.execute('INSERT INTO recuerdos(tipo,clave,valor,peso,ts,fuente) VALUES(?,?,?,?,?,?)',(tipo,clave,valor,float(peso),time.time(),fuente)); self.db.commit()
        self.db.execute('DELETE FROM recuerdos WHERE id NOT IN (SELECT id FROM recuerdos ORDER BY ts DESC LIMIT ?)',(self.max_items,)); self.db.commit(); return True
    def buscar(self, texto, k=6):
        words=set(re.findall(r'[\wáéíóúüñ]{4,}', texto.lower()));
        if not words:return []
        rows=self.db.execute('SELECT tipo,clave,valor,peso,ts,fuente FROM recuerdos ORDER BY ts DESC LIMIT 1000').fetchall()
        scored=[]
        for tipo,clave,valor,peso,ts,fuente in rows:
            toks=set(re.findall(r'[\wáéíóúüñ]{4,}', clave+' '+valor)); overlap=len(words&toks)
            if overlap: scored.append((overlap*float(peso), {'tipo':tipo,'clave':clave,'valor':valor,'fuente':fuente}))
        scored.sort(key=lambda x:x[0],reverse=True); return [x[1] for x in scored[:k]]
    def contexto(self, texto, k=6):
        rows=self.buscar(texto,k); return '\n'.join(f"[{r['tipo']}] {r['clave']}: {r['valor']}" for r in rows)
    def total(self): return int(self.db.execute('SELECT COUNT(*) FROM recuerdos').fetchone()[0])
