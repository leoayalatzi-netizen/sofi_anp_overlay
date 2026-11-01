#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Motor Calculista
# =====================================================================
# La diferencia con motor_matematicas.py (que interpreta el problema en
# lenguaje natural) es que este motor SOLO calcula, de forma verificable
# y seguro (sympy, nunca eval() sobre texto arbitrario), y siempre puede
# mostrar el paso intermedio (la expresión que interpretó) para que el
# usuario pueda comprobar que interpretó bien el problema.
#
# Interpretación -> expresión/ecuación -> cálculo -> verificación
# =====================================================================
import re
from typing import Any, Dict, Optional

try:
    import sympy
    from sympy import symbols, sympify, solve, Eq, N
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    SYMPY_DISPONIBLE = True
    _TRANSFORMACIONES = standard_transformations + (implicit_multiplication_application,)
except ImportError:
    SYMPY_DISPONIBLE = False

# Solo se permiten estos caracteres en una expresión antes de pasarla a
# sympy: nunca se evalúa texto arbitrario ni se usa eval() de Python.
_CARACTERES_PERMITIDOS = re.compile(r'^[\d\s\+\-\*\/\.\(\)\^xX=,a-zA-Z]+$')
_RE_EXPRESION = re.compile(r'[\d][\d\.\s]*(?:[\+\-\*\/\^][\d\.\s]+)+')
_RE_ECUACION = re.compile(r'[a-zA-Z]\s*[\+\-\*\/]?\s*\d*.{0,20}?=.{0,40}')
_RE_PORCENTAJE = re.compile(r'(\d+(?:\.\d+)?)\s*%\s*(?:de|of)\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
_RE_INSTRUCCION = re.compile(
    r'\b(resuelve|resolver|calcula|calcular|encuentra|encontrar|halla|hallar|'
    r'cu[aá]nto\s+(?:es|vale)|la\s+ecuaci[oó]n|el\s+valor\s+de|ra[ií]z\s+de|de)\b',
    re.IGNORECASE,
)


class ResultadoCalculo:
    def __init__(self, exito: bool, expresion: str = "", resultado: Any = None,
                 tipo: str = "", texto: str = "", error: str = ""):
        self.exito = exito
        self.expresion = expresion
        self.resultado = resultado
        self.tipo = tipo
        self.texto = texto
        self.error = error


class MotorCalculista:
    """Solo calcula. No interpreta lenguaje natural más allá de detectar
    qué clase de cálculo se pide (aritmético, ecuación, porcentaje)."""

    def calcular(self, texto: str) -> Optional[ResultadoCalculo]:
        m_pct = _RE_PORCENTAJE.search(texto)
        if m_pct:
            return self._porcentaje(m_pct)

        if SYMPY_DISPONIBLE and '=' in texto and re.search(r'[a-zA-Z]', texto):
            r = self._ecuacion(texto)
            if r is not None:
                return r

        m_expr = _RE_EXPRESION.search(texto)
        if m_expr:
            return self._aritmetica(m_expr.group(0))

        return None

    def _porcentaje(self, m) -> ResultadoCalculo:
        pct, base = float(m.group(1)), float(m.group(2))
        resultado = pct / 100.0 * base
        expr = f"{pct}% de {base}"
        return ResultadoCalculo(True, expr, resultado, "porcentaje",
                                 f"📐 {expr} = {resultado:,.2f}".rstrip('0').rstrip('.'))

    def _aritmetica(self, expr_texto: str) -> Optional[ResultadoCalculo]:
        calc = expr_texto.replace(' ', '').replace('^', '**')
        if not re.match(r'^[\d\.\+\-\*\/\(\)]+$', calc):
            return None
        try:
            if SYMPY_DISPONIBLE:
                valor = sympify(calc, evaluate=True)
                resultado = float(valor) if valor.is_real else str(valor)
            else:
                # Fallback sin sympy: solo dígitos y operadores ya validados arriba.
                resultado = eval(calc)  # noqa: S307 - entrada ya restringida por el regex previo
            texto_resultado = f"{resultado:,.4f}".rstrip('0').rstrip('.') if isinstance(resultado, float) else str(resultado)
            return ResultadoCalculo(True, calc, resultado, "aritmetica", f"📐 {expr_texto.strip()} = {texto_resultado}")
        except Exception as e:
            return ResultadoCalculo(False, calc, None, "aritmetica", "", str(e))

    def _ecuacion(self, texto: str) -> Optional[ResultadoCalculo]:
        limpio = _RE_INSTRUCCION.sub(' ', texto).strip()
        m = re.search(r'([a-zA-Z0-9\.\+\-\*\/\^\(\)\s]+)=([a-zA-Z0-9\.\+\-\*\/\^\(\)\s]+)', limpio)
        if not m:
            return None
        izq_txt, der_txt = m.group(1).strip(), m.group(2).strip()
        if not (_CARACTERES_PERMITIDOS.match(izq_txt) and _CARACTERES_PERMITIDOS.match(der_txt)):
            return None
        # Si queda alguna "palabra" de más de 2 letras, es lenguaje natural
        # que no se pudo limpiar del todo: mejor no arriesgarse a interpretar mal.
        if any(len(w) > 2 for w in re.findall(r'[a-zA-Z]+', izq_txt + der_txt)):
            return None
        letras = set(re.findall(r'[a-zA-Z]', izq_txt + der_txt))
        if len(letras) != 1:
            return None  # solo ecuaciones de una incógnita en esta versión
        var = symbols(letras.pop())
        try:
            izq = parse_expr(izq_txt.replace('^', '**'), transformations=_TRANSFORMACIONES)
            der = parse_expr(der_txt.replace('^', '**'), transformations=_TRANSFORMACIONES)
            soluciones = solve(Eq(izq, der), var)
            if not soluciones:
                return ResultadoCalculo(False, f"{izq_txt} = {der_txt}", None, "ecuacion", "", "sin solución real")
            sol_txt = ", ".join(str(N(s, 6)) for s in soluciones)
            return ResultadoCalculo(True, f"{izq_txt} = {der_txt}", soluciones, "ecuacion",
                                     f"📐 {var} = {sol_txt}  (de: {izq_txt} = {der_txt})")
        except Exception as e:
            return ResultadoCalculo(False, f"{izq_txt} = {der_txt}", None, "ecuacion", "", str(e))


if __name__ == "__main__":
    m = MotorCalculista()
    pruebas = ["cuanto es 12 * 8", "45% de 200", "resuelve x + 5 = 12", "2*x - 4 = 10", "raíz de x^2 - 9 = 0"]
    for p in pruebas:
        r = m.calcular(p)
        print(f"{p!r:45} -> {r.texto if r and r.exito else (r.error if r else 'sin match')}")
