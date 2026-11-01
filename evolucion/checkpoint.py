#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checkpoint ampliado, sin alterar el formato .anp histórico."""
import json, pickle
from pathlib import Path
import numpy as np

def guardar_checkpoint(red, ruta, metadata=None):
    ruta=Path(ruta); ruta.parent.mkdir(parents=True,exist_ok=True)
    payload={'version':2,'nombre':red.nombre,'epocas_entrenadas':red.epocas_entrenadas,
             'historial':red._historial,'capas':[],'metadata':metadata or {}}
    for c in red.capas:
        item={'pesos':c.pesos,'sesgos':c.sesgos,'config':{'entrada_dim':c.entrada_dim,'salida_dim':c.salida_dim,'activacion':c.activacion.value,'dropout_rate':c.dropout_rate,'regularizador':c.regularizador.value,'lambda_reg':c.lambda_reg,'normalizacion':c.normalizacion.value,'inicializador':c.inicializador.value,'use_bias':c.use_bias}}
        if c._batchnorm: item['batchnorm']={'gamma':c._batchnorm.gamma,'beta':c._batchnorm.beta,'running_mean':c._batchnorm.running_mean,'running_var':c._batchnorm.running_var}
        payload['capas'].append(item)
    with ruta.open('wb') as f: pickle.dump(payload,f,protocol=pickle.HIGHEST_PROTOCOL)
    return ruta

def huella_archivo(path):
    import hashlib
    h=hashlib.sha256();
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
