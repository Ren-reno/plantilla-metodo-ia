# tools/

Herramientas locales del método. Son scripts de Python que usan solo la biblioteca estándar (no hay nada que instalar; funcionan con Python 3.7 o más) y se corren desde la raíz del repo: `python tools/<nombre>.py`. Si `python` no se reconoce en Windows, usa `py`.

**Estado:** `init_diseno.py` está listo. El resto se construye de a una, y cada una se prueba en una app real antes de pasar a la siguiente.

| Herramienta | Para qué sirve | Orden | Estado |
|---|---|---|---|
| `init_diseno.py` | Reparte `DISENO.md` tal cual en `docs/`, guarda el original en `docs/archivo/` y avisa de errores de formato con el número de línea | 1 | listo |
| `init_plan.py` | Reparte `PLAN.md` (formato en `docs/plantillas/plan.md`): el backlog en `docs/plan/backlog.md`, la matriz de cobertura en `docs/plan/cobertura.md` y las tarjetas de la ola en `docs/plan/tareas/T-xxx.md`. Se corre una vez por ola y no pisa tarjetas existentes | 1 | pendiente (formato decidido) |
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

## Chequeos acordados para las herramientas que faltan

Salieron de revisar ideas de otros flujos de trabajo con IA y de las decisiones del nivel 2 (caminos, plan por olas, modo estricto y chat de hito), en octubre de 2026. Se prefiere un chequeo aquí antes que una regla más en `00-LEEME-IA.md`: los LLM a veces ignoran las reglas escritas, y un chequeo no.

- **`bundle.py`:** se niega a armar el bundle si una tarea de `Depende de:` no está «hecha» (línea base en verde); `--forzar` lo salta bajo tu responsabilidad. Se suma a la compuerta de ADR no aceptados. En modo estricto, el bundle del parche 2 trae los tests del parche 1 en `Leer:` y en `No tocar:`.
- **`aplicar.py` y `cerrar.py`:** en el parche 1 del modo estricto se espera que el test falle, y eso no es un error; `cerrar.py --parcial` cierra esa fase. Comprobarán que el rojo no sea un error de importación o de sintaxis (la señal exacta se decide al construir `cerrar.py`; mientras tanto, la persona lee el mensaje).
- **`cerrar.py`:** avisa de archivos tocados fuera de `Tocar:`, dependencias nuevas, cambios en `contratos/` y decisiones que afectan a otras tareas. «Tests existentes modificados» es un aviso y, con `--reintento` (segundo intento de una tarea), un error. Una tarjeta `REF-NN` que toque un test es siempre un error. Al cerrar una tarea borra su tarjeta de `docs/plan/tareas/` (su historia queda en git y en `docs/plan/reportes/`); hasta que exista, se borra a mano con `git rm`.
- **`validar.py`:** toda tarjeta tiene la línea `Fuera de alcance:`, y los `Ejemplos aprobados`, si los hay, tienen la forma `entrada → resultado`. Revisa en dos niveles: el **backlog completo** (cobertura criterio → RF → tareas, ciclos, IDs, y que la matriz escrita sea igual a la calculada) y las **tarjetas que existen** (máximo 4 criterios y un solo módulo —si se pasa, el trabajo sube de camino—, y que `Depende de:` y `Cubre:` sean los de su línea del backlog). `Modo:` solo puede valer `estricto`. Las tarjetas `REF-NN` no cubren criterios: quedan fuera del backlog y de la matriz. Al cerrar cada rebanada hace además un **chequeo de estructura** (archivos muy grandes, bloques repetidos): solo lee, y sus umbrales se calibran con la primera app real, no antes.
- **`init_plan.py`:** el formato quedó fijado en `docs/plantillas/plan.md`: tres secciones con título exacto (`## Backlog`, `## Matriz de cobertura`, `## Tarjetas de la ola N`). Una prueba exigirá que la plantilla y el analizador coincidan, como con `diseno.md`. Un archivo con solo `## Tarjetas de la ola N` (las olas siguientes) reparte solo tarjetas; uno con backlog (la ola 1, o una replanificación de versión 2 o más, con su `Motivo del cambio:`) reparte también `docs/plan/backlog.md` y `docs/plan/cobertura.md`. Las tarjetas existentes no se pisan. Es una propuesta: se confirma al construirla.

## Si vas a construir una herramienta

- Solo biblioteca estándar de Python; debe funcionar en Windows (PowerShell) y en Linux (el CI).
- Cada herramienta lleva sus pruebas en `tools/tests/` (con `unittest`, que viene con Python) y el CI las corre: `python -m unittest discover -s tools/tests -v`.
- `validar.py` debe terminar con código 0 en un repo recién creado desde la plantilla: el CI lo ejecuta apenas el archivo exista.
- `bundle.py` deja sus archivos en `bundles/`, una carpeta que git ignora (son derivados y pesados).
- Las preferencias del usuario (terminal y carpeta de parches) viven fuera del repo, en `~/.metodo-ia.json`: `bundle.py` las vuelca en la sección «Entorno del usuario» y `aplicar.py` las usa.
- `cerrar.py` es el único escritor de `docs/plan/ESTADO.md` y del índice de `docs/decisiones/`. `docs/plan/backlog.md` lo escribe el chat de plan o de hito y lo aprueba la persona; `init_plan.py` solo lo reparte.
- Las plantillas en blanco están en `docs/plantillas/`.
