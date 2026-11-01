from __future__ import annotations
import re, time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Turno:
    rol: str
    texto: str
    timestamp: float

class GestorDialogo:
    """Memoria de trabajo lingüística: mantiene tema, turnos y contexto sin contaminar hechos."""
    def __init__(self, max_turnos: int = 12, max_chars: int = 12000):
        self.turnos = deque(maxlen=max_turnos)
        self.max_chars = max_chars
        self.tema: Optional[str] = None

    def añadir(self, rol: str, texto: str):
        texto = re.sub(r'\s+', ' ', str(texto)).strip()
        if not texto: return
        self.turnos.append(Turno(rol, texto, time.time()))
        if rol == 'user':
            palabras = re.findall(r'[\wáéíóúüñ]{5,}', texto.lower())
            if palabras: self.tema = ' '.join(palabras[:5])

    def historial(self):
        return [asdict(t) for t in self.turnos]

    def contexto(self, max_chars=None):
        limite = max_chars or self.max_chars
        piezas=[]; total=0
        for t in reversed(self.turnos):
            s=f'<|{t.rol}|> {t.texto}'
            if total + len(s) > limite: break
            piezas.append(s); total += len(s)
        return '\n'.join(reversed(piezas))

    def contexto_para_modelo(self, consulta: str, evidencia: str = ''):
        hist=self.contexto()
        partes=[]
        if hist: partes.append(hist)
        if evidencia: partes.append(f'<|context|> {evidencia}')
        partes.append(f'<|user|> {consulta}\n<|assistant|>')
        return '\n'.join(partes)

    def responder_registrada(self, consulta, respuesta):
        self.añadir('user', consulta); self.añadir('assistant', respuesta)
