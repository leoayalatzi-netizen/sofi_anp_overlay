"""Convierte datos propios de Nevula a formato conversacional JSONL.

Entradas admitidas:
- JSONL con `messages`, `instruction`/`input`/`output`, `prompt`/`completion`,
  o `question`/`answer`.
- JSON que contenga una lista de esos objetos.
- TXT con ejemplos etiquetados <|system|>, <|user|>, <|assistant|>.
No convierte texto libre en preguntas/respuestas inventadas.
"""
from __future__ import annotations
import argparse, hashlib, json, random, re
from pathlib import Path

TAGGED = re.compile(r"(?:(?:<\|system\|>\s*(.*?)\s*)?)<\|user\|>\s*(.*?)\s*<\|assistant\|>\s*(.*)", re.S)
DEFAULT_SYSTEM = (
    "Eres Nevula, un asistente útil, honesto y preciso. Responde en el idioma del usuario. "
    "No inventes hechos; expresa incertidumbre cuando no tengas evidencia suficiente."
)

def clean_text(x):
    if isinstance(x, list):
        return "\n".join(str(y) for y in x).strip()
    return str(x or "").strip()

def normalize_record(obj):
    if not isinstance(obj, dict): return None
    if isinstance(obj.get("messages"), list):
        messages=[]
        for m in obj["messages"]:
            if not isinstance(m, dict): continue
            role=str(m.get("role", "")).strip().lower()
            content=clean_text(m.get("content", ""))
            if role in {"system", "user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        if any(m["role"]=="user" for m in messages) and any(m["role"]=="assistant" for m in messages):
            if not any(m["role"]=="system" for m in messages): messages.insert(0,{"role":"system","content":DEFAULT_SYSTEM})
            return {"messages": messages}
    user = obj.get("instruction", obj.get("prompt", obj.get("question", obj.get("user"))))
    extra = clean_text(obj.get("input", ""))
    assistant = obj.get("output", obj.get("completion", obj.get("answer", obj.get("response", obj.get("assistant")))))
    if user is not None and assistant is not None:
        user=clean_text(user); assistant=clean_text(assistant)
        if extra: user += "\n\nContexto:\n" + extra
        if user and assistant:
            system=clean_text(obj.get("system", DEFAULT_SYSTEM))
            return {"messages":[{"role":"system","content":system},{"role":"user","content":user},{"role":"assistant","content":assistant}]}
    return None

def load_path(path: Path):
    suffix=path.suffix.lower()
    if suffix == ".jsonl":
        for n,line in enumerate(path.read_text(encoding="utf-8",errors="ignore").splitlines(),1):
            if not line.strip(): continue
            try: obj=json.loads(line)
            except json.JSONDecodeError: print(f"AVISO: JSON inválido en {path}:{n}"); continue
            rec=normalize_record(obj)
            if rec: yield rec
    elif suffix == ".json":
        try: data=json.loads(path.read_text(encoding="utf-8",errors="ignore"))
        except json.JSONDecodeError as e:
            print(f"AVISO: JSON inválido en {path}: {e}"); return
        if isinstance(data,dict): data=data.get("data", data.get("examples", [data]))
        if isinstance(data,list):
            for obj in data:
                rec=normalize_record(obj)
                if rec: yield rec
    elif suffix in {".txt", ".md"}:
        for line in path.read_text(encoding="utf-8",errors="ignore").splitlines():
            match=TAGGED.fullmatch(line.strip())
            if not match: continue
            system,user,assistant=match.groups()
            user=clean_text(user); assistant=clean_text(assistant)
            if user and assistant:
                yield {"messages":[{"role":"system","content":clean_text(system) or DEFAULT_SYSTEM},{"role":"user","content":user},{"role":"assistant","content":assistant}]}

def fingerprint(rec):
    user="\n".join(m["content"] for m in rec["messages"] if m["role"]=="user").lower()
    assistant="\n".join(m["content"] for m in rec["messages"] if m["role"]=="assistant").lower()
    return hashlib.sha256((user+"\0"+assistant).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", nargs="+", required=True, help="Uno o más .jsonl, .json, .txt o .md")
    ap.add_argument("--out", default="entrenamiento/llm_moderno/data")
    ap.add_argument("--validation-ratio", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=20261026)
    ap.add_argument("--min-examples", type=int, default=100)
    args=ap.parse_args()
    if not 0.01 <= args.validation_ratio <= 0.3: raise SystemExit("validation-ratio debe estar entre 0.01 y 0.30")
    rows=[]; seen=set(); candidates=0
    for raw in args.input:
        p=Path(raw)
        if not p.exists(): raise SystemExit(f"No existe el archivo: {p}")
        for rec in load_path(p):
            candidates += 1
            fp=fingerprint(rec)
            if fp not in seen: seen.add(fp); rows.append(rec)
    rng=random.Random(args.seed); rng.shuffle(rows)
    if len(rows)<2: raise SystemExit(f"Solo se encontraron {len(rows)} ejemplos conversacionales válidos. Añade ejemplos curados; el texto libre no se convierte automáticamente en diálogos.")
    n_val=max(1,round(len(rows)*args.validation_ratio)); val=rows[:n_val]; train=rows[n_val:]
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    for name,data in (("train.jsonl",train),("validation.jsonl",val)):
        with (out/name).open("w",encoding="utf-8") as f:
            for rec in data: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
    report={"examples_total":len(rows),"train_examples":len(train),"validation_examples":len(val),"duplicates_removed":candidates - len(rows),"sources":[str(Path(p)) for p in args.input],"warning":None if len(rows)>=args.min_examples else f"Solo {len(rows)} ejemplos. Esto valida el pipeline, pero normalmente es insuficiente para una especialización robusta; amplía y revisa el conjunto."}
    (out/"dataset_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["warning"]: print("\nADVERTENCIA:",report["warning"])
if __name__=="__main__": main()
