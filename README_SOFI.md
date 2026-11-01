# Sofi 1.0 — ANP evolucionado
`python principal.py` arranca **Sofi**: el cerebro ANP (28 motores, redes, APEX, memoria, pensamiento autónomo) gobernando la cartera cripto, la búsqueda en internet y un LLM. `python principal.py --consola` abre la consola clásica de ANP.

## 1) Subir a GitHub (con GitHub Desktop, sin comandos)
1. Descomprime el ZIP. Entra a la carpeta `Sofi-ANP`: ahí deben verse `principal.py`, `requirements.txt` y la carpeta `sofi`.
2. GitHub Desktop → File → Add local repository → elige esa carpeta `Sofi-ANP` → "create a repository" → Commit → Publish repository.
3. En github.com comprueba que `requirements.txt` aparece en la raíz del repositorio (no dentro de otra carpeta).
(Con terminal: `git init && git add . && git commit -m "Sofi" && git branch -M main && git remote add origin <repo> && git push -u origin main`.)

## 2) Render (gratis)
New → Web Service → tu repositorio. Language: Python 3. Build: `pip install -r requirements.txt`. Start: `python principal.py`. Instance: Free. Health Check Path (Advanced): `/health`.
Variables (Environment): `SOFI_CLAVE` = tu clave · `SOFI_LLM_PROVIDER` = groq · `SOFI_LLM_KEY` = tu API key de console.groq.com/keys.
El archivo `.python-version` ya fija Python 3.12 (Render usa 3.14 por defecto y no todas las librerías lo soportan).
Opcional: `SOFI_TAVILY_KEY` (tavily.com, plan gratis) para una búsqueda web más fiable; `SOFI_LLM_MODEL` para cambiar de modelo (por defecto qwen/qwen3-32b).

## Cómo piensa Sofi
ANP responde primero (cálculo, conocimiento verificado, memoria). Con LLM, este razona y puede usar herramientas: `buscar_web`, `anp`, `cartera`, `cartera_comando`. Sin LLM, un enrutador por reglas usa ANP y, si no hay evidencia, busca en internet y resume con fuentes.

## Aprendizaje
Cada 👍 se guarda en la memoria de ANP y en un dataset para afinar el LLM (ENTRENAR_LLM.md). Render gratis borra el disco al reiniciar: descarga el dataset desde Mente → Aprendizaje.
