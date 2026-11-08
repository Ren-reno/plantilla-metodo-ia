# Reglas para cualquier LLM

Este archivo viaja dentro de cada bundle. Léelo completo antes de escribir nada.

## Tu trabajo

Recibes un **bundle** con **una** tarea. Haces solo esa tarea y entregas como dice tu perfil (ver «Cómo entregas»).

El bundle trae, en este orden: el árbol actual del repo · el «Entorno del usuario» · la tarjeta de la tarea · las reglas (RN/RNF) que citan sus criterios, si cita alguna · los documentos que la tarjeta manda leer, con estas reglas, el anexo de tu perfil y, si el proyecto ya los declaró, sus comandos (`comprobaciones.json`) · el contenido actual de los archivos de `Tocar:` que ya existen.

## Reglas

1. Haz solo la tarea del bundle.
2. Usa solo lo que trae el bundle. No supongas archivos que no estén en el árbol.
3. Cada criterio tiene evidencia definida. Para lo automatizable, tests primero. Para apariencia o uso, sigue los pasos y referencias de revisión indicados; declara pendiente lo que no puedas comprobar. Los «Ejemplos aprobados» de la tarjeta van en los tests tal cual, con sus valores esperados.
4. Modifica solo los archivos de `Tocar:`. En `Tocar:` el `*` es recursivo: `src/inicio/*` incluye sus subcarpetas. Si necesitas otro archivo, no lo toques: anótalo en *Pendientes* del reporte. Lo que la tarjeta pone en «Fuera de alcance» no se construye, aunque parezca razonable.
5. Dependencias nuevas: decláralas en el archivo de dependencias y en *Decisiones tomadas*.
6. Decisión que afecta a otras tareas: **pregunta** antes de seguir. Decisión local: decídela y regístrala en el reporte.
7. No edites archivos de estado compartido: `docs/plan/` (incluido `ESTADO.md`) ni `docs/decisiones/`. Los mantiene `tools/cerrar.py`.
8. Máximo dos intentos por fallo. Al segundo, para y reporta qué probaste. Al reintentar tras tests que fallan, **no modifiques los tests que ya existían**: corrige el código.
9. Entrega como dice el anexo de tu perfil, y no afirmes haber hecho nada que no hiciste.
10. Respeta las «Convenciones» y usa solo los comandos de «Comandos» (más abajo).
11. **Tú no cierras la tarea.** «Hecha» lo declara la persona, cuando el CI está en verde y se completaron las comprobaciones de aceptación exigidas. Aprobado, implementado y probado son tres cosas distintas: no las confundas al reportar.

## Cómo leer la tarjeta

- **Cubre**: criterios y requisitos que la tarea satisface. **Depende de**: tareas que ya deben estar hechas.
- **Modo** (opcional): `estricto` = la tarea son dos parches y la persona te dice cuál toca. Parche 1: solo tests y, si hace falta para importarlos, un esqueleto que lance «no implementado» (en Python, `NotImplementedError`); deben fallar por falta de funcionalidad, no por un error de importación. En Python, `aplicar.py --estricto "<comando de test>"` devuelve 0 si reconoce el rojo esperado; en otros stacks se revisa a mano. Nada se guarda hasta que la persona confirma que el rojo es el correcto. Parche 2: implementa sin tocar esos tests (vienen en `Leer:` y `No tocar:`).
- **Leer (solo esto)**: los únicos documentos que debes consultar. Un ADR citado ahí ya está aceptado.
- **Contrato**: cómo llamas a otro módulo. Si la pieza real aún no existe, usa el *stub* que indica la tarjeta; no implementes el otro módulo.
- **Produce**: contratos u otros archivos que esta tarea deja listos para otras tareas.
- **Tocar** / **No tocar**: lo que puedes y no puedes cambiar. **Fuera de alcance**: lo que no debes construir en esta tarea.
- **Ejemplos aprobados** (opcionales): casos «entrada → resultado» que la persona aprobó. Inclúyelos en los tests tal cual; no cambies sus valores esperados.
- **Criterios de aceptación**: máximo 4. Los marcados `[verifica: CI]` solo se comprueban en el CI de GitHub: impleméntalos, pero di en el reporte que no los verificaste.
- **UI y evidencia**: usa la experiencia y las referencias vigentes citadas. Las imágenes deben llegar como adjuntos reales o ser accesibles con una herramienta: una ruta en el bundle no equivale a verlas. Si falta material necesario, decláralo como bloqueo; no inventes otra apariencia.
- **Comando de test**: el de la sección «Comandos», aplicado solo a la ruta que indica la tarjeta.

## El reporte

Va en toda entrega, en cualquier perfil. Sigue `docs/plantillas/reporte.md`: seis secciones, en este orden y con estos títulos exactos (los revisa `tools/cerrar.py`):

**Hecho** · **Supuestos** · **Decisiones tomadas** · **Pendientes** · **Cómo probar** · **Mensaje de commit sugerido**

- *Decisiones tomadas* puede decir «ninguna». Si una decisión afecta a otras tareas, termina su línea con «Afecta a otras tareas».
- En correcciones, *Hecho* explica fallo, resultado esperado, causa y solución; *Cómo probar* conserva reproducción y evidencia. En UI, indica referencias, versión, estados/tamaños y quién revisó; no inventes aprobación humana.
- En *Cómo probar*, dos viñetas con estos nombres exactos: `Verificado:` lo que comprobaste de verdad y cómo, y `No verificado:` lo que no pudiste comprobar (por ejemplo, el CI de GitHub). `cerrar.py` las busca así. No afirmes haber corrido algo que no corriste.

## Cómo entregas: tu perfil

El método no cambia según dónde corras; solo cambia cómo llega el trabajo. El bundle trae el anexo del perfil declarado, y es el único sitio donde se describe tu forma de entregar:

| Perfil | Quién eres | Anexo |
|---|---|---|
| `chat-web` | Una conversación que no ve el repositorio: el contexto te llega en el bundle y en adjuntos | [perfiles/chat-web.md](perfiles/chat-web.md) |
| `agente` | Tienes acceso declarado al repositorio y a la terminal, y editas en local | [perfiles/agente.md](perfiles/agente.md) |

**Lo mismo en los dos:** qué es una tarea pequeña, qué cuenta como evidencia, los contratos y las compuertas de ADR, el reporte de seis secciones, los límites de las reglas de arriba y quién declara «hecha». **Lo que cambia:** cómo accedes al contexto, quién ejecuta los comandos, cómo se aplica el cambio y cómo se captura la evidencia. Si el bundle no trae ningún anexo, trabaja como `chat-web`: es el perfil que no supone ningún acceso.

## Convenciones

Fijas (vienen de la plantilla):

- Un módulo por carpeta en `src/`; sus tests en `tests/<módulo>/`.
- Commits convencionales: `tipo: T-NNN descripción corta en español`. Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

Las completa T-001 (cada app decide las suyas con un ADR; la tarjeta de T-001 incluye este archivo en `Tocar:`):

- Idioma de los identificadores del código: *(pendiente)*
- Estructura interna de `src/` y de `tests/`: *(pendiente)*
- Idioma y formato de docstrings/documentación del código, con un ejemplo del stack: *(pendiente)*

Documenta interfaces públicas y lógica no evidente: propósito, restricciones, unidades, errores y efectos relevantes. Evita repetir lo que ya explica la firma. Actualiza el docstring en el mismo cambio que altera su contrato; no copies requisitos completos. Funciones evidentes pueden llevar una línea o ninguna explicación adicional. T-001 elige un formato consistente adecuado al lenguaje; el lint de documentación es opcional.

La detección de tests de `bundle.py --parche2` y las guardas de tests de `cerrar.py` dependen hoy de `tests/`. Permitir tests junto al código requiere adaptar y verificar esas herramientas; un ADR por sí solo no lo habilita.

## Comandos

Los comandos del proyecto están declarados **una sola vez**, en `comprobaciones.json` de la raíz del repo: el mismo archivo que usa la persona y que usa el CI. Lo crea T-001 cuando el stack está decidido, y viaja en el bundle cuando ya existe. No uses otros comandos y no inventes ninguno: si falta el que necesitas, decláralo como bloqueo.

- Comprobar mientras trabajas: `python tools/comprobar.py rapido`
- Comprobar antes de entregar: `python tools/comprobar.py entrega`
- Probar solo la ruta de la tarjeta: `python tools/comprobar.py rapido --ruta «la ruta de la tarjeta»`
- Ver qué comandos hay declarados: `python tools/comprobar.py --listar`
- Activar el entorno virtual, si el stack usa uno: PowerShell `.venv\Scripts\Activate.ps1` · bash o zsh `source .venv/bin/activate`

`comprobar.py` falla cuando un comando termina bien sin haber ejecutado ninguna prueba, porque «salió sin error» y «probó algo» no son lo mismo. No presentes como verde un paso que no probó nada, y no quites pruebas para que pase. Las suites largas no se vigilan con mensajes cada pocos segundos: las corre la persona o el CI, y tú recibes el resumen.

T-001 declara ahí cada stack con su comando de pruebas y sus archivos de dependencias, los comandos de instalar y arrancar, el alcance de distribución y las plataformas; para varios servicios, el comando de cada uno más la prueba integrada. Un stack declarado no se omite silenciosamente si falta su configuración.
