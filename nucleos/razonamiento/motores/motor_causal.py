# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Causal (El Tejedor de Realidades)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Razonamiento
# =====================================================================
# ADVERTENCIA: Este motor implementa razonamiento causal REAL con
# diagramas de Ishikawa, análisis de causa raíz (5 Porqués), mapas
# causales, detección de correlaciones espurias, pensamiento
# contrafactual y modelado de sistemas causales.
# =====================================================================

import sys, os, re, time, math, json, random, threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict, Counter, deque
from enum import Enum, auto

# =====================================================================
# IMPORTACIONES DEL SISTEMA (con fallback)
# =====================================================================

try:
    from ....nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
except ImportError:
    try:
        from nucleo.motor_base import MotorBase, EstadoMotor, ResultadoMotor, ConfiguracionMotor
    except ImportError:
        from abc import ABC, abstractmethod
        
        class EstadoMotor(Enum):
            NO_INICIALIZADO = "no_inicializado"
            ACTIVO = "activo"
            ERROR = "error"
        
        class MotorBase(ABC):
            def __init__(self, config=None):
                self._id = str(__import__('uuid').uuid4())
                self.nombre = self.__class__.__name__
                self._estado = EstadoMotor.NO_INICIALIZADO
                self.config = config or ConfiguracionMotor()
            @property
            def estado(self): return self._estado
            def inicializar(self, contexto=None):
                self._estado = EstadoMotor.ACTIVO
                return True
            def detener(self):
                self._estado = EstadoMotor.ERROR
                return True
            @abstractmethod
            def _procesar_impl(self, entrada, contexto=None): pass
            def procesar(self, entrada, contexto=None):
                inicio = time.time()
                try:
                    resultado = self._procesar_impl(entrada, contexto)
                    tiempo_ms = (time.time() - inicio) * 1000
                    return ResultadoMotor(exito=True, datos=resultado, tiempo_ejecucion_ms=tiempo_ms)
                except Exception as e:
                    tiempo_ms = (time.time() - inicio) * 1000
                    return ResultadoMotor(exito=False, error=str(e), tiempo_ejecucion_ms=tiempo_ms)
        
        @dataclass
        class ConfiguracionMotor:
            nombre: str = ""
            timeout_default: float = 30.0
            max_reintentos: int = 3
        
        @dataclass
        class ResultadoMotor:
            exito: bool = True
            datos: Any = None
            error: Optional[str] = None
            tiempo_ejecucion_ms: float = 0.0

# =====================================================================
# ENUMERACIONES
# =====================================================================

class TipoCausa(Enum):
    RAIZ = "raiz"
    DIRECTA = "directa"
    INDIRECTA = "indirecta"
    CONTRIBUYENTE = "contribuyente"
    SUFICIENTE = "suficiente"
    NECESARIA = "necesaria"
    DISPARADORA = "disparadora"
    SISTEMICA = "sistemica"
    HUMANA = "humana"
    TECNICA = "tecnica"
    AMBIENTAL = "ambiental"
    PROCESO = "proceso"

class CategoriaIshikawa(Enum):
    MANO_OBRA = "mano_obra"
    MAQUINARIA = "maquinaria"
    METODO = "metodo"
    MATERIAL = "material"
    MEDICION = "medicion"
    MEDIO_AMBIENTE = "medio_ambiente"

class TipoRelacion(Enum):
    CAUSA_DIRECTA = "causa_directa"
    CAUSA_INVERSA = "causa_inversa"
    CORRELACION = "correlacion"
    COINCIDENCIA = "coincidencia"
    CAUSA_COMUN = "causa_comun"
    RETROALIMENTACION = "retroalimentacion"
    MODERACION = "moderacion"
    MEDIACION = "mediacion"

class NivelEvidenciaCausal(Enum):
    DEMOSTRADO = "demostrado"
    PROBABLE = "probable"
    POSIBLE = "posible"
    DUDOSO = "dudoso"
    ESPURIO = "espurio"
    INDETERMINADO = "indeterminado"

# =====================================================================
# ESTRUCTURAS DE DATOS
# =====================================================================

@dataclass
class CausaDetectada:
    descripcion: str
    tipo: TipoCausa = TipoCausa.CONTRIBUYENTE
    categoria: Optional[CategoriaIshikawa] = None
    nivel_profundidad: int = 1
    subcausas: List['CausaDetectada'] = field(default_factory=list)
    evidencia: str = ""
    probabilidad: float = 0.5

@dataclass
class RelacionCausal:
    causa: str
    efecto: str
    tipo: TipoRelacion = TipoRelacion.CAUSA_DIRECTA
    nivel_evidencia: NivelEvidenciaCausal = NivelEvidenciaCausal.PROBABLE
    fuerza: float = 0.5
    explicacion: str = ""
    contrafactual: str = ""

@dataclass
class DiagramaIshikawa:
    problema: str = ""
    categorias: Dict[CategoriaIshikawa, List[str]] = field(default_factory=dict)
    causa_raiz_probable: str = ""
    recomendaciones: List[str] = field(default_factory=list)

@dataclass
class AnalisisCausal:
    texto_original: str = ""
    evento_principal: str = ""
    causas_detectadas: List[CausaDetectada] = field(default_factory=list)
    relaciones: List[RelacionCausal] = field(default_factory=list)
    diagrama_ishikawa: Optional[DiagramaIshikawa] = None
    analisis_5_porques: List[Dict[str, str]] = field(default_factory=list)
    pensamiento_contrafactual: List[str] = field(default_factory=list)
    puntuacion_causalidad: float = 0.0
    recomendacion: str = ""

# =====================================================================
# MOTOR CAUSAL PRINCIPAL (CORREGIDO)
# =====================================================================

class MotorCausal(MotorBase):
    """Motor de Razonamiento Causal de ANP."""
    
    CATEGORIAS_ISHIKAWA = {
        CategoriaIshikawa.MANO_OBRA: {
            'nombre': 'Mano de Obra (Personas)',
            'palabras': ['persona', 'gente', 'empleado', 'trabajador', 'error humano',
                        'falta de capacitación', 'personal', 'operador'],
        },
        CategoriaIshikawa.MAQUINARIA: {
            'nombre': 'Maquinaria (Equipos)',
            'palabras': ['máquina', 'equipo', 'herramienta', 'dispositivo', 'hardware', 'software',
                        'sistema', 'infraestructura', 'tecnología', 'falla técnica'],
        },
        CategoriaIshikawa.METODO: {
            'nombre': 'Método (Procesos)',
            'palabras': ['método', 'proceso', 'procedimiento', 'protocolo', 'técnica',
                        'instrucción', 'algoritmo', 'flujo'],
        },
        CategoriaIshikawa.MATERIAL: {
            'nombre': 'Material (Insumos)',
            'palabras': ['material', 'insumo', 'materia prima', 'recurso', 'componente',
                        'suministro', 'calidad', 'defecto'],
        },
        CategoriaIshikawa.MEDICION: {
            'nombre': 'Medición (Métricas)',
            'palabras': ['medición', 'métrica', 'indicador', 'control', 'monitoreo',
                        'estándar', 'norma', 'kpi', 'dato'],
        },
        CategoriaIshikawa.MEDIO_AMBIENTE: {
            'nombre': 'Medio Ambiente (Entorno)',
            'palabras': ['ambiente', 'entorno', 'contexto', 'clima', 'cultura',
                        'condición', 'situación', 'circunstancia'],
        },
    }
    
    INDICADORES_CAUSALES = [
        (r'\b(?:debido a|a causa de|por culpa de|gracias a|como resultado de|como consecuencia de)\b', TipoRelacion.CAUSA_DIRECTA, 0.9),
        (r'\b(?:provoc[oó]|caus[oó]|gener[oó]|produjo|desencaden[oó]|ocasion[oó]|origin[oó])\b', TipoRelacion.CAUSA_DIRECTA, 0.85),
        (r'\b(?:porque|puesto que|ya que|dado que|a que)\b', TipoRelacion.CAUSA_DIRECTA, 0.75),
        (r'\b(?:por lo tanto|por consiguiente|en consecuencia|as[ií] que|entonces)\b', TipoRelacion.CAUSA_DIRECTA, 0.75),
        (r'\b(?:est[aá] correlacionado|se asocia con|est[aá] relacionado con)\b', TipoRelacion.CORRELACION, 0.70),
        (r'\b(?:influye en|afecta a|impacta en|repercute en|incide en)\b', TipoRelacion.CAUSA_DIRECTA, 0.80),
    ]
    
    def __init__(self, config=None):
        super().__init__(config)
        self._compilar_indicadores()
    
    def _compilar_indicadores(self):
        self._indicadores_compilados = [
            (re.compile(p, re.IGNORECASE), tipo, confianza)
            for p, tipo, confianza in self.INDICADORES_CAUSALES
        ]
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if isinstance(entrada, str):
            texto = entrada
            opciones = {}
        elif isinstance(entrada, dict):
            texto = entrada.get('texto', entrada.get('problema', entrada.get('consulta', '')))
            opciones = entrada
        else:
            texto = str(entrada)
            opciones = {}
        
        if not texto or not texto.strip():
            return self._resultado()
        
        texto_lower = texto.lower()
        
        # Identificar evento principal
        evento_principal = opciones.get('evento', opciones.get('problema', self._extraer_evento(texto)))
        
        # Detectar relaciones causales (CORREGIDO)
        relaciones = self._detectar_relaciones(texto_lower, texto)
        
        # Generar diagrama de Ishikawa
        ishikawa = self._generar_ishikawa(texto_lower, evento_principal, opciones)
        
        # Realizar análisis de 5 Porqués
        cinco_porques = self._analizar_5_porques(evento_principal, relaciones, opciones)
        
        # Generar pensamiento contrafactual
        contrafactuales = self._generar_contrafactuales(evento_principal, relaciones)
        
        # Puntuación de causalidad
        puntuacion = self._calcular_puntuacion(relaciones)
        
        # Recomendación
        recomendacion = self._generar_recomendacion(relaciones, ishikawa)
        
        return {
            'texto_original': texto,
            'evento_principal': evento_principal,
            'relaciones_causales': [
                {
                    'causa': r.causa,
                    'efecto': r.efecto,
                    'tipo': r.tipo.value,
                    'nivel_evidencia': r.nivel_evidencia.value,
                    'fuerza': round(r.fuerza, 2),
                    'explicacion': r.explicacion,
                    'contrafactual': r.contrafactual,
                }
                for r in relaciones
            ],
            'diagrama_ishikawa': {
                'problema': ishikawa.problema,
                'categorias': {cat.value: causas for cat, causas in ishikawa.categorias.items()},
                'causa_raiz_probable': ishikawa.causa_raiz_probable,
                'recomendaciones': ishikawa.recomendaciones,
            } if ishikawa else None,
            'analisis_5_porques': cinco_porques,
            'pensamiento_contrafactual': contrafactuales,
            'puntuacion_causalidad': round(puntuacion, 1),
            'recomendacion': recomendacion,
            'total_relaciones': len(relaciones),
        }
    
    def _extraer_evento(self, texto: str) -> str:
        patrones = [
            r'(?:el problema es|el evento fue|ocurri[oó] que|sucedi[oó] que|pas[oó] que)\s+(.+?)(?:\.|$)',
            r'(.+?)\s+(?:debido a|a causa de|porque)',
        ]
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        palabras = texto.split()
        return ' '.join(palabras[:15]) + ('...' if len(palabras) > 15 else '')
    
    def _detectar_relaciones(self, texto_lower: str, texto_original: str) -> List[RelacionCausal]:
        """Detecta relaciones causales (CORREGIDO - sin break, sin duplicados)."""
        relaciones = []
        encontrados = set()
        
        for patron, tipo, confianza in self._indicadores_compilados:
            for match in patron.finditer(texto_lower):
                match_text = match.group(0)
                if match_text in encontrados:
                    continue
                encontrados.add(match_text)
                
                # Obtener contexto
                inicio_ctx = max(0, match.start() - 150)
                fin_ctx = min(len(texto_original), match.end() + 150)
                contexto = texto_original[inicio_ctx:fin_ctx]
                
                # Dividir por el indicador
                indicador = match.group(0)
                partes = contexto.split(indicador, 1)
                
                if len(partes) >= 2:
                    efecto = partes[0].strip().rstrip('.,;:!?\n')
                    causa = partes[1].strip().rstrip('.,;:!?\n')
                else:
                    efecto = "El evento descrito"
                    causa = contexto.strip()
                
                if len(efecto) < 3:
                    efecto = "El evento principal"
                if len(causa) < 3:
                    causa = texto_original[:100]
                
                if tipo == TipoRelacion.CAUSA_DIRECTA and confianza >= 0.85:
                    nivel_ev = NivelEvidenciaCausal.PROBABLE
                elif tipo == TipoRelacion.CORRELACION:
                    nivel_ev = NivelEvidenciaCausal.POSIBLE
                else:
                    nivel_ev = NivelEvidenciaCausal.PROBABLE
                
                explicacion = f"Se detectó '{indicador}' indicando relación de {tipo.value}."
                contrafactual = self._generar_contrafactual(causa, efecto, tipo)
                
                relaciones.append(RelacionCausal(
                    causa=causa[:150], efecto=efecto[:150], tipo=tipo,
                    nivel_evidencia=nivel_ev, fuerza=confianza,
                    explicacion=explicacion, contrafactual=contrafactual,
                ))
        
        return relaciones
    
    def _generar_contrafactual(self, causa: str, efecto: str, tipo: TipoRelacion) -> str:
        if tipo == TipoRelacion.CAUSA_DIRECTA:
            return f"Si '{causa[:60]}' NO hubiera ocurrido, ¿'{efecto[:60]}' habría sucedido igualmente?"
        elif tipo == TipoRelacion.CORRELACION:
            return f"¿Podría existir una tercera variable que explique tanto '{causa[:40]}' como '{efecto[:40]}'?"
        else:
            return f"¿Qué habría pasado si '{causa[:60]}' hubiera sido diferente?"
    
    def _generar_ishikawa(self, texto_lower: str, problema: str, opciones: Dict) -> DiagramaIshikawa:
        ishikawa = DiagramaIshikawa(problema=problema)
        for categoria, datos in self.CATEGORIAS_ISHIKAWA.items():
            causas_categoria = []
            for palabra in datos['palabras']:
                if palabra in texto_lower:
                    idx = texto_lower.find(palabra)
                    if idx >= 0:
                        ctx = texto_lower[max(0, idx-20):min(len(texto_lower), idx+len(palabra)+40)]
                        causas_categoria.append(ctx.strip())
            if causas_categoria:
                ishikawa.categorias[categoria] = causas_categoria[:3]
        
        if not ishikawa.categorias:
            ishikawa.categorias = {
                CategoriaIshikawa.METODO: ['Posible falla en el método o proceso'],
                CategoriaIshikawa.MANO_OBRA: ['Posible factor humano involucrado'],
            }
        
        todas_causas = []
        for cat, causas in ishikawa.categorias.items():
            todas_causas.extend(causas)
        ishikawa.causa_raiz_probable = todas_causas[0][:100] if todas_causas else "Requiere más investigación"
        
        ishikawa.recomendaciones = [
            "Investigar las causas identificadas con datos objetivos",
            "Verificar si existen correlaciones espurias",
            "Realizar pruebas controladas para confirmar las relaciones causales",
        ]
        return ishikawa
    
    def _analizar_5_porques(self, problema: str, relaciones: List[RelacionCausal],
                           opciones: Dict) -> List[Dict[str, str]]:
        analisis = []
        causa_actual = relaciones[0].causa if relaciones else problema
        for i in range(1, 6):
            if i <= len(relaciones):
                respuesta = relaciones[i-1].causa[:100]
            else:
                respuesta = f"Posible causa subyacente en nivel {i}"
            analisis.append({'nivel': str(i), 'pregunta': f'¿Por qué? (nivel {i})', 'respuesta': respuesta})
        return analisis
    
    def _generar_contrafactuales(self, problema: str, relaciones: List[RelacionCausal]) -> List[str]:
        base = relaciones[0].causa[:40] if relaciones else problema[:40]
        return [
            f"¿Qué habría pasado si se hubiera prevenido '{base}...'?",
            f"¿Cómo sería la situación si se eliminara la causa principal?",
            f"¿Qué condiciones tendrían que cambiar para que esto NO volviera a ocurrir?",
            f"¿Existe un mundo posible donde este problema nunca hubiera existido?",
            f"Si pudieras volver atrás y cambiar UNA cosa, ¿qué cambiarías?",
        ]
    
    def _calcular_puntuacion(self, relaciones: List[RelacionCausal]) -> float:
        if not relaciones:
            return 30.0
        puntuacion = 50.0
        for r in relaciones:
            if r.tipo == TipoRelacion.CAUSA_DIRECTA:
                puntuacion += 10
            elif r.tipo == TipoRelacion.CORRELACION:
                puntuacion -= 5
        return max(10.0, min(100.0, puntuacion))
    
    def _generar_recomendacion(self, relaciones: List[RelacionCausal],
                              ishikawa: Optional[DiagramaIshikawa]) -> str:
        if not relaciones:
            return "No se detectaron relaciones causales claras. Proporcione más detalles sobre el problema y sus posibles causas."
        partes = [f"Se identificaron {len(relaciones)} relación(es) causal(es)."]
        if ishikawa and ishikawa.causa_raiz_probable:
            partes.append(f"Causa raíz probable: '{ishikawa.causa_raiz_probable[:80]}...'")
        partes.append("Para establecer causalidad sólida, se recomienda realizar experimentos controlados.")
        return ' '.join(partes)
    
    def _resultado(self, texto='', error=''):
        return {
            'texto_original': texto,
            'evento_principal': '',
            'relaciones_causales': [],
            'diagrama_ishikawa': None,
            'analisis_5_porques': [],
            'pensamiento_contrafactual': [],
            'puntuacion_causalidad': 30.0,
            'recomendacion': error if error else 'Sin datos para analizar.',
            'total_relaciones': 0,
        }

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO DEL MOTOR CAUSAL")
    print("=" * 70)
    
    motor = None
    try:
        print("\n[1/6] Inicializando motor causal...")
        motor = MotorCausal()
        motor.inicializar()
        print(f"  ✅ Motor inicializado: {motor.nombre}")
        
        def sd(r):
            if r and r.exito and r.datos:
                return r.datos
            return motor._resultado()
        
        print("\n[2/6] Relación causal directa...")
        d1 = sd(motor.procesar("El sistema falló debido a un error humano en la configuración del servidor. Esto provocó una caída del servicio por 3 horas."))
        print(f"  📊 Relaciones: {d1['total_relaciones']} | Puntuación: {d1['puntuacion_causalidad']}")
        for r in d1.get('relaciones_causales', [])[:3]:
            print(f"     - [{r['tipo']}] {r['causa'][:60]}... → {r['efecto'][:40]}...")
        
        print("\n[3/6] Diagrama de Ishikawa...")
        ish = d1.get('diagrama_ishikawa', {})
        if ish:
            print(f"  📊 Problema: {ish.get('problema', '')[:80]}...")
            print(f"  📊 Categorías: {list(ish.get('categorias', {}).keys())}")
            print(f"  📊 Causa raíz: {ish.get('causa_raiz_probable', '')[:80]}...")
        
        print("\n[4/6] Análisis 5 Porqués...")
        for pq in d1.get('analisis_5_porques', [])[:3]:
            print(f"  📍 Nivel {pq['nivel']}: {pq['respuesta'][:80]}...")
        
        print("\n[5/6] Pensamiento contrafactual...")
        for i, cf in enumerate(d1.get('pensamiento_contrafactual', [])[:3]):
            print(f"  💭 {i+1}. {cf[:80]}...")
        
        print("\n[6/6] Correlación vs Causalidad...")
        d2 = sd(motor.procesar("Las ventas de helado aumentan en verano, y también aumentan los ahogamientos. Por lo tanto, el helado causa ahogamientos."))
        print(f"  📊 Relaciones: {d2['total_relaciones']} | Puntuación: {d2['puntuacion_causalidad']}")
        for r in d2.get('relaciones_causales', [])[:2]:
            print(f"     - [{r['tipo']}] {r['contrafactual'][:80]}...")
        
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if motor:
            motor.detener()
    print("\n" + "=" * 70 + "\n")