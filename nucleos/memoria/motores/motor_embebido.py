#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Embebido — Word2Vec Skip-gram + Similitud Coseno
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, time, math, random, pickle, traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter, defaultdict
from enum import Enum

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    NUMPY_DISPONIBLE = False
    np = None

# =====================================================================
# IMPORTACIONES DEL SISTEMA
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
                self.config = config if config is not None else ConfiguracionMotor()
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
                    return ResultadoMotor(exito=True, datos=resultado,
                                          tiempo_ejecucion_ms=(time.time() - inicio) * 1000)
                except Exception as e:
                    return ResultadoMotor(exito=False, error=str(e),
                                          tiempo_ejecucion_ms=(time.time() - inicio) * 1000)

        class ConfiguracionMotor:
            def __init__(self):
                self.nombre = ""
                self.timeout_default = 30.0
                self.max_reintentos = 3

        class ResultadoMotor:
            def __init__(self, exito=True, datos=None, error=None, tiempo_ejecucion_ms=0.0):
                self.exito = exito
                self.datos = datos
                self.error = error
                self.tiempo_ejecucion_ms = tiempo_ejecucion_ms

# =====================================================================
# VOCABULARIO
# =====================================================================

class Vocabulario:
    def __init__(self, min_frecuencia=1, max_vocabulario=50000):
        self.min_frecuencia = min_frecuencia
        self.max_vocabulario = max_vocabulario
        self.token_a_id = {}
        self.id_a_token = {}
        self.frecuencias = Counter()
        self.total_tokens = 0

    def tokenizar(self, texto):
        texto = texto.lower()
        tokens = []
        actual = []
        for c in texto:
            if ('a' <= c <= 'z') or c in 'áéíóúüñ':
                actual.append(c)
            else:
                if len(actual) >= 2:
                    tokens.append(''.join(actual))
                actual = []
        if len(actual) >= 2:
            tokens.append(''.join(actual))
        return tokens

    def construir(self, corpus, reconstruir=False):
        if reconstruir:
            self.token_a_id.clear()
            self.id_a_token.clear()
            self.frecuencias.clear()
            self.total_tokens = 0
        conteo = Counter()
        for doc in corpus:
            if isinstance(doc, str):
                tokens = self.tokenizar(doc)
                conteo.update(tokens)
            elif isinstance(doc, list):
                for t in doc:
                    tok = str(t).lower().strip()
                    if len(tok) >= 2:
                        conteo[tok] += 1
        self.total_tokens += sum(conteo.values())
        self.frecuencias.update(conteo)
        for token, cuenta in conteo.most_common():
            if cuenta < self.min_frecuencia:
                continue
            if token in self.token_a_id:
                continue
            if len(self.token_a_id) >= self.max_vocabulario:
                break
            idx = len(self.token_a_id)
            self.token_a_id[token] = idx
            self.id_a_token[idx] = token

    def codificar(self, tokens):
        d = self.token_a_id
        out = []
        for t in tokens:
            tok = str(t).lower().strip()
            tid = d.get(tok)
            if tid is not None:
                out.append(tid)
        return out

    @property
    def tamano(self):
        return len(self.token_a_id)

    def obtener_frecuencias(self):
        total = max(1, self.total_tokens)
        f = self.frecuencias
        id_a = self.id_a_token
        return [f.get(id_a.get(i, ''), 1) / total for i in range(self.tamano)]


# =====================================================================
# WORD2VEC
# =====================================================================

class Word2VecSkipGram:
    def __init__(self, dimension=50, ventana=3, negativas=5, lr=0.05,
                 epocas=20, semilla=42):
        self.dimension = dimension
        self.ventana = ventana
        self.negativas = negativas
        self.tasa_aprendizaje = lr
        self.epocas = epocas
        self.semilla = semilla
        self.vocabulario = None
        self.W = None
        self._tabla_neg = None
        self._tabla_tam = 5000000
        self._entrenado = False
        self._perdida_hist = []
        self._W_norm = None

    def _construir_tabla(self, freqs):
        p = np.array(freqs, dtype=np.float64) ** 0.75
        s = p.sum()
        if s < 1e-12:
            p = np.ones(len(freqs), dtype=np.float64)
            s = p.sum()
        p /= s
        self._tabla_neg = np.random.choice(len(freqs), self._tabla_tam, p=p).astype(np.int32)

    def entrenar(self, corpus, vocabulario=None):
        if not NUMPY_DISPONIBLE:
            return {'error': 'NumPy requerido', 'exito': False}
        t0 = time.time()
        if vocabulario is not None:
            self.vocabulario = vocabulario
        else:
            self.vocabulario = Vocabulario(min_frecuencia=1)
            self.vocabulario.construir(corpus)
        V = self.vocabulario.tamano
        if V < 3:
            return {'error': f'Vocabulario insuficiente: {V} tokens', 'exito': False}
        corpus_ids = []
        for doc in corpus:
            if isinstance(doc, str):
                tokens = self.vocabulario.tokenizar(doc)
            elif isinstance(doc, list):
                tokens = [str(t).lower().strip() for t in doc]
            else:
                continue
            ids = self.vocabulario.codificar(tokens)
            if len(ids) >= 2:
                corpus_ids.append(ids)
        if not corpus_ids:
            return {'error': 'Corpus vacío', 'exito': False}
        coocurrencias = defaultdict(Counter)
        for seq in corpus_ids:
            n = len(seq)
            for i in range(n):
                centro = seq[i]
                ini = max(0, i - self.ventana)
                fin = min(n, i + self.ventana + 1)
                for j in range(ini, fin):
                    if i != j:
                        distancia = abs(i - j)
                        peso = 1.0 / distancia
                        coocurrencias[centro][seq[j]] += peso
        if len(coocurrencias) < 2:
            return {'error': 'Co-ocurrencias insuficientes', 'exito': False}
        np.random.seed(self.semilla)
        escala = 0.1 / math.sqrt(self.dimension)
        self.W = np.random.randn(V, self.dimension).astype(np.float64) * escala
        freqs = self.vocabulario.obtener_frecuencias()
        self._construir_tabla(freqs)
        self._perdida_hist = []
        palabras = list(coocurrencias.keys())
        for epoca in range(self.epocas):
            random.shuffle(palabras)
            lr = self.tasa_aprendizaje * max(0.001, 1.0 - epoca / self.epocas)
            perdida_epoca = 0.0
            n_updates = 0
            for centro in palabras:
                contextos = coocurrencias[centro]
                if len(contextos) < 1:
                    continue
                mejor_contexto = contextos.most_common(1)[0][0]
                neg_ids = np.random.randint(0, self._tabla_tam, size=self.negativas)
                neg_ids = self._tabla_neg[neg_ids]
                neg_ids = [n for n in neg_ids if n != mejor_contexto and n != centro]
                if len(neg_ids) < 1:
                    continue
                neg_ids = neg_ids[:self.negativas]
                vc = self.W[centro].copy()
                vp = self.W[mejor_contexto].copy()
                n_c = np.linalg.norm(vc) + 1e-12
                n_p = np.linalg.norm(vp) + 1e-12
                vc_n = vc / n_c
                vp_n = vp / n_p
                sp = np.dot(vc_n, vp_n)
                vn_list = []
                sn_list = []
                for nid in neg_ids[:3]:
                    vn = self.W[nid].copy()
                    n_n = np.linalg.norm(vn) + 1e-12
                    vn_n = vn / n_n
                    vn_list.append(vn)
                    sn_list.append(np.dot(vc_n, vn_n))
                if not sn_list:
                    continue
                max_sn = max(sn_list)
                loss = -sp + max_sn
                if loss < 0:
                    continue
                perdida_epoca += loss
                n_updates += 1
                factor_pos = lr * (1.0 - sp)
                self.W[centro] += factor_pos * vp_n
                self.W[mejor_contexto] += factor_pos * vc_n
                idx_max = sn_list.index(max_sn)
                if max_sn > -0.5:
                    factor_neg = lr * 0.5 * max_sn
                    self.W[centro] -= factor_neg * vn_list[idx_max]
            if n_updates > 0:
                perdida_epoca /= n_updates
            self._perdida_hist.append(perdida_epoca)
        self._normalizar_embeddings()
        self._entrenado = True
        self._precalcular_normas()
        return {
            'exito': True,
            'vocabulario_tamano': V,
            'dimension': self.dimension,
            'epocas_completadas': self.epocas,
            'perdida_final': round(self._perdida_hist[-1], 4) if self._perdida_hist else 0.0,
            'tiempo_segundos': round(time.time() - t0, 2),
            'perdida_historica': [round(x, 4) for x in self._perdida_hist]
        }

    def _normalizar_embeddings(self):
        if self.W is None: return
        normas = np.linalg.norm(self.W, axis=1, keepdims=True)
        normas[normas < 1e-12] = 1e-12
        self.W = self.W / normas

    def obtener_vector(self, token):
        if not self._entrenado or self.vocabulario is None or self.W is None:
            return None
        tok = str(token).lower().strip()
        tid = self.vocabulario.token_a_id.get(tok)
        if tid is None or tid >= len(self.W):
            return None
        v = self.W[tid].copy()
        n = np.linalg.norm(v)
        if n > 0: v /= n
        return v

    def similitud(self, t1, t2):
        v1 = self.obtener_vector(t1)
        v2 = self.obtener_vector(t2)
        if v1 is None or v2 is None: return None
        return round(float(np.clip(np.dot(v1, v2), -1.0, 1.0)), 4)

    def mas_similares(self, token, k=10, excluir=None):
        if not self._entrenado or self._W_norm is None or self.vocabulario is None:
            return []
        tok = str(token).lower().strip()
        tid = self.vocabulario.token_a_id.get(tok)
        if tid is None: return []
        sims = np.dot(self._W_norm, self._W_norm[tid])
        excluir_ids = {tid}
        if excluir:
            for t in excluir:
                x = self.vocabulario.token_a_id.get(str(t).lower().strip())
                if x is not None: excluir_ids.add(x)
        res = []
        for idx in np.argsort(-sims):
            if idx in excluir_ids: continue
            tok_out = self.vocabulario.id_a_token.get(idx, '')
            if tok_out:
                res.append((tok_out, round(float(sims[idx]), 4)))
                if len(res) >= k: break
        return res

    def analogia(self, a, b, c, k=5):
        va = self.obtener_vector(a)
        vb = self.obtener_vector(b)
        vc = self.obtener_vector(c)
        if va is None or vb is None or vc is None: return []
        vr = vb - va + vc
        nr = np.linalg.norm(vr)
        if nr < 1e-12: return []
        vr /= nr
        sims = np.dot(self._W_norm, vr)
        excluir = {str(a).lower().strip(), str(b).lower().strip(), str(c).lower().strip()}
        res = []
        for idx in np.argsort(-sims):
            tok = self.vocabulario.id_a_token.get(idx, '')
            if tok and tok.lower().strip() not in excluir:
                res.append((tok, round(float(sims[idx]), 4)))
                if len(res) >= k: break
        return res

    def _precalcular_normas(self):
        if self.W is None: return
        self._normalizar_embeddings()
        self._W_norm = np.ascontiguousarray(self.W.copy())

    def guardar(self, ruta):
        try:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            data = {
                'dim': self.dimension, 'win': self.ventana, 'neg': self.negativas,
                'lr': self.tasa_aprendizaje, 'ep': self.epocas, 'entr': self._entrenado,
                'hist': self._perdida_hist,
                'tok2id': self.vocabulario.token_a_id if self.vocabulario else {},
                'id2tok': [(int(k), str(v)) for k, v in self.vocabulario.id_a_token.items()] if self.vocabulario else [],
                'freq': dict(self.vocabulario.frecuencias) if self.vocabulario else {},
                'total': self.vocabulario.total_tokens if self.vocabulario else 0,
            }
            with open(ruta + '.pkl', 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            if self.W is not None:
                np.save(ruta + '.npy', self.W.astype(np.float32))
            return True
        except:
            return False

    @classmethod
    def cargar(cls, ruta):
        try:
            with open(ruta + '.pkl', 'rb') as f:
                d = pickle.load(f)
            m = cls(d['dim'], d['win'], d['neg'], d['lr'], d['ep'], semilla=42)
            m._entrenado = d['entr']
            m._perdida_hist = d['hist']
            m.vocabulario = Vocabulario()
            m.vocabulario.token_a_id = d['tok2id']
            m.vocabulario.id_a_token = {}
            raw = d.get('id2tok', [])
            if isinstance(raw, list):
                for k, v in raw:
                    m.vocabulario.id_a_token[int(k)] = str(v)
            elif isinstance(raw, dict):
                for k, v in raw.items():
                    try:
                        m.vocabulario.id_a_token[int(k)] = str(v)
                    except (ValueError, TypeError):
                        pass
            m.vocabulario.frecuencias = Counter(d.get('freq', {}))
            m.vocabulario.total_tokens = d.get('total', 0)
            if Path(ruta + '.npy').exists():
                m.W = np.load(ruta + '.npy').astype(np.float64)
            else:
                m.W = None
            if m.W is not None and len(m.W) > 0:
                m._normalizar_embeddings()
                m._precalcular_normas()
            return m
        except:
            return False


# =====================================================================
# MOTOR EMBEBIDO
# =====================================================================

class MotorEmbebido(MotorBase):
    def __init__(self, config=None):
        super().__init__(config)
        self._modelos = {}
        self._activo = None
        self._dir = Path("almacenamiento/embeddings")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _procesar_impl(self, entrada, contexto=None):
        if not isinstance(entrada, dict):
            return {'error': 'Entrada debe ser diccionario', 'exito': False}
        accion = entrada.get('accion', 'info')
        metodos = {
            'entrenar': self._entrenar, 'vector': self._vector,
            'similitud': self._similitud, 'mas_similares': self._similares,
            'analogia': self._analogia, 'guardar': self._guardar,
            'cargar': self._cargar, 'info': self._info,
            'listar': lambda e: {'exito': True, 'modelos': list(self._modelos.keys()), 'activo': self._activo}
        }
        func = metodos.get(accion)
        return func(entrada) if func else {'error': f'Acción: {accion}', 'exito': False}

    def _entrenar(self, e):
        nombre = e.get('nombre', f'w2v_{len(self._modelos)+1}')
        corpus = e.get('corpus', [])
        if not corpus: return {'error': 'Corpus requerido', 'exito': False}
        modelo = Word2VecSkipGram(
            dimension=e.get('dimension', 50), ventana=e.get('ventana', 3),
            negativas=e.get('negativas', 5), lr=e.get('tasa_aprendizaje', 0.05),
            epocas=e.get('epocas', 20), semilla=e.get('semilla', 42)
        )
        voc = Vocabulario(min_frecuencia=e.get('min_frecuencia', 1))
        voc.construir(corpus)
        if voc.tamano < 3:
            return {'error': f'Vocabulario insuficiente: {voc.tamano} tokens', 'exito': False}
        r = modelo.entrenar(corpus, vocabulario=voc)
        if r.get('exito'):
            self._modelos[nombre] = modelo
            self._activo = nombre
            r['nombre'] = nombre
        return r

    def _modelo(self, e):
        n = e.get('nombre', self._activo)
        if n in self._modelos: return self._modelos[n]
        if self._activo in self._modelos: return self._modelos[self._activo]
        return None

    def _vector(self, e):
        m = self._modelo(e)
        if not m: return {'error': 'Sin modelo', 'exito': False}
        v = m.obtener_vector(e.get('token', ''))
        if v is None: return {'exito': False, 'error': 'Token no encontrado'}
        return {'exito': True, 'token': e.get('token', ''), 'dim': len(v)}

    def _similitud(self, e):
        m = self._modelo(e)
        if not m: return {'error': 'Sin modelo', 'exito': False}
        s = m.similitud(e.get('token1', ''), e.get('token2', ''))
        if s is None: return {'exito': False, 'error': 'Tokens no encontrados'}
        return {'exito': True, 'token1': e.get('token1', ''), 'token2': e.get('token2', ''), 'similitud': s}

    def _similares(self, e):
        m = self._modelo(e)
        if not m: return {'error': 'Sin modelo', 'exito': False}
        r = m.mas_similares(e.get('token', ''), e.get('k', 10), set(e.get('excluir', [])))
        return {'exito': len(r) > 0, 'token': e.get('token', ''), 'similares': r}

    def _analogia(self, e):
        m = self._modelo(e)
        if not m: return {'error': 'Sin modelo', 'exito': False}
        r = m.analogia(e.get('a', ''), e.get('b', ''), e.get('c', ''), e.get('k', 5))
        return {'exito': len(r) > 0, 'resultados': r}

    def _guardar(self, e):
        n = e.get('nombre', self._activo)
        if n not in self._modelos: return {'error': 'Modelo no existe', 'exito': False}
        ruta = e.get('ruta', str(self._dir / f'{n}'))
        if ruta.endswith('.anp_emb'): ruta = ruta[:-8]
        if ruta.endswith('.pkl'): ruta = ruta[:-4]
        if ruta.endswith('.npy'): ruta = ruta[:-4]
        return {'exito': self._modelos[n].guardar(ruta), 'ruta': ruta + '.anp_emb', 'nombre': n}

    def _cargar(self, e):
        ruta = e.get('ruta', '')
        nombre = e.get('nombre', Path(ruta).stem if ruta else 'cargado')
        if ruta.endswith('.anp_emb'): ruta = ruta[:-8]
        if ruta.endswith('.pkl'): ruta = ruta[:-4]
        if ruta.endswith('.npy'): ruta = ruta[:-4]
        if not Path(ruta + '.pkl').exists():
            return {'error': f'Archivo no existe: {ruta}.pkl', 'exito': False}
        m = Word2VecSkipGram.cargar(ruta)
        if not m: return {'error': 'Error carga', 'exito': False}
        self._modelos[nombre] = m
        self._activo = nombre
        return {'exito': True, 'nombre': nombre, 'vocabulario_tamano': m.vocabulario.tamano if m.vocabulario else 0}

    def _info(self, e):
        m = self._modelo(e)
        if not m: return {'error': 'Sin modelo', 'exito': False}
        return {
            'exito': True, 'activo': self._activo, 'dimension': m.dimension,
            'entrenado': m._entrenado,
            'vocabulario_tamano': m.vocabulario.tamano if m.vocabulario else 0,
            'perdida_final': round(m._perdida_hist[-1], 4) if m._perdida_hist else 0.0
        }


# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR EMBEBIDO — WORD2VEC + SIMILITUD COSENO")
    print("=" * 70)
    motor = None
    try:
        print(f"\n[0] NumPy: {'✅ ' + np.__version__ if NUMPY_DISPONIBLE else '❌ No'}")
        if not NUMPY_DISPONIBLE: sys.exit(1)

        motor = MotorEmbebido()
        motor.inicializar()
        print(f"[1] Motor: {motor.nombre} | {motor.estado}")

        corpus = [
            "el perro juega con el gato en el parque",
            "el gato duerme en la casa con el perro",
            "el perro es amigo del hombre y el gato es una mascota",
            "el gato bebe leche y el perro come carne",
            "el perro y el gato son animales domesticos",
            "el hombre trabaja en la oficina con la mujer",
            "la mujer lee un libro en el sofa",
            "el hombre y la mujer caminan juntos por la calle",
            "el rey vive en el castillo con la reina y sus hijos",
            "la reina gobierna el reino con sabiduria",
            "el rey y la reina estan en el trono del castillo",
            "el principe y la princesa pasean por el jardin del reino",
            "la madre cocina la cena para el padre y los hijos",
            "el padre lee el periodico y la madre prepara el te",
            "el hijo y la hija juegan en el jardin con su madre",
            "el padre enseña al hijo a andar en bicicleta",
            "la hermana y el hermano van a la escuela juntos",
            "el abuelo cuenta historias a su nieto",
            "la abuela cocina galletas para su nieta",
            "el perro es leal y fiel a su dueño",
            "el gato es independiente y curioso",
            "el leon ruge fuerte en la selva africana",
            "el tigre caza en la jungla con sigilo",
            "el arbol da sombra en el bosque verde",
            "la flor es hermosa y colorida en primavera",
            "el sol brilla intensamente en el cielo azul",
            "la luna refleja la luz del sol en la noche",
            "las estrellas brillan en el universo infinito",
            "la tierra es nuestro planeta en el sistema solar",
            "el agua del rio fluye hacia el mar azul",
            "el oceano es profundo y misterioso",
            "la lluvia moja la tierra seca del campo",
            "la comida saludable incluye fruta y verdura fresca",
            "el pescado es rico en omega tres",
            "la carne asada es deliciosa para la cena",
            "el amor es mas fuerte que el miedo",
            "la amistad verdadera dura para siempre",
            "la felicidad consiste en apreciar lo que tienes",
            "la alegria se comparte con los amigos y la familia",
            "la tristeza pasa con el tiempo y el apoyo",
            "python es un lenguaje de programacion moderno",
            "el codigo fuente esta en el repositorio de github",
            "el algoritmo ordena los numeros eficientemente",
            "la inteligencia artificial aprende de los datos",
            "el aprendizaje automatico necesita muchos ejemplos",
            "las redes neuronales imitan al cerebro humano",
            "el conocimiento es la base de la sabiduria",
            "la educacion transforma vidas y sociedades",
            "la memoria del ordenador guarda la informacion",
            "internet conecta millones de computadoras en el mundo",
        ] * 6

        print(f"\n[2] Entrenando ({len(corpus)} documentos)...")
        t0 = time.time()
        res = motor.procesar({
            'accion': 'entrenar', 'nombre': 'diag', 'corpus': corpus,
            'dimension': 50, 'ventana': 3, 'negativas': 5, 'epocas': 20,
            'min_frecuencia': 2, 'tasa_aprendizaje': 0.05
        })
        d = res.datos if res and res.exito and res.datos else {}
        if not d.get('exito'):
            print(f"  ❌ {d.get('error', 'Fallo')}")
            sys.exit(1)
        print(f"  ✅ V: {d['vocabulario_tamano']} | Épocas: {d['epocas_completadas']} | Pérdida: {d['perdida_final']} | T: {d['tiempo_segundos']}s")

        print(f"\n[3] Similitudes:")
        for t1, t2 in [('perro','gato'),('hombre','mujer'),('rey','reina'),('sol','luna'),
                        ('madre','padre'),('hermano','hermana'),('abuelo','abuela'),
                        ('alegria','felicidad'),('amor','amistad'),('leon','tigre'),
                        ('rey','castillo'),('python','codigo'),('inteligencia','aprendizaje')]:
            r = motor.procesar({'accion':'similitud','token1':t1,'token2':t2})
            s = r.datos.get('similitud') if r and r.exito and r.datos else 'N/A'
            print(f"  {t1:>14} ↔ {t2:<14} = {s}")

        print(f"\n[4] Más similares:")
        for token in ['perro','rey','madre','alegria']:
            r = motor.procesar({'accion':'mas_similares','token':token,'k':4})
            sims = r.datos.get('similares',[]) if r and r.exito and r.datos else []
            print(f"  {token:>14} → {', '.join(f'{t}({s:.3f})' for t,s in sims)}")

        ruta = 'almacenamiento/embeddings/diag'
        print(f"\n[5] Guardar: {'✅' if motor.procesar({'accion':'guardar','ruta':ruta}).datos.get('exito') else '❌'}")

        rc = motor.procesar({'accion':'cargar','ruta':ruta,'nombre':'copia'})
        ok = rc.exito and rc.datos and rc.datos.get('exito')
        print(f"[6] Cargar: {'✅' if ok else '❌'}")

        rv = motor.procesar({'accion':'similitud','nombre':'copia','token1':'perro','token2':'gato'})
        s = rv.datos.get('similitud') if rv.exito and rv.datos else 'N/A'
        print(f"[7] Post-carga perro-gato: {s}")

        rv2 = motor.procesar({'accion':'mas_similares','nombre':'copia','token':'perro','k':3})
        sims2 = rv2.datos.get('similares',[]) if rv2.exito and rv2.datos else []
        print(f"[8] Post-carga similares: {', '.join(f'{t}({s:.3f})' for t,s in sims2)}")

        print(f"\n{'='*70}")
        print(f"   ✅ DIAGNÓSTICO COMPLETADO | V: {d['vocabulario_tamano']} | T: {d['tiempo_segundos']}s")
        print(f"{'='*70}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor: motor.detener()
    print(f"\n{'='*70}\n")
       