# Cómo subir el proyecto a GitHub

Guía paso a paso. Ejecuta cada bloque en la terminal de VS Code, en orden.

Todos los comandos son de `git` y funcionan igual en CMD y en PowerShell. La
única excepción es el conteo del Paso 3, que trae una versión para cada una.

Si algo falla, **detente y avísame** en vez de seguir al siguiente bloque.

---

## Paso 0 — Situarte en la carpeta correcta

```
cd "C:\Users\GAG\Documents\Maestria\00_Trabajo_de_Grado_TODO\TG_Maestria\TG_Maestria"
```

Comprueba que el prompt termine en `TG_Maestria>` antes de continuar.

---

## Paso 1 — Configurar tu identidad en Git

Solo hace falta la primera vez en este computador.

```
git config --global user.name "Gerardo Aguilar"
git config --global user.email "gerardoaguilarg@proton.me"
```

---

## Paso 2 — Iniciar el repositorio local

```
git init
git branch -M main
git remote add origin https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil.git
```

Si dice `remote origin already exists`, ejecuta esto en su lugar:

```
git remote set-url origin https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil.git
```

---

## Paso 3 — Comprobar qué se va a subir

**No te saltes este paso.** Debe salir alrededor de 703 archivos y ningún PDF.

```
git add -A
```

Ahora cuenta los archivos. **El comando depende de tu terminal**: mira el prompt.
Si empieza con `PS ` es PowerShell; si empieza directo con `C:\` es CMD.

**En CMD** (prompt tipo `C:\Users\GAG\...>`):

```cmd
git ls-files | find /c /v ""
git ls-files "*.pdf" "*.rtf" "*.sqlite3" "*.bin" | find /c /v ""
```

**En PowerShell** (prompt tipo `PS C:\Users\GAG\...>`):

```powershell
(git ls-files).Count
(git ls-files "*.pdf" "*.rtf" "*.sqlite3" "*.bin").Count
```

La primera cifra debe rondar **703**. La segunda tiene que ser **0**.

Si la segunda no es cero, detente y avísame.

---

## Paso 4 — Commits por fases

Se sube en varios commits temáticos, no todo en uno. Usa Conventional Commits.

```
git reset

git add .gitignore requirements.txt LICENSE LICENSE-DATA README.md SUBIR_A_GITHUB.md
git commit -m "chore: estructura inicial, licencias y documentacion"

git add 04_Golden_Set/
git commit -m "data: agregar golden set de 120 preguntas de derecho civil"

git add 01_Corpus_Raw/Codigo_Civil/ 01_Corpus_Raw/Codigo_Comercio/ 01_Corpus_Raw/Ley_1480/ 01_Corpus_Raw/Ley_222/
git commit -m "data: agregar corpus normativo estructurado por articulos"

git add 01_Corpus_Raw/Sentencias/Corte_Suprema/
git commit -m "data: agregar 245 sentencias de Corte Suprema normalizadas (143 por OCR)"

git add 01_Corpus_Raw/Sentencias/Corte_Constitucional/
git commit -m "data: agregar 411 sentencias de Corte Constitucional recuperadas"

git add 05_Codigo_Fuente/SCRAPERS/
git commit -m "feat: scripts de descarga, validacion de integridad y OCR"

git add 05_Codigo_Fuente/RAG_COT_COV/ 05_Codigo_Fuente/Graficas/
git commit -m "feat: notebooks de indexacion y evaluacion comparativa RAG vs agente"

git add 03_Results/
git commit -m "results: resultados de ambas corridas, telemetria y matrices expertas"

git add -A
git commit -m "chore: archivos restantes" --allow-empty
```

Revisa el historial:

```
git log --oneline
```

---

## Paso 5 — Sincronizar con lo que ya está en GitHub

El repositorio remoto probablemente tenga algún commit (un README creado al abrirlo). Hay que integrarlo antes de subir.

```
git fetch origin
git log --oneline origin/main
```

**Si el segundo comando no muestra nada** (el remoto está vacío), salta al Paso 6.

**Si muestra commits**, intégralos:

```
git pull origin main --allow-unrelated-histories --no-rebase
```

Si se abre un editor pidiendo mensaje de merge, escribe `:wq` y Enter (es Vim).

Si aparece un conflicto en `README.md`, quédate con el tuyo:

```
git checkout --ours README.md
git add README.md
git commit -m "chore: conservar README del proyecto"
```

---

## Paso 6 — Subir

```
git push -u origin main
```

La primera vez pedirá autenticación. Se abrirá una ventana del navegador para iniciar sesión en GitHub. Si en su lugar pide usuario y contraseña en la terminal, **la contraseña no funciona**: necesitas un token personal desde https://github.com/settings/tokens (marca el permiso `repo`).

La subida son unos 59 MB, calcula 1 a 3 minutos.

---

## Paso 7 — Verificar

```
git log --oneline origin/main
```

Y abre en el navegador:
https://github.com/Tiritingo/TG-RAG-vs-CoT-CoV-DerechoCivil

Comprueba que:

- El README se ve formateado, con las tablas y los badges
- Existe `01_Corpus_Raw/Sentencias/Corte_Suprema/texto_plano/` con 245 archivos
- Al abrir cualquier `.txt` se lee la sentencia con acentos correctos
- **No** aparece la carpeta `02_Vectorstore/` ni ningún PDF

---

## Actualizaciones posteriores

Cada vez que cambies algo:

```
cd "C:\Users\GAG\Documents\Maestria\00_Trabajo_de_Grado_TODO\TG_Maestria\TG_Maestria"
git add -A
git status --short
git commit -m "tipo: descripcion breve en presente"
git push
```

Prefijos de Conventional Commits para este proyecto:

| Prefijo | Cuándo usarlo |
|---|---|
| `feat:` | código o funcionalidad nueva |
| `fix:` | corrección de un error |
| `data:` | cambios en el corpus o el golden set |
| `results:` | nuevos resultados o análisis |
| `docs:` | README, metodología, documentación |
| `chore:` | configuración, dependencias, mantenimiento |

Cuando cierres un hito, márcalo con una etiqueta de versión:

```
git tag -a v1.0 -m "results: corpus reparado y reindexado, 62.784 chunks"
git push origin v1.0
```

---

## Si algo sale mal

**«fatal: not a git repository»** — no estás en la carpeta correcta. Vuelve al Paso 0.

**«failed to push some refs»** — el remoto tiene commits que no tienes. Vuelve al Paso 5.

**«file is too large»** — se coló un binario. Detente y avísame; hay que limpiarlo del historial antes de reintentar.

**Subiste algo por error** — no hagas `push --force` sin avisar. Escríbeme primero.
