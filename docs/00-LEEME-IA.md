# Reglas para cualquier LLM

Este archivo viaja dentro de cada bundle. Léelo completo antes de escribir nada.

## Tu trabajo

Recibes un **bundle** con **una** tarea. Haces solo esa tarea y respondes con **tres bloques** (ver «Entrega»).

El bundle trae, en este orden: el árbol actual del repo · el «Entorno del usuario» · la tarjeta de la tarea · los documentos que la tarjeta manda leer · el contenido actual de los archivos de `Tocar:` que ya existen.

## Reglas

1. Haz solo la tarea del bundle.
2. Usa solo lo que trae el bundle. No supongas archivos que no estén en el árbol.
3. Tests primero: cada criterio de aceptación queda como un test. Los «Ejemplos aprobados» de la tarjeta van en los tests tal cual, con sus valores esperados.
4. Modifica solo los archivos de `Tocar:`. En `Tocar:` el `*` es recursivo: `src/inicio/*` incluye sus subcarpetas. Si necesitas otro archivo, no lo toques: anótalo en *Pendientes* del reporte. Lo que la tarjeta pone en «Fuera de alcance» no se construye, aunque parezca razonable.
5. Dependencias nuevas: decláralas en el archivo de dependencias y en *Decisiones tomadas*.
6. Decisión que afecta a otras tareas: **pregunta** antes de seguir (es lo único que puedes escribir fuera de los tres bloques). Decisión local: decídela y regístrala en el reporte.
7. No edites archivos de estado compartido: `docs/plan/` (incluido `ESTADO.md`) ni `docs/decisiones/`. Los mantiene `tools/cerrar.py`.
8. Máximo dos intentos por fallo. Al segundo, para y reporta qué probaste. Al reintentar tras tests que fallan, **no modifiques los tests que ya existían**: corrige el código.
9. Entrega los tres bloques como se explica en «Entrega».
10. Respeta las «Convenciones» y usa solo los comandos de «Comandos» (más abajo).

## Cómo leer la tarjeta

- **Cubre**: criterios y requisitos que la tarea satisface. **Depende de**: tareas que ya deben estar hechas.
- **Modo** (opcional): `estricto` = la tarea son dos parches y el usuario te dice cuál toca. Parche 1: solo tests y, si hace falta para importarlos, un esqueleto que lance «no implementado» (en Python, `NotImplementedError`); deben fallar por falta de funcionalidad, no por un error de importación. Su bloque de comandos termina en el test, sin commit (el rojo es lo esperado); el commit (`test: …`) va en un segundo bloque que el usuario pega solo si el rojo es el correcto. Parche 2: implementa sin tocar esos tests (vienen en `Leer:` y `No tocar:`).
- **Leer (solo esto)**: los únicos documentos que debes consultar. Un ADR citado ahí ya está aceptado.
- **Contrato**: cómo llamas a otro módulo. Si la pieza real aún no existe, usa el *stub* que indica la tarjeta; no implementes el otro módulo.
- **Produce**: contratos u otros archivos que esta tarea deja listos para otras tareas.
- **Tocar** / **No tocar**: lo que puedes y no puedes cambiar. **Fuera de alcance**: lo que no debes construir en esta tarea.
- **Ejemplos aprobados** (opcionales): casos «entrada → resultado» que la persona aprobó. Inclúyelos en los tests tal cual; no cambies sus valores esperados.
- **Criterios de aceptación**: máximo 4. Los marcados `[verifica: CI]` solo se comprueban en el CI de GitHub: impleméntalos, pero di en el reporte que no los verificaste.
- **Comando de test**: el de la sección «Comandos», aplicado solo a la ruta que indica la tarjeta.

## Entrega: tres bloques

Sin texto fuera de los bloques (salvo una pregunta bloqueante). Cada bloque va en su propia valla de código; usa cuatro acentos graves si el contenido ya contiene vallas de tres.

### 1. Parche

Un solo `git diff` en formato unificado:

- Rutas con `a/` y `b/`, 3 líneas de contexto, archivos nuevos con `--- /dev/null`.
- Termina con un salto de línea (un parche cortado da *corrupt patch*).
- El usuario lo aplica con `git apply`. Si falla con *corrupt patch*, repite con `--recount`: por eso los números de los encabezados `@@` pueden ser aproximados. Las líneas de contexto no: deben ser exactas.
- Si el usuario te pega tests que fallan, corrige el código, no los tests: el parche nuevo no debe modificar ningún test que ya existía. Si crees que un test está mal, dilo y espera su respuesta. El parche anterior sigue aplicado en su repo, sin guardar: el nuevo parte de ese estado.
- Si el usuario te pega un error de `git apply`, responde solo con la parte corregida (el archivo y el bloque `@@` que falló, con sus encabezados `---` y `+++`), no con el parche entero.

### 2. Reporte

Sigue `docs/plantillas/reporte.md`: seis secciones, en este orden y con estos títulos exactos (los revisa `tools/cerrar.py`):

**Hecho** · **Supuestos** · **Decisiones tomadas** · **Pendientes** · **Cómo probar** · **Mensaje de commit sugerido**

- *Decisiones tomadas* puede decir «ninguna». Si una decisión afecta a otras tareas, termina su línea con «Afecta a otras tareas».
- Di qué verificaste y qué **no** (por ejemplo, el CI de GitHub). No afirmes haber corrido algo que no corriste.

### 3. Comandos para aplicar

Un bloque de comandos listo para pegar, con la terminal y las rutas del «Entorno del usuario» del bundle. PowerShell no se detiene solo cuando falla un comando externo (un test, por ejemplo), así que cada paso lleva su freno: corre solo si el anterior salió bien. Modelo para PowerShell:

```powershell
cd "<carpeta del repo>"
git status --short   # debe salir vacío
git apply --check "<carpeta de parches>\<tarea>-<tema>.patch"
if ($LASTEXITCODE -eq 0) { git apply "<carpeta de parches>\<tarea>-<tema>.patch" }
if ($LASTEXITCODE -eq 0) { <comando de test de la tarjeta> }   # solo si la tarjeta lo trae
if ($LASTEXITCODE -eq 0) { git add -A; git commit -m "<mensaje de commit del reporte>" }
if ($LASTEXITCODE -eq 0) { git push }
if ($LASTEXITCODE -ne 0) { Write-Host "Algo falló: el bloque se detuvo ahí. Pega aquí lo que dice la terminal." }
```

Reglas del bloque:

- Tú propones el nombre del archivo (`<tarea>-<tema>.patch`) y lo usas igual en todos los comandos.
- Rutas siempre entre comillas.
- El comando de test, si la tarjeta lo trae, va entre `git apply` y el commit.
- El mensaje de commit sale del reporte y es un commit convencional.
- `git status --short` vacío al inicio es lo que hace seguro el `git add -A`: así solo entra lo del parche. En un reintento tras un test fallido, el parche anterior sigue aplicado sin guardar: `git status --short` listará sus archivos (cámbiale el comentario) y el commit guarda los dos parches juntos.

Equivalentes para otras terminales:

| Terminal | Parche en Descargas | Entrar al repo | Comentario |
|---|---|---|---|
| PowerShell | `"$env:USERPROFILE\Downloads\x.patch"` | `cd "<ruta>"` | `#` |
| CMD | `"%USERPROFILE%\Downloads\x.patch"` | `cd /d "<ruta>"` | `REM` |
| Git Bash, macOS, Linux | `"$HOME/Downloads/x.patch"` (Linux en español: `"$HOME/Descargas/x.patch"`) | `cd "<ruta>"` | `#` |

En CMD, Git Bash, macOS y Linux el mismo freno se logra uniendo los comandos con `&&`: se detienen en el primero que falla.

### Si falta el «Entorno del usuario»

El bundle debe traer tres datos: **terminal**, **carpeta de parches** y **carpeta del repo**. Si falta alguno, pregunta **una sola vez** por conversación, solo lo que falte, con este texto:

> Para darte los comandos listos para pegar, necesito tres datos (si no sabes alguno, te digo cómo encontrarlo):
>
> 1. **Terminal:** ¿qué usas para escribir comandos? PowerShell, CMD, Git Bash o la Terminal de Mac/Linux.
> 2. **Carpeta de los parches:** ¿dónde se guardan tus descargas? Normalmente es Descargas; ahí quedará el archivo `.patch`.
> 3. **Carpeta del repo:** abre la terminal dentro de tu repo, escribe `pwd` (en CMD, `cd`) y pégame lo que salga.
>
> Con eso te dejo el bloque completo, desde entrar al repo hasta el `git push`.

Si ya conoces la terminal y la carpeta de parches, solo confirma en una línea: «Uso PowerShell y tu carpeta Descargas; ¿el repo sigue en `<ruta>`?».

## Convenciones

Fijas (vienen de la plantilla):

- Un módulo por carpeta en `src/`; sus tests en `tests/<módulo>/`.
- Commits convencionales: `tipo: descripción corta en español`. Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

Las completa T-001 (cada app decide las suyas con un ADR; la tarjeta de T-001 incluye este archivo en `Tocar:`):

- Idioma de los identificadores del código: *(pendiente)*
- Estructura interna de `src/` y de `tests/`: *(pendiente)*

## Comandos

Los completa T-001 cuando el stack esté decidido. Hasta entonces, no inventes comandos.

- Instalar: *(pendiente)*
- Arrancar: *(pendiente)*
- Tests, todos: *(pendiente)*
- Tests de una ruta o módulo (el que usa la tarjeta, con la ruta como argumento): *(pendiente)*
- Activar el entorno virtual, si el stack usa uno: PowerShell `.venv\Scripts\Activate.ps1` · bash o zsh `source .venv/bin/activate`
