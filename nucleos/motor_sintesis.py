#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  ANP — MOTOR DE SÍNTESIS GENERATIVA                         ║
║  nucleo/motor_sintesis.py                                   ║
║  Crea conocimiento nuevo combinando datos existentes         ║
╚══════════════════════════════════════════════════════════════╝
"""
import sys, os, re, json, random
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

# Detectar BASE
ARCHIVO = Path(__file__).resolve()
BASE = ARCHIVO.parent.parent
sys.path.insert(0, str(BASE))

from nucleo.motor_base import MotorBase, ResultadoMotor

# ═══════════════════════════════════════════════════════════
# BIBLIOTECA (acceso directo a datos)
# ═══════════════════════════════════════════════════════════
class Biblioteca:
    def __init__(self):
        self.datos_dir = BASE / "datos"
        self.cache = {}
        self.archivos = list(self.datos_dir.rglob("*.json")) if self.datos_dir.exists() else []
    
    def _cargar(self, ruta):
        clave = str(ruta)
        if clave not in self.cache:
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    self.cache[clave] = json.load(f)
            except:
                self.cache[clave] = {}
        return self.cache[clave]
    
    def buscar_todo(self, palabra: str) -> List[Dict]:
        """Busca todas las ocurrencias de una palabra"""
        resultados = []
        for archivo in self.archivos:
            datos = self._cargar(archivo)
            items = datos.get("datos", [])
            if isinstance(items, list):
                for item in items:
                    if palabra.lower() in str(item).lower():
                        resultados.append({"fuente": archivo.stem, "datos": item})
        return resultados

# ═══════════════════════════════════════════════════════════
# MOTOR DE SÍNTESIS
# ═══════════════════════════════════════════════════════════
class MotorSintesis(MotorBase):
    """Motor que genera conocimiento nuevo combinando datos"""
    
    def __init__(self):
        super().__init__()
        self.biblioteca = Biblioteca()
        self.templates = []
        try:
            from nucleo.semantica import NucleoSemantico, ModeloMundo
            self.semantica=NucleoSemantico(); self.modelo_mundo=ModeloMundo(self.semantica)
        except Exception:
            self.semantica=self.modelo_mundo=None
    
    def _procesar_impl(self, entrada: Dict) -> Any:
        texto=str(entrada.get("texto","")).strip()
        if not texto: return {"respuesta":"","tipo":"vacio"}
        if self.semantica:
            hits=self.semantica.buscar(texto,top_k=6,min_score=.06)
            if hits:
                respuesta=self._sintesis_fundamentada(texto,hits)
                conceptos=[]
                for h in hits:
                    c=h["datos"].get("concepto") or h["datos"].get("nombre")
                    if c: conceptos.append(str(c))
                return {"respuesta":respuesta,"tipo":"sintesis_fundamentada","conceptos":list(dict.fromkeys(conceptos))[:8],"fuentes":len(hits),"confianza":round(min(1.0,hits[0]["score"]*1.35),4)}
        return {"respuesta":"No encontré evidencia local suficiente para sintetizar esta consulta sin inventar información.","tipo":"evidencia_insuficiente","fuentes":0,"confianza":0.0}

    def _sintesis_fundamentada(self,pregunta,hits):
        top=hits[0]["datos"]; nombre=top.get("nombre") or top.get("concepto") or "el concepto principal"
        defin=top.get("definicion") or top.get("significado") or top.get("dato") or ""
        partes=[f"**{nombre}:** {str(defin)[:500]}" if defin else f"**{nombre}** aparece como el concepto más relevante para la consulta."]
        if self.modelo_mundo:
            rel=self.modelo_mundo.vecinos(str(top.get("concepto") or top.get("nombre") or ""),limite=4)
            if rel:
                enlaces='; '.join(f"{e['relacion']} → {e['objetivo']}" for e in rel[:4])
                partes.append(f"Relaciones registradas: {enlaces}.")
        if len(hits)>1:
            secundarios=[]
            for h in hits[1:4]:
                x=h["datos"]; n=x.get("nombre") or x.get("concepto")
                if n: secundarios.append(str(n))
            if secundarios: partes.append("Conceptos relacionados recuperados: " + ", ".join(dict.fromkeys(secundarios)) + ".")
        partes.append("La respuesta está limitada a la evidencia local recuperada; las relaciones inferidas deben verificarse antes de tratarlas como hechos.")
        return " ".join(partes)

    def _extraer_palabras_clave(self, texto: str) -> List[str]:
        """Extrae palabras clave ignorando stopwords"""
        stopwords = {'que', 'como', 'para', 'por', 'del', 'los', 'las', 'una', 'con', 'más', 'qué', 'cómo', 'cuál', 'sus', 'son', 'era', 'fue', 'hay', 'tiene', 'entre', 'sobre', 'desde', 'hasta', 'cada', 'todo', 'muy', 'sin', 'pero', 'porque', 'cuando', 'donde', 'esto', 'esta', 'estos', 'ese', 'esa', 'aquel', 'cual', 'cuales', 'cuanto', 'cuanta', 'también', 'solo', 'tan', 'ser', 'estar', 'haber', 'tener', 'hacer', 'decir', 'ir', 'ver', 'dar', 'saber', 'querer', 'llegar', 'pasar', 'deber', 'poner', 'parecer', 'quedar', 'creer', 'hablar', 'llevar', 'dejar', 'seguir', 'encontrar', 'llamar', 'pensar', 'salir', 'volver', 'tomar', 'conocer', 'vivir', 'sentir', 'tratar', 'mirar', 'contar', 'empezar', 'esperar', 'buscar', 'existir', 'entrar', 'trabajar', 'escribir', 'perder', 'producir', 'entender', 'pedir', 'recordar', 'terminar', 'permitir', 'lograr', 'ocurrir', 'cambiar', 'presentar', 'crear', 'abrir', 'considerar', 'ofrecer', 'morir', 'comprar', 'explicar', 'preguntar', 'utilizar', 'gustar', 'escuchar', 'jugar', 'convertir', 'correr', 'aceptar', 'alcanzar', 'necesitar', 'formar', 'reconocer', 'servir', 'ganar', 'recibir', 'ayudar', 'funcionar', 'resultar', 'suponer', 'comprender', 'obtener', 'elegir', 'representar', 'levantar', 'intentar', 'desarrollar', 'mostrar', 'señalar', 'mantener', 'observar', 'imaginar'}
        
        palabras = re.findall(r'[a-záéíóúñ]{4,}', texto.lower())
        return [p for p in palabras if p not in stopwords][:6]
    
    def _seleccionar_estrategia(self, texto: str) -> str:
        """Elige cómo sintetizar según el tipo de pregunta"""
        t = texto.lower()
        if any(p in t for p in ['relación', 'relaciona', 'conexión', 'comparar', 'diferencia', 'parecido']):
            return "contraste"
        if any(p in t for p in ['por qué', 'causa', 'efecto', 'consecuencia', 'razón']):
            return "causa_efecto"
        if any(p in t for p in ['aplicar', 'uso', 'utilidad', 'práctica', 'ejemplo']):
            return "aplicacion"
        if any(p in t for p in ['historia', 'origen', 'evolución', 'surgió', 'descubrimiento']):
            return "historia"
        if any(p in t for p in ['futuro', 'será', 'predicción', 'tendencia', 'próximo']):
            return "futuro"
        if any(p in t for p in ['imagina', 'creativo', 'metáfora', 'como si']):
            return "metafora"
        if any(p in t for p in ['qué es', 'definición', 'significa', 'concepto']):
            return "socratico"
        return random.choice(["analogia", "contraste", "metafora"])
    
    def _generar_sintesis(self, datos: Dict[str, List], estrategia: str, pregunta: str) -> str:
        """Genera la síntesis según la estrategia"""
        conceptos = list(datos.keys())
        
        # Extraer definiciones
        definiciones = {}
        for concepto, resultados in datos.items():
            for r in resultados:
                item = r["datos"]
                for campo in ['definicion', 'dato', 'cita', 'significado']:
                    if campo in item:
                        definiciones[concepto] = str(item[campo])[:300]
                        break
                if concepto in definiciones:
                    break
        
        c1 = conceptos[0]
        c2 = conceptos[1] if len(conceptos) > 1 else conceptos[0]
        d1 = definiciones.get(c1, f"el concepto de {c1}")
        d2 = definiciones.get(c2, f"el concepto de {c2}")
        
        # ─── ESTRATEGIAS DE SÍNTESIS ───
        
        if estrategia == "analogia":
            templates = [
                f"🌉 **{c1.title()} y {c2.title()} son como dos caras de una misma moneda.** {d1} Por otro lado, {d2} Aunque parecen distintos, ambos comparten una esencia común: la búsqueda de patrones y estructura.",
                f"🔍 **Pensemos en {c1.title()} como si fuera {c2.title()}.** {d1} De manera similar, {d2} Ambos nos muestran que el universo sigue reglas que podemos descubrir.",
                f"💡 **Existe un paralelismo fascinante entre {c1.title()} y {c2.title()}.** {d1} Y {d2} Es como si la naturaleza usara el mismo lenguaje en diferentes escalas.",
            ]
        
        elif estrategia == "contraste":
            templates = [
                f"⚖️ **{c1.title()} vs {c2.title()}:** {d1} En contraste, {d2} Aunque parecen opuestos, se complementan: uno no puede existir sin el otro, como la luz y la oscuridad.",
                f"🔄 **{c1.title()} y {c2.title()} representan fuerzas complementarias.** {d1} Mientras que {d2} Juntos forman un equilibrio dinámico esencial.",
            ]
        
        elif estrategia == "causa_efecto":
            templates = [
                f"🔗 **{c1.title()} es la causa, {c2.title()} es el efecto.** {d1} Esto produce inevitablemente que {d2} Es una cadena de causalidad que se repite en la naturaleza y la sociedad.",
                f"🌊 **{c1.title()} desencadena {c2.title()}.** {d1} Como consecuencia, {d2} Entender esta relación nos permite predecir y actuar.",
            ]
        
        elif estrategia == "historia":
            templates = [
                f"📜 **El viaje de {c1.title()} a través de {c2.title()}:** {d1} Históricamente, esto llevó a {d2} Es fascinante ver cómo las ideas evolucionan y se entrelazan.",
                f"⏳ **{c1.title()} tiene una historia profunda conectada con {c2.title()}.** {d1} Con el tiempo, {d2} El pasado ilumina el presente.",
            ]
        
        elif estrategia == "metafora":
            templates = [
                f"🎨 **Imagina que {c1.title()} es un jardín y {c2.title()} es la lluvia que lo nutre.** {d1} Así como {d2} Cada elemento juega un papel en el ecosistema del conocimiento.",
                f"🌌 **{c1.title()} es como una estrella y {c2.title()} como su constelación.** {d1} De la misma forma, {d2} Solos son interesantes, juntos son extraordinarios.",
            ]
        
        elif estrategia == "socratico":
            templates = [
                f"🤔 **¿Qué es realmente {c1.title()}?** {d1} Pero, ¿cómo se relaciona con {c2.title()}? {d2} Quizás la respuesta no está en definirlos por separado, sino en entender su conexión.",
                f"❓ **Te invito a reflexionar:** Si {c1.title()} es {d1} ¿No es cierto que {c2.title()} ({d2}) es una manifestación de lo mismo?",
            ]
        
        else:
            templates = [
                f"🧩 **{c1.title()} y {c2.title()} son piezas del mismo rompecabezas.** {d1} {d2} Juntos revelan una imagen más grande del universo.",
            ]
        
        sintesis = random.choice(templates)
        
        # Agregar cierre reflexivo
        cierres = [
            f"\n\n✨ La belleza del conocimiento está en estas conexiones inesperadas.",
            f"\n\n🧠 Cada concepto es una ventana a un universo más amplio.",
            f"\n\n💭 La curiosidad es el motor que une todas las ideas.",
            f"\n\n🌟 Cuando conectamos ideas, creamos algo nuevo.",
        ]
        
        return sintesis + random.choice(cierres)

# ═══════════════════════════════════════════════════════════
# PRUEBA RÁPIDA
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    motor = MotorSintesis()
    motor.inicializar()
    
    pruebas = [
        "¿Qué relación hay entre la música y las matemáticas?",
        "¿Cómo se conectan la filosofía y la ciencia?",
        "¿Qué tienen en común el arte y la tecnología?",
        "Explícame la relación entre emociones y razón",
    ]
    
    print("🧬 PRUEBA DEL MOTOR DE SÍNTESIS\n")
    for p in pruebas:
        print(f"📥 Pregunta: {p}")
        res = motor.procesar({"texto": p, "operacion": "sintetizar"})
        if res.exito and res.datos:
            print(f"📤 Síntesis: {res.datos.get('respuesta', '')[:500]}")
            print(f"   Estrategia: {res.datos.get('estrategia')}")
            print(f"   Conceptos: {res.datos.get('conceptos')}")
            print(f"   Fuentes consultadas: {res.datos.get('fuentes')}")
        else:
            print(f"   ❌ {res.error}")
        print()