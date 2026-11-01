#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Nevula 1.3.
Compatibilidad:
GET  /health /info /v1/models /v1/memory?session_id=...
POST /chat {"texto":...,"session_id":...,"generativo":true}
POST /predict {"texto":...}
POST /v1/chat/completions (OpenAI-compatible envelope)

El generador externo es OPCIONAL y se activa con:
NEVULA_LLM_URL, NEVULA_LLM_API_KEY (opcional), NEVULA_LLM_MODEL.
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(BASE))
from evolucion.cerebro_conversacional import ConversationBrain

BRAIN=ConversationBrain()
VERSION="1.3-CUANTICA"
class Handler(BaseHTTPRequestHandler):
    def send_json(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get("Content-Length","0") or 0)
        return json.loads(self.rfile.read(n) or b"{}")
    def do_GET(self):
        if self.path==" /health": self.path="/health"
        if self.path=="/health":
            return self.send_json(200,{"ok":True,"modelo":"nevula-"+VERSION,"generacion_externa":bool(os.getenv("NEVULA_LLM_URL"))})
        if self.path=="/info":
            return self.send_json(200,{"modelo":"nevula-"+VERSION,"capacidades":["memoria_multiturno","resolucion_referencias","continuidad_tematica","hechos_explicitos","clasificacion_neuronal","api_openai_compatible","llm_externo_opcional"]})
        if self.path=="/v1/models":
            return self.send_json(200,{"object":"list","data":[{"id":"nevula-"+VERSION,"object":"model","owned_by":"ANP"}]})
        if self.path.startswith("/v1/memory"):
            import urllib.parse
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            sid=q.get("session_id",[None])[0]
            if not sid: return self.send_json(400,{"error":"session_id_requerido"})
            return self.send_json(200,BRAIN.history(sid))
        return self.send_json(404,{"error":"ruta_no_encontrada"})
    def do_POST(self):
        try: data=self.body()
        except Exception: return self.send_json(400,{"error":"json_invalido"})
        try:
            if self.path in ("/chat","/predict"):
                text=str(data.get("texto",data.get("mensaje",""))).strip()
                if not text: return self.send_json(400,{"error":"texto_vacio"})
                sid=data.get("session_id")
                result=BRAIN.process(sid,text)
                if self.path=="/chat":
                    generated=None
                    if data.get("generativo",True):
                        generated=BRAIN.llm(result["session_id"],text)
                    if generated:
                        result["respuesta"]=generated
                        BRAIN.add_assistant(result["session_id"],generated)
                    else:
                        # Respuesta de continuidad; no pretende sustituir a un LLM.
                        topic=result["tema_actual"] or "eso"
                        result["respuesta"]=f"Entiendo. Seguimos con {topic}. Tengo presente lo que acabamos de hablar y puedo continuar desde ahí."
                        BRAIN.add_assistant(result["session_id"],result["respuesta"])
                return self.send_json(200,result)
            if self.path=="/v1/chat/completions":
                msgs=data.get("messages",[])
                user=next((m.get("content","") for m in reversed(msgs) if m.get("role")=="user"),"")
                sid=data.get("session_id") or data.get("user") or None
                result=BRAIN.process(sid,user)
                answer=BRAIN.llm(result["session_id"],user)
                if not answer:
                    answer=f"Entiendo. Continuemos desde {result['tema_actual'] or 'lo anterior'}."
                BRAIN.add_assistant(result["session_id"],answer)
                return self.send_json(200,{"id":"chatcmpl-nevula","object":"chat.completion","model":"nevula-"+VERSION,
                    "choices":[{"index":0,"message":{"role":"assistant","content":answer},"finish_reason":"stop"}],
                    "nevula":{"session_id":result["session_id"],"intencion":result["intencion"],"dominio":result["dominio"],"resumen":result["resumen"]}})
            return self.send_json(404,{"error":"ruta_no_encontrada"})
        except Exception as e:
            return self.send_json(500,{"error":"error_interno","detalle":str(e)})
    def log_message(self,*args): pass

if __name__=="__main__":
    host=os.getenv("NEVULA_HOST","127.0.0.1"); port=int(os.getenv("NEVULA_PORT","8080"))
    print(f"Nevula 1.3 API: http://{host}:{port}")
    ThreadingHTTPServer((host,port),Handler).serve_forever()
