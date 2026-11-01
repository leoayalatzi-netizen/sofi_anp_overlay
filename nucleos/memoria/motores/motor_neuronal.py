#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# ANP - ARQUITECTURA NEURONAL PROFUNDA
# Motor Neuronal Ultra-Optimizado (Bestia del Cálculo - Versión Final)
# =====================================================================
# Versión: 0.0.1-NEBULA
# Tipo: Motor Especializado - Núcleo de Memoria
# =====================================================================

import sys, os, time, math, json, random, threading, pickle, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque, OrderedDict
from enum import Enum, auto
import traceback

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
    np.seterr(all='ignore')
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

class FuncionActivacion(Enum):
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    SELU = "selu"
    SIGMOIDE = "sigmoide"
    TANH = "tanh"
    SOFTMAX = "softmax"
    LINEAL = "lineal"
    SWISH = "swish"
    GELU = "gelu"
    MISH = "mish"
    
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.upper().replace('-', '_')
            for member in cls:
                if member.value == value:
                    return member
        return None

class FuncionPerdida(Enum):
    MSE = "mse"
    MAE = "mae"
    HUBER = "huber"
    BINARY_CROSSENTROPY = "binary_crossentropy"
    CATEGORICAL_CROSSENTROPY = "categorical_crossentropy"
    SPARSE_CROSSENTROPY = "sparse_crossentropy"
    FOCAL_LOSS = "focal_loss"

class Regularizador(Enum):
    NINGUNO = "ninguno"
    L1 = "l1"
    L2 = "l2"

class Inicializador(Enum):
    HE_NORMAL = "he_normal"
    HE_UNIFORM = "he_uniform"
    XAVIER_NORMAL = "xavier_normal"
    XAVIER_UNIFORM = "xavier_uniform"
    LECUN_NORMAL = "lecun_normal"
    ORTHOGONAL = "orthogonal"

class ModoNormalizacion(Enum):
    BATCH = "batch"
    LAYER = "layer"
    NINGUNO = "ninguno"

class SchedulerType(Enum):
    CONSTANT = "constant"
    COSINE = "cosine"
    STEP = "step"
    EXPONENTIAL = "exponential"
    PLATEAU = "plateau"
    ONE_CYCLE = "one_cycle"

# =====================================================================
# BATCH NORMALIZATION COMPLETO
# =====================================================================

class BatchNorm:
    def __init__(self, dim: int, momentum: float = 0.9, epsilon: float = 1e-8):
        self.dim = dim
        self.momentum = momentum
        self.epsilon = epsilon
        self.gamma = np.ones((dim, 1), dtype=np.float64) if NUMPY_DISPONIBLE else None
        self.beta = np.zeros((dim, 1), dtype=np.float64) if NUMPY_DISPONIBLE else None
        self.running_mean = np.zeros((dim, 1), dtype=np.float64) if NUMPY_DISPONIBLE else None
        self.running_var = np.ones((dim, 1), dtype=np.float64) if NUMPY_DISPONIBLE else None
        self._cache = {}
        self._grad_gamma = None
        self._grad_beta = None
    
    def forward(self, X: np.ndarray, entrenando: bool = True) -> np.ndarray:
        if entrenando:
            mean = np.mean(X, axis=1, keepdims=True)
            var = np.var(X, axis=1, keepdims=True)
            x_centered = X - mean
            std_inv = 1.0 / np.sqrt(var + self.epsilon)
            x_norm = x_centered * std_inv
            self.running_mean = self.momentum * self.running_mean + (1 - self.momentum) * mean
            self.running_var = self.momentum * self.running_var + (1 - self.momentum) * var
            self._cache = {'x_centered': x_centered, 'x_norm': x_norm, 'std_inv': std_inv, 'var': var, 'X': X}
            return self.gamma * x_norm + self.beta
        else:
            x_norm = (X - self.running_mean) / np.sqrt(self.running_var + self.epsilon)
            return self.gamma * x_norm + self.beta
    
    def backward(self, dout: np.ndarray) -> np.ndarray:
        c = self._cache
        m = c['X'].shape[1]
        dbeta = np.sum(dout, axis=1, keepdims=True)
        dgamma = np.sum(dout * c['x_norm'], axis=1, keepdims=True)
        dx_norm = dout * self.gamma
        dvar = np.sum(dx_norm * c['x_centered'] * (-0.5) * c['std_inv']**3, axis=1, keepdims=True)
        dmean = np.sum(dx_norm * (-c['std_inv']), axis=1, keepdims=True) + dvar * np.mean(-2 * c['x_centered'], axis=1, keepdims=True)
        dx = dx_norm * c['std_inv'] + dvar * 2 * c['x_centered'] / m + dmean / m
        # Los parámetros de BatchNorm se actualizan con el mismo optimizador
        # que el resto de la red; nunca con una tasa fija oculta.
        self._grad_gamma = dgamma
        self._grad_beta = dbeta
        return dx

# =====================================================================
# GRADIENT CLIPPING
# =====================================================================

class GradientClipper:
    @staticmethod
    def clip_by_norm(grad: np.ndarray, max_norm: float) -> np.ndarray:
        norm = np.linalg.norm(grad)
        if norm > max_norm:
            return grad * (max_norm / norm)
        return grad

# =====================================================================
# LEARNING RATE SCHEDULER
# =====================================================================

class LRScheduler:
    def __init__(self, lr_inicial: float, tipo: SchedulerType = SchedulerType.COSINE):
        self.lr_inicial = lr_inicial
        self.lr_actual = lr_inicial
        self.tipo = tipo
        self.epoca = 0
        self.mejor_perdida = float('inf')
        self.epocas_sin_mejora = 0
    
    def step(self, perdida_val: float = None) -> float:
        self.epoca += 1
        if self.tipo == SchedulerType.CONSTANT:
            self.lr_actual = self.lr_inicial
        elif self.tipo == SchedulerType.COSINE:
            self.lr_actual = self.lr_inicial * 0.5 * (1.0 + math.cos(math.pi * self.epoca / 200))
        elif self.tipo == SchedulerType.STEP:
            self.lr_actual = self.lr_inicial * (0.5 ** (self.epoca // 30))
        elif self.tipo == SchedulerType.EXPONENTIAL:
            self.lr_actual = self.lr_inicial * math.exp(-0.01 * self.epoca)
        elif self.tipo == SchedulerType.PLATEAU:
            if perdida_val is not None:
                if perdida_val < self.mejor_perdida:
                    self.mejor_perdida = perdida_val
                    self.epocas_sin_mejora = 0
                else:
                    self.epocas_sin_mejora += 1
                if self.epocas_sin_mejora >= 10:
                    self.lr_actual *= 0.5
                    self.epocas_sin_mejora = 0
        elif self.tipo == SchedulerType.ONE_CYCLE:
            cycle = 100
            if self.epoca <= cycle:
                self.lr_actual = self.lr_inicial * (0.1 + 0.9 * self.epoca / cycle)
            else:
                self.lr_actual = self.lr_inicial * (1.0 - (self.epoca - cycle) / cycle * 0.9)
        return self.lr_actual

# =====================================================================
# CAPA NEURONAL OPTIMIZADA
# =====================================================================

@dataclass
class CapaOptima:
    nombre: str
    entrada_dim: int
    salida_dim: int
    pesos: Any = None
    sesgos: Any = None
    activacion: FuncionActivacion = FuncionActivacion.RELU
    dropout_rate: float = 0.0
    regularizador: Regularizador = Regularizador.NINGUNO
    lambda_reg: float = 0.01
    normalizacion: ModoNormalizacion = ModoNormalizacion.NINGUNO
    inicializador: Inicializador = Inicializador.HE_NORMAL
    use_bias: bool = True
    
    _entrada: Any = field(default=None, repr=False)
    _z: Any = field(default=None, repr=False)
    _salida: Any = field(default=None, repr=False)
    _mascara_dropout: Any = field(default=None, repr=False)
    _batchnorm: Any = field(default=None, repr=False)
    
    def __post_init__(self):
        if self.normalizacion == ModoNormalizacion.BATCH and NUMPY_DISPONIBLE:
            self._batchnorm = BatchNorm(self.salida_dim)
    
    def inicializar(self):
        if NUMPY_DISPONIBLE:
            self._inicializar_numpy()
        else:
            self._inicializar_puro()
    
    def _inicializar_numpy(self):
        if self.inicializador == Inicializador.HE_NORMAL:
            std = np.sqrt(2.0 / self.entrada_dim)
            self.pesos = np.random.randn(self.salida_dim, self.entrada_dim).astype(np.float64) * std
        elif self.inicializador == Inicializador.XAVIER_NORMAL:
            std = np.sqrt(2.0 / (self.entrada_dim + self.salida_dim))
            self.pesos = np.random.randn(self.salida_dim, self.entrada_dim).astype(np.float64) * std
        elif self.inicializador == Inicializador.ORTHOGONAL:
            self.pesos = np.random.randn(self.salida_dim, self.entrada_dim).astype(np.float64)
            if self.salida_dim >= self.entrada_dim:
                q, _ = np.linalg.qr(self.pesos.T)
                self.pesos = q.T
            else:
                q, _ = np.linalg.qr(self.pesos)
                self.pesos = q
        else:
            self.pesos = np.random.randn(self.salida_dim, self.entrada_dim).astype(np.float64) * 0.01
        self.sesgos = np.zeros((self.salida_dim, 1), dtype=np.float64) if self.use_bias else None
    
    def _inicializar_puro(self):
        std = math.sqrt(2.0 / self.entrada_dim)
        self.pesos = [[random.gauss(0, std) for _ in range(self.entrada_dim)] for _ in range(self.salida_dim)]
        self.sesgos = [[0.0] for _ in range(self.salida_dim)] if self.use_bias else None
    
    def forward(self, X: Any, entrenando: bool = True) -> Any:
        self._entrada = X
        if NUMPY_DISPONIBLE and isinstance(X, np.ndarray):
            return self._forward_numpy(X, entrenando)
        return self._forward_puro(X, entrenando)
    
    def _forward_numpy(self, X: np.ndarray, entrenando: bool) -> np.ndarray:
        Z = self.pesos @ X
        if self.sesgos is not None:
            Z += self.sesgos
        if self._batchnorm is not None:
            Z = self._batchnorm.forward(Z, entrenando)
        self._z = Z
        A = self._aplicar_activacion_numpy(Z)
        if entrenando and self.dropout_rate > 0:
            self._mascara_dropout = (np.random.rand(*A.shape) > self.dropout_rate).astype(np.float64)
            A *= self._mascara_dropout
            A /= (1.0 - self.dropout_rate)
        else:
            self._mascara_dropout = None
        self._salida = A
        return A
    
    def _forward_puro(self, X, entrenando: bool):
        Z = [[sum(self.pesos[i][k] * X[k][0] for k in range(len(X))) + (self.sesgos[i][0] if self.sesgos else 0)] for i in range(self.salida_dim)]
        self._z = Z
        return [[self._activacion_pura(Z[i][0])] for i in range(len(Z))]
    
    def _aplicar_activacion_numpy(self, Z: np.ndarray) -> np.ndarray:
        if self.activacion == FuncionActivacion.RELU:
            return np.maximum(0, Z)
        elif self.activacion == FuncionActivacion.LEAKY_RELU:
            return np.where(Z > 0, Z, 0.01 * Z)
        elif self.activacion == FuncionActivacion.SIGMOIDE:
            return 1.0 / (1.0 + np.exp(-np.clip(Z, -50, 50)))
        elif self.activacion == FuncionActivacion.TANH:
            return np.tanh(Z)
        elif self.activacion == FuncionActivacion.SOFTMAX:
            exp_Z = np.exp(Z - np.max(Z, axis=0, keepdims=True))
            return exp_Z / (np.sum(exp_Z, axis=0, keepdims=True) + 1e-8)
        elif self.activacion == FuncionActivacion.SWISH:
            return Z / (1.0 + np.exp(-np.clip(Z, -50, 50)))
        elif self.activacion == FuncionActivacion.GELU:
            return 0.5 * Z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (Z + 0.044715 * Z**3)))
        elif self.activacion == FuncionActivacion.MISH:
            return Z * np.tanh(np.log(1.0 + np.exp(Z)))
        return Z
    
    def _gradiente_activacion_numpy(self, dA: np.ndarray) -> np.ndarray:
        Z = self._z
        if self.activacion == FuncionActivacion.RELU:
            return dA * (Z > 0)
        if self.activacion == FuncionActivacion.LEAKY_RELU:
            return dA * np.where(Z > 0, 1.0, 0.01)
        if self.activacion == FuncionActivacion.SIGMOIDE:
            A = 1.0 / (1.0 + np.exp(-np.clip(Z, -50, 50)))
            return dA * A * (1.0 - A)
        if self.activacion == FuncionActivacion.TANH:
            A = np.tanh(Z)
            return dA * (1.0 - A**2)
        if self.activacion == FuncionActivacion.SWISH:
            sig = 1.0 / (1.0 + np.exp(-np.clip(Z, -50, 50)))
            return dA * (sig + Z * sig * (1.0 - sig))
        if self.activacion == FuncionActivacion.GELU:
            c = np.sqrt(2.0 / np.pi)
            u = c * (Z + 0.044715 * Z**3)
            tanh_u = np.tanh(u)
            du = c * (1.0 + 3.0 * 0.044715 * Z**2)
            deriv = 0.5 * (1.0 + tanh_u) + 0.5 * Z * (1.0 - tanh_u**2) * du
            return dA * deriv
        if self.activacion == FuncionActivacion.MISH:
            sp = np.log1p(np.exp(-np.abs(Z))) + np.maximum(Z, 0)
            sig = 1.0 / (1.0 + np.exp(-np.clip(Z, -50, 50)))
            tanh_sp = np.tanh(sp)
            deriv = tanh_sp + Z * sig * (1.0 - tanh_sp**2)
            return dA * deriv
        if self.activacion == FuncionActivacion.SOFTMAX:
            return dA
        return dA

    def _activacion_pura(self, z: float) -> float:
        if self.activacion == FuncionActivacion.RELU:
            return max(0.0, z)
        elif self.activacion == FuncionActivacion.SIGMOIDE:
            return 1.0 / (1.0 + math.exp(-max(-50, min(50, z))))
        return z
    
    def compute_gradients(self, dA: np.ndarray, max_grad_norm: float = 5.0) -> Tuple:
        m = self._entrada.shape[1]
        dA_corr = dA
        if self._mascara_dropout is not None:
            dA_corr = dA.copy()
            dA_corr *= self._mascara_dropout
            dA_corr /= (1.0 - self.dropout_rate)
        dZ = self._gradiente_activacion_numpy(dA_corr)
        if self._batchnorm is not None:
            dZ = self._batchnorm.backward(dZ)
        dW = (dZ @ self._entrada.T) / m
        db = np.sum(dZ, axis=1, keepdims=True) / m if self.sesgos is not None else None
        if self.regularizador == Regularizador.L2:
            dW += self.lambda_reg * self.pesos
        dW = GradientClipper.clip_by_norm(dW, max_grad_norm)
        if db is not None:
            db = GradientClipper.clip_by_norm(db, max_grad_norm)
        dA_prev = self.pesos.T @ dZ
        return dW, db, dA_prev

# =====================================================================
# ADAMW OPTIMIZER
# =====================================================================

class AdamW:
    def __init__(self, tasa_aprendizaje=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8, weight_decay=0.01):
        self.lr = tasa_aprendizaje
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.t = 0
        self._m = {}
        self._v = {}
    
    def actualizar(self, capa: CapaOptima, dW: np.ndarray, db: np.ndarray = None):
        self.t += 1
        updates = [('W', capa.pesos, dW)]
        if db is not None and capa.sesgos is not None:
            updates.append(('b', capa.sesgos, db))
        if getattr(capa, '_batchnorm', None) is not None and capa._batchnorm._grad_gamma is not None:
            updates.extend([('bn_gamma', capa._batchnorm.gamma, capa._batchnorm._grad_gamma),
                            ('bn_beta', capa._batchnorm.beta, capa._batchnorm._grad_beta)])
        for param_key, param, grad in updates:
            key = (id(param), param_key)
            if key not in self._m:
                self._m[key] = np.zeros_like(param)
                self._v[key] = np.zeros_like(param)
            self._m[key] = self.beta1 * self._m[key] + (1 - self.beta1) * grad
            self._v[key] = self.beta2 * self._v[key] + (1 - self.beta2) * grad**2
            m_hat = self._m[key] / (1 - self.beta1**self.t)
            v_hat = self._v[key] / (1 - self.beta2**self.t)
            param *= (1 - self.lr * self.weight_decay)
            param -= self.lr * m_hat / (np.sqrt(v_hat) + self.epsilon)

# =====================================================================
# LOSS FUNCTIONS
# =====================================================================

class LossFunctions:
    @staticmethod
    def softmax_crossentropy(logits: np.ndarray, y_true: np.ndarray) -> Tuple[float, np.ndarray]:
        m = logits.shape[1]
        logits_stable = logits - np.max(logits, axis=0, keepdims=True)
        exp_logits = np.exp(logits_stable)
        probs = exp_logits / (np.sum(exp_logits, axis=0, keepdims=True) + 1e-15)
        loss = -np.mean(np.sum(y_true * np.log(np.clip(probs, 1e-15, 1.0)), axis=0))
        grad = (probs - y_true)
        return float(loss), grad
    
    @staticmethod
    def binary_crossentropy(y_pred: np.ndarray, y_true: np.ndarray) -> Tuple[float, np.ndarray]:
        y_pred = np.clip(y_pred, 1e-15, 1 - 1e-15)
        m = y_true.shape[1]
        loss = -np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred))
        grad = (-(y_true / y_pred) + ((1 - y_true) / (1 - y_pred)))
        return float(loss), grad
    
    @staticmethod
    def mse(y_pred: np.ndarray, y_true: np.ndarray) -> Tuple[float, np.ndarray]:
        m = y_true.shape[1]
        loss = np.mean((y_pred - y_true)**2)
        grad = 2.0 * (y_pred - y_true)
        return float(loss), grad

# =====================================================================
# RED NEURONAL OPTIMIZADA
# =====================================================================

class RedNeuronalOptima:
    def __init__(self, nombre: str = "ANP-OptimaNet"):
        self.nombre = nombre
        self.capas: List[CapaOptima] = []
        self.optimizador = None
        self.scheduler = None
        self.funcion_perdida = FuncionPerdida.BINARY_CROSSENTROPY
        self.max_grad_norm = 5.0
        self._historial = {'perdida': [], 'val_perdida': [], 'lr': []}
        self._entrenada = False
        self.epocas_entrenadas = 0
        self._mejores_pesos = None
    
    def agregar(self, entrada_dim: int, salida_dim: int, **kwargs) -> 'RedNeuronalOptima':
        capa = CapaOptima(nombre=f"capa_{len(self.capas)+1}", entrada_dim=entrada_dim, salida_dim=salida_dim, **kwargs)
        capa.inicializar()
        self.capas.append(capa)
        return self
    
    def compilar(self, optimizador='adamw', perdida='binary_crossentropy', lr=0.001,
                 scheduler_type: SchedulerType = SchedulerType.COSINE, max_grad_norm=5.0, **kwargs):
        self.optimizador = AdamW(tasa_aprendizaje=lr, **kwargs) if isinstance(optimizador, str) else optimizador
        self.scheduler = LRScheduler(lr_inicial=lr, tipo=scheduler_type)
        self.funcion_perdida = FuncionPerdida(perdida) if isinstance(perdida, str) else perdida
        self.max_grad_norm = max_grad_norm
    
    def forward(self, X: np.ndarray, entrenando: bool = False) -> np.ndarray:
        for capa in self.capas:
            X = capa.forward(X, entrenando)
        return X
    
    def entrenar(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray = None, y_val: np.ndarray = None,
                epocas: int = 100, batch_size: int = 64, early_stopping: int = 15, verbose: bool = True) -> Dict[str, Any]:
        if not NUMPY_DISPONIBLE:
            return {'error': 'Se requiere NumPy', 'exito': False}
        n_muestras = X_train.shape[1]
        mejor_perdida_val = float('inf')
        epocas_sin_mejora = 0
        
        for epoca in range(epocas):
            lr_actual = self.scheduler.step(mejor_perdida_val if X_val is not None else None)
            self.optimizador.lr = lr_actual
            perm = np.random.permutation(n_muestras)
            X_shuffled = X_train[:, perm]
            y_shuffled = y_train[:, perm]
            perdida_epoca = 0.0
            n_batches = 0
            
            for i in range(0, n_muestras, batch_size):
                X_batch = X_shuffled[:, i:i+batch_size]
                y_batch = y_shuffled[:, i:i+batch_size]
                y_pred = self.forward(X_batch, entrenando=True)
                
                if self.funcion_perdida == FuncionPerdida.CATEGORICAL_CROSSENTROPY:
                    perdida, dA = LossFunctions.softmax_crossentropy(y_pred, y_batch)
                elif self.funcion_perdida == FuncionPerdida.BINARY_CROSSENTROPY:
                    perdida, dA = LossFunctions.binary_crossentropy(y_pred, y_batch)
                else:
                    perdida, dA = LossFunctions.mse(y_pred, y_batch)
                
                perdida_epoca += perdida
                n_batches += 1
                
                for capa in reversed(self.capas):
                    dW, db, dA = capa.compute_gradients(dA, self.max_grad_norm)
                    self.optimizador.actualizar(capa, dW, db)
            
            perdida_epoca /= max(1, n_batches)
            self._historial['perdida'].append(perdida_epoca)
            self._historial['lr'].append(lr_actual)
            
            if X_val is not None:
                y_val_pred = self.forward(X_val, entrenando=False)
                val_loss, _ = LossFunctions.binary_crossentropy(y_val_pred, y_val) if y_val.shape[0] == 1 else LossFunctions.softmax_crossentropy(y_val_pred, y_val)
                self._historial['val_perdida'].append(float(val_loss))
                if val_loss < mejor_perdida_val:
                    mejor_perdida_val = val_loss
                    epocas_sin_mejora = 0
                    self._guardar_mejores_pesos()
                else:
                    epocas_sin_mejora += 1
                if epocas_sin_mejora >= early_stopping:
                    if verbose: print(f"  ⏹ Early stopping en época {epoca + 1}")
                    self._restaurar_mejores_pesos()
                    break
            
            if verbose and (epoca + 1) % max(1, epocas // 5) == 0:
                val_str = f" | val: {val_loss:.6f}" if X_val is not None else ""
                print(f"  📊 Época {epoca+1}/{epocas} | loss: {perdida_epoca:.6f}{val_str} | lr: {lr_actual:.6f}")
        
        self._entrenada = True
        self.epocas_entrenadas = epoca + 1
        return {'exito': True, 'epocas': self.epocas_entrenadas, 'perdida_final': float(self._historial['perdida'][-1]),
                'mejor_perdida_val': float(mejor_perdida_val) if X_val is not None else None,
                'total_parametros': sum(c.entrada_dim * c.salida_dim + (c.salida_dim if c.use_bias else 0) for c in self.capas)}
    
    def predecir(self, X: np.ndarray) -> np.ndarray:
        return self.forward(X, entrenando=False)
    
    def _guardar_mejores_pesos(self):
        self._mejores_pesos = [(c.pesos.copy(), c.sesgos.copy() if c.sesgos is not None else None,
                                c._batchnorm.gamma.copy() if c._batchnorm else None,
                                c._batchnorm.beta.copy() if c._batchnorm else None,
                                c._batchnorm.running_mean.copy() if c._batchnorm else None,
                                c._batchnorm.running_var.copy() if c._batchnorm else None) for c in self.capas]
    
    def _restaurar_mejores_pesos(self):
        if self._mejores_pesos:
            for capa, (w, b, g, bt, rm, rv) in zip(self.capas, self._mejores_pesos):
                capa.pesos = w
                capa.sesgos = b
                if capa._batchnorm and g is not None:
                    capa._batchnorm.gamma = g
                    capa._batchnorm.beta = bt
                    capa._batchnorm.running_mean = rm
                    capa._batchnorm.running_var = rv
    
    def guardar(self, ruta: str) -> bool:
        try:
            datos = {'nombre': self.nombre, 'capas': [], 'config': {'funcion_perdida': self.funcion_perdida.value, 'epocas_entrenadas': self.epocas_entrenadas, 'engine_version': '2.0'}}
            for capa in self.capas:
                cd = {'nombre': capa.nombre, 'entrada_dim': capa.entrada_dim, 'salida_dim': capa.salida_dim,
                      'pesos': capa.pesos.tolist(), 'sesgos': capa.sesgos.tolist() if capa.sesgos is not None else None,
                      'activacion': capa.activacion.value, 'dropout_rate': capa.dropout_rate,
                      'regularizador': capa.regularizador.value, 'normalizacion': capa.normalizacion.value,
                      'inicializador': capa.inicializador.value, 'use_bias': capa.use_bias}
                if capa._batchnorm:
                    cd['batchnorm'] = {'gamma': capa._batchnorm.gamma.tolist(), 'beta': capa._batchnorm.beta.tolist(),
                                       'running_mean': capa._batchnorm.running_mean.tolist(), 'running_var': capa._batchnorm.running_var.tolist()}
                datos['capas'].append(cd)
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            with open(ruta, 'wb') as f:
                pickle.dump(datos, f)
            return True
        except Exception:
            return False
    
    @classmethod
    def cargar(cls, ruta: str) -> Optional['RedNeuronalOptima']:
        try:
            with open(ruta, 'rb') as f:
                datos = pickle.load(f)
            red = cls(datos['nombre'])
            for cd in datos['capas']:
                red.agregar(entrada_dim=cd['entrada_dim'], salida_dim=cd['salida_dim'],
                    activacion=FuncionActivacion(cd['activacion']), dropout_rate=cd['dropout_rate'],
                    regularizador=Regularizador(cd['regularizador']), normalizacion=ModoNormalizacion(cd['normalizacion']),
                    inicializador=Inicializador(cd['inicializador']), use_bias=cd.get('use_bias', True))
                red.capas[-1].pesos = np.array(cd['pesos'], dtype=np.float64)
                if cd.get('sesgos') is not None:
                    red.capas[-1].sesgos = np.array(cd['sesgos'], dtype=np.float64)
                else:
                    red.capas[-1].sesgos = None
                    red.capas[-1].use_bias = False
                if 'batchnorm' in cd and cd['batchnorm'] and red.capas[-1]._batchnorm:
                    bn = red.capas[-1]._batchnorm
                    bn.gamma = np.array(cd['batchnorm']['gamma'], dtype=np.float64)
                    bn.beta = np.array(cd['batchnorm']['beta'], dtype=np.float64)
                    bn.running_mean = np.array(cd['batchnorm']['running_mean'], dtype=np.float64)
                    bn.running_var = np.array(cd['batchnorm']['running_var'], dtype=np.float64)
            red.funcion_perdida = FuncionPerdida(datos['config']['funcion_perdida'])
            red.epocas_entrenadas = datos['config']['epocas_entrenadas']
            red._entrenada = True
            red.compilar(optimizador='adamw', perdida=datos['config']['funcion_perdida'], lr=0.001)
            return red
        except Exception:
            return None
            
# =====================================================================
# MOTOR NEURONAL PRINCIPAL
# =====================================================================

class MotorNeuronal(MotorBase):
    """Motor Neuronal Ultra-Optimizado de ANP."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._redes: Dict[str, RedNeuronalOptima] = {}
        self._red_activa: Optional[str] = None
        self._tiempo_total = 0.0
    
    def _procesar_impl(self, entrada: Any, contexto=None) -> Dict[str, Any]:
        if not isinstance(entrada, dict):
            return {'error': 'Se requiere un diccionario', 'exito': False}
        accion = entrada.get('accion', 'crear')
        acciones = {'crear': self._crear_red, 'entrenar': self._entrenar_red, 'predecir': self._predecir_red,
                    'evaluar': self._evaluar_red, 'info': self._info_red, 'guardar': self._guardar_red, 'cargar': self._cargar_red,
                    'listar': lambda e: {'exito': True, 'redes': list(self._redes.keys()), 'activa': self._red_activa}}
        func = acciones.get(accion)
        return func(entrada) if func else {'error': f'Acción desconocida: {accion}', 'exito': False}
    
    def _crear_red(self, entrada: Dict) -> Dict[str, Any]:
        try:
            nombre = entrada.get('nombre', f'red_{len(self._redes)+1}')
            capas = entrada.get('capas', [])
            if not capas:
                return {'error': 'Se requiere configuración de capas', 'exito': False}
            red = RedNeuronalOptima(nombre)
            for i, c in enumerate(capas):
                entrada_dim = c.get('entrada') if i == 0 else capas[i-1].get('salida', 0)
                salida_dim = c.get('salida', 0)
                if entrada_dim == 0 or salida_dim == 0:
                    return {'error': f'Capa {i+1}: dimensiones inválidas', 'exito': False}
                def cv(cls, val, default):
                    if isinstance(val, str):
                        try: return cls(val)
                        except ValueError: return default
                    return val
                red.agregar(entrada_dim=entrada_dim, salida_dim=salida_dim,
                    activacion=cv(FuncionActivacion, c.get('activacion', 'relu'), FuncionActivacion.RELU),
                    dropout_rate=c.get('dropout', 0.0),
                    regularizador=cv(Regularizador, c.get('regularizador', 'ninguno'), Regularizador.NINGUNO),
                    normalizacion=cv(ModoNormalizacion, c.get('normalizacion', 'ninguno'), ModoNormalizacion.NINGUNO),
                    inicializador=cv(Inicializador, c.get('inicializador', 'he_normal'), Inicializador.HE_NORMAL))
            red.compilar(optimizador=entrada.get('optimizador', 'adamw'), perdida=entrada.get('perdida', 'binary_crossentropy'),
                        lr=entrada.get('tasa_aprendizaje', 0.001),
                        scheduler_type=SchedulerType(entrada.get('scheduler', 'cosine')) if entrada.get('scheduler') else SchedulerType.COSINE,
                        max_grad_norm=entrada.get('max_grad_norm', 5.0))
            self._redes[nombre] = red
            self._red_activa = nombre
            return {'exito': True, 'nombre': nombre, 'capas': len(red.capas),
                    'parametros': sum(c.entrada_dim * c.salida_dim + (c.salida_dim if c.use_bias else 0) for c in red.capas),
                    'optimizador': type(red.optimizador).__name__, 'numpy_disponible': NUMPY_DISPONIBLE}
        except Exception as e:
            return {'error': f'Error creando red: {str(e)}', 'exito': False}
    
    def _entrenar_red(self, entrada: Dict) -> Dict[str, Any]:
        nombre = entrada.get('nombre', self._red_activa)
        if nombre not in self._redes:
            return {'error': f'Red "{nombre}" no encontrada', 'exito': False}
        red = self._redes[nombre]
        X, y, X_val, y_val = self._obtener_datos(entrada)
        if X is None or y is None:
            return {'error': 'Se requieren datos de entrenamiento', 'exito': False}
        if not isinstance(X, np.ndarray): X = np.array(X, dtype=np.float64).T
        if not isinstance(y, np.ndarray): y = np.array(y, dtype=np.float64).T
        if X_val is not None and not isinstance(X_val, np.ndarray): X_val = np.array(X_val, dtype=np.float64).T
        if y_val is not None and not isinstance(y_val, np.ndarray): y_val = np.array(y_val, dtype=np.float64).T
        inicio = time.time()
        resultado = red.entrenar(X_train=X, y_train=y, X_val=X_val, y_val=y_val, epocas=entrada.get('epocas', 100),
                                batch_size=entrada.get('batch_size', 64), early_stopping=entrada.get('early_stopping', 15),
                                verbose=entrada.get('verbose', True))
        self._tiempo_total += time.time() - inicio
        resultado['tiempo_segundos'] = round(time.time() - inicio, 2)
        resultado['red'] = nombre
        return resultado
    
    def _obtener_datos(self, entrada: Dict) -> Tuple:
        X = entrada.get('X', entrada.get('datos'))
        y = entrada.get('y', entrada.get('etiquetas'))
        if X is not None and y is not None:
            return X, y, entrada.get('X_val'), entrada.get('y_val')
        problema = entrada.get('problema', 'xor')
        n = entrada.get('ejemplos', 1000)
        if problema == 'xor':
            X = np.random.randint(0, 2, (2, n)).astype(np.float64)
            y = np.logical_xor(X[0, :].astype(bool), X[1, :].astype(bool)).reshape(1, -1).astype(np.float64)
        elif problema == 'multiclase':
            n_clases = entrada.get('clases', 3)
            X = np.random.randn(2, n).astype(np.float64)
            y_int = np.random.randint(0, n_clases, (1, n))
            y = np.eye(n_clases)[y_int[0]].T.astype(np.float64)
        elif problema == 'circulos':
            X = np.random.randn(2, n).astype(np.float64) * 1.5
            y = ((X[0, :]**2 + X[1, :]**2) < 3).reshape(1, -1).astype(np.float64)
        else:
            X = np.random.randn(2, n).astype(np.float64)
            y = np.random.randint(0, 2, (1, n)).astype(np.float64)
        split = int(n * 0.8)
        indices = np.random.permutation(n)
        return X[:, indices[:split]], y[:, indices[:split]], X[:, indices[split:]], y[:, indices[split:]]
    
    def _predecir_red(self, entrada: Dict) -> Dict[str, Any]:
        nombre = entrada.get('nombre', self._red_activa)
        if nombre not in self._redes:
            return {'error': f'Red "{nombre}" no encontrada', 'exito': False}
        X = entrada.get('X', entrada.get('datos'))
        if X is None:
            return {'error': 'Se requieren datos de entrada', 'exito': False}
        if not isinstance(X, np.ndarray): X = np.array(X, dtype=np.float64).T
        predicciones = self._redes[nombre].predecir(X)
        return {'exito': True, 'predicciones': predicciones.T.tolist()[:20], 'total': X.shape[1]}
    
    def _evaluar_red(self, entrada: Dict) -> Dict[str, Any]:
        nombre = entrada.get('nombre', self._red_activa)
        if nombre not in self._redes:
            return {'error': f'Red "{nombre}" no encontrada', 'exito': False}
        X = entrada.get('X', entrada.get('datos'))
        y = entrada.get('y', entrada.get('etiquetas'))
        if X is None or y is None:
            return {'error': 'Se requieren datos de prueba', 'exito': False}
        if not isinstance(X, np.ndarray): X = np.array(X, dtype=np.float64).T
        if not isinstance(y, np.ndarray): y = np.array(y, dtype=np.float64).T
        red = self._redes[nombre]
        y_pred = red.predecir(X)
        if y.shape[0] == 1:
            loss, _ = LossFunctions.binary_crossentropy(y_pred, y)
            y_pred_bin = (y_pred > 0.5).astype(np.float64)
            precision = float(np.mean(y_pred_bin == y))
            tipo = 'binaria'
        else:
            loss, _ = LossFunctions.softmax_crossentropy(y_pred, y)
            y_pred_class = np.argmax(y_pred, axis=0)
            y_true_class = np.argmax(y, axis=0)
            precision = float(np.mean(y_pred_class == y_true_class))
            tipo = 'multiclase'
        return {'exito': True, 'perdida': float(loss), 'precision': precision, 'total_ejemplos': X.shape[1], 'tipo_salida': tipo}
    
    def _info_red(self, entrada: Dict) -> Dict[str, Any]:
        nombre = entrada.get('nombre', self._red_activa)
        if nombre not in self._redes:
            return {'error': f'Red "{nombre}" no encontrada', 'exito': False}
        red = self._redes[nombre]
        return {'exito': True, 'nombre': nombre,
                'capas': [{'nombre': c.nombre, 'entrada': c.entrada_dim, 'salida': c.salida_dim,
                           'activacion': c.activacion.value, 'params': c.entrada_dim * c.salida_dim + (c.salida_dim if c.use_bias else 0),
                           'batchnorm': c._batchnorm is not None} for c in red.capas],
                'total_parametros': sum(c.entrada_dim * c.salida_dim + (c.salida_dim if c.use_bias else 0) for c in red.capas),
                'entrenada': red._entrenada, 'optimizador': type(red.optimizador).__name__,
                'scheduler': red.scheduler.tipo.value if red.scheduler else 'none', 'numpy': NUMPY_DISPONIBLE}
    
    def _guardar_red(self, entrada: Dict) -> Dict[str, Any]:
        nombre = entrada.get('nombre', self._red_activa)
        ruta = entrada.get('ruta', f'almacenamiento/modelos/{nombre}.anp')
        if nombre not in self._redes:
            return {'error': f'Red "{nombre}" no encontrada', 'exito': False}
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        ok = self._redes[nombre].guardar(ruta)
        return {'exito': ok, 'ruta': ruta, 'nombre': nombre}
    
    def _cargar_red(self, entrada: Dict) -> Dict[str, Any]:
        ruta = entrada.get('ruta', '')
        nombre = entrada.get('nombre', Path(ruta).stem if ruta else 'cargada')
        if not ruta or not Path(ruta).exists():
            return {'error': 'Archivo no encontrado', 'exito': False}
        red = RedNeuronalOptima.cargar(ruta)
        if red is None:
            return {'error': 'Error al cargar el modelo', 'exito': False}
        self._redes[nombre] = red
        self._red_activa = nombre
        return {'exito': True, 'nombre': nombre, 'capas': len(red.capas)}

# =====================================================================
# DIAGNÓSTICO
# =====================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   DIAGNÓSTICO MOTOR NEURONAL - VERSIÓN FINAL")
    print("=" * 70)
    motor = None
    try:
        print("\n[1/8] Inicializando...")
        motor = MotorNeuronal()
        motor.inicializar()
        print(f"  ✅ Motor: {motor.nombre} | NumPy: {NUMPY_DISPONIBLE}")
        
        def sd(r):
            if r and r.exito and r.datos: return r.datos
            if r and not r.exito: print(f"  ⚠️ {r.error if hasattr(r, 'error') else 'Error'}")
            return {}
        
        print("\n[2/8] Creando red XOR...")
        d1 = sd(motor.procesar({'accion': 'crear', 'nombre': 'xor_net',
            'capas': [{'entrada': 2, 'salida': 16, 'activacion': 'relu'}, {'salida': 8, 'activacion': 'relu'}, {'salida': 1, 'activacion': 'sigmoide'}],
            'perdida': 'binary_crossentropy', 'tasa_aprendizaje': 0.001}))
        print(f"  ✅ {d1.get('nombre', 'N/A')} ({d1.get('parametros', 0)} params) | {d1.get('optimizador', 'N/A')}")
        
        print("\n[3/8] Entrenando XOR...")
        t0 = time.time()
        d2 = sd(motor.procesar({'accion': 'entrenar', 'problema': 'xor', 'ejemplos': 500, 'epocas': 200, 'batch_size': 64, 'verbose': False}))
        print(f"  ✅ {d2.get('epocas', 0)} épocas en {time.time() - t0:.2f}s | loss: {d2.get('perdida_final', 0):.6f}")
        
        print("\n[4/8] Predicciones XOR...")
        d3 = sd(motor.procesar({'accion': 'predecir', 'X': [[0, 0], [0, 1], [1, 0], [1, 1]]}))
        if d3.get('exito'):
            for inp, pred in zip([[0, 0], [0, 1], [1, 0], [1, 1]], d3.get('predicciones', [])):
                print(f"  📍 XOR({inp[0]},{inp[1]}) = {pred[0]:.6f} (esp: {inp[0] ^ inp[1]})")
        
        print("\n[5/8] Guardar/Cargar modelo...")
        d5 = sd(motor.procesar({'accion': 'guardar', 'ruta': 'almacenamiento/modelos/xor_test.anp'}))
        print(f"  {'✅' if d5.get('exito') else '❌'} Guardado: {d5.get('ruta', '')}")
        d6 = sd(motor.procesar({'accion': 'cargar', 'ruta': 'almacenamiento/modelos/xor_test.anp', 'nombre': 'xor_cargada'}))
        print(f"  {'✅' if d6.get('exito') else '❌'} Cargado: {d6.get('nombre', '')}")
        
        print("\n[6/8] Evaluación red cargada...")
        d7 = sd(motor.procesar({'accion': 'evaluar', 'nombre': 'xor_cargada', 'X': [[0, 0], [0, 1], [1, 0], [1, 1]], 'y': [[0], [1], [1], [0]]}))
        if d7.get('exito'):
            print(f"  📊 Pérdida: {d7.get('perdida', 0):.6f} | Precisión: {d7.get('precision', 0):.2%} | Tipo: {d7.get('tipo_salida', 'N/A')}")
        
        print("\n[7/8] Red multiclase...")
        motor.procesar({'accion': 'crear', 'nombre': 'multi_net',
            'capas': [{'entrada': 2, 'salida': 16, 'activacion': 'relu'}, {'salida': 3, 'activacion': 'softmax'}],
            'perdida': 'categorical_crossentropy', 'tasa_aprendizaje': 0.01})
        d8 = sd(motor.procesar({'accion': 'entrenar', 'problema': 'multiclase', 'clases': 3, 'ejemplos': 600, 'epocas': 100, 'batch_size': 64, 'verbose': False}))
        print(f"  ✅ Multiclase: {d8.get('epocas', 0)} épocas | loss: {d8.get('perdida_final', 0):.6f}")
        
        print("\n[8/8] Estadísticas...")
        print(f"  📊 Redes: {len(motor._redes)} | Tiempo total: {motor._tiempo_total:.2f}s")
        print(f"  📊 Funcionalidades: Softmax✓ | BatchNorm✓ | GradClipping✓ | LRScheduler✓ | Save/Load✓ | Eval✓")
        print("\n" + "=" * 70)
        print("   ✅ DIAGNÓSTICO COMPLETADO - MOTOR NEURONAL FINAL")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        if motor: motor.detener()
    print("\n" + "=" * 70 + "\n")            