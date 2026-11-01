from __future__ import annotations
import json,platform,sys,time
from .core import LanguageCore

def run():
 c=LanguageCore(); d=c.diagnostico(); d.update({'python':sys.version.split()[0],'platform':platform.platform(),'machine':platform.machine(),'timestamp':time.strftime('%Y-%m-%dT%H:%M:%S')}); print(json.dumps(d,ensure_ascii=False,indent=2)); return d
if __name__=='__main__':run()
