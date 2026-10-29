# tools/

Herramientas locales del método. Son scripts de Python que usan solo la biblioteca estándar (no hay nada que instalar; funcionan con Python 3.7 o más) y se corren desde la raíz del repo: `python tools/<nombre>.py`. Si `python` no se reconoce en Windows, usa `py`.

**Estado:** `init_diseno.py` e `init_plan.py` están listos. El resto se construye de a una, y cada una se prueba en una app real antes de pasar a la siguiente.

| Herramienta | Para qué sirve | Orden | Estado |
|---|---|---|---|
| `init_diseno.py` | Reparte `DISENO.md` tal cual en `docs/`, guarda el original en `docs/archivo/` y avisa de errores de formato con el número de línea | 1 | listo |
| `init_plan.py` | Reparte `PLAN.md` (formato en `docs/plantillas/plan.md`): el backlog en `docs/plan/backlog.md`, la matriz de cobertura en `docs/plan/cobertura.md` y las tarjetas de la ola en `docs/plan/tareas/T-xxx.md`. Se corre una vez por ola y no pisa tarjetas existentes | 1 | listo |
| `bundle.py T-007` | Arma el paquete de contexto de una tarea para pegarlo en un LLM | 2 | pendiente |
| `aplicar.py` | Aplica el parche más reciente de tu carpeta de parches, con reintentos y diagnóstico | 3 | pendiente |
| `cerrar.py T-007 reporte.md` | Valida el reporte, actualiza `ESTADO.md`, crea propuestas de ADR y avisa de cosas raras | 4 | pendiente |
| `validar.py` | Revisa que diseño, plan, tarjetas y diagramas sean coherentes entre sí | 5 | pendiente |

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

## Chequeos acordados para las herramientas que faltan

Salieron de revisar ideas de otros flujos de trabajo con IA y de las decisiones del nivel 2 (caminos, plan por olas, modo estricto y chat de hito), en octubre de 2026. Se prefiere un chequeo aquí antes que una regla más en `00-LEEME-IA.md`: los LLM a veces ignoran las reglas escritas, y un chequeo no.

- **`bundle.py`:** se niega a armar el bundle si una tarea de `Depende de:` no está «hecha» (línea base en verde); `--forzar` lo salta bajo tu responsabilidad. Se suma a la compuerta de ADR no aceptados. En modo estricto, el bundle del parche 2 trae los tests del parche 1 en `Leer:` y en `No tocar:`.
- **`aplicar.py` y `cerrar.py`:** en el parche 1 del modo estricto se espera que el test falle, y eso no es un error; `cerrar.py --parcial` cierra esa fase. Comprobarán que el rojo no sea un error de importación o de sintaxis (la señal exacta se decide al construir `cerrar.py`; mientras tanto, la persona lee el mensaje).
- **`cerrar.py`:** avisa de archivos tocados fuera de `Tocar:`, dependencias nuevas, cambios en `contratos/` y decisiones que afectan a otras tareas. «Tests existentes modificados» es un aviso y, con `--reintento` (segundo intento de una tarea), un error. Una tarjeta `REF-NN` que toque un test es siempre un error. Al cerrar una tarea borra su tarjeta de `docs/plan/tareas/` (su historia queda en git y en `docs/plan/reportes/`); hasta que exista, se borra a mano con `git rm`.
- **`validar.py`:** toda tarjeta tiene la línea `Fuera de alcance:`, y los `Ejemplos aprobados`, si los hay, tienen la forma `entrada → resultado`. Revisa en dos niveles: el **backlog completo** (cobertura criterio → RF → tareas, ciclos, IDs, y que la matriz escrita sea igual a la calculada) y las **tarjetas que existen** (máximo 4 criterios y un solo módulo —si se pasa, el trabajo sube de camino—, y que `Depende de:` y `Cubre:` sean los de su línea del backlog). `Modo:` solo puede valer `estricto`. Las tarjetas `REF-NN` no cubren criterios: quedan fuera del backlog y de la matriz. Al cerrar cada rebanada hace además un **chequeo de estructura** (archivos muy grandes, bloques repetidos): solo lee, y sus umbrales se calibran con la primera app real, no antes.

## Si vas a construir una herramienta

- Solo biblioteca estándar de Python; debe funcionar en Windows (PowerShell) y en Linux (el CI).
- Una herramienta puede importar de otra de `tools/` (`init_plan.py` reutiliza el lector de bloques y el formato de salida de `init_diseno.py`). Sus pruebas copian al repo temporal las herramientas de las que dependen.
- Cada herramienta lleva sus pruebas en `tools/tests/` (con `unittest`, que viene con Python) y el CI las corre: `python -m unittest discover -s tools/tests -v`.
- `validar.py` debe terminar con código 0 en un repo recién creado desde la plantilla: el CI lo ejecuta apenas el archivo exista.
- `bundle.py` deja sus archivos en `bundles/`, una carpeta que git ignora (son derivados y pesados).
- Las preferencias del usuario (terminal y carpeta de parches) viven fuera del repo, en `~/.metodo-ia.json`: `bundle.py` las vuelca en la sección «Entorno del usuario» y `aplicar.py` las usa.
- `cerrar.py` es el único escritor de `docs/plan/ESTADO.md` y del índice de `docs/decisiones/`. `docs/plan/backlog.md` lo escribe el chat de plan o de hito y lo aprueba la persona; `init_plan.py` solo lo reparte.
- Las plantillas en blanco están en `docs/plantillas/`.
