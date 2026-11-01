from __future__ import annotations
from pathlib import Path
import json

class RuntimeSelector:
    """Selecciona el backend más capaz disponible sin romper portabilidad."""
    VERSION='2.5-APEX-runtime'
    def __init__(self, model_dir):
        self.dir=Path(model_dir); self.backend='none'; self.detail=''
        self.onnx=None
        try:
            import onnxruntime as ort
            p=self.dir/'language_core.onnx'
            if p.exists():
                self.onnx=ort.InferenceSession(str(p), providers=['CPUExecutionProvider'])
                self.backend='onnx'; self.detail='onnxruntime-cpu'
        except Exception as e: self.detail=f'onnx-no-disponible:{type(e).__name__}'
    def diagnostico(self): return {'backend':self.backend,'detalle':self.detail,'version':self.VERSION}
