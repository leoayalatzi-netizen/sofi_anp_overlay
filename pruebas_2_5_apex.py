from __future__ import annotations
import tempfile
from pathlib import Path
from lenguaje.core import LanguageCore
from cognicion.memoria_jerarquica import MemoriaJerarquica


def check(name, cond, detail=''):
    if not cond:
        raise AssertionError(f'{name}: {detail}')
    print(f'OK  {name}')


def main():
    c=LanguageCore()
    d=c.diagnostico()
    check('version 2.5', d['version']=='2.5-APEX', d)
    check('backend APEX/portable', d['backend'] in ('apex-torch','torch','numpy-portable','fallback'), d['backend'])

    r=c.responder('¿Qué es la célula?') or ''
    check('conocimiento grounded', 'unidad estructural' in r.lower(), r)

    r=c.responder('¿Cuánto es 37 * 24?') or ''
    check('herramienta cálculo', '888' in r, r)
    check('verificador cálculo', bool(c.traza_ultima() and c.traza_ultima()['verificaciones'][-1]['aprobado']))

    r=c.responder('Explica la diferencia entre correlación y causalidad.') or ''
    check('razonamiento causalidad', 'no demuestra causalidad' in r.lower(), r)

    r=c.responder('¿Cómo resolver un problema complejo?') or ''
    check('planificación', 'subproblemas' in r.lower() and 'dependencias' in r.lower(), r)
    trace=c.traza_ultima(); check('traza cognitiva', trace is not None and len(trace['pasos'])>=4, str(trace))
    check('sin fuga de prompt', all(x not in r for x in ('<|system|>','INSTRUCCIÓN:','PREGUNTA DEL USUARIO:')))

    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'mem.db'
        m=MemoriaJerarquica(p);m.registrar_semantica('proyecto','Nevula APEX usa memoria jerárquica')
        del m
        m2=MemoriaJerarquica(p); rows=m2.recordar('memoria jerárquica Nevula',k=3)
        check('memoria persistente', bool(rows), rows)
        check('capa semántica', rows[0]['capa']=='semantica', rows[0])
    print('TODAS LAS PRUEBAS 2.5 PASARON')

if __name__=='__main__': main()
