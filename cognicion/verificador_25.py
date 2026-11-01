from __future__ import annotations
import re, math, unicodedata
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from collections import Counter

@dataclass
class Verificacion25:
    aprobado: bool
    puntuacion: float
    relevancia: float
    evidencia: float
    coherencia: float
    completitud: float
    señales: Dict[str, Any]
    motivo: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class VerificadorAPEX:
    VERSION = "2.5-APEX-verifier"
    STOP = {"que","como","para","por","los","las","una","uno","unos","unas","del","con","sin","sobre","entre","esta","este","esto","ese","esa","son","ser","hay","una","más","muy","también","solo","cuando","donde","desde","hasta"}

    def _tokens(self, s: str) -> list[str]:
        x=unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().lower()
        return re.findall(r"[a-z0-9]{3,}", x)

    def _keywords(self, s: str) -> set[str]:
        return {x for x in self._tokens(s) if x not in self.STOP}

    def _linguistic(self, answer: str) -> float:
        if not answer: return 0.0
        words = self._tokens(answer)
        if len(words) < 4: return 0.15
        unique = len(set(words)) / len(words)
        sentences = max(1, len(re.findall(r"[.!?]", answer)))
        return max(0.0, min(1.0, 0.45*min(1.0, unique/0.65) + 0.35*min(1.0, sentences/3) + 0.20*min(1.0, len(answer)/120)))

    def _negation_conflict(self, question: str, answer: str) -> bool:
        q = question.lower(); a = answer.lower()
        # Detector deliberadamente conservador: solo marca contradicción si la
        # misma proposición aparece con polaridad opuesta.
        q_atoms = re.findall(r"(?:es|son|tiene|puede|permite|usa|causa|produce)\s+[^.!?]{3,60}", q)
        for atom in q_atoms:
            if atom.startswith("es ") and f"no {atom}" in a: return True
            if atom.startswith("son ") and f"no {atom}" in a: return True
        return False

    def verificar(self, pregunta: str, respuesta: str, evidencia: str = "", calculo: Any = None) -> Verificacion25:
        p = self._keywords(pregunta)
        a = self._keywords(respuesta)
        e = self._keywords(evidencia)
        overlap_q = len(p & a) / max(1, len(p))
        overlap_e = len(a & e) / max(1, len(a)) if a and e else 0.0
        if not evidencia and any(x in pregunta.lower() for x in ("qué es", "quién es", "define", "explica", "cuál")):
            overlap_e = min(overlap_e, 0.2)
        relevancia = overlap_q
        evidencia_score = min(1.0, overlap_e * 1.35) if evidencia else 0.0
        coherencia = self._linguistic(respuesta)
        completitud = min(1.0, len(self._tokens(respuesta))/40.0)
        calculo_ok = True
        if calculo is not None:
            calculo_text = getattr(calculo, "texto", "") or ""
            if getattr(calculo, "exito", False):
                calculo_ok = str(getattr(calculo, "resultado", "")) in respuesta or calculo_text in respuesta or "📐" in respuesta
                if calculo_ok:
                    # Un resultado determinista verificado puede ser relevante
                    # aunque la pregunta y la salida compartan pocas palabras.
                    relevancia = max(relevancia, 1.0)
                    evidencia_score = max(evidencia_score, 1.0)
        prompt_leak = any(x in respuesta for x in ('<|system|>','<|user|>','<|assistant|>','INSTRUCCIÓN:','PREGUNTA DEL USUARIO:','Eres Nevula'))
        contradice = self._negation_conflict(pregunta, respuesta)
        puntuacion = 0.34*relevancia + 0.28*evidencia_score + 0.18*coherencia + 0.10*completitud + 0.10*(1.0 if calculo_ok else 0.0)
        hard_fail = (len(p) >= 2 and relevancia == 0.0) or contradice or not calculo_ok or prompt_leak
        if hard_fail: puntuacion = min(puntuacion, 0.28)
        puntuacion = max(0.0, min(1.0, puntuacion))
        aprobado = puntuacion >= 0.60 and not hard_fail
        motivo = "aprobada" if aprobado else ("salida con instrucciones internas" if prompt_leak else ("contradicción detectada" if contradice else ("cálculo no verificado" if not calculo_ok else "evidencia o relevancia insuficiente")))
        return Verificacion25(aprobado, round(puntuacion,4), round(relevancia,4), round(evidencia_score,4), round(coherencia,4), round(completitud,4),
                              {"palabras_pregunta": sorted(p), "solapamiento_evidencia": round(overlap_e,4), "prompt_leak": prompt_leak, "hard_fail": hard_fail}, motivo)
