"""Capa LLM de Sofi. Cualquier endpoint compatible con OpenAI. Solo defines SOFI_LLM_PROVIDER + SOFI_LLM_KEY."""
import json, os, re, urllib.request
PRESETS={"groq":("https://api.groq.com/openai/v1/chat/completions","qwen/qwen3-32b"),
"dashscope":("https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions","qwen-plus"),
"openrouter":("https://openrouter.ai/api/v1/chat/completions","qwen/qwen-2.5-72b-instruct"),
"ollama":("http://localhost:11434/v1/chat/completions","qwen3:8b"),
"openai":("https://api.openai.com/v1/chat/completions","gpt-4o-mini")}
ERR={"e":None}
def config():
    p=(os.environ.get("SOFI_LLM_PROVIDER") or "").strip().lower()
    url=os.environ.get("SOFI_LLM_URL") or os.environ.get("NEVULA_LLM_URL"); mod=os.environ.get("SOFI_LLM_MODEL") or os.environ.get("NEVULA_LLM_MODEL")
    if p in PRESETS: url=url or PRESETS[p][0]; mod=mod or PRESETS[p][1]
    return p or ("personalizado" if url else ""),url,os.environ.get("SOFI_LLM_KEY") or os.environ.get("NEVULA_LLM_API_KEY"),mod or "qwen-plus"
def activo(): return bool(config()[1])
def estado(): p,u,k,m=config(); return {"activo":bool(u),"proveedor":p,"modelo":m if u else None,"clave":bool(k),"error":ERR["e"]}
def chat(messages,temperature=.4,timeout=55):
    p,url,key,mod=config()
    if not url: return None
    h={"Content-Type":"application/json"}
    if key: h["Authorization"]="Bearer "+key
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,json.dumps({"model":mod,"messages":messages,"temperature":temperature}).encode(),h),timeout=timeout)
        x=json.load(r)["choices"][0]["message"]["content"]; ERR["e"]=None
        return re.sub(r"<think>.*?</think>","",x or "",flags=re.S).strip() or None
    except urllib.error.HTTPError as e:
        try: d=e.read().decode()[:160]
        except Exception: d=""
        ERR["e"]=f"HTTP {e.code} {d}"
    except Exception as e: ERR["e"]=f"{type(e).__name__}: {str(e)[:100]}"
    return None
