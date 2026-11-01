from __future__ import annotations
from pathlib import Path
import json, re

class TokenizadorPortable:
    """Tokenizador ligero para runtimes sin SentencePiece.
    Usa la tabla de piezas exportada del tokenizer y una segmentación greedy.
    No pretende replicar al 100% SentencePiece, pero permite inferencia autónoma.
    """
    def __init__(self, vocab_json):
        data=json.loads(Path(vocab_json).read_text(encoding='utf-8'))
        self.pieces=data['pieces']; self.piece_to_id={p:i for i,p in enumerate(self.pieces)}
        self.unk_id=data.get('unk_id',0); self.bos_id=data.get('bos_id',1); self.eos_id=data.get('eos_id',2)
        self.vocab_size=len(self.pieces)
        # longest-first, excluding control pieces
        self.match=[p for p in self.pieces if p and not p.startswith('<')]
        self.match.sort(key=len, reverse=True)
    def encode(self,text):
        # SentencePiece's visible word-boundary marker is U+2581.
        s='▁'+re.sub(r'\s+','▁',str(text).strip())
        out=[]; i=0
        while i<len(s):
            found=None
            for p in self.match:
                if s.startswith(p,i): found=p; break
            if found:
                out.append(self.piece_to_id[found]); i+=len(found)
            else:
                ch=s[i]; out.append(self.piece_to_id.get(ch,self.unk_id)); i+=1
        return out
    def decode(self,ids):
        s=''.join(self.pieces[int(i)] if 0<=int(i)<len(self.pieces) else '�' for i in ids)
        return s.replace('▁',' ').strip()
