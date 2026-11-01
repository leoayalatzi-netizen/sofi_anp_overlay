"""Búsqueda en internet para Sofi/ANP: Tavily/Brave (si hay clave) → DuckDuckGo → Wikipedia. Lee páginas y resume. Solo stdlib."""
import html as H, ipaddress, json, os, re, socket, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ULT={"motor":None,"error":None,"n":0}
def _get(url,data=None,headers=None,timeout=12,tope=1_500_000):
    h={"User-Agent":UA,"Accept-Language":"es-MX,es;q=0.9,en;q=0.6"}; h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h),timeout=timeout) as r:
        raw=r.read(tope); return raw.decode(r.headers.get_content_charset() or "utf-8","replace"),r.headers.get("Content-Type","")
def _limpia(s): return re.sub(r"\s+"," ",H.unescape(re.sub(r"<[^>]+>"," ",s or ""))).strip()
def _seguro(url):
    try:
        u=urllib.parse.urlparse(url)
        if u.scheme not in("http","https") or not u.hostname: return False
        for f in socket.getaddrinfo(u.hostname,None):
            ip=ipaddress.ip_address(f[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: return False
        return True
    except Exception: return False
def _tavily(q,n):
    k=os.environ.get("SOFI_TAVILY_KEY")
    if not k: return []
    d=json.loads(_get("https://api.tavily.com/search",json.dumps({"api_key":k,"query":q,"max_results":n,"search_depth":"basic"}).encode(),{"Content-Type":"application/json"})[0])
    return [{"titulo":x.get("title",""),"url":x.get("url",""),"snippet":x.get("content","")[:400],"texto":x.get("content","")} for x in d.get("results",[])]
def _brave(q,n):
    k=os.environ.get("SOFI_BRAVE_KEY")
    if not k: return []
    d=json.loads(_get("https://api.search.brave.com/res/v1/web/search?"+urllib.parse.urlencode({"q":q,"count":n,"search_lang":"es"}),headers={"X-Subscription-Token":k,"Accept":"application/json"})[0])
    return [{"titulo":_limpia(x.get("title")),"url":x.get("url",""),"snippet":_limpia(x.get("description"))} for x in d.get("web",{}).get("results",[])]
def parse_ddg(page,n=5):
    out=[]
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>",page,re.S):
        a,inner=m.group(1),m.group(2)
        if "result__a" in a:
            h=re.search(r'href="([^"]+)"',a)
            if not h: continue
            u=H.unescape(h.group(1))
            if u.startswith("//"): u="https:"+u
            if "duckduckgo.com/l/" in u: u=urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("uddg",[""])[0]
            if u.startswith("http") and "duckduckgo.com/y.js" not in u: out.append({"titulo":_limpia(inner),"url":u,"snippet":""})
        elif "result__snippet" in a and out and not out[-1]["snippet"]: out[-1]["snippet"]=_limpia(inner)
    return out[:n]
def _ddg(q,n):
    page,_=_get("https://html.duckduckgo.com/html/",urllib.parse.urlencode({"q":q,"kl":"mx-es"}).encode(),{"Content-Type":"application/x-www-form-urlencoded","Referer":"https://html.duckduckgo.com/"})
    return parse_ddg(page,n)
def _wiki(q,n):
    d=json.loads(_get("https://es.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","list":"search","srsearch":q,"format":"json","srlimit":min(n,3),"utf8":1}))[0])
    out=[{"titulo":x["title"],"url":"https://es.wikipedia.org/wiki/"+urllib.parse.quote(x["title"].replace(" ","_")),"snippet":_limpia(x.get("snippet"))} for x in d.get("query",{}).get("search",[])]
    if out:
        try: out[0]["texto"]=json.loads(_get("https://es.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(out[0]["titulo"].replace(" ","_")))[0]).get("extract","")
        except Exception: pass
    return out
MOTORES=[("tavily",_tavily),("brave",_brave),("duckduckgo",_ddg),("wikipedia",_wiki)]
def buscar(q,n=5):
    errs=[]
    for nombre,f in MOTORES:
        try:
            r=[x for x in f(q,n) if x.get("url")]
            if r: ULT.update(motor=nombre,error=None,n=len(r)); return r
        except Exception as e: errs.append(f"{nombre}: {type(e).__name__}")
    ULT.update(motor=None,error="; ".join(errs) or "sin resultados",n=0); return []
class _T(HTMLParser):
    SKIP={"script","style","noscript","nav","footer","header","aside","form","svg","iframe"}; KEEP={"p","li","h1","h2","h3"}
    def __init__(s): super().__init__(convert_charrefs=True); s.skip=0; s.keep=0; s.cur=[]; s.buf=[]
    def handle_starttag(s,t,a):
        if t in s.SKIP: s.skip+=1
        elif t in s.KEEP: s.keep+=1
    def handle_endtag(s,t):
        if t in s.SKIP and s.skip: s.skip-=1
        elif t in s.KEEP:
            s.keep=max(0,s.keep-1)
            if not s.keep:
                x=" ".join("".join(s.cur).split()); s.cur=[]
                if len(x)>40: s.buf.append(x)
    def handle_data(s,d):
        if s.keep and not s.skip: s.cur.append(d)
def leer(url):
    if not _seguro(url): return ""
    try:
        page,ct=_get(url,timeout=9)
        if "html" not in ct and "text" not in ct: return ""
        p=_T(); p.feed(page[:800000]); return " ".join(p.buf)[:4000]
    except Exception: return ""
def investigar(q,n=5,leer_n=3):
    r=buscar(q,n)
    if not r: return {"consulta":q,"motor":None,"resultados":[]}
    falta=[x for x in r[:leer_n] if not x.get("texto") and _seguro(x["url"])]
    if falta:
        with ThreadPoolExecutor(len(falta)) as ex:
            for x,t in zip(falta,ex.map(lambda z:leer(z["url"]),falta)):
                if t: x["texto"]=t
    return {"consulta":q,"motor":ULT["motor"],"resultados":r}
def resumen_extractivo(q,res):
    tk=set(re.findall(r"\w{4,}",q.lower())); c=[]
    for i,r in enumerate(res,1):
        for s in re.split(r"(?<=[.!?])\s+",(r.get("texto") or "")[:3000]+" "+r.get("snippet","")):
            s=s.strip()
            if 40<len(s)<320: c.append((len(tk&set(re.findall(r"\w{4,}",s.lower())))/(1+len(tk)**.5),i,s))
    c.sort(reverse=True); out=[]; vistos=set()
    for sc,i,s in c:
        if sc>0 and s[:40] not in vistos and len(out)<4: vistos.add(s[:40]); out.append(f"{s} [{i}]")
    return " ".join(out)
def estado(): return {"motores":[n for n,_ in MOTORES if n in("duckduckgo","wikipedia") or os.environ.get("SOFI_"+n.upper()+"_KEY")],"ultima":ULT}
