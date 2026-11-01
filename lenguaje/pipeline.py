from __future__ import annotations
import json
from pathlib import Path
from .corpus import build_corpus
from .curriculum import construir_curriculum

BASE=Path(__file__).resolve().parents[1]

def preparar(online_urls=None):
    corpus=BASE/'almacenamiento/modelos/lenguaje/corpus.txt'
    # La adquisición web es explícita: no se realiza crawling indiscriminado.
    if online_urls:
        from .ingesta_web import ingestar_urls
        ingestar_urls(online_urls)
    n=build_corpus(corpus)
    curriculum=construir_curriculum(corpus,BASE/'almacenamiento/modelos/lenguaje/curriculum')
    manifest={'lineas':n,'curriculum':curriculum,'online':bool(online_urls),'modo':'offline-cache + online-explicito'}
    (corpus.parent/'pipeline_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    return manifest
