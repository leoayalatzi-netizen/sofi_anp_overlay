#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - Nevula 1.0 - Sistema Metacognitivo
# =====================================================================
# No afirma que Nevula tenga consciencia. Responde, con datos reales de
# la última resolución del planificador (no con frases genéricas
# aleatorias como hacía el generador de pensamientos original):
#   ¿qué intentaba resolver?  ¿qué sé?  ¿qué no sé?  ¿qué supuse?
#   ¿qué evidencia tengo?  ¿qué motores usé?  ¿qué salió mal?
#   ¿qué debería hacer ahora?
# =====================================================================
from typing import Optional


class SistemaMetacognitivo:
    def reportar(self, resultado) -> str:
        if resultado is None:
            return "🪞 Todavía no he resuelto nada en esta sesión sobre lo que reflexionar."

        a = resultado.analisis
        v = resultado.veredicto
        inc = resultado.incertidumbre
        fuentes = sorted({c.fuente for c in resultado.candidatos}) or ["ninguna"]

        lineas = [
            f"🪞 **Qué intentaba resolver:** \"{a.texto[:100]}\"",
            f"   Supuse dominio='{a.dominio}' ({a.confianza_dominio:.0%}), intención='{a.intencion}', "
            f"complejidad={a.complejidad:.2f}, ambigüedad={a.ambiguedad:.2f}.",
            f"🔧 **Motores que consulté:** {', '.join(fuentes)}",
        ]

        if v.aprobado:
            lineas.append(f"✅ **Qué sé:** mi respuesta pasó el verificador con confianza {v.confianza_total:.0%} "
                          f"(incertidumbre {inc.nivel()}).")
        else:
            lineas.append(f"❌ **Qué salió mal:** el verificador rechazó la respuesta ({v.motivo}, "
                          f"confianza {v.confianza_total:.0%}).")
            lineas.append(f"❓ **Qué no sé:** no tengo suficiente evidencia relevante para '{a.texto[:60]}'.")

        if inc.conflicto > 0.5:
            lineas.append("⚠️ Hubo conflicto real entre las fuentes que consulté (ninguna dominaba con claridad).")

        if a.ambiguedad > 0.5:
            sugerencia = "pedir aclaración al usuario, la pregunta es ambigua"
        elif not v.aprobado:
            sugerencia = "investigar más sobre este tema (candidato para la biblioteca de conocimiento)"
        elif inc.confianza_final < 0.6:
            sugerencia = "responder mencionando incertidumbre en vez de afirmar con seguridad total"
        else:
            sugerencia = "responder con confianza, no se detectan señales de alerta"
        lineas.append(f"➡️ **Qué debería hacer ahora:** {sugerencia}.")

        return "\n".join(lineas)
