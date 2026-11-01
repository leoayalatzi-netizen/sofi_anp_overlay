"""Servidor web de Sofi: acceso con clave, API, interfaz. Solo biblioteca estándar. Lee $PORT (Render)."""
import hashlib, hmac, json, os, re, secrets, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from . import llm, buscador
from .cerebro import Sofi, SYS, RAIZ
DATA=Path(os.environ.get("SOFI_DATA") or RAIZ/"datos_sofi")
try: DATA.mkdir(parents=True,exist_ok=True)
except Exception: pass
CLAVE=os.environ.get("SOFI_CLAVE")
if not CLAVE: CLAVE=secrets.token_urlsafe(9); print(f"[Sofi] SOFI_CLAVE no definida. Clave temporal: {CLAVE}",flush=True)
SECRET=(os.environ.get("SOFI_SECRET") or hashlib.sha256(("sofi|"+CLAVE).encode()).hexdigest()).encode()
FALLOS={}; S=Sofi(DATA)
def firmar(e): return hmac.new(SECRET,str(e).encode(),"sha256").hexdigest()
def token(): e=int(time.time())+30*86400; return f"{e}.{firmar(e)}"
def valido(t):
    try: e,s=t.split("."); return int(e)>time.time() and hmac.compare_digest(s,firmar(e))
    except Exception: return False
def bloqueado(ip): n,t=FALLOS.get(ip,(0,0)); return n>=5 and time.time()-t<300
def fallo(ip): n,t=FALLOS.get(ip,(0,0)); FALLOS[ip]=(1 if time.time()-t>300 else n+1,time.time())
CSP="default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.binance.com https://data-api.binance.vision; frame-ancestors 'none'"
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def ip(self): return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
    def auth(self): m=re.search(r"sofi=([^;]+)",self.headers.get("Cookie","")); return bool(m and valido(m.group(1)))
    def out(self,c,raw,ct="application/json; charset=utf-8",extra=()):
        self.send_response(c); self.send_header("Content-Type",ct); self.send_header("Content-Length",str(len(raw)))
        self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Referrer-Policy","no-referrer"); self.send_header("Cache-Control","no-store")
        if ct.startswith("text/html"): self.send_header("Content-Security-Policy",CSP)
        for k,v in extra: self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def j(self,c,o,extra=()): self.out(c,json.dumps(o,ensure_ascii=False,default=str).encode(),extra=extra)
    def body(self): return json.loads(self.rfile.read(min(int(self.headers.get("Content-Length",0) or 0),3_000_000)) or b"{}")
    def do_GET(self):
        p=self.path.split("?")[0]
        if p=="/health": return self.j(200,{"ok":True})
        if p=="/api/me": return self.j(200 if self.auth() else 401,{"ok":self.auth(),"anp":S.estado["anp"],"llm":llm.activo()})
        if p.startswith("/api/"):
            if not self.auth(): return self.j(401,{})
            if p=="/api/cartera": f=DATA/"cartera.json"; return self.j(200,json.loads(f.read_text()) if f.exists() else {})
            if p=="/api/mente": return self.j(200,S.mente())
            if p=="/api/dataset": return self.out(200,S.apr.dataset(SYS).encode(),"application/x-ndjson; charset=utf-8",[("Content-Disposition","attachment; filename=dataset_sofi.jsonl")])
            return self.j(404,{})
        self.out(200,(Path(__file__).parent/"static"/"index.html").read_bytes(),"text/html; charset=utf-8")
    def do_POST(self):
        p=self.path
        try:
            if p=="/api/login":
                ip=self.ip()
                if bloqueado(ip): return self.j(429,{"error":"Demasiados intentos. Espera 5 minutos."})
                if hmac.compare_digest(str(self.body().get("clave","")).encode(),CLAVE.encode()):
                    FALLOS.pop(ip,None); sec="; Secure" if self.headers.get("X-Forwarded-Proto")=="https" else ""
                    return self.j(200,{"ok":True},[("Set-Cookie",f"sofi={token()}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000{sec}")])
                fallo(ip); return self.j(401,{"error":"Clave incorrecta."})
            if p=="/api/logout": return self.j(200,{"ok":True},[("Set-Cookie","sofi=; HttpOnly; Path=/; Max-Age=0")])
            if not self.auth(): return self.j(401,{"error":"auth"})
            d=self.body()
            if p=="/api/chat": return self.j(200,S.responder(str(d.get("texto",""))[:2000],d.get("cartera"),d.get("hist") or []))
            if p=="/api/feedback": return self.j(200,{"ok":S.feedback(str(d.get("id")),1 if d.get("v")==1 else -1)})
            self.j(404,{})
        except Exception as e: self.j(400,{"error":str(e)})
    def do_PUT(self):
        if self.path!="/api/cartera" or not self.auth(): return self.j(401,{})
        try: (DATA/"cartera.json").write_text(json.dumps(self.body())); self.j(200,{"ok":True})
        except Exception as e: self.j(500,{"error":str(e)})
def servir(puerto=None):
    threading.Thread(target=S.cargar,daemon=True).start()
    p=int(puerto or os.environ.get("PORT",8080)); print(f"[Sofi] escuchando en 0.0.0.0:{p}",flush=True)
    try: ThreadingHTTPServer(("0.0.0.0",p),H).serve_forever()
    except KeyboardInterrupt: pass
    return 0
