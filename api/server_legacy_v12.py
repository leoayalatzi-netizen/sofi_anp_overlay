#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API opcional de Nevula 1.2. Solo librería estándar.
POST /chat o /predict con {"texto":"..."}. GET /health y /info.
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from evolucion.vectorizador_hibrido import VectorizadorHibrido
from nucleos.memoria.motores.motor_neuronal import RedNeuronalOptima
OUT=BASE/'almacenamiento'/'modelos'/'evolucionado'
GROUPS=json.loads((OUT/'clasificador_grupo_vocab.json').read_text(encoding='utf-8'))
RG=RedNeuronalOptima.cargar(str(OUT/'clasificador_grupo.anp')); VG=VectorizadorHibrido.cargar(OUT/'clasificador_grupo_vocab.json')
MODELS={}
for g in GROUPS['clases']:
    b=OUT/f'grupo_{g}';
    if b.with_suffix('.anp').exists(): MODELS[g]=(RedNeuronalOptima.cargar(str(b.with_suffix('.anp'))),VectorizadorHibrido.cargar(Path(str(b)+'_vocab.json')),json.loads(Path(str(b)+'_vocab.json').read_text())['clases'])
class Handler(BaseHTTPRequestHandler):
    def _send(self,code,obj):
        data=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path=='/health': return self._send(200,{'ok':True,'modelo':'nevula-1.2-evolucionada'})
        if self.path=='/info': return self._send(200,{'modelo':'nevula-1.2-evolucionada','grupos':GROUPS['clases'],'dominios_por_grupo':{g:m[2] for g,m in MODELS.items()}})
        self._send(404,{'error':'ruta_no_encontrada'})
    def do_POST(self):
        if self.path not in ('/chat','/predict'): return self._send(404,{'error':'ruta_no_encontrada'})
        try:
            n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n)); text=str(body.get('texto','')).strip()
            if not text: return self._send(400,{'error':'texto_vacio'})
            pg=RG.predecir(VG.transformar([text]).T).flatten(); oi=pg.argsort()[::-1]; gi=int(oi[0]); g=GROUPS['clases'][gi]; cg=float(pg[gi]); rr,vv,ds=MODELS[g]; pd=rr.predecir(vv.transformar([text]).T).flatten(); od=pd.argsort()[::-1]; di=int(od[0]); self._send(200,{'exito':True,'dominio':ds[di],'grupo':g,'confianza':round(cg*float(pd[di]),6),'confianza_grupo':round(cg,6),'top3':[{'dominio':ds[int(i)],'confianza':round(cg*float(pd[int(i)]),6)} for i in od[:3]]})
        except Exception as e: self._send(500,{'error':'error_interno','detalle':str(e)})
    def log_message(self,*args): pass
if __name__=='__main__':
    host=os.getenv('NEVULA_HOST','127.0.0.1'); port=int(os.getenv('NEVULA_PORT','8080')); print(f'Nevula API: http://{host}:{port}'); ThreadingHTTPServer((host,port),Handler).serve_forever()
