"""Escalas 2.3.1: mobile conserva portabilidad; evolution prioriza calidad."""
PRESETS={
 'mobile':dict(block_size=128,d_model=192,n_layers=4,n_heads=4,kv_heads=2,vocab=4096),
 'small':dict(block_size=256,d_model=384,n_layers=8,n_heads=6,kv_heads=3,vocab=8192),
 'evolution':dict(block_size=512,d_model=512,n_layers=12,n_heads=8,kv_heads=4,vocab=16384),
 'large':dict(block_size=1024,d_model=768,n_layers=16,n_heads=12,kv_heads=4,vocab=32768),
 'xlarge':dict(block_size=2048,d_model=1024,n_layers=24,n_heads=16,kv_heads=8,vocab=32768),
}
def parametros_aprox(vocab,d_model,layers,ff_mult=2.75):
 return int(vocab*d_model+layers*(4*d_model*d_model+2*d_model*int(d_model*ff_mult)))
