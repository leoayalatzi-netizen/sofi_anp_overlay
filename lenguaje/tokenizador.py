from __future__ import annotations
from pathlib import Path
import sentencepiece as spm

class TokenizadorNevula:
    def __init__(self, model_path: str|Path):
        self.model_path=Path(model_path); self.sp=spm.SentencePieceProcessor(model_file=str(self.model_path))
        self.pad_id=self.sp.pad_id(); self.bos_id=self.sp.bos_id(); self.eos_id=self.sp.eos_id(); self.unk_id=self.sp.unk_id()
        self.vocab_size=self.sp.get_piece_size()
    def encode(self,text): return self.sp.encode(str(text),out_type=int)
    def decode(self,ids): return self.sp.decode([int(x) for x in ids])
