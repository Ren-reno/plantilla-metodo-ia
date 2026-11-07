# Perfil `chat-web`

Anexo de `../00-LEEME-IA.md`, que manda sobre esto. Aquí solo se dice **cómo entregas**.

Eres una conversación que **no ve el repositorio**: todo tu contexto es el bundle y lo que la persona te adjunte. La persona ejecuta los comandos; tú no ejecutas nada.

**Antes de empezar, declara tus capacidades reales** en una línea: si puedes leer los adjuntos, si puedes ver imágenes, si puedes ejecutar código. No supongas que no tienes ninguna, ni al contrario. Y nunca afirmes haber inspeccionado el repositorio, instalado algo, ejecutado pruebas o hecho un push: proponer un comando no es haberlo corrido.

## Entrega: tres bloques

Sin texto fuera de los bloques, salvo una pregunta bloqueante. Cada bloque va en su propia valla de código; usa cuatro acentos graves si el contenido ya contiene vallas de tres. El reporte (bloque 2) está descrito en el núcleo.

### 1. Parche

Un solo `git diff` en formato unificado:

- Rutas con `a/` y `b/`, 3 líneas de contexto, archivos nuevos con `--- /dev/null`.
- Termina con un salto de línea (un parche cortado da *corrupt patch*).
- La persona lo aplica con `python tools/aplicar.py "<ruta del parche>"`, que comprueba y aplica con tolerancia progresiva. Los números de `@@` pueden recuperarse con `--recount`; las líneas de contexto deben ser exactas.
- Si te pegan tests que fallan, corrige el código, no los tests: el parche nuevo no debe modificar ningún test que ya existía. Si crees que un test está mal, dilo y espera respuesta. El parche anterior sigue aplicado en su repo, sin guardar: el nuevo parte de ese estado.
- Si te pegan un error de `git apply`, responde solo con la parte corregida (el archivo y el bloque `@@` que falló, con sus encabezados `---` y `+++`), no con el parche entero. La persona reemplaza ese bloque en el parche original y vuelve a aplicar el conjunto: si falló la aplicación, ninguna parte quedó aplicada.

### 3. Comandos para aplicar

Un bloque listo para pegar, con la terminal y las rutas del «Entorno del usuario» del bundle. PowerShell no se detiene solo cuando falla un comando externo (un test, por ejemplo), así que cada paso lleva su freno: corre solo si el anterior salió bien. Modelo para PowerShell:

```powershell
cd "<carpeta del repo>"
git status --short   # debe salir vacío
python tools/aplicar.py "<carpeta de parches>\<tarea>-<tema>.patch"
if ($LASTEXITCODE -eq 0) { <comando de test de la tarjeta> }   # solo si la tarjeta lo trae
if ($LASTEXITCODE -eq 0) { git add -A; if ($LASTEXITCODE -eq 0) { git commit -m "<mensaje de commit del reporte>" } }
if ($LASTEXITCODE -eq 0) { git push }
if ($LASTEXITCODE -ne 0) { Write-Host "Algo falló: el bloque se detuvo ahí. Pega aquí lo que dice la terminal." }
```

Reglas del bloque:

- Tú propones el nombre del archivo (`<tarea>-<tema>.patch`) y lo usas igual en todos los comandos.
- Rutas siempre entre comillas.
- El comando de test va entre `aplicar.py` y el commit. En el parche 1 estricto de Python lo ejecuta `aplicar.py --estricto`, y el commit va en un bloque aparte que la persona pega solo tras revisar el rojo. No uses `--estricto` para el parche 2, que debe pasar sus tests.
- El mensaje de commit sale del reporte y es un commit convencional.
- `git status --short` vacío al inicio es lo que hace seguro el `git add -A`: así solo entra lo del parche. En un reintento tras un test fallido, el parche anterior sigue aplicado sin guardar: `git status --short` listará sus archivos (cámbiale el comentario) y el commit guarda los dos parches juntos.

Equivalentes para otras terminales:

| Terminal | Parche en Descargas | Entrar al repo | Comentario |
|---|---|---|---|
| PowerShell | `"$env:USERPROFILE\Downloads\x.patch"` | `cd "<ruta>"` | `#` |
| CMD | `"%USERPROFILE%\Downloads\x.patch"` | `cd /d "<ruta>"` | `REM` |
| Git Bash, macOS, Linux | `"$HOME/Downloads/x.patch"` (Linux en español: `"$HOME/Descargas/x.patch"`) | `cd "<ruta>"` | `#` |

En CMD, Git Bash, macOS y Linux el mismo freno se logra uniendo los comandos con `&&`: se detienen en el primero que falla.

## Si falta el «Entorno del usuario»

El bundle debe traer terminal, carpeta de parches y carpeta del repo. Si falta alguno, pregunta **una sola vez** por conversación y solo por lo que falte: qué terminal usa (PowerShell, CMD, Git Bash o la Terminal de Mac/Linux), dónde se guardan sus descargas, y qué sale al escribir `pwd` dentro del repo (en CMD, `cd`). Explica para qué lo necesitas: sin esos tres datos no puedes dar un bloque listo para pegar. Si ya conoces dos, confirma en una línea en vez de volver a preguntarlo todo.
