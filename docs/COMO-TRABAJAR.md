# Cómo trabajar con este repo

Esta guía es para ti, la persona que dirige el proyecto. Los LLM leen `00-LEEME-IA.md`; tú lees esta.

## La idea, con una analogía

Piensa en construir una casa. Primero hablas con el arquitecto y quedan escritos los **planos** (el diseño y los diagramas). Después se arma el **plan de obra**: una lista de tareas pequeñas, cada una con su orden de trabajo. Por último, cada tarea se le entrega a un obrero (un LLM) con *solo* lo que necesita, y el obrero devuelve el trabajo hecho y un informe.

Este repo es el **cuaderno de obra**: todo queda escrito aquí. Por eso puedes cambiar de LLM, o abrir un chat nuevo, sin explicar todo desde cero: el cuaderno ya lo dice.

## Las 5 etapas

| Etapa | Qué haces tú | Qué queda en el repo |
|---|---|---|
| 1. Diseño | Iteras problema, recorrido, apariencia y viabilidad con [DISENAR.md](DISENAR.md) | Diseño, experiencia si aplica y referencias vigentes |
| 2. Diagramas | Eliges un inventario y revisas los diagramas necesarios para el alcance | `docs/diagramas/`, incluido su índice |
| 3. Plan | Pides el plan por olas: la lista completa de tareas y tarjetas solo para la próxima ola | `docs/plan/backlog.md`, `docs/plan/cobertura.md` y `docs/plan/tareas/` |
| 4. Código | Repites el ciclo de abajo, una tarea a la vez | Un parche por tarea y `docs/plan/ESTADO.md` |
| 5. Entrega y operación | Publicas una versión que alguien pueda instalar y usar, y que no pierda sus datos | `comprobaciones.json`, datos de ejemplo de las versiones anteriores y notas de cambio |

Las **decisiones** (`docs/decisiones/`) y los **tests** atraviesan las cinco etapas.

## Elegir el camino

Las cuatro etapas de arriba son el camino **completo**. Pero no es lo mismo construir una casa que remodelar una pieza o arreglar una gotera: el rigor debe ser proporcional al trabajo. Tú, con el LLM, eliges el camino **antes de empezar**.

| Camino | Cuándo | Qué escribes |
|---|---|---|
| **Completo** (construir una casa) | App o módulo nuevo, o entidades y relaciones nuevas | Las 5 etapas |
| **Cambio** (remodelar una pieza) | Una funcionalidad nueva en una app que ya existe; un campo nuevo en una entidad cuenta como cambio | Un mini-diseño de una página (`docs/plantillas/cambio.md`; se guarda en `docs/cambios/`) y de 1 a 3 tarjetas |
| **Rápido** (arreglar una gotera) | Un bug o un ajuste | Una tarjeta rápida (variante en `docs/plantillas/tarjeta.md`); un bug parte con su reproducción y evidencia; test primero cuando es automatizable |

- **Regla de subida:** si una tarjeta de un camino liviano necesita más de 4 criterios o más de un módulo, el trabajo no era liviano: sube al camino siguiente. *Para qué:* un camino corto no debe servir para saltarse el rigor. Aunque el camino sea corto, cada tarea lleva su tarjeta, evidencia de aceptación y reporte; lo automatizable mantiene sus tests.
- **Los documentos se mantienen vivos.** Si una tarea cambia el comportamiento, su parche actualiza también el RF o la sección de `docs/modelo.md` que corresponda (y el `.puml` si cambia el modelo), y esos archivos van en el `Tocar:` de la tarjeta. También se actualizan actores, permisos, experiencia, referencias visuales y diagramas cuando estén afectados. La versión vigente está en `docs/requisitos/`, `docs/modelo.md` y los complementos del repo; el `DISENO.md` original queda en `docs/archivo/` como foto histórica. *Para qué:* si nadie los actualiza, el mapa de lo que hace la app termina mintiendo.
- **Las tarjetas se desechan al cerrar la tarea.** Su historia queda en git y en `docs/plan/reportes/`, y la traza «qué tarea cubre qué» queda en el backlog (o, en un cambio, en su mini-diseño).
- **Una app que ya existe** (por ejemplo CrafTerraria): se documenta solo lo que se toca; el primer cambio sobre un área crea el RF o la sección de `modelo.md` de esa área. *(Pendiente: copiar el esqueleto del método a un repo que ya existe.)*

## Qué funciona hoy y qué falta

Las siete herramientas están implementadas: `init_diseno.py`, `init_plan.py`, `bundle.py`, `aplicar.py`, `cerrar.py`, `validar.py` y `comprobar.py`. Sus opciones están en `tools/README.md`. El ciclo completo se recorrió una vez en un piloto; una vez no valida el método. El mini-diseño de cambios sigue siendo un documento manual; no hay instalador del método para repos existentes.

El CI omite la validación cruzada con un aviso mientras no existan `tools/validar.py` o `docs/plan/backlog.md`. Así se puede guardar el diseño antes de planificar. Con backlog, ejecuta el validador y propaga sus errores. Ejecutar `validar.py` a mano sin backlog sigue devolviendo 2.

Las pruebas de las herramientas corren mientras tu repo todavía no tiene `comprobaciones.json`, es decir antes de T-001. Después no: **el CI de tu proyecto prueba tu proyecto, no el método**. Las de `tools/` viven en el repo de la plantilla y ahí siguen corriendo. *Para qué:* en el piloto el CI ejecutaba 388 pruebas del método frente a 13 de la app, y esa suite era además la espera más larga del ciclo en Windows. Si en algún momento cambias algo de `tools/`, añade el paso `herramientas` al perfil de entrega de tu `comprobaciones.json` y vuelven a correr aquí.

## Empezar una app nueva

**Primero el diseño, después el repo.** Sigue [Diseñar antes de planificar](DISENAR.md): problema → alcance → comportamiento → apariencia y prototipo si hay UI → viabilidad → revisión de versión. Cada conversación recibe los documentos vigentes y devuelve sus cambios consolidados.

Durante el diseño conserva `DISENO.md`, `EXPERIENCIA.md` si aplica, referencias en `visual/` y un inventario en `diagramas/README.md`. Las imágenes son opcionales para explorar apariencia; un prototipo permite comprobar interacciones. La guía incluye prompts para generar imágenes en otro LLM y revisarlas.

Un diseño está listo para planificar cuando:

- el alcance delimita dentro/fuera y un primer recorrido útil;
- actores, roles y permisos aplicables tienen nombres e IDs consistentes;
- cada RF tiene `Aporta a:` y criterios con evidencia prevista;
- entidades, reglas con ejemplos y flujos son coherentes con la experiencia;
- hay referencia visual vigente y prueba del recorrido cuando la interacción lo necesita;
- los diagramas necesarios están seleccionados y revisados contra sus fuentes;
- están resueltas las decisiones técnicas y operativas que condicionan la próxima ola;
- los pendientes indican impacto y momento de resolución; ninguno bloquea el alcance que se va a planificar;
- la persona confirma la versión, alcance y decisiones necesarias. Puede hacerlo en bloque; el acta propuesta está en la plantilla de diseño.

Se puede aprobar un alcance independiente dejando dudas futuras localizadas. El límite de cuatro criterios no se aplica al diseño.

Con el diseño cerrado:

1. **En GitHub, botón *Use this template* → *Create a new repository*.** *Para qué:* obtienes una copia limpia de toda esta estructura, sin arrastrar la historia de otros proyectos.
2. **Clona el repo nuevo en tu computador.** *Para qué:* tener la copia donde puedas trabajarla. En PowerShell:

   ```powershell
   $escritorio = [Environment]::GetFolderPath("Desktop")   # encuentra tu Escritorio aunque OneDrive lo haya movido
   cd $escritorio
   git clone URL-DEL-REPO-NUEVO
   ```

3. **Copia `DISENO.md` a la raíz del repo y corre `python tools/init_diseno.py DISENO.md`.** *Para qué:* reparte el diseño en `docs/` (un archivo por requisito y por decisión, más el contexto y el modelo) sin que cortes y pegues. Si el formato tiene errores, te dice en qué línea y no escribe nada. El original se mueve a `docs/archivo/`. Si quieres revisar sin escribir nada, agrega `--check` al final; y si `python` no se reconoce en tu PowerShell, prueba con `py`.
4. **Incorpora manualmente los complementos.** Copia `EXPERIENCIA.md` a `docs/experiencia.md`, `visual/` a `docs/visual/` si aplican, e inventario y fuentes a `docs/diagramas/`. Revisa referencias según [DISENAR.md](DISENAR.md#documentos-y-entrega-al-repo). `init_diseno.py` no copia estos archivos. **Revisa con `git status` y `git diff`; luego commit y push.** *Para qué:* ver qué se repartió antes de guardarlo.
5. **Pide el plan por olas y repártelo con `python tools/init_plan.py PLAN.md`; después, valídalo con `python tools/validar.py`**. *Para qué:* `init_plan.py` revisa el formato y deja en `docs/plan/` la lista completa de tareas (el backlog), su cuadro de cobertura y las tarjetas completas solo de la primera ola. Las demás se escriben cuando les llega el turno, como los planos de detalle de cada piso: se dibujan cuando el piso anterior ya está construido y se puede medir. Si el formato tiene errores, te dice en qué línea y no escribe nada; con `--check` solo revisa. El original se mueve a `docs/archivo/`. `validar.py` comprueba cobertura, matriz y referencias del plan, y detecta ciclos. Son chequeos mecánicos: la revisión humana sigue evaluando si el plan satisface el diseño.

## Qué pedirle a un LLM en cada etapa

Textos para copiar y pegar. Si algo te cuesta entender, agrega: «explícame con una analogía».

**Diseño.** Adjunta tu problema, `docs/DISENAR.md` y `docs/plantillas/diseno.md`; añade los complementos aplicables o sus versiones vigentes:

> Vamos a diseñar esta app siguiendo DISENAR.md. Primero aclara problema, actores y alcance; luego recorrido, experiencia y viabilidad. Pregunta hasta tres cosas por tanda (hasta cinco si están relacionadas). Separa hechos, supuestos y propuestas; usa los títulos exactos de diseno.md. Si hay UI, prepara EXPERIENCIA.md: podemos explorar imágenes con prompts autocontenidos y probar un prototipo según la interacción. Selecciona el inventario de diagramas. Antes del plan, revisa coherencia, pendientes y evidencia; presenta la versión y el alcance para confirmar. Devuelve los documentos actualizados al terminar cada sesión.

**Diagramas.** Adjunta las fuentes vigentes: diseño (o requisitos y modelo ya repartidos), experiencia si aplica e inventario con el formato de `docs/plantillas/inventario-diagramas.md`:

> Selecciona los diagramas que resuelven dudas del alcance según DISENAR.md. Justifica los tipos omitidos. Genera un .puml por diagrama seleccionado, conserva actores, roles y RF de las fuentes y actualiza el inventario. Distingue generado, renderizado y revisado; no afirmes haber renderizado si no lo hiciste. Si encuentras contradicciones entre fuentes, señálalas para resolverlas.

La skill externa `puml-diagramas` es opcional; debe seguir el inventario y las decisiones del proyecto.

**Plan.** Adjunta la versión y el alcance confirmados del diseño, la experiencia con referencias reales si aplica, el inventario y los diagramas, `docs/plantillas/plan.md` y `docs/plantillas/tarjeta.md`:

> Con esto, arma el plan por olas, en un solo archivo `PLAN.md` con el formato de `plan.md`:
>
> - Backlog completo: todas las tareas, una línea cada una (ID, título, depende de, cubre), agrupadas en rebanadas verticales ordenadas por peso, riesgo y dependencias; cada rebanada deja algo ejecutable.
> - Matriz de cobertura sobre todo el backlog: cada criterio → RF → tareas, sin RF huérfanos ni tareas sin criterio.
> - Tarjetas completas solo para la ola 1 (la primera rebanada), con el formato de `tarjeta.md`: máximo 4 criterios y un solo módulo propio por tarjeta. Las demás tareas se quedan como línea del backlog.
> - Cada tarjeta lleva «Fuera de alcance». Para las reglas con números, fechas o dinero, propón 2 a 4 ejemplos aprobados (entrada → resultado esperado) para que yo los apruebe.
> - Antes de T-001, registra como ADR las decisiones que arrastra el stack (base de datos local, versión mínima del lenguaje).
> - En UI, las tarjetas citan experiencia y referencias; cada criterio indica evidencia. Preparar el layout compartido en T-001 si cabe, o en una tarea fundacional antes de las pantallas. Los bloqueos compartidos se resuelven con tareas y dependencias explícitas.
> - T-001 es el esqueleto andante: la app arranca, un test pasa y el CI corre. También crea `comprobaciones.json` con los comandos del proyecto (un stack por lenguaje con su comando de pruebas y sus archivos de dependencias, instalar y arrancar, alcance de distribución y plataformas), completa la sección *Convenciones* de `docs/00-LEEME-IA.md` y adapta `.github/workflows/ci.yml` al stack, con build si aplica. Define idioma y formato de docstrings con un ejemplo; en varios servicios identifica sus comandos y la comprobación integrada.
> - Hito mínimo = el flujo ejecutable más corto de punta a punta; después, el entregable completo.
> - Entre módulos, contratos con stub. Para lo incierto, exploraciones con tiempo acotado.
>
> Si falta decidir el stack, pregúntamelo antes.

**Cambio en una app que ya existe.** Adjunta la salida de `git ls-files` (el árbol real), `docs/modelo.md`, los RF relacionados, `docs/plantillas/cambio.md` y `docs/plantillas/tarjeta.md`:

> Quiero hacer este cambio: (descríbelo). Escribe el mini-diseño en el formato de `cambio.md` (una página): qué se cambia, por qué, qué RF modifica o crea (dime cuál), fuera de alcance, criterios de aceptación y, si hay reglas con números, fechas o dinero, 2 a 4 ejemplos aprobados para que yo los apruebe. Después escribe de 1 a 3 tarjetas con el formato de `tarjeta.md` (máximo 4 criterios y un solo módulo propio cada una); en `Tocar:` incluye el RF o la sección de `modelo.md` que el parche actualiza, con la parte exacta. Si el cambio necesita más que eso, dímelo antes: subimos al camino completo.

**Bug o ajuste.** Adjunta el archivo donde ocurre, su RF y `docs/plantillas/tarjeta.md`:

> Hay un problema: (qué pasa y qué esperabas que pasara). Escribe una sola tarjeta rápida, con el formato de la variante «tarjeta rápida» de `tarjeta.md`. Su primer criterio debe reproducir el fallo: test que falla antes y pasa después cuando sea automatizable; para un defecto visual, evidencia reproducible de antes/después y las pruebas pertinentes. Registra la tarea nueva en el backlog y cobertura mediante replanificación. Si ves que hace falta más de un módulo o más de 4 criterios, dímelo antes: subimos de camino.

**Tarea.** Pega el bundle debajo de este texto:

> Implementa la tarea de este bundle siguiendo las reglas de `00-LEEME-IA.md`. Responde solo con los tres bloques: parche, reporte y comandos.

**Tarea en modo estricto** (la tarjeta dice `Modo: estricto`; la explicación está más abajo). Pega el bundle debajo de uno de estos textos, según la fase. En la fase 2, arma el bundle con `python tools/bundle.py T-007 --parche2`: suma los tests del parche 1.

> **Parche 1.** Haz solo la fase 1 de la tarea de este bundle: escribe los tests y, si hace falta para poder importarlos, un esqueleto que lance «no implementado». Los tests deben fallar por falta de funcionalidad, no por un error de importación. Responde solo con los tres bloques; el bloque de comandos termina en el test, sin commit, y el commit va en un segundo bloque aparte.

> **Parche 2.** Haz la fase 2: implementa la tarea sin tocar los tests del parche 1. Responde solo con los tres bloques.

**Un parche falló.** En el mismo chat:

> Al aplicar el parche me salió este error: (pega aquí el error). Devuélveme solo la parte corregida (el archivo y el bloque `@@` que falló), no el parche entero.

**Un test falló.** En el mismo chat:

> Al correr los tests me fallan estos: (pega aquí la salida). Corrige el código, no los tests. Si crees que algún test está mal, dímelo y espera mi respuesta. El parche nuevo no debe modificar los tests que ya existían. Tu parche anterior sigue aplicado en mi repo, sin guardar: parte de ese estado.

**Chat de hito** (al cerrar cada rebanada; los adjuntos y los pasos están más abajo). Pega esto:

> Es el chat de hito de la rebanada que acabo de cerrar. Haz tres cosas, en este orden. 1) Revisa la coherencia del proyecto y la evidencia de uso/UI frente a las referencias vigentes: dime si hay decisiones que se contradicen, decisiones tomadas sin registrar o tareas que se saltaron un contrato. 2) Mira la estructura del código: ¿hay algún archivo enorme, código repetido o un módulo que debió separarse? Si algo vale la pena, descríbelo como una tarjeta de refactor `REF-NN` (variante «tarjeta de refactor» de `tarjeta.md`) y **detente ahí**: todavía no escribas las tarjetas de la ola siguiente. 3) Si no hay nada que ordenar (o cuando te traiga el árbol ya ordenado), escribe las tarjetas completas de la ola siguiente, con el árbol real a la vista y el formato de `tarjeta.md`: «Fuera de alcance» en todas y ejemplos aprobados para las reglas con números, fechas o dinero. No cambies el backlog: si crees que hay que cambiarlo, dime qué y por qué.

## El ciclo de cada tarea (etapa 4)

**Antes de cada tarea, línea base en verde.** Confirma que la tarea anterior está terminada: los tests pasan en tu computador y el CI del último commit está en verde. *Para qué:* si empiezas sobre algo que ya está roto, nadie sabrá si un fallo nuevo es del LLM o heredado, y los errores se acumulan. `bundle.py` se niega a armar el bundle si una tarea de `Depende de:` no está «hecha» (una tarea está hecha cuando su tarjeta ya no existe en `docs/plan/tareas/`: la borra `cerrar.py --hecha`; `--forzar` salta esta compuerta, bajo tu responsabilidad).

1. **Preparar:** `python tools/bundle.py T-007`. *Para qué:* arma un solo archivo, `bundles/T-007.md`, con lo justo que el LLM necesita; así gasta pocos tokens y no se confunde. Ábrelo, copia todo su contenido y pégalo en el LLM. Si se niega a armarlo, te dice por qué (todos los motivos juntos). Lo más común es que la tarea cite una decisión que aún no aceptaste (acéptala primero: cambia su línea `Estado: propuesta` por `Estado: aceptada` y haz commit) o que una tarea anterior siga sin cerrarse. La primera vez, crea `~/.metodo-ia.json` con tu terminal y tu carpeta de parches (la línea para hacerlo está en `tools/README.md`); si no existe, el LLM te las preguntará.
2. **Implementar:** pega el bundle en el LLM que prefieras. Te devuelve **tres bloques**: un parche, un reporte y los comandos.
3. **Aplicar:** guarda el parche en Descargas y pega el bloque de comandos (explicado abajo). *Para qué:* el bloque prueba el parche, lo aplica, corre los tests y recién entonces guarda y sube.
4. **Verificar:** los tests corren en tu computador antes del commit; el bloque de comandos ya los incluye y, si fallan, se detiene sin guardar nada. Antes de cerrar, `python tools/comprobar.py entrega` repasa todo lo declarado del proyecto: pruebas que de verdad corrieron, dependencias fijadas, comandos documentados que existen y, si el software se distribuye, versión, plataformas y licencia. *Para qué:* un comando que sale sin error no demuestra que se haya probado algo; esa diferencia produjo cinco entregas en verde que eran falsas. El CI de GitHub es la red de seguridad, no la primera prueba.
5. **Cerrar (recepción provisoria):** `python tools/cerrar.py T-007 reporte.md --llm Claude`. *Para qué:* es el inspector que recibe la obra. Revisa que el reporte esté completo, mira qué archivos cambió el commit (el bloque de comandos ya lo hizo) y te avisa de lo raro: archivos fuera de `Tocar:`, dependencias nuevas, tests antiguos modificados, cambios en contratos. Guarda el reporte en `docs/plan/reportes/` (si estaba en la raíz del repo, lo mueve; si estaba en otra carpeta, lo copia), actualiza `ESTADO.md` y convierte las decisiones que afectan a otras tareas en propuestas de ADR. La tarea queda «en revisión». Si el reporte tiene errores, te dice cuáles y no escribe nada; con `--check` solo ensaya. Si es un segundo intento (por ejemplo, el CI falló y lo corregiste), agrega `--reintento`.
6. **Decidir y cerrar del todo (recepción definitiva):** revisa con `git diff` y acepta o rechaza las propuestas de ADR (para aceptar una, cambia su línea `Estado: propuesta` por `Estado: aceptada`). Cuando el CI de GitHub salga en verde y se hayan completado las comprobaciones de aceptación exigidas (incluida revisión de UI o uso), corre `python tools/cerrar.py T-007 --hecha`. El script no consulta el CI ni verifica aprobación visual por sí solo. *Para qué:* «hecha» significa línea base en verde, y eso solo lo sabes tú al mirar el CI. El comando deja la tarea «hecha», borra su tarjeta de `docs/plan/tareas/` con un borrado normal (sin `git rm`) y te dice qué tareas quedaron desbloqueadas. Después haces **un** commit con todo el cierre (`ESTADO.md`, el reporte, las decisiones y la tarjeta borrada): su historia queda en git y en los reportes.

Si la tarjeta dice `Modo: estricto`, la tarea son dos parches: mira «Modo estricto» más abajo.

**Si te pierdes en cualquier punto del ciclo, abre `docs/plan/ESTADO.md`.** Sus tres primeras líneas dicen en qué etapa estás, cuál es el siguiente comando exacto y qué decisión está esperándote. Las escribe `cerrar.py` con cada cierre, a partir de lo que ya hay en el repo. *Para qué:* no tener que reconstruir la conversación para saber qué sigue.

### El bloque de comandos, línea por línea

Ejemplo en PowerShell. El LLM te lo entrega ya con tus rutas y el nombre real del parche.

```powershell
cd "$env:USERPROFILE\Desktop\mi-app"
git status --short   # debe salir vacío
python tools/aplicar.py "$env:USERPROFILE\Downloads\T-007-registrar-actividad.patch"
if ($LASTEXITCODE -eq 0) { pytest tests/actividades }   # el comando de test de la tarjeta; si no trae uno, esta línea no va
if ($LASTEXITCODE -eq 0) { git add -A; if ($LASTEXITCODE -eq 0) { git commit -m "feat: registrar actividad" } }
if ($LASTEXITCODE -eq 0) { git push }
if ($LASTEXITCODE -ne 0) { Write-Host "Algo falló: el bloque se detuvo ahí. Pega aquí lo que dice la terminal." }
```

**El freno.** PowerShell no se detiene solo cuando un comando externo falla (por ejemplo, un test que da error): seguiría con la línea siguiente y guardaría igual el código roto. Por eso cada paso corre solo si el anterior salió bien (`$LASTEXITCODE` vale 0), como una cadena de semáforos: si uno se pone en rojo, los siguientes no avanzan y la última línea te avisa.

| Línea | Para qué |
|---|---|
| `cd …` | Entra a la carpeta de tu repo. Confirma la ruta con `pwd`: OneDrive a veces mueve el Escritorio. |
| `git status --short` | Lista lo que está sin guardar. **Debe salir vacío**: así el `git add -A` solo mete lo del parche. |
| `python tools/aplicar.py …` | Limpia, comprueba y aplica el parche. Si no encaja, diagnostica sin aplicar ninguna parte. |
| comando de test | Corre los tests de la tarea antes de guardar. Si fallan, no se guarda nada. |
| `git add -A` y luego `git commit -m …`, con freno entre ambos | Marca todos los cambios y los guarda con un mensaje (viene en el reporte). |
| `git push` | Sube el commit a GitHub. |
| última línea | Si algo falló, te lo dice; si todo salió bien, no dice nada. |

Para otras terminales (CMD, Git Bash, macOS, Linux), mira la tabla de equivalentes en `00-LEEME-IA.md`; allí el freno se escribe uniendo los comandos con `&&`.

### Guardar el parche

- Si el chat te entrega un archivo descargable, queda en Descargas: úsalo tal cual.
- Si no: pega el bloque `diff` en el Bloc de notas → *Guardar como* → tipo «Todos los archivos» → nombre `T-007-tema.patch` → codificación UTF-8.
- Windows oculta las extensiones: comprueba que no quedó `T-007-tema.patch.txt` (Explorador → Vista → Mostrar → *Extensiones de nombre de archivo*).
- El archivo debe terminar con un salto de línea; un parche cortado al final da *corrupt patch*.

### Si algo falla (en este orden)

1. **Cambios previos:** antes de una tarea nueva, revisa `git status --short`; resuélvelos antes de aplicar. En un reintento tras un test fallido es normal ver el parche anterior sin commit.
2. **Falla la aplicación:** `aplicar.py` ya probó la cadena acumulativa y no aplicó ninguna parte. Pega el diagnóstico al LLM. Si devuelve solo el bloque corregido, reemplázalo en el parche original conservando los demás bloques y aplica el parche completo de nuevo. No uses `--reject` sobre tu repo: el diagnóstico ya lo usa en una copia temporal.
3. **Un test falla después de aplicar:** el parche queda aplicado sin guardar. Pega la salida al LLM con «Un test falló»: el nuevo parche parte de ese estado y corrige código, sin cambiar tests existentes.
4. **Parche ya aplicado:** revisa el nombre y el diff; no lo apliques otra vez. Indica explícitamente el archivo nuevo.
5. **Descartar un intento:** `git stash -u` lo guarda aparte y deja limpio el repo; revisa lo guardado antes de decidir borrarlo.

### Modo estricto (opcional)

Si la tarjeta dice `Modo: estricto`, la tarea son **dos parches**, en este orden:

1. **Solo los tests** (y, si hace falta para poder importarlos, un esqueleto vacío que lance «no implementado»). Los corres, compruebas que **fallan por la razón correcta** y haces commit.
2. **La implementación**, con esos tests a la vista y sin tocarlos.

*Para qué:* es como marcar en la pared hasta dónde debe llegar la repisa *antes* de colgarla. Si el mismo LLM escribe los tests y el código a la vez, puede escribir un test que confirme su propio error: la marca queda donde quedó la repisa. Con dos pasos, la marca existe primero y la repisa tiene que ajustarse a ella.

**Cuándo usarlo:** solo si ya hubo un primer fallo en esa tarea, si las reglas no caben en 2 a 4 ejemplos aprobados o si tú lo pides. **No** «por peso 5»: eso arrastraría casi todas las tareas. *Cuánto cuesta:* dos llamadas al LLM y dos aplicaciones por tarea. Una idea sin probar: que los tests los escriba un LLM distinto del que implementa.

**Cómo funciona el parche 1.** Pega el texto «Tarea en modo estricto» (arriba, entre los prompts). El bloque de comandos llega hasta el test y se detiene, sin commit, porque aquí el rojo es lo esperado:

```powershell
cd "$env:USERPROFILE\Desktop\mi-app"
git status --short   # debe salir vacío
python tools/aplicar.py "$env:USERPROFILE\Downloads\T-007-actividades-tests.patch"
if ($LASTEXITCODE -eq 0) { pytest tests/actividades }   # aquí se ESPERA que falle: lee el mensaje
```

Lee lo que salió (los nombres son de Python; en otro lenguaje busca lo equivalente):

- **Rojo correcto:** el mensaje habla de lo que falta (`NotImplementedError`, o una comprobación que no se cumple: `AssertionError`).
- **Rojo equivocado:** el test ni siquiera llegó a ejecutarse (`ImportError`, `ModuleNotFoundError`, `SyntaxError`, `NameError`). Pega la salida al LLM (el texto «Un test falló») y pídele el parche corregido, que se aplica encima.

En Python, el comando recomendado para el parche 1 es:

```powershell
python tools/aplicar.py "$env:USERPROFILE\Downloads\T-007-actividades-tests.patch" --estricto "pytest tests/actividades"
```

Este comando reemplaza la aplicación y el test del ejemplo anterior; no ejecutes ambos ejemplos seguidos. Devuelve 0 si reconoce el rojo esperado y 1 si el test pasa, falla por otro motivo o no puede clasificarlo. Con 1, revisa el mensaje antes de continuar; el parche sigue aplicado. Para otros lenguajes conserva la revisión manual.

Si el rojo es el correcto, pega este segundo bloque (el commit) y sigue con el parche 2:

```powershell
git add -A
if ($LASTEXITCODE -eq 0) { git commit -m "test: registrar actividad (rojo)" }
if ($LASTEXITCODE -eq 0) { git push }
```

Después del commit, ciérrala con `python tools/cerrar.py T-007 reporte.md --parcial`: queda «parcial» y su tarjeta se queda, porque aún falta el parche 2. *Para qué:* deja constancia de que el parche 1 está hecho y te recuerda qué rojo es el correcto. Luego arma el bundle del parche 2 con `python tools/bundle.py T-007 --parche2` y, al terminar, cierra con `cerrar.py T-007 reporte.md` (sin `--parcial`).

## Al cerrar cada rebanada: prueba de uso y chat de hito

Los tests pueden pasar y la app, aun así, no servir. Al terminar cada rebanada (el grupo de tareas que deja algo usable), haz estas dos cosas, en este orden. *Para qué:* es la inspección de obra de cada piso: antes de levantar el siguiente se comprueba que sirve y que no quedó nada torcido.

**Primero, la prueba de uso.** Corre la app y haz tú mismo un recorrido corto, como lo haría quien la va a usar. *Para qué:* es la única comprobación que no depende de lo que escribió el LLM.

1. Pide el recorrido a un LLM con el modelo, actores y experiencia aplicable; adjunta las referencias visuales reales:

   > Con los flujos principales, actores y experiencia vigente si aplica, escríbeme una prueba de uso de 3 a 5 pasos para lo que ya funciona: qué hacer en cada paso y qué debería pasar.

2. Haz los pasos. Si hay UI, comprueba acción principal, recuperación de error, tamaños previstos, teclado, foco y legibilidad. Registra versión, resultado y capturas pertinentes. Si falla una tarea ya cerrada, registra una nueva corrección con su evidencia.
3. Contrasta el conjunto con las referencias aprobadas. Estas comprobaciones también se realizan durante cada tarea de UI; el hito revisa la coherencia global.

**Después, el chat de hito.** Un chat nuevo por rebanada, de preferencia con otro LLM. *Para qué:* unos ojos frescos revisan lo hecho, miran si el código se está enredando y dejan escritas las tarjetas de la ola siguiente, todo en un solo chat para gastar menos. Adjunta la salida de `git ls-files` (el árbol real), el índice de decisiones, los ADR relacionados con la rebanada, la salida de `git log --oneline`, `docs/plan/backlog.md` y `docs/plantillas/tarjeta.md`, la experiencia y evidencia de uso si hay UI, y pega el texto «Chat de hito» (arriba, entre los prompts).

- Si el LLM propone un refactor (una tarjeta `REF-NN`), se ejecuta como cualquier tarea, con la regla extra de que los tests no cambian y siguen verdes, **antes** de escribir las tarjetas de la ola siguiente. *Para qué:* así las tarjetas se escriben sobre un árbol ya ordenado y no sobre uno que va a cambiar. Cuando termine, vuelve al mismo chat con el `git ls-files` nuevo y pídele el paso 3.
- Las tarjetas nuevas se reparten con `python tools/init_plan.py PLAN-ola2.md` (un archivo con solo `## Tarjetas de la ola 2`). *Para qué:* las verifica contra el backlog guardado y no pisa las tarjetas que ya existen.
- Escribir las tarjetas de la ola siguiente es rutina. **Cambiar el backlog** (orden, dependencias, tareas nuevas) es replanificar: se guarda como un archivo nuevo, `PLAN-v2.md`, con las tres secciones, la versión siguiente y su `Motivo del cambio:` (formato en `docs/plantillas/plan.md`), y se reparte con `python tools/init_plan.py PLAN-v2.md`. *Para qué:* reemplaza `backlog.md` y `cobertura.md` por los nuevos y deja como están las tarjetas que ya existen.

## Etapa 5: entrega, operación y distribución

Las cuatro etapas anteriores terminan en «CI verde y tarea cerrada». Eso todavía no es software que alguien use: falta que arranque en una máquina que no es la tuya, que los datos sobrevivan a una actualización y que un fallo se pueda diagnosticar sin estar tú delante. *Para qué:* es la parte de la que depende que el software sea confiable con datos reales y con el tiempo, y es también donde el método se quedaba corto.

Esta etapa **no va al final del proyecto**. Su alcance se declara en el diseño, porque cambia el plan (una migración o un empaquetado son tareas), y se ejerce en cada versión que publicas.

**Primero, el alcance.** Lo declaras en el diseño y en `distribucion` de `comprobaciones.json`. Una herramienta personal no paga el coste de un producto distribuido:

| Alcance | Cuándo | Qué exige, además de lo anterior |
|---|---|---|
| `solo-yo` | Solo tú, en tu máquina | Arranque reproducible · tus datos sobreviven a una actualización · un fallo se ve y se puede diagnosticar |
| `mis-dispositivos` | La misma app en tu PC y en tu móvil | Versión de producto · identidad de cada dispositivo · qué pasa si dos copias cambian lo mismo |
| `otras-personas` | Alguien más la instala | Empaquetado · plataformas verificadas, no supuestas · notas de cambio para quien la usa · licencia propia y de terceros · qué sale del equipo cuando hay red |

**Las siete preguntas de la etapa.** Cada respuesta tiene un sitio; ninguna crea un documento nuevo.

1. ¿Quién la instala, y en qué plataformas y versiones **exactas**? → `plataformas` de `comprobaciones.json` y la sección *Tecnología* del diseño.
2. ¿Cómo se instala, y cómo se comprueba que quedó bien desde un entorno limpio? → `comandos` de `comprobaciones.json`; la instalación real la ejecuta el CI en cada plataforma declarada.
3. ¿Qué versión es esta y qué cambió para quien la usa? → la versión en el manifiesto del stack, y las notas de cambio que salen de los reportes de las tareas cerradas.
4. ¿Qué pasa con los datos al actualizar? → `datos` de `comprobaciones.json`: la versión de tus datos, y una carpeta con ejemplos de cada versión anterior que alguna prueba use. Respalda antes de migrar.
5. ¿Cómo se ve y se diagnostica un fallo en una máquina ajena? → un registro en una ubicación conocida, un mensaje que diga qué hacer, y una forma de que te lo envíen.
6. ¿Qué se expone cuando hay red? → una ADR **antes** del primer incremento con red: identidad de dispositivos, qué se sincroniza y qué no sale del equipo.
7. ¿Qué licencia tiene lo tuyo y lo de terceros que distribuyes? → un archivo de licencia en la raíz.

**Qué comprueba una máquina y qué no.** `python tools/comprobar.py entrega` comprueba las preguntas 1, 2, 3, 4 y 7, y falla cuando la respuesta es una promesa en vez de un hecho: una plataforma declarada que el CI no ejecuta, unos datos viejos que ninguna prueba usa, una licencia que no está. Las preguntas **5 y 6 no tienen comprobación automática**: la 5 depende de cada proyecto y la 6 es una decisión. No finjas que están cubiertas porque el ejecutor salió en verde.

**La tarjeta de entrega** es una `T-NNN` normal, como los cambios visuales: no hay un prefijo nuevo. Sus criterios son los de arriba que apliquen, con su evidencia; y la prueba de uso de la rebanada se hace sobre la versión instalada, no sobre tu copia de desarrollo.

## Documentar correcciones

| Situación | Qué hacer | Dónde queda |
|---|---|---|
| El parche no se aplica | Corregir el parche de la misma tarea; una aplicación rechazada no dejó cambios parciales. | Registrar el incidente si explica una limitación o decisión; no hace falta un registro de cada intento de formato. |
| Falla una tarea abierta | Corregir la misma tarea. Si ya está en revisión, seguir `cerrar.py --reintento`. | Reporte de la tarea y commits existentes. |
| Aparece un bug después del cierre | Crear una T-NNN nueva, rápida si cabe; registrarla en backlog y cobertura con replanificación. | Nueva tarjeta, reporte y commits, citando RF y tarea de origen cuando se conozca. |

En `Hecho` del reporte escribe fallo, comportamiento esperado, causa encontrada (o desconocida) y solución. En `Cómo probar`, reproducción y evidencia de antes/después: test de regresión cuando sea automatizable o evidencia visual reproducible y pruebas pertinentes. Mantén las seis secciones de la plantilla. Usa el ID de tarea en el commit, por ejemplo `fix: T-023 conservar datos al reintentar`.

`cerrar.py --reintento` escribe en la misma ruta del reporte. Git conserva versiones anteriores solo si se guardaron en commits; resume en el reporte final los intentos no guardados que sea importante conservar. No es necesario almacenar cada `.patch` además del código versionado y su explicación.

Si el código incumplía un requisito correcto, ese requisito se conserva. Si estaba mal el diseño, actualiza también RF, roles, experiencia o diagramas afectados y decláralos en `Tocar:`. Una corrección no se disfraza de REF.

## Hábitos que ahorran tokens y esperas

- **Un chat por tarea** (y uno por hito). Cada mensaje hace que el LLM relea todo el chat: cuanto más largo, más cuesta. Si un chat se alarga, ciérralo y retoma con un bundle o un archivo nuevo.
- **Máximo dos intentos por fallo.** Al segundo, el LLM debe parar y reportar qué probó; seguir insistiendo gasta sesión sin avanzar.
- **Tareas chicas:** una sesión, hasta 4 criterios, un solo módulo propio.
- **Decide pronto lo que afecta a otras tareas.** Un LLM que decide en silencio algo que toca otras tareas es la forma más fácil de que el proyecto se contradiga.
- **Un error que se repite se arregla en el método, no en el chat.** Si el mismo problema aparece dos veces (en cualquier LLM), agrega una regla corta a `00-LEEME-IA.md` o, mejor, un chequeo a `tools/cerrar.py`. *Para qué:* el método mejora con el uso en vez de repetir fallos. Un chequeo automático pesa más que una regla escrita, porque los LLM a veces ignoran las reglas.

## Avisos que no son errores

- `warning: LF will be replaced by CRLF…` al hacer `git add` en Windows: Git está ajustando los saltos de línea. Es normal; puedes ignorarlo.
- Un CI en verde con un aviso amarillo «Todavía no hay tests»: es lo esperado antes de T-001. Quiere decir que el CI no probó nada, no que todo esté bien.

## PowerShell y entornos virtuales de Python

*Solo si el stack de tu app usa Python.* Para activar el entorno virtual: `.venv\Scripts\Activate.ps1`. Si PowerShell dice que la ejecución de scripts está deshabilitada, corre esto una vez (es opcional y afecta solo a tu usuario): `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Glosario rápido

| Término | Significado |
|---|---|
| ADR | Registro de decisión: una hoja corta por decisión, con su motivo y estado |
| Bundle | Paquete con solo el contexto que una tarea necesita; es lo que se pega en el LLM |
| Tarjeta de tarea | Orden de trabajo pequeña y autocontenida |
| Compuerta | Punto donde una decisión debe resolverse antes de que otras tareas dependan de ella |
| Contrato / stub | Contrato: acuerdo sobre cómo se llaman dos módulos. Stub: implementación de mentira que lo cumple mientras llega la real |
| Esqueleto andante | Versión mínima de punta a punta que arranca, prueba y corre en CI |
| Rebanada vertical | Funcionalidad completa (datos, lógica e interfaz) en lugar de una capa suelta |
| Parche (patch o diff) | Archivo de texto con los cambios exactos, que se aplica con `git apply` |
| Entorno del usuario | Terminal, carpeta de parches y carpeta del repo: lo que permite dar comandos listos para pegar |
| CI | Pruebas automáticas que GitHub corre en cada cambio |
| Fuera de alcance | Lo que una tarea (o la app) explícitamente no construye, aunque parezca razonable; corta el código que nadie pidió |
| Ejemplo aprobado | Caso concreto «entrada → resultado esperado» que tú apruebas; los tests lo incluyen tal cual y su valor esperado no se cambia |
| Línea base en verde | Tests locales y CI pasando antes de empezar una tarea nueva |
| Backlog | La lista completa de tareas del plan, una línea por tarea (ID, título, depende de, cubre) |
| Matriz de cobertura | Tabla criterio → requisito → tareas: muestra qué tarea cubre qué y evita que algo quede sin hacer |
| Ola | La rebanada cuyas tarjetas completas se escriben ahora; las demás viven solo como línea del backlog |
| Camino | El tamaño del proceso según el trabajo: completo, cambio o rápido |
| Mini-diseño | Página del camino «cambio»: qué se cambia, por qué, qué RF toca, fuera de alcance, criterios y ejemplos |
| Rojo / verde | Rojo: los tests nuevos fallan porque falta la funcionalidad. Verde: pasan después de implementarla, sin cambiar los tests |
| Refactor | Ordenar el código sin cambiar lo que hace; la prueba es que los tests no cambian y siguen en verde |
| Chat de hito | El chat al cerrar cada rebanada: revisión de coherencia, pregunta de estructura y tarjetas de la ola siguiente |
