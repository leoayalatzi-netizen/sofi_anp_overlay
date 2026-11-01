
#!/usr/bin/env python3
"""Módulo de Pensamiento Emergente para ANP"""
import sqlite3, json, re, random, urllib.request, urllib.error, urllib.parse, hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

BASE = Path(__file__).parent.parent
DB_PATH = BASE / "almacenamiento" / "cerebro.db"

class MenteEmergente:
    """Sistema de pensamiento que conecta todos los motores"""
    
    def __init__(self):
        self.db = DB_PATH
        self._cache = {}
        self._historial = []
    
    def pensar(self, texto: str, motores: Dict = None) -> Dict:
        """Procesa un pensamiento usando todos los recursos disponibles"""
        resultado = {
            "texto_original": texto,
            "intencion": self._detectar_intencion(texto),
            "emocion": self._detectar_emocion(texto),
            "entidades": self._extraer_entidades(texto),
            "conocimiento": self._buscar_conocimiento(texto),
            "respuesta": "",
            "fuente": "sintesis"
        }
        
        # 1. Si es un cálculo, resolver directamente
        calc = self._calcular(texto)
        if calc:
            resultado["respuesta"] = calc
            resultado["fuente"] = "calculo"
            return resultado
        
        # 2. Buscar en memoria
        memoria = self._buscar_memoria(texto)
        if memoria:
            resultado["conocimiento"] = memoria
        
        # 3. Buscar en internet si es necesario
        if not resultado["conocimiento"] and self._necesita_internet(texto):
            web = self._buscar_internet(texto)
            if web:
                resultado["conocimiento"] = web
                resultado["fuente"] = "internet"
        
        # 4. Construir respuesta contextual
        resultado["respuesta"] = self._construir_respuesta(resultado, motores)
        
        # 5. Guardar en memoria
        self._guardar_memoria(texto, resultado["respuesta"])
        
        return resultado
    
    def _detectar_intencion(self, texto: str) -> str:
        t = texto.lower().strip()
        patrones = {
            'calculo': r'[\d]+\s*[\+\-\*\/]\s*[\d]',
            'saludo': r'(hola|hey|saludos|buenas|buenos\s*d[ií]as)',
            'despedida': r'(ad[ió]s|chao|bye|hasta\s*luego)',
            'pregunta': r'(qu[ée]|qui[ée]n|c[óo]mo|cu[áa]l|cu[áa]ndo|d[óo]nde|por\s*qu[ée])',
            'agradecimiento': r'gracias',
            'afirmacion': r'(s[ií]|claro|ok|vale|correcto)',
            'negacion': r'(no|nunca|jam[áa]s)',
        }
        for intencion, patron in patrones.items():
            if re.search(patron, t):
                return intencion
        return 'conversacion'
    
    def _detectar_emocion(self, texto: str) -> str:
        t = texto.lower()
        positivas = ['feliz', 'genial', 'excelente', 'amor', 'gracias', 'maravilloso', '😊', '🎉']
        negativas = ['triste', 'mal', 'enojado', 'frustrado', 'odio', 'terrible', '😢', '😡']
        
        if any(p in t for p in positivas):
            return 'positiva'
        if any(p in t for p in negativas):
            return 'negativa'
        return 'neutral'
    
    def _extraer_entidades(self, texto: str) -> List[str]:
        entidades = []
        # Nombres propios (mayúsculas)
        nombres = re.findall(r'[A-ZÁÉÍÓÚ][a-záéíóú]+', texto)
        entidades.extend(nombres)
        # Números
        numeros = re.findall(r'\d+', texto)
        entidades.extend(numeros)
        return entidades[:10]
    
    def _calcular(self, texto: str) -> Optional[str]:
        """Resuelve operaciones matemáticas"""
        t = texto.strip().replace(' ', '')
        if re.match(r'^[\d\+\-\*\/\.\(\)\^]+$', t):
            try:
                t = t.replace('^', '**')
                resultado = eval(t)
                return f"📐 {texto} = {resultado}"
            except:
                pass
        return None
    
    def _buscar_conocimiento(self, texto: str) -> Optional[str]:
        """Busca en la base de datos local"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            palabras = texto.lower().split()
            for palabra in palabras:
                if len(palabra) > 3:
                    c.execute("SELECT definicion FROM conceptos WHERE palabra=?", (palabra,))
                    row = c.fetchone()
                    if row:
                        conn.close()
                        return row[0]
            conn.close()
        except:
            pass
        return None
    
    def _buscar_memoria(self, texto: str) -> Optional[str]:
        """Busca en la memoria de conversaciones pasadas"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT contenido FROM memoria WHERE tipo='conversacion' ORDER BY id DESC LIMIT 5")
            rows = c.fetchall()
            conn.close()
            if rows:
                return " | ".join([r[0][:100] for r in rows])
        except:
            pass
        return None
    
    def _buscar_internet(self, texto: str) -> Optional[str]:
        """Busca información en Wikipedia"""
        try:
            query = urllib.parse.quote(texto.strip('¿?.,!'))
            url = f"https://es.wikipedia.org/w/api.php?action=opensearch&search={query}&limit=1&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'ANP/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data and len(data) > 2 and data[2]:
                    return data[2][0][:500]
        except:
            pass
        return None
    
    def _necesita_internet(self, texto: str) -> bool:
        return any(p in texto.lower() for p in ['qué es', 'quién es', 'define', 'explica', 'busca'])
    
    def _construir_respuesta(self, info: Dict, motores: Dict = None) -> str:
        """Construye una respuesta coherente usando toda la información disponible"""
        intencion = info["intencion"]
        conocimiento = info.get("conocimiento")
        emocion = info["emocion"]
        texto = info["texto_original"]
        
        # Respuestas por intención
        if intencion == 'saludo':
            respuestas = [
                f"¡Hola! 👋 Soy ANP, una inteligencia artificial con 29 motores cognitivos. ¿En qué puedo ayudarte?",
                f"¡Bienvenido/a! Soy ANP Nevula. Tengo 6 núcleos de procesamiento listos para ayudarte. ¿Qué necesitas?",
                f"¡Hey! Qué gusto verte. Soy ANP, tu asistente de IA. ¿Qué quieres hacer hoy?"
            ]
            return random.choice(respuestas)
        
        if intencion == 'despedida':
            return random.choice([
                "¡Hasta pronto! 👋 Estaré aquí cuando me necesites.",
                "¡Cuídate! Fue un placer conversar contigo.",
                "¡Adiós! Que tengas un excelente día. Vuelve cuando quieras."
            ])
        
        if intencion == 'pregunta' or conocimiento:
            if conocimiento:
                return "📚 " + str(conocimiento) + "\n\n¿Quieres que profundice en algo más?"
            else:
                # Intentar respuesta creativa
                return "He analizado tu pregunta. Aunque no tengo información específica en mi base, puedo razonar sobre ello. ¿Te gustaría que explore este tema contigo?"
        
        if intencion == 'agradecimiento':
            return random.choice([
                "¡De nada! 😊 Para eso estoy. ¿Algo más en que pueda ayudarte?",
                "Es un placer. ¿Necesitas algo más?"
            ])
        
        if intencion == 'calculo':
            return self._calcular(texto) or f"No pude resolver el cálculo. ¿Puedes escribirlo de otra forma?"
        
        # Respuesta por defecto con contexto
        if self._historial:
            ultimo = self._historial[-1]
            return "Basado en nuestra conversación anterior, ¿quieres que profundicemos en algo específico?"
        
        return f"Estoy analizando tu mensaje. Tengo 29 motores trabajando en paralelo. ¿Puedes darme más detalles sobre lo que necesitas?"
    
    def _guardar_memoria(self, entrada: str, respuesta: str):
        """Guarda la conversación en memoria"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("INSERT INTO memoria (tipo, contenido) VALUES (?, ?)", 
                     ('conversacion', f"E: {entrada[:200]} | R: {respuesta[:200]}"))
            conn.commit()
            conn.close()
        except:
            pass
    
    def recordar(self, limite: int = 5) -> List[str]:
        """Recupera las últimas conversaciones"""
        try:
            conn = sqlite3.connect(str(self.db))
            c = conn.cursor()
            c.execute("SELECT contenido FROM memoria WHERE tipo='conversacion' ORDER BY id DESC LIMIT ?", (limite,))
            rows = c.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except:
            return []

# Instancia global
mente = MenteEmergente()
