# tools/

Herramientas locales del método. Son scripts de Python que usan solo la biblioteca estándar (no hay nada que instalar; funcionan con Python 3.7 o más) y se corren desde la raíz del repo: `python tools/<nombre>.py`. Si `python` no se reconoce en Windows, usa `py`.

**Estado:** las seis herramientas están implementadas: `init_diseno.py`, `init_plan.py`, `bundle.py`, `aplicar.py`, `cerrar.py` y `validar.py`. El ciclo completo con una app real sigue pendiente de validación.

| Herramienta | Para qué sirve | Orden | Estado |
|---|---|---|---|
| `init_diseno.py` | Reparte `DISENO.md` tal cual en `docs/`, guarda el original en `docs/archivo/` y avisa de errores de formato con el número de línea | 1 | listo |
| `init_plan.py` | Reparte `PLAN.md` (formato en `docs/plantillas/plan.md`): el backlog en `docs/plan/backlog.md`, la matriz de cobertura en `docs/plan/cobertura.md` y las tarjetas de la ola en `docs/plan/tareas/T-xxx.md`. Se corre una vez por ola y no pisa tarjetas existentes | 1 | listo |
| `bundle.py T-007` | Arma el paquete de contexto de una tarea para pegarlo en un LLM | 2 | listo |
| `aplicar.py` | Aplica el parche más reciente de tu carpeta de parches, con comprobaciones acumulativas y diagnóstico | 3 | listo |
| `cerrar.py T-007 reporte.md` | Valida el reporte, actualiza `ESTADO.md`, crea propuestas de ADR y avisa de cosas raras | 4 | listo |
| `validar.py` | Revisa que diseño, plan, cobertura, tarjetas y código sean coherentes entre sí | 5 | listo |

## init_diseno.py

Revisa el formato de `DISENO.md` y lo reparte en `docs/`.

```powershell
python tools/init_diseno.py DISENO.md            # revisa y reparte
python tools/init_diseno.py DISENO.md --check    # solo revisa: no escribe nada y muestra qué repartiría
python tools/init_diseno.py DISENO.md --force    # reparte aunque ya existan los archivos de destino
```

| De `DISENO.md` | Queda en |
|---|---|
| Cada requisito (`### RF-001 · Título`) | `docs/requisitos/RF-001-titulo.md` |
| Problema, actores, alcance, criterios de éxito, reglas, tecnología, preguntas y supuestos, con el título y la línea de versión | `docs/requisitos/contexto.md` |
| Datos principales y flujos principales | `docs/modelo.md` |
| Cada decisión (`### ADR-0001 · Título`) | `docs/decisiones/0001-titulo.md` |
| El original | `docs/archivo/` (si estaba en la raíz del repo se mueve; si estaba en otra carpeta se copia) |

- **Se reparte tal cual.** El texto no se reescribe. Solo cambia el nivel del título de cada requisito y decisión (`###` pasa a `#`), y se agregan los títulos `# Contexto — …` y `# Modelo — …`. Los contenedores `## Funcionalidades` y `## Decisiones` no se copian: no tienen contenido propio, su contenido son los requisitos y las decisiones.
- **Errores** (impiden repartir; no se escribe nada): títulos de sección ausentes o mal escritos; tabla de criterios ausente o mal formada; un requisito sin `Aporta a:` en la línea siguiente al título, sin criterios de aceptación o que cita un criterio que no existe; una decisión sin la línea `Estado: … · Motivo: … · Afecta: …` o con un estado inválido; marcas `[PENDIENTE P-xx]` o `[RESUELTA → ADR-xxxx]` que citan algo que no existe; identificadores repetidos.
- **Avisos** (se reparte igual): preguntas que bloquean tareas, decisiones todavía en estado «propuesta», campos de la plantilla sin llenar y texto suelto que no caería en ningún archivo.
- **No pisa nada.** Si alguno de los archivos de destino ya existe, se niega salvo que uses `--force`.
- **Códigos de salida:** 0 todo bien · 1 el formato tiene errores · 2 problema de uso o de escritura.

Para probarla sin riesgo con un diseño de ejemplo (no escribe nada):

```powershell
python tools/init_diseno.py tools/tests/fixtures/DISENO-ejemplo.md --check
```

## init_plan.py

Revisa el formato de `PLAN.md` (el de `docs/plantillas/plan.md`) y lo reparte en `docs/plan/`. Se corre una vez por archivo de plan: el de la ola 1, el de cada ola siguiente y el de cada replanificación.

```powershell
python tools/init_plan.py PLAN.md            # revisa y reparte
python tools/init_plan.py PLAN.md --check    # solo revisa: no escribe nada y muestra qué repartiría
python tools/init_plan.py PLAN.md --force    # acepta un plan completo aunque ya haya un backlog guardado
```

Reconoce solo en cuál de tres situaciones está, por los títulos `##` del archivo y por lo que ya hay en `docs/plan/`:

| Situación | Cómo se reconoce | Qué hace |
|---|---|---|
| Primera vez (ola 1) | Las tres secciones; aún no hay `docs/plan/backlog.md` | Reparte backlog, matriz y tarjetas |
| Olas siguientes (`PLAN-ola2.md`…) | Solo `## Tarjetas de la ola N` | Reparte solo tarjetas, verificándolas contra el backlog guardado |
| Replanificación (`PLAN-v2.md`) | Las tres secciones y ya hay un backlog guardado | Exige versión = la guardada + 1 y `Motivo del cambio:`; reemplaza backlog y matriz |

| De `PLAN.md` | Queda en |
|---|---|
| `## Backlog` (cada `### Rebanada` pasa a `## Rebanada`), con el título y la línea de versión | `docs/plan/backlog.md` |
| `## Matriz de cobertura`, con el título y la línea de versión | `docs/plan/cobertura.md` |
| Cada tarjeta (`### T-001 · Título`, o `### REF-01 · Título`) | `docs/plan/tareas/T-001.md` |
| El original | `docs/archivo/` con su propio nombre (si estaba en la raíz del repo se mueve; si estaba en otra carpeta se copia) |

- **Se reparte tal cual.** El texto no se reescribe. Solo cambia el nivel de los títulos de rebanadas y tarjetas, y se agregan los títulos `# Backlog — …` y `# Cobertura — …`. La matriz se copia como viene: no se recalcula.
- **Qué no revisa.** Que el plan tenga sentido (ciclos, cobertura real contra los requisitos, matriz escrita = calculada) es de `validar.py`. Esta herramienta comprueba que está bien escrito y que sus referencias internas existen.
- **Errores** (impiden repartir; no se escribe nada): títulos de sección ausentes o mal escritos, combinaciones imposibles (backlog sin matriz, «ola» sin número, más de una ola por archivo); la línea de versión ausente, o una versión 2 o más sin `Motivo del cambio:`; tareas mal escritas, repetidas, fuera de toda rebanada, que dependen de una tarea inexistente o de sí mismas, o con un `Cubre:` inválido; una matriz mal formada o que cita una tarea inexistente; una tarjeta mal escrita, repetida o de una tarea que no está en el backlog (las `REF-NN` no van en el backlog, así que no se comparan con él); una ola que no existe en el backlog.
- **Avisos** (se reparte igual): tarjetas que ya existen (se omiten); tareas de la ola sin tarjeta o tarjetas de otra ola; `Depende de:` o `Cubre:` de una tarjeta distintos a los de su línea del backlog (o una tarjeta sin la línea `Estado: …`); un `Cubre:` que cita un RF sin archivo en `docs/requisitos/`; `Cubre: —`; tarjetas guardadas de tareas que ya no están en el backlog nuevo; campos de la plantilla sin llenar y texto suelto que no caería en ningún archivo.
- **No pisa nada.** Las tarjetas que ya existen nunca se pisan, ni con `--force` (si quieres rehacer una, bórrala antes con `git rm`). `backlog.md` y `cobertura.md` solo se reemplazan en una replanificación válida o con `--force`. Un plan ya archivado en `docs/archivo/` tampoco se pisa, ni con `--force`: dale otro nombre al archivo nuevo (`PLAN-v2.md`, `PLAN-ola3.md`). Si algo falla a medias, deshace lo creado y devuelve a su contenido lo que había reemplazado.
- **Códigos de salida:** 0 todo bien · 1 el formato tiene errores · 2 problema de uso, del repo o de escritura (no hay backlog guardado, el plan ya está repartido, el archivo ya está archivado…). Con `--check` el código es el que tendría el reparto real.
- **Depende de `init_diseno.py`:** reutiliza su lectura de bloques (ignora comentarios y bloques de código) y su formato de salida, así que ambos archivos deben estar juntos en `tools/`.

Para probarla sin riesgo con un plan de ejemplo (no escribe nada; si aún no repartiste el diseño de ejemplo, avisará de que no encuentra sus RF en `docs/requisitos/`, y es lo esperado):

```powershell
python tools/init_plan.py tools/tests/fixtures/PLAN-ejemplo.md --check
```

## bundle.py

Arma, para una tarea, un solo archivo con lo justo que el LLM necesita: `bundles/T-007.md` (git lo ignora).

```powershell
python tools/bundle.py T-007                 # arma bundles/T-007.md
python tools/bundle.py T-007 --forzar        # salta la compuerta de dependencias (bajo tu responsabilidad)
python tools/bundle.py T-007 --parche2       # modo estricto, parche 2: suma los tests del parche 1
python tools/bundle.py T-007 --max-kb 80     # cambia el tamaño desde el cual avisa (por defecto, 60)
```

Trae, en este orden (el que fija `docs/00-LEEME-IA.md`):

| Sección | De dónde sale |
|---|---|
| Árbol del repo | Los archivos que existen y git conoce, más los nuevos que no ignora |
| Entorno del usuario | `~/.metodo-ia.json` (claves `terminal` y `carpeta_parches`); la carpeta del repo es esta. Lo que falte se marca «(sin configurar)» y el LLM lo pregunta una vez: no se inventa nada |
| Tarjeta | `docs/plan/tareas/T-007.md`, tal cual |
| Documentos que la tarjeta manda leer | Los de `Leer:`. `docs/00-LEEME-IA.md` va siempre primero, lo pida o no la tarjeta |
| Archivos de `Tocar:` que ya existen | Su contenido actual. Lo que aún no existe se lista como «por crear» |

- **Sin duplicar.** Un archivo que está en `Leer:` y en `Tocar:` viaja una sola vez. Los textos se normalizan a saltos LF y sin BOM, como los guarda git. Las vallas son de 4 acentos graves, o más si un archivo ya trae vallas largas. Los archivos binarios o que no están en UTF-8 se omiten con aviso. Nunca lee fuera del repo.
- **Se niega** (no escribe nada, y dice todos los motivos juntos) si: un ADR de `Leer:` no está `aceptada` (`propuesta` o `reemplazada`; **no se puede saltar**, porque pasar un ADR a aceptada es una decisión tuya); una tarea de `Depende de:` no está hecha (`--forzar` lo salta); un archivo de `Leer:` no existe y la tarjeta no dice qué tarea lo produce (`(lo produce T-003)`); o la tarjeta no se puede leer (le falta `Estado:`, `Leer:` o `Tocar:`, o trae algo que no es una ruta).
- **«Hecha».** Una tarea está hecha cuando su tarjeta ya no existe en `docs/plan/tareas/`: así la deja `cerrar.py --hecha`. Si hay un backlog guardado, también comprueba que la dependencia exista en él, y eso ni `--forzar` lo salta. `ESTADO.md` no hace falta como fuente: como `cerrar.py --hecha` borra la tarjeta, las dos cosas siempre coinciden.
- **Modo estricto.** El bundle normal sirve para el parche 1. Para el parche 2 usa `--parche2`: suma los tests del parche 1 (los archivos de `tests/` que `Tocar:` ya tiene) en una sección propia, que vale como `Leer:` y como `No tocar:`. Si no hay ninguno, se niega. Si la tarjeta es estricta, ya hay tests y no usaste `--parche2`, te lo avisa.
- **Avisos** (arma igual): cambios sin guardar (el bundle refleja tu disco, no el último commit); `bundles/` fuera de `.gitignore`; `~/.metodo-ia.json` ausente o incompleto; campos de la tarjeta sin llenar; el bundle supera el tamaño límite (conviene partir la tarea; los 60 KB son provisionales hasta medirlos con la primera app real).
- **Resumen.** Imprime qué incluyó, con tamaños y una estimación de tokens (caracteres ÷ 4, aproximada).
- **Códigos de salida:** 0 armado · 1 se negó · 2 problema de uso o del entorno (no existe la tarjeta, no hay git, no se pudo escribir).
- **Necesita** git y los archivos `init_plan.py` e `init_diseno.py` junto a él en `tools/`.

Para crear tu `~/.metodo-ia.json` una sola vez (PowerShell; cambia la terminal si usas otra):

```powershell
@{ terminal = "PowerShell"; carpeta_parches = "$env:USERPROFILE\Downloads" } | ConvertTo-Json | Set-Content -Encoding utf8 "$env:USERPROFILE\.metodo-ia.json"
```

## aplicar.py

Aplica un parche desde la raíz del repositorio, aunque se invoque desde una subcarpeta. Necesita Git; no tiene dependencias de Python externas.

```powershell
python tools/aplicar.py                        # el .patch más reciente de la carpeta configurada
python tools/aplicar.py T-007-tema.patch        # ruta explícita o nombre en la carpeta de parches
python tools/aplicar.py T-007-tema.patch --check # ensayo: no aplica ni ejecuta tests
python tools/aplicar.py T-007-tests.patch --estricto "pytest tests/actividades"
```

- **Selección:** lee `carpeta_parches` de `~/.metodo-ia.json`; sin esa clave busca `~/Downloads` y luego `~/Descargas`. Avisa de un `.patch.txt` más nuevo y de parches con más de una hora. En bloques entregados por un LLM usa siempre el nombre explícito para evitar elegir otro parche.
- **Limpieza:** en una copia temporal quita vallas y texto ajeno, acepta UTF-8 con o sin BOM y UTF-16 con BOM, corrige CRLF del envoltorio y agrega el salto final. Conserva el CRLF que pertenece al contenido de un parche legítimo. No modifica el parche original.
- **Cadena acumulativa:** `git apply --check` → `--check --recount` → `--check --recount --ignore-whitespace`. Aplica con las mismas banderas del primer ensayo exitoso. La tolerancia de espacios no arregla cualquier diferencia; revisa el diff si fue necesaria.
- **Fallo de aplicación:** no aplica ninguna parte. Detecta parches ya aplicados y usa `--reject` solo en una copia temporal; muestra las líneas esperadas y reales. Si pides al LLM solo el bloque corregido, reemplázalo en el parche original, conservando los demás bloques, y vuelve a comprobar el parche completo. No apliques la corrección aislada como si los demás cambios ya estuvieran presentes.
- **Modo estricto (parche 1):** ejecuta el comando indicado después de aplicar. Solo clasifica salidas Python de pytest/unittest. Devuelve 0 si detecta `NotImplementedError` o una aserción fallida; rechaza errores de sintaxis, importación y nombres (incluidas sus subclases reconocidas). Si los tests pasan o el motivo es indeterminado, devuelve 1. Si hay señales buenas y malas, gana la mala. Es una ayuda para revisar el rojo, no demuestra que el test represente correctamente el requisito.
- **Sin reversión automática:** si falla el test estricto, el parche queda aplicado sin commit. El reintento parte de ese estado. `--check --estricto "..."` solo comprueba el parche, sin ejecutar el test.
- **Git:** no modifica el índice ni hace commits, push o stash; solo cambia los archivos del parche. Los tests que ejecutes pueden tener sus propios efectos.
- **Códigos:** 0 aplicado o ensayo exitoso (en modo estricto, rojo reconocido) · 1 parche rechazado o rojo no confirmado · 2 problema de uso o entorno.
- **Pruebas:** 137 casos propios. La suite de herramientas anterior al ajuste del CI corrió en Windows: 378 casos, 377 aprobados y uno omitido. Los resultados de otras versiones y de mutaciones comunicados por otro LLM no se reprodujeron aquí.

## cerrar.py

Cierra una tarea en dos momentos, como la recepción provisoria y la definitiva de una obra: revisa el reporte, anota lo raro y mantiene `docs/plan/ESTADO.md`.

```powershell
python tools/cerrar.py T-007 reporte.md              # provisoria: revisa el reporte y deja la tarea «en revisión»
python tools/cerrar.py T-007 reporte.md --parcial    # parche 1 del modo estricto: queda «parcial»
python tools/cerrar.py T-007 reporte.md --reintento  # segundo intento tras un fallo
python tools/cerrar.py T-007 --hecha                 # definitiva (el CI salió en verde): «hecha» y se borra la tarjeta
```

Opciones de datos y ensayo: `--desde REF` (commit desde el que mirar lo que cambió la tarea; por defecto `HEAD~1`, el último commit, porque el bloque de comandos del LLM ya hizo el commit), `--llm NOMBRE` (qué LLM la hizo; se anota en `ESTADO.md`) y `--check` (ensayo: no escribe ni borra nada).

| Momento | Cuándo | Qué hace |
|---|---|---|
| `cerrar.py T-007 reporte.md` | Después del bloque de comandos (el commit ya está hecho) | Valida el reporte, mira qué archivos cambió el commit, levanta banderas, guarda el reporte en `docs/plan/reportes/T-007.md`, deja la tarea «en revisión», propone ADR y regenera el índice de decisiones |
| `cerrar.py T-007 --hecha` | Cuando el CI de GitHub salió en verde | La deja «hecha», borra su tarjeta y lista las tareas que quedan desbloqueadas |

- **Errores** (impiden cerrar; no se escribe nada): el reporte no tiene exactamente las seis secciones (falta alguna, tiene otro título, va fuera de orden, está repetida o vacía) o es de otra tarea; la tarea no está en el backlog (y no es `REF-NN`); la tarjeta tiene errores; `--parcial` en una tarjeta que no es de modo estricto; cerrar una tarea ya «hecha», o ya «en revisión» sin `--reintento`; `--hecha` sobre una tarea que no está «en revisión»; una tarjeta `REF-NN` que toca un test; con `--reintento`, un test que ya existía modificado; un reporte archivado que ya existe (sin `--reintento`).
- **Banderas** (para revisar; no frenan, y quedan en la columna *Notas* de `ESTADO.md`): archivos fuera de `Tocar:`; un documento «solo la sección X» cambiado fuera de esa sección (solo se comprueba en Markdown); un archivo de dependencias tocado (`requirements.txt`, `pyproject.toml`, `package.json`…), con una pista si «Decisiones tomadas» no dice nada; cambios en `docs/contratos/`; decisiones que afectan a otras tareas.
- **Avisos:** «Cómo probar» sin «Verificado:» o sin «No verificado:»; el mensaje de commit sugerido no es convencional; campos de la plantilla sin llenar; tests que ya existían modificados (con `--reintento` es un error); notas de `Tocar:` que no sabe comprobar, como `solo INSTALLED_APPS` («revisa a mano»); no hay cambios entre `--desde` y HEAD; cambios sin guardar (solo mira commits; el propio reporte en la raíz no cuenta).
- **Estados.** `pendiente` (todo el backlog empieza así), `parcial` (parche 1 del modo estricto; la tarjeta se queda), `en revisión` (reporte revisado; falta el CI) y `hecha` (la tarjeta se borra). `en curso` y `bloqueada` existen en la tabla, pero ningún paso del flujo los escribe todavía.
- **`ESTADO.md`.** Una tabla (tarea · estado · LLM · commit · notas) que solo escribe `cerrar.py`: no se edita a mano. Trae el avance («3 de 12 tareas hechas») y no pierde las filas de las tareas que ya no están en el backlog ni las de refactor (`REF-NN`).
- **Decisiones.** Cada decisión del reporte que termina en «Afecta a otras tareas» se convierte en `docs/decisiones/NNNN-slug.md` con `Estado: propuesta` (el siguiente número libre). `bundle.py` se niega a usarla hasta que la aceptes. El índice `docs/decisiones/README.md` (ADR · título · estado) se regenera completo en cada ejecución a partir de los propios ADR: nadie lo edita.
- **Rojo del modo estricto:** `cerrar.py --parcial` no lo clasifica; esa ayuda está en `aplicar.py --estricto` para Python. Revisa igualmente el mensaje del test.
- **Nunca modifica git.** Solo lo lee (con una lista blanca de comandos de lectura, probada). Todo lo que escribe queda sin commit para que lo revises con `git diff`. La tarjeta se borra con un borrado normal de archivo, no con `git rm`: tú la guardas en el commit de cierre, junto con `ESTADO.md`.
- **Codificación.** Lee y escribe todo en UTF-8: el reporte puede traer BOM o saltos de línea de Windows, y lo que escribe va sin BOM y con saltos LF. Una prueba revisa el código de las cinco herramientas y falla si algún `open`, `read_text` o `write_text` no declara su `encoding` (o si una escritura no fija el salto de línea), porque en Windows el valor predeterminado (cp1252) fallaría con «·» y con «».
- **Códigos de salida:** 0 hecho · 1 el reporte tiene errores o el estado de la tarea no lo permite · 2 problema de uso o del entorno (no existe la tarjeta, no hay git, no se pudo escribir).
- **Necesita** git y los archivos `bundle.py`, `init_plan.py` e `init_diseno.py` junto a él en `tools/`.

## validar.py

Revisa que diseño, plan, cobertura, tarjetas y código sean coherentes entre sí. Reúne chequeos mecánicos que `init_plan.py` no revisa; no sustituye la revisión del significado del diseño.

```powershell
python tools/validar.py            # revisa coherencia del repo actual
python tools/validar.py --estricto # trata avisos como errores
python tools/validar.py --repo DIR # revisa otro repositorio
```

Comprueba:
1. **Grafo de dependencias y ciclos en el backlog:** detecta tareas que dependen de sí mismas, de tareas inexistentes, de rebanadas posteriores o ciclos cerrados (A -> B -> A).
2. **Cobertura de requisitos y criterios:** ningún `RF-xxx` en `docs/requisitos/` queda huérfano (todos cubiertos por al menos una tarea en el backlog) y todo criterio de éxito de `contexto.md` está cubierto.
3. **Matriz de cobertura (`docs/plan/cobertura.md`):** verifica que la tabla escrita coincida con lo declarado en el backlog (sin tareas inexistentes, sin omisiones y respetando los criterios a los que cada RF aporta).
4. **Tarjetas de `docs/plan/tareas/`:**
   - **Máximo 4 criterios de aceptación (D16):** cada tarjeta debe tener entre 1 y 4 criterios; si pasa de 4, el arnés exige partirla o subir de camino.
   - **`Fuera de alcance:` obligatorio (D16):** delimita explícitamente lo que no se construye para cortar código innecesario.
   - **Coherencia con el backlog:** `Depende de:` y `Cubre:` de la tarjeta deben ser idénticos a los de su línea del backlog.
   - **Tarjetas de refactor (`REF-NN`, D37):** rechaza rutas en `tests/` y `docs/`; no comprueba que cualquier otra ruta sea código de producción.
   - **Archivos citados en `Leer:`:** comprueba que existan o indiquen `(lo produce T-xxx)`; avisa si un ADR citado está en estado «propuesta» (bloqueará `bundle.py`).
5. **Estructura y alertas de refactor (D37):** avisa si hay archivos de código muy grandes (>500 líneas) como candidatos a evaluar en el chat de hito.

- **Límites:** no valida PlantUML ni duplicación de código. Si falta la matriz de cobertura o no tiene filas, no comprueba sus relaciones; por eso salida 0 no certifica la integridad de todos los documentos. El umbral de 500 líneas es provisional.

- **Códigos de salida:** 0 todo bien · 1 errores de coherencia (o avisos con `--estricto`) · 2 problema de uso o entorno (falta `docs/` o `backlog.md`).

## Integración con CI

El CI omite la validación cruzada con un aviso mientras no existan `tools/validar.py` o `docs/plan/backlog.md`. Así se puede guardar el diseño antes de planificar. Con backlog, ejecuta el validador y propaga sus errores; las pruebas de `tools/` corren igualmente. Ejecutar `validar.py` a mano sin backlog sigue devolviendo 2.

Las siete pruebas de `test_ci.py` ejecutan el bloque real en Bash: plantilla vacía, diseño sin plan, plan válido, incoherente, backlog dañado, fallo interno y herramienta ausente.

## Si vas a construir una herramienta

- Solo biblioteca estándar de Python; debe funcionar en Windows (PowerShell) y en Linux (el CI).
- Una herramienta puede importar de otra de `tools/` (`init_plan.py` reutiliza el lector de bloques y el formato de salida de `init_diseno.py`; `bundle.py` lee el backlog guardado con `init_plan.py`; `cerrar.py` reutiliza la lectura de tarjetas y el acceso a git de `bundle.py`). Sus pruebas copian al repo temporal las herramientas de las que dependen.
- Cada herramienta lleva sus pruebas en `tools/tests/` (con `unittest`, que viene con Python) y el CI las corre: `python -m unittest discover -s tools/tests -v`.
- La integración del CI decide cuándo existe un plan que validar; no convierte los errores del validador en éxitos.
- `bundle.py` deja sus archivos en `bundles/`, una carpeta que git ignora (son derivados y pesados).
- Las preferencias del usuario (terminal y carpeta de parches) viven fuera del repo, en `~/.metodo-ia.json` (claves `terminal` y `carpeta_parches`): `bundle.py` las vuelca en la sección «Entorno del usuario» y `aplicar.py` las usa.
- `cerrar.py` es el único escritor de `docs/plan/ESTADO.md` y del índice de `docs/decisiones/`. `docs/plan/backlog.md` lo escribe el chat de plan o de hito y lo aprueba la persona; `init_plan.py` solo lo reparte.
- Las plantillas en blanco están en `docs/plantillas/`.

## Complementos de diseño y evidencia de UI

El flujo humano está en [DISENAR.md](../docs/DISENAR.md). `init_diseno.py` mantiene sus títulos actuales y reparte las tablas de actores/roles dentro de `docs/requisitos/contexto.md`. Experiencia, imágenes, prototipo e inventario de diagramas se incorporan manualmente según esa guía; no se pasan al importador como nuevas secciones.

Las tarjetas pueden usar `Criterios de aceptación:` (también se admite el encabezado anterior con `→ tests`). Cada criterio indica evidencia; las comprobaciones automáticas siguen siendo obligatorias donde corresponden. La evidencia de uso/UI se describe dentro de `Cómo probar` del reporte de seis secciones. No hay un nuevo `Modo: UI`, ni validación automática de aprobación visual, ACT/ROL o PlantUML. `bundle.py` sigue incluyendo texto, no las imágenes: entrégalas como adjuntos reales.
