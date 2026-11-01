from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Iterable

class FiltroCorpus:
    """Control de calidad para preentrenamiento: deduplicación, PII básica y ruido."""
    EMAIL=re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b')
    URL=re.compile(r'https?://\S+')
    PHONE=re.compile(r'(?<!\d)(?:\+?\d[\d .()\-]{7,}\d)(?!\d)')
    def __init__(self, min_chars=40, max_chars=200000): self.min_chars=min_chars; self.max_chars=max_chars; self.seen=set()
    def clean(self,text):
        text=re.sub(r'<[^>]+>', ' ', str(text)); text=re.sub(r'\s+', ' ', text).strip()
        text=self.EMAIL.sub(' [EMAIL] ',text); text=self.PHONE.sub(' [TELEFONO] ',text)
        return text[:self.max_chars].strip()
    def accept(self,text):
        text=self.clean(text)
        if len(text)<self.min_chars: return None
        low=text.lower()
        if low.count('{')>20 or low.count('javascript')>8 or low.count('lorem ipsum')>2: return None
        key=hashlib.sha256(re.sub(r'\W+',' ',low).encode()).hexdigest()
        if key in self.seen: return None
        self.seen.add(key); return text

def escribir_manifiesto(path: Path, records: Iterable[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(list(records),ensure_ascii=False,indent=2),encoding='utf8')
