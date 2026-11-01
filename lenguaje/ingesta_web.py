#!/usr/bin/env python3
"""Adquisición web controlada para el corpus de Nevula 2.1.

Sólo procesa URLs proporcionadas explícitamente. Respeta robots.txt cuando puede
consultarlo, guarda procedencia, hash y fecha, y deja todo cacheado para uso offline.
"""
from __future__ import annotations
import hashlib,json,re,time,urllib.robotparser
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse,urljoin
BASE=Path(__file__).resolve().parents[1]

class IngestorWeb:
    def __init__(self,root=None):
        self.root=Path(root or BASE/'almacenamiento/web_corpus'); self.raw=self.root/'raw'; self.raw.mkdir(parents=True,exist_ok=True)
        self.ua='NevulaLanguageCore/2.1 (+controlled-corpus; offline-cache)'
    def _id(self,url): return hashlib.sha256(url.encode()).hexdigest()[:20]
    def _robots(self,url):
        p=urlparse(url); robots=urljoin(f'{p.scheme}://{p.netloc}','/robots.txt')
        rp=urllib.robotparser.RobotFileParser(); rp.set_url(robots)
        try: rp.read(); return rp.can_fetch(self.ua,url),robots
        except Exception: return True,robots
    def descargar(self,url,timeout=20,require_robots=True):
        if urlparse(url).scheme not in ('http','https'): raise ValueError('Sólo se aceptan URLs HTTP/HTTPS')
        allowed,robots=self._robots(url)
        if require_robots and not allowed: raise PermissionError('robots.txt no permite esta URL')
        req=Request(url,headers={'User-Agent':self.ua,'Accept':'text/html,text/plain;q=0.9,*/*;q=0.1'})
        data=urlopen(req,timeout=timeout).read(); text=data.decode('utf-8','ignore')
        text=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<noscript[\s\S]*?</noscript>',' ',text,flags=re.I)
        text=re.sub(r'<[^>]+>',' ',text); text=re.sub(r'\s+',' ',text).strip()
        rec={'url':url,'host':urlparse(url).netloc,'retrieved_at':time.time(),'retrieved_iso':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'robots_checked':robots,'sha256':hashlib.sha256(text.encode()).hexdigest(),'chars':len(text),'text':text}
        (self.raw/f'{self._id(url)}.json').write_text(json.dumps(rec,ensure_ascii=False),encoding='utf8'); return rec
    def importar_urls(self,urls):
        return [self._safe(u) for u in urls]
    def _safe(self,u):
        try: return self.descargar(u)
        except Exception as e: return {'url':u,'error':str(e)}
    def exportar_texto(self,out=None):
        out=Path(out or self.root/'internet_corpus.txt'); seen=set(); lines=[]
        for p in sorted(self.raw.glob('*.json')):
            try: r=json.loads(p.read_text(encoding='utf8'))
            except Exception: continue
            t=r.get('text',''); h=r.get('sha256')
            if t and h not in seen: seen.add(h); lines.append(t)
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text('\n'.join(lines),encoding='utf8'); return {'documentos':len(lines),'ruta':str(out)}

def ingestar_urls(urls): return IngestorWeb().importar_urls(urls)
