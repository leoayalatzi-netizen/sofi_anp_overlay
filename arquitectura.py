#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  AUDITOR ARQUITECTÓNICO ANP — Nevula v0.0.1                             ║
║  Análisis completo para migración a v0.2 "Golondrina"                   ║
║  Imparcial · Exhaustivo · Genera reporte JSON                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import sys, os, re, json, ast, time, hashlib, importlib, traceback
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
ARCHIVO = Path(__file__).resolve()
BASE = ARCHIVO.parent
while BASE != BASE.parent:
    if (BASE / "principal.py").exists():
        break
    BASE = BASE.parent

os.chdir(str(BASE))
sys.path.insert(0, str(BASE))

REPORTE_PATH = BASE / f"auditoria_ANP_v0.0.1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

print("═" * 70)
print("   🔍 AUDITOR ARQUITECTÓNICO ANP — Nevula v0.0.1")
print("   Análisis para migración a v0.2 'Golondrina'")
print("═" * 70)

# ═══════════════════════════════════════════════════════════════
# CLASIFICADOR DE NIVEL ARQUITECTÓNICO
# ═══════════════════════════════════════════════════════════════
NIVELES = {
    1: "Base - Infraestructura fundamental",
    2: "Núcleo - Componente central del sistema",
    3: "Motor - Motor de procesamiento especializado",
    4: "Servicio - Servicio de soporte",
    5: "Orquestador - Coordinación y gestión",
    6: "Dato - Almacenamiento y conocimiento",
    7: "Interfaz - Entrada/Salida",
    8: "Prueba - Testing y diagnóstico",
    9: "Utilidad - Herramienta auxiliar",
    10: "Experimental - En desarrollo o prueba",
    11: "Redundante - Duplicado o innecesario",
    12: "Obsoleto - Ya no se usa",
}

# ═══════════════════════════════════════════════════════════════
# CATEGORÍAS DE ARCHIVOS
# ═══════════════════════════════════════════════════════════════
CATEGORIAS = {
    # Principal
    "principal.py": (1, "Orquestador central V3 - Entrada principal del sistema"),
    "configuracion.py": (2, "Configuración global del sistema"),
    
    # Nucleo - Infraestructura base
    "nucleo/motor_base.py": (1, "Clase base abstracta para todos los motores"),
    "nucleo/nucleo_base.py": (2, "Clase base para núcleos cognitivos"),
    "nucleo/metricas.py": (4, "Sistema de recolección de métricas"),
    "nucleo/reserva_memoria.py": (4, "Gestión de reserva de memoria"),
    
    # Nucleo - Orquestador
    "nucleo/orquestador/maestro.py": (5, "Orquestador principal - Coordina núcleos"),
    "nucleo/orquestador/enrutador.py": (5, "Enrutador - Dirige tareas a motores"),
    "nucleo/orquestador/planificador.py": (5, "Planificador - Prioriza y secuencia tareas"),
    "nucleo/orquestador/integrador.py": (5, "Integrador - Consolida resultados"),
    "nucleo/orquestador/conciencia_sistemica.py": (10, "Conciencia sistémica - Estado global"),
    
    # Nucleo - Bus de eventos
    "nucleo/bus_eventos/bus.py": (5, "Bus de eventos central"),
    "nucleo/bus_eventos/eventos.py": (5, "Definiciones de eventos"),
    "nucleo/bus_eventos/middleware.py": (5, "Middleware de eventos"),
    "nucleo/bus_eventos/prioridad.py": (5, "Sistema de prioridades de eventos"),
    "nucleo/bus_eventos/suscriptor.py": (5, "Gestor de suscripciones"),
    "nucleo/bus_eventos/tipos.py": (5, "Tipos de eventos"),
    
    # Nucleo - Fallback
    "nucleo/orquestador/fallback/registro_fallos.py": (5, "Registro de fallos del sistema"),
    "nucleo/orquestador/fallback/respuestas_emergencia.py": (5, "Respuestas de emergencia"),
    "nucleo/orquestador/fallback/wrappers.py": (5, "Wrappers de tolerancia a fallos"),
    
    # Nucleo - Contexto
    "nucleo/contexto/contexto.py": (4, "Gestor de contexto compartido"),
    
    # Nucleo - Servicios
    "nucleo/servicios/cache.py": (4, "Servicio de caché"),
    "nucleo/servicios/base_datos.py": (4, "Servicio de base de datos"),
    "nucleo/servicios/asincrono.py": (4, "Servicio de ejecución asíncrona"),
    "nucleo/servicios/formateador.py": (4, "Formateador de salida"),
    "nucleo/servicios/https.py": (4, "Cliente HTTP seguro"),
    "nucleo/servicios/registro.py": (4, "Servicio de logging"),
    "nucleo/servicios/validador.py": (4, "Validador de datos"),
    
    # Nucleo - Módulos importados por integrador
    "nucleo/motor_atencion.py": (11, "REDUNDANTE - Debería estar en nucleos/memoria/motores/"),
    "nucleo/motor_trabajo.py": (11, "REDUNDANTE - Debería estar en nucleos/memoria/motores/"),
    "nucleo/conocimiento.py": (11, "REDUNDANTE - Reemplazado por datos/ y BibliotecaANP"),
    "nucleo/pensamiento.py": (11, "REDUNDANTE - Reemplazado por pensamiento/"),
    
    # Pensamiento (V3)
    "pensamiento/generador.py": (2, "Generador de pensamientos desde memoria real"),
    "pensamiento/reflexion.py": (2, "Analizador de calidad de pensamientos"),
    "pensamiento/objetivos.py": (2, "Gestor de objetivos con progreso por eventos"),
    "pensamiento/curiosidad.py": (2, "Motor de curiosidad basada en datos"),
    "pensamiento/ciclo_autonomo.py": (2, "Hilo permanente de pensamiento autónomo"),
    
    # Utilidades
    "utilidades/logger.py": (4, "Sistema de logging"),
    "utilidades/monitor.py": (4, "Monitor de rendimiento"),
    "utilidades/seguridad.py": (4, "Módulo de seguridad"),
    "utilidades/networking.py": (4, "Utilidades de red"),
}

# ═══════════════════════════════════════════════════════════════
# ANALIZADOR DE ARCHIVOS PYTHON
# ═══════════════════════════════════════════════════════════════
def analizar_python(ruta: Path) -> Dict:
    """Analiza un archivo Python en profundidad"""
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            codigo = f.read()
        
        resultado = {
            "lineas": len(codigo.split('\n')),
            "imports": [],
            "clases": [],
            "funciones": [],
            "herencias": [],
            "dependencias_externas": [],
            "dependencias_internas": [],
            "errores_sintaxis": [],
            "warnings": [],
            "complejidad": "baja",
            "docstring": False,
        }
        
        # Detectar docstring
        if '"""' in codigo[:200] or "'''" in codigo[:200]:
            resultado["docstring"] = True
        
        # Analizar AST
        try:
            arbol = ast.parse(codigo)
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    for alias in nodo.names:
                        resultado["imports"].append(alias.name)
                        if alias.name not in sys.stdlib_module_names and not alias.name.startswith('nucleo') and not alias.name.startswith('nucleos') and not alias.name.startswith('pensamiento') and not alias.name.startswith('utilidades') and not alias.name.startswith('datos'):
                            resultado["dependencias_externas"].append(alias.name)
                        else:
                            resultado["dependencias_internas"].append(alias.name)
                elif isinstance(nodo, ast.ImportFrom):
                    if nodo.module:
                        resultado["imports"].append(nodo.module)
                        if nodo.module not in sys.stdlib_module_names and not nodo.module.startswith('nucleo') and not nodo.module.startswith('nucleos') and not nodo.module.startswith('pensamiento') and not nodo.module.startswith('utilidades') and not nodo.module.startswith('datos'):
                            resultado["dependencias_externas"].append(nodo.module)
                        else:
                            resultado["dependencias_internas"].append(nodo.module)
                elif isinstance(nodo, ast.ClassDef):
                    bases = [b.id for b in nodo.bases if isinstance(b, ast.Name)]
                    resultado["clases"].append({"nombre": nodo.name, "bases": bases})
                    if bases:
                        resultado["herencias"].append({"clase": nodo.name, "hereda_de": bases})
                elif isinstance(nodo, ast.FunctionDef):
                    resultado["funciones"].append(nodo.name)
        except SyntaxError as e:
            resultado["errores_sintaxis"].append(str(e))
        
        # Calcular complejidad
        lineas = resultado["lineas"]
        if lineas > 1000: resultado["complejidad"] = "muy_alta"
        elif lineas > 500: resultado["complejidad"] = "alta"
        elif lineas > 200: resultado["complejidad"] = "media"
        
        # Detectar problemas comunes
        if 'import *' in codigo:
            resultado["warnings"].append("Usa 'import *' (mala práctica)")
        if 'except:' in codigo and 'except Exception' not in codigo:
            resultado["warnings"].append("Usa 'except:' sin especificar excepción")
        if 'global ' in codigo:
            resultado["warnings"].append("Usa variables globales")
        
        return resultado
    except Exception as e:
        return {"error": str(e), "lineas": 0}

# ═══════════════════════════════════════════════════════════════
# ANALIZADOR DE COMPATIBILIDAD
# ═══════════════════════════════════════════════════════════════
def analizar_compatibilidad(todos_los_archivos: Dict) -> List[Dict]:
    """Detecta problemas de compatibilidad entre módulos"""
    problemas = []
    
    # 1. Módulos redundantes en nucleo/
    redundantes = ['nucleo/motor_atencion.py', 'nucleo/motor_trabajo.py', 'nucleo/conocimiento.py', 'nucleo/pensamiento.py']
    for red in redundantes:
        if red in todos_los_archivos:
            motores_equivalentes = []
            if 'atencion' in red:
                motores_equivalentes = ['nucleos/memoria/motores/motor_atencion.py']
            elif 'trabajo' in red:
                motores_equivalentes = ['nucleos/memoria/motores/motor_trabajo.py']
            elif 'conocimiento' in red:
                motores_equivalentes = ['datos/', 'principal.py (BibliotecaANP)']
            elif 'pensamiento' in red:
                motores_equivalentes = ['pensamiento/']
            
            if motores_equivalentes:
                problemas.append({
                    "tipo": "redundancia",
                    "severidad": "media",
                    "archivo": red,
                    "descripcion": f"Módulo duplicado. Ya existe en: {', '.join(motores_equivalentes)}",
                    "recomendacion": f"Mover lógica a {motores_equivalentes[0]} y eliminar {red}",
                    "afecta_v02": True
                })
    
    # 2. Dependencias circulares
    if 'nucleo/orquestador/integrador.py' in todos_los_archivos:
        datos = todos_los_archivos['nucleo/orquestador/integrador.py']
        if datos.get('analisis', {}).get('dependencias_internas'):
            deps = datos['analisis']['dependencias_internas']
            if 'nucleo.motor_atencion' in deps or 'motor_atencion' in str(deps):
                problemas.append({
                    "tipo": "dependencia_fragil",
                    "severidad": "alta",
                    "archivo": "nucleo/orquestador/integrador.py",
                    "descripcion": "Depende de nucleo/motor_atencion.py que es redundante. Si se mueve, se rompe.",
                    "recomendacion": "Actualizar imports para usar nucleos/memoria/motores/motor_atencion.py",
                    "afecta_v02": True
                })
    
    # 3. MotorBase duplicado
    if 'nucleo/motor_base.py' in todos_los_archivos:
        # Verificar si principal.py redefine MotorBase
        if 'principal.py' in todos_los_archivos:
            datos_principal = todos_los_archivos['principal.py'].get('analisis', {})
            if datos_principal.get('clases'):
                clases = [c['nombre'] for c in datos_principal['clases']]
                if 'MotorBase' in clases:
                    problemas.append({
                        "tipo": "redefinicion",
                        "severidad": "critica",
                        "archivo": "principal.py",
                        "descripcion": "Redefine MotorBase. Debe usar exclusivamente nucleo/motor_base.py",
                        "recomendacion": "Eliminar definición local y usar 'from nucleo.motor_base import MotorBase'",
                        "afecta_v02": True
                    })
    
    # 4. __pycache__ en producción
    for archivo in todos_los_archivos:
        if '__pycache__' in archivo:
            problemas.append({
                "tipo": "cache_en_repositorio",
                "severidad": "baja",
                "archivo": archivo,
                "descripcion": "Caché de Python en el repositorio",
                "recomendacion": "Añadir __pycache__/ a .gitignore",
                "afecta_v02": False
            })
    
    return problemas

# ═══════════════════════════════════════════════════════════════
# AUDITOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════
class AuditorANP:
    def __init__(self):
        self.resultados = {
            "metadata": {
                "version_auditada": "Nevula v0.0.1",
                "version_objetivo": "v0.2 'Golondrina'",
                "fecha_auditoria": datetime.now().isoformat(),
                "ruta_proyecto": str(BASE),
                "auditor": "Sistema Automático de Auditoría ANP",
            },
            "resumen_ejecutivo": {},
            "estructura": {},
            "archivos": {},
            "componentes": defaultdict(list),
            "metricas": {},
            "problemas_compatibilidad": [],
            "recomendaciones_v02": [],
            "riesgos": [],
        }
    
    def auditar(self):
        print("\n🔍 INICIANDO AUDITORÍA COMPLETA...")
        
        # 1. Analizar estructura
        self._analizar_estructura()
        
        # 2. Analizar cada archivo Python
        self._analizar_archivos()
        
        # 3. Analizar datos JSON
        self._analizar_datos()
        
        # 4. Detectar problemas de compatibilidad
        self._detectar_problemas()
        
        # 5. Generar métricas
        self._generar_metricas()
        
        # 6. Generar recomendaciones para v0.2
        self._generar_recomendaciones()
        
        # 7. Guardar reporte
        self._guardar_reporte()
        
        return self.resultados
    
    def _analizar_estructura(self):
        print("   📁 Analizando estructura de directorios...")
        estructura = {"carpetas": [], "archivos_por_tipo": defaultdict(int)}
        
        for ruta in sorted(BASE.rglob("*")):
            if ruta.is_dir():
                if not ruta.name.startswith('.') and ruta.name != '__pycache__':
                    estructura["carpetas"].append(str(ruta.relative_to(BASE)))
            else:
                ext = ruta.suffix if ruta.suffix else 'sin_extension'
                estructura["archivos_por_tipo"][ext] += 1
        
        self.resultados["estructura"] = estructura
    
    def _analizar_archivos(self):
        print("   📄 Analizando archivos Python...")
        total_py = 0
        
        for ruta in BASE.rglob("*.py"):
            if '__pycache__' in str(ruta) or 'scripts_archivados' in str(ruta):
                continue
            
            total_py += 1
            rel = str(ruta.relative_to(BASE))
            analisis = analizar_python(ruta)
            
            # Clasificar
            nivel_info = CATEGORIAS.get(rel, (10, "Sin clasificar"))
            nivel = nivel_info[0]
            funcion = nivel_info[1]
            
            componente = {
                "ruta": rel,
                "funcion": funcion,
                "nivel_arquitectonico": nivel,
                "nivel_nombre": NIVELES.get(nivel, "Desconocido"),
                "analisis": analisis,
            }
            
            self.resultados["archivos"][rel] = componente
            self.resultados["componentes"][NIVELES.get(nivel, "Desconocido")].append(rel)
        
        self.resultados["metricas"]["total_archivos_python"] = total_py
    
    def _analizar_datos(self):
        print("   📊 Analizando archivos de datos...")
        total_json = 0
        total_entradas = 0
        
        for ruta in BASE.rglob("*.json"):
            if 'scripts_archivados' in str(ruta) or '__pycache__' in str(ruta):
                continue
            total_json += 1
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                items = datos.get("datos", [])
                if isinstance(items, list):
                    total_entradas += len(items)
                elif isinstance(items, dict):
                    total_entradas += len(items)
            except:
                pass
        
        self.resultados["metricas"]["total_archivos_json"] = total_json
        self.resultados["metricas"]["total_entradas_datos"] = total_entradas
    
    def _detectar_problemas(self):
        print("   🔗 Detectando problemas de compatibilidad...")
        self.resultados["problemas_compatibilidad"] = analizar_compatibilidad(self.resultados["archivos"])
    
    def _generar_metricas(self):
        print("   📏 Generando métricas...")
        metricas = self.resultados["metricas"]
        
        # Total líneas
        total_lineas = sum(
            a.get("analisis", {}).get("lineas", 0) 
            for a in self.resultados["archivos"].values()
        )
        metricas["total_lineas_codigo"] = total_lineas
        
        # Total motores
        motores = [a for a in self.resultados["archivos"].keys() if 'nucleos/' in a and '/motores/' in a and a.endswith('.py') and not a.endswith('__init__.py')]
        metricas["total_motores"] = len(motores)
        
        # Total núcleos
        nucleos = set()
        for m in motores:
            partes = m.split('/')
            if len(partes) >= 2:
                nucleos.add(partes[1])
        metricas["total_nucleos"] = len(nucleos)
        
        # Archivos con errores
        con_errores = [a for a, v in self.resultados["archivos"].items() if v.get("analisis", {}).get("errores_sintaxis")]
        metricas["archivos_con_errores_sintaxis"] = len(con_errores)
        
        # Archivos con warnings
        con_warnings = [a for a, v in self.resultados["archivos"].items() if v.get("analisis", {}).get("warnings")]
        metricas["archivos_con_warnings"] = len(con_warnings)
        
        # Dependencias externas
        deps = set()
        for v in self.resultados["archivos"].values():
            for d in v.get("analisis", {}).get("dependencias_externas", []):
                deps.add(d)
        metricas["dependencias_externas"] = len(deps)
        metricas["lista_dependencias"] = sorted(deps)
    
    def _generar_recomendaciones(self):
        print("   💡 Generando recomendaciones para v0.2 'Golondrina'...")
        recs = []
        riesgos = []
        
        # 1. Consolidar módulos redundantes
        recs.append({
            "id": "V02-001",
            "titulo": "Consolidar módulos redundantes en nucleo/",
            "descripcion": "nucleo/motor_atencion.py, nucleo/motor_trabajo.py, nucleo/conocimiento.py, nucleo/pensamiento.py están duplicados. Mover su lógica a sus ubicaciones canónicas.",
            "impacto": "Alto - Reduce confusión y errores de importación",
            "esfuerzo": "Medio - Requiere actualizar imports en integrador.py",
            "prioridad": "ALTA",
        })
        
        # 2. Unificar MotorBase
        recs.append({
            "id": "V02-002",
            "titulo": "Unificar MotorBase - Eliminar redefiniciones",
            "descripcion": "Algunos motores redefinen MotorBase localmente. Todos deben usar exclusivamente nucleo/motor_base.py",
            "impacto": "Crítico - Evita comportamientos divergentes",
            "esfuerzo": "Bajo - Estandarizar imports",
            "prioridad": "CRITICA",
        })
        
        # 3. Base de datos unificada
        recs.append({
            "id": "V02-003",
            "titulo": "Unificar bases de datos",
            "descripcion": "Múltiples archivos .db en almacenamiento/. Usar solo cerebro_anp.db con migraciones.",
            "impacto": "Medio - Simplifica persistencia",
            "esfuerzo": "Medio - Requiere migración de datos",
            "prioridad": "MEDIA",
        })
        
        # 4. Sistema de plugins
        recs.append({
            "id": "V02-004",
            "titulo": "Implementar sistema de carga dinámica de datos",
            "descripcion": "Crear un cargador de datos JSON que detecte automáticamente nuevos archivos en datos/",
            "impacto": "Alto - Facilita expansión de conocimiento",
            "esfuerzo": "Bajo - La BibliotecaANP ya existe, solo mejorarla",
            "prioridad": "ALTA",
        })
        
        # 5. Pipeline de pensamiento
        recs.append({
            "id": "V02-005",
            "titulo": "Pipeline de pensamiento emergente real",
            "descripcion": "Conectar DetectorPatrones → GeneradorPensamiento → Reflexion → Memoria en un pipeline continuo que se realimente",
            "impacto": "Crítico - Diferencia entre V2 y V3 real",
            "esfuerzo": "Alto - Requiere rediseñar el ciclo autónomo",
            "prioridad": "CRITICA",
        })
        
        # 6. API de motores
        recs.append({
            "id": "V02-006",
            "titulo": "Estandarizar API de motores",
            "descripcion": "Todos los motores deben implementar la misma interfaz: inicializar(), procesar(entrada), detener()",
            "impacto": "Alto - Garantiza compatibilidad",
            "esfuerzo": "Medio - La mayoría ya lo cumple",
            "prioridad": "ALTA",
        })
        
        # Riesgos identificados
        riesgos.append({
            "id": "RIESGO-001",
            "descripcion": "El integrador.py tiene dependencias frágiles con módulos redundantes",
            "probabilidad": "Alta",
            "impacto": "Medio - Puede romperse al reorganizar",
            "mitigacion": "Actualizar imports antes de mover archivos",
        })
        
        riesgos.append({
            "id": "RIESGO-002",
            "descripcion": "No hay tests automatizados para verificar que todos los motores cargan correctamente",
            "probabilidad": "Media",
            "impacto": "Alto - Regresiones silenciosas",
            "mitigacion": "Crear test de carga de motores en CI",
        })
        
        riesgos.append({
            "id": "RIESGO-003",
            "descripcion": "La base de datos cerebro_anp.db no tiene esquema documentado",
            "probabilidad": "Baja",
            "impacto": "Medio - Dificulta migraciones",
            "mitigacion": "Documentar esquema y crear migraciones",
        })
        
        self.resultados["recomendaciones_v02"] = recs
        self.resultados["riesgos"] = riesgos
    
    def _guardar_reporte(self):
        print(f"   💾 Guardando reporte en {REPORTE_PATH}...")
        
        # Convertir sets a listas para JSON
        def convertir(obj):
            if isinstance(obj, set):
                return list(obj)
            if isinstance(obj, defaultdict):
                return dict(obj)
            return obj
        
        with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, ensure_ascii=False, indent=2, default=convertir)
    
    def mostrar_resumen(self):
        m = self.resultados["metricas"]
        p = self.resultados["problemas_compatibilidad"]
        r = self.resultados["recomendaciones_v02"]
        
        print("\n" + "═" * 70)
        print("   📊 RESUMEN DE AUDITORÍA")
        print("═" * 70)
        print(f"""
   📁 Archivos Python:       {m.get('total_archivos_python', 0)}
   📊 Archivos JSON:         {m.get('total_archivos_json', 0)}
   📝 Líneas de código:      {m.get('total_lineas_codigo', 0):,}
   🤖 Motores:               {m.get('total_motores', 0)}
   🧠 Núcleos:               {m.get('total_nucleos', 0)}
   📚 Entradas de datos:     {m.get('total_entradas_datos', 0)}
   📦 Dependencias externas: {m.get('dependencias_externas', 0)}
   ⚠️  Problemas:            {len(p)}
   💡 Recomendaciones v0.2:  {len(r)}
   🔴 Riesgos:               {len(self.resultados['riesgos'])}
""")
        print(f"   📄 Reporte completo: {REPORTE_PATH}")
        print("═" * 70)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    auditor = AuditorANP()
    auditor.auditar()
    auditor.mostrar_resumen()
    
    print("\n✅ Auditoría completada. El reporte JSON contiene:")
    print("   - Análisis de cada archivo")
    print("   - Nivel arquitectónico de cada componente")
    print("   - Problemas de compatibilidad detectados")
    print("   - Recomendaciones priorizadas para v0.2 'Golondrina'")
    print("   - Riesgos identificados con mitigaciones") 