# Cómo trabajar con este repo

Esta guía es para ti, la persona que dirige el proyecto. Los LLM leen `00-LEEME-IA.md`; tú lees esta.

## La idea, con una analogía

Piensa en construir una casa. Primero hablas con el arquitecto y quedan escritos los **planos** (el diseño y los diagramas). Después se arma el **plan de obra**: una lista de tareas pequeñas, cada una con su orden de trabajo. Por último, cada tarea se le entrega a un obrero (un LLM) con *solo* lo que necesita, y el obrero devuelve el trabajo hecho y un informe.

Este repo es el **cuaderno de obra**: todo queda escrito aquí. Por eso puedes cambiar de LLM, o abrir un chat nuevo, sin explicar todo desde cero: el cuaderno ya lo dice.

## Las 4 etapas

| Etapa | Qué haces tú | Qué queda en el repo |
|---|---|---|
| 1. Diseño | Conversas con un LLM hasta cerrar `DISENO.md` | `DISENO.md`, repartido luego en `docs/` |
| 2. Diagramas | Pides diagramas a partir del diseño | `docs/diagramas/` |
| 3. Plan | Pides el plan por olas: la lista completa de tareas y tarjetas solo para la próxima ola | `docs/plan/backlog.md`, `docs/plan/cobertura.md` y `docs/plan/tareas/` |
| 4. Código | Repites el ciclo de abajo, una tarea a la vez | Un parche por tarea y `docs/plan/ESTADO.md` |

Las **decisiones** (`docs/decisiones/`) y los **tests** atraviesan las cuatro etapas.

## Elegir el camino

Las cuatro etapas de arriba son el camino **completo**. Pero no es lo mismo construir una casa que remodelar una pieza o arreglar una gotera: el rigor debe ser proporcional al trabajo. Tú, con el LLM, eliges el camino **antes de empezar**.

| Camino | Cuándo | Qué escribes |
|---|---|---|
| **Completo** (construir una casa) | App o módulo nuevo, o entidades y relaciones nuevas | Las 4 etapas |
| **Cambio** (remodelar una pieza) | Una funcionalidad nueva en una app que ya existe; un campo nuevo en una entidad cuenta como cambio | Un mini-diseño de una página (`docs/plantillas/cambio.md`; se guarda en `docs/cambios/`) y de 1 a 3 tarjetas |
| **Rápido** (arreglar una gotera) | Un bug o un ajuste | Una tarjeta rápida (variante en `docs/plantillas/tarjeta.md`); un bug parte con el test que lo reproduce |

- **Regla de subida:** si una tarjeta de un camino liviano necesita más de 4 criterios o más de un módulo, el trabajo no era liviano: sube al camino siguiente. *Para qué:* un camino corto no debe servir para saltarse el rigor. Aunque el camino sea corto, cada tarea lleva su tarjeta, su test y su reporte.
- **Los documentos se mantienen vivos.** Si una tarea cambia el comportamiento, su parche actualiza también el RF o la sección de `docs/modelo.md` que corresponda (y el `.puml` si cambia el modelo), y esos archivos van en el `Tocar:` de la tarjeta. La versión vigente es la de `docs/requisitos/` y `docs/modelo.md`; el `DISENO.md` original queda en `docs/archivo/` como foto histórica. *Para qué:* si nadie los actualiza, el mapa de lo que hace la app termina mintiendo.
- **Las tarjetas se desechan al cerrar la tarea.** Su historia queda en git y en `docs/plan/reportes/`, y la traza «qué tarea cubre qué» queda en el backlog (o, en un cambio, en su mini-diseño).
- **Una app que ya existe** (por ejemplo CrafTerraria): se documenta solo lo que se toca; el primer cambio sobre un área crea el RF o la sección de `modelo.md` de esa área. *(Pendiente: copiar el esqueleto del método a un repo que ya existe.)*

## Qué funciona hoy y qué falta

Esta plantilla trae la estructura de carpetas, las guías, los formatos en blanco (`docs/plantillas/`) y un CI mínimo. **Las herramientas de `tools/` se construyen de a una**: hoy existen `init_diseno.py` e `init_plan.py`; las demás todavía no. Los pasos que dependen de una herramienta que falta llevan la marca *(pendiente)*; mientras no exista, ese paso hay que hacerlo a mano. Cuando una herramienta existe, se quita su marca. El formato del plan por olas ya lo lee `init_plan.py`. Los del mini-diseño de cambio y de las tarjetas rápida y de refactor están definidos en `docs/plantillas/`, pero todavía no los lee ninguna herramienta.

## Empezar una app nueva

**Primero el diseño, después el repo.** El diseño cambia mucho al principio, así que vive en un solo archivo (`DISENO.md`) fuera del repo hasta que se cierra. Cada chat de diseño empieza adjuntándolo y termina devolviéndolo actualizado.

Un diseño está listo para cerrarse cuando:

- el alcance dice también lo que queda **fuera**;
- cada requisito (RF) tiene criterios de aceptación comprobables y su línea `Aporta a:`;
- están las entidades, las relaciones y los flujos principales;
- la tecnología está decidida (o queda anotada como pendiente);
- no quedan preguntas marcadas `[BLOQUEA]`;
- los ADR propuestos se revisaron: se aceptan o se rechazan **en bloque**.

Tú decides si cierras dejando huecos anotados.

Con el diseño cerrado:

1. **En GitHub, botón *Use this template* → *Create a new repository*.** *Para qué:* obtienes una copia limpia de toda esta estructura, sin arrastrar la historia de otros proyectos.
2. **Clona el repo nuevo en tu computador.** *Para qué:* tener la copia donde puedas trabajarla. En PowerShell:

   ```powershell
   $escritorio = [Environment]::GetFolderPath("Desktop")   # encuentra tu Escritorio aunque OneDrive lo haya movido
   cd $escritorio
   git clone URL-DEL-REPO-NUEVO
   ```

3. **Copia `DISENO.md` a la raíz del repo y corre `python tools/init_diseno.py DISENO.md`.** *Para qué:* reparte el diseño en `docs/` (un archivo por requisito y por decisión, más el contexto y el modelo) sin que cortes y pegues. Si el formato tiene errores, te dice en qué línea y no escribe nada. El original se mueve a `docs/archivo/`. Si quieres revisar sin escribir nada, agrega `--check` al final; y si `python` no se reconoce en tu PowerShell, prueba con `py`.
4. **Revisa con `git status` y `git diff`; luego commit y push.** *Para qué:* ver qué se repartió antes de guardarlo.
5. **Pide el plan por olas y repártelo con `python tools/init_plan.py PLAN.md`; después, valídalo con `python tools/validar.py`** *(validar.py: pendiente)*. *Para qué:* `init_plan.py` revisa el formato y deja en `docs/plan/` la lista completa de tareas (el backlog), su cuadro de cobertura y las tarjetas completas solo de la primera ola. Las demás se escriben cuando les llega el turno, como los planos de detalle de cada piso: se dibujan cuando el piso anterior ya está construido y se puede medir. Si el formato tiene errores, te dice en qué línea y no escribe nada; con `--check` solo revisa. El original se mueve a `docs/archivo/`. El validador comprobará que no falte ni sobre nada; mientras no exista, repasa tú la matriz de cobertura: que cada criterio llegue a alguna tarea y que ninguna tarea quede sin criterio.

## Qué pedirle a un LLM en cada etapa

Textos para copiar y pegar. Si algo te cuesta entender, agrega: «explícame con una analogía».

**Diseño.** Adjunta tu enunciado o tus notas y `docs/plantillas/diseno.md` (o tu `DISENO.md` si ya existe):

> Vamos a diseñar una app. Ordena lo que te cuento en el formato de `diseno.md`. Pregunta solo lo que falte; todo lo que yo no haya dicho márcalo como supuesto (S-xx) o pregunta (P-xx), sin inventar cifras. Antes de dar el diseño por cerrado, pregúntame (máximo 5 preguntas por tanda) por lo que cuesta cambiar después: ¿un usuario o varios?, ¿hay login?, ¿idiomas?, ¿datos sensibles?, ¿dónde corre (web, escritorio, móvil)?, ¿cuántos datos? Lo que quede sin resolver anótalo como pregunta P-xx con [BLOQUEA] o como ADR propuesto. Cuando terminemos, devuélveme el `DISENO.md` completo y actualizado.

**Diagramas.** Adjunta `DISENO.md`:

> A partir de este `DISENO.md`, genera los diagramas en PlantUML: ER de las entidades, secuencia de los flujos principales, despliegue lógico y casos de uso. Un archivo `.puml` por diagrama.

Con Claude, la skill `puml-diagramas` ya conoce el formato.

**Plan.** Adjunta `DISENO.md`, los diagramas, `docs/plantillas/plan.md` y `docs/plantillas/tarjeta.md`:

> Con esto, arma el plan por olas, en un solo archivo `PLAN.md` con el formato de `plan.md`:
>
> - Backlog completo: todas las tareas, una línea cada una (ID, título, depende de, cubre), agrupadas en rebanadas verticales ordenadas por peso, riesgo y dependencias; cada rebanada deja algo ejecutable.
> - Matriz de cobertura sobre todo el backlog: cada criterio → RF → tareas, sin RF huérfanos ni tareas sin criterio.
> - Tarjetas completas solo para la ola 1 (la primera rebanada), con el formato de `tarjeta.md`: máximo 4 criterios y un solo módulo propio por tarjeta. Las demás tareas se quedan como línea del backlog.
> - Cada tarjeta lleva «Fuera de alcance». Para las reglas con números, fechas o dinero, propón 2 a 4 ejemplos aprobados (entrada → resultado esperado) para que yo los apruebe.
> - Antes de T-001, registra como ADR las decisiones que arrastra el stack (base de datos local, versión mínima del lenguaje).
> - T-001 es el esqueleto andante: la app arranca, un test pasa y el CI corre. También completa las secciones *Convenciones* y *Comandos* de `docs/00-LEEME-IA.md` y adapta `.github/workflows/ci.yml` al stack.
> - Hito mínimo = el flujo ejecutable más corto de punta a punta; después, el entregable completo.
> - Entre módulos, contratos con stub. Para lo incierto, exploraciones con tiempo acotado.
>
> Si falta decidir el stack, pregúntamelo antes.

**Cambio en una app que ya existe.** Adjunta la salida de `git ls-files` (el árbol real), `docs/modelo.md`, los RF relacionados, `docs/plantillas/cambio.md` y `docs/plantillas/tarjeta.md`:

> Quiero hacer este cambio: (descríbelo). Escribe el mini-diseño en el formato de `cambio.md` (una página): qué se cambia, por qué, qué RF modifica o crea (dime cuál), fuera de alcance, criterios de aceptación y, si hay reglas con números, fechas o dinero, 2 a 4 ejemplos aprobados para que yo los apruebe. Después escribe de 1 a 3 tarjetas con el formato de `tarjeta.md` (máximo 4 criterios y un solo módulo propio cada una); en `Tocar:` incluye el RF o la sección de `modelo.md` que el parche actualiza, con la parte exacta. Si el cambio necesita más que eso, dímelo antes: subimos al camino completo.

**Bug o ajuste.** Adjunta el archivo donde ocurre, su RF y `docs/plantillas/tarjeta.md`:

> Hay un problema: (qué pasa y qué esperabas que pasara). Escribe una sola tarjeta rápida, con el formato de la variante «tarjeta rápida» de `tarjeta.md`. Su primer criterio debe ser el test que reproduce el fallo: falla hoy y pasará cuando esté arreglado. Si ves que hace falta más de un módulo o más de 4 criterios, dímelo antes: subimos de camino.

**Tarea.** Pega el bundle debajo de este texto:

> Implementa la tarea de este bundle siguiendo las reglas de `00-LEEME-IA.md`. Responde solo con los tres bloques: parche, reporte y comandos.

**Tarea en modo estricto** (la tarjeta dice `Modo: estricto`; la explicación está más abajo). Pega el bundle debajo de uno de estos textos, según la fase. Mientras `bundle.py` no exista, adjunta tú los tests del parche 1 en la fase 2:

> **Parche 1.** Haz solo la fase 1 de la tarea de este bundle: escribe los tests y, si hace falta para poder importarlos, un esqueleto que lance «no implementado». Los tests deben fallar por falta de funcionalidad, no por un error de importación. Responde solo con los tres bloques; el bloque de comandos termina en el test, sin commit, y el commit va en un segundo bloque aparte.

> **Parche 2.** Haz la fase 2: implementa la tarea sin tocar los tests del parche 1. Responde solo con los tres bloques.

**Un parche falló.** En el mismo chat:

> Al aplicar el parche me salió este error: (pega aquí el error). Devuélveme solo la parte corregida (el archivo y el bloque `@@` que falló), no el parche entero.

**Un test falló.** En el mismo chat:

> Al correr los tests me fallan estos: (pega aquí la salida). Corrige el código, no los tests. Si crees que algún test está mal, dímelo y espera mi respuesta. El parche nuevo no debe modificar los tests que ya existían. Tu parche anterior sigue aplicado en mi repo, sin guardar: parte de ese estado.

**Chat de hito** (al cerrar cada rebanada; los adjuntos y los pasos están más abajo). Pega esto:

> Es el chat de hito de la rebanada que acabo de cerrar. Haz tres cosas, en este orden. 1) Revisa la coherencia del proyecto: dime si hay decisiones que se contradicen, decisiones tomadas sin registrar o tareas que se saltaron un contrato. 2) Mira la estructura del código: ¿hay algún archivo enorme, código repetido o un módulo que debió separarse? Si algo vale la pena, descríbelo como una tarjeta de refactor `REF-NN` (variante «tarjeta de refactor» de `tarjeta.md`) y **detente ahí**: todavía no escribas las tarjetas de la ola siguiente. 3) Si no hay nada que ordenar (o cuando te traiga el árbol ya ordenado), escribe las tarjetas completas de la ola siguiente, con el árbol real a la vista y el formato de `tarjeta.md`: «Fuera de alcance» en todas y ejemplos aprobados para las reglas con números, fechas o dinero. No cambies el backlog: si crees que hay que cambiarlo, dime qué y por qué.

## El ciclo de cada tarea (etapa 4)

**Antes de cada tarea, línea base en verde.** Confirma que la tarea anterior está terminada: los tests pasan en tu computador y el CI del último commit está en verde. *Para qué:* si empiezas sobre algo que ya está roto, nadie sabrá si un fallo nuevo es del LLM o heredado, y los errores se acumulan. Cuando exista `bundle.py`, se negará a armar el bundle si una tarea de `Depende de:` no está «hecha».

1. **Preparar:** `python tools/bundle.py T-007` *(pendiente)*. *Para qué:* arma un solo archivo con lo justo que el LLM necesita; así gasta pocos tokens y no se confunde. Si se niega a armarlo, es porque la tarea cita una decisión que aún no aceptaste: acéptala primero.
2. **Implementar:** pega el bundle en el LLM que prefieras. Te devuelve **tres bloques**: un parche, un reporte y los comandos.
3. **Aplicar:** guarda el parche en Descargas y pega el bloque de comandos (explicado abajo). *Para qué:* el bloque prueba el parche, lo aplica, corre los tests y recién entonces guarda y sube.
4. **Verificar:** los tests corren en tu computador antes del commit; el bloque de comandos ya los incluye y, si fallan, se detiene sin guardar nada. El CI de GitHub es la red de seguridad, no la primera prueba.
5. **Cerrar:** `python tools/cerrar.py T-007 reporte.md` *(pendiente)*. *Para qué:* registra el reporte, actualiza `ESTADO.md`, convierte las decisiones nuevas en propuestas y te avisa de cosas raras (dependencias nuevas, tests antiguos modificados, cambios en contratos). La tarea queda «en revisión» hasta que pase en tu computador y en el CI.
6. **Decidir:** aceptas o rechazas las decisiones que el LLM propuso, haces commit y sigues. Cuando una tarea queda «hecha», su tarjeta se borra de `docs/plan/tareas/` (`cerrar.py` lo hará; mientras no exista, hazlo tú con `git rm` y un commit): su historia queda en git y en los reportes.

Si la tarjeta dice `Modo: estricto`, la tarea son dos parches: mira «Modo estricto» más abajo.

### El bloque de comandos, línea por línea

Ejemplo en PowerShell. El LLM te lo entrega ya con tus rutas y el nombre real del parche.

```powershell
cd "$env:USERPROFILE\Desktop\mi-app"
git status --short   # debe salir vacío
git apply --check "$env:USERPROFILE\Downloads\T-007-registrar-actividad.patch"
if ($LASTEXITCODE -eq 0) { git apply "$env:USERPROFILE\Downloads\T-007-registrar-actividad.patch" }
if ($LASTEXITCODE -eq 0) { pytest tests/actividades }   # el comando de test de la tarjeta; si no trae uno, esta línea no va
if ($LASTEXITCODE -eq 0) { git add -A; git commit -m "feat: registrar actividad" }
if ($LASTEXITCODE -eq 0) { git push }
if ($LASTEXITCODE -ne 0) { Write-Host "Algo falló: el bloque se detuvo ahí. Pega aquí lo que dice la terminal." }
```

**El freno.** PowerShell no se detiene solo cuando un comando externo falla (por ejemplo, un test que da error): seguiría con la línea siguiente y guardaría igual el código roto. Por eso cada paso corre solo si el anterior salió bien (`$LASTEXITCODE` vale 0), como una cadena de semáforos: si uno se pone en rojo, los siguientes no avanzan y la última línea te avisa.

| Línea | Para qué |
|---|---|
| `cd …` | Entra a la carpeta de tu repo. Confirma la ruta con `pwd`: OneDrive a veces mueve el Escritorio. |
| `git status --short` | Lista lo que está sin guardar. **Debe salir vacío**: así el `git add -A` solo mete lo del parche. |
| `git apply --check …` | Prueba si el parche encaja, sin tocar nada. Si va a fallar, falla aquí y tu repo queda intacto. |
| `git apply …` | Aplica el parche de verdad. |
| comando de test | Corre los tests de la tarea antes de guardar. Si fallan, no se guarda nada. |
| `git add -A; git commit -m …` | Marca todos los cambios y los guarda con un mensaje (viene en el reporte). |
| `git push` | Sube el commit a GitHub. |
| última línea | Si algo falló, te lo dice; si todo salió bien, no dice nada. |

Para otras terminales (CMD, Git Bash, macOS, Linux), mira la tabla de equivalentes en `00-LEEME-IA.md`; allí el freno se escribe uniendo los comandos con `&&`.

### Guardar el parche

- Si el chat te entrega un archivo descargable, queda en Descargas: úsalo tal cual.
- Si no: pega el bloque `diff` en el Bloc de notas → *Guardar como* → tipo «Todos los archivos» → nombre `T-007-tema.patch` → codificación UTF-8.
- Windows oculta las extensiones: comprueba que no quedó `T-007-tema.patch.txt` (Explorador → Vista → Mostrar → *Extensiones de nombre de archivo*).
- El archivo debe terminar con un salto de línea; un parche cortado al final da *corrupt patch*.

### Si algo falla (en este orden)

1. **`git status --short` no sale vacío:** hay cambios sin guardar. Haz commit o `git stash` antes. Si no sabes cuál conviene, pega la salida al LLM y pregúntale.
2. **`--check` dice *corrupt patch*:** repite el `--check` y el `git apply` agregando `--recount` (los números de los encabezados `@@` vienen mal).
3. **Falla por espacios o fines de línea** (típico al copiar en Windows): agrega también `--ignore-whitespace`.
4. **Dice *patch does not apply*:** el contexto no coincide. Pega el error al LLM y pídele **solo ese bloque** corregido (hay un texto para eso arriba).
5. **Último recurso:** `git apply --reject` aplica lo que encaje y deja archivos `*.rej` con lo que no. Revísalos, aplica a mano lo que falte y **bórralos antes del commit** (si no, el `git add -A` los incluiría). Si los parches fallan muy seguido, avísalo: hay un plan B de entrega (archivos completos, o bloques «buscar y reemplazar» sin números de línea).
6. **Un test falló:** el bloque se detiene antes del commit y el parche queda aplicado, sin guardar. Pega la salida al LLM (el texto «Un test falló», arriba): el parche corregido se aplica **encima** y se guarda todo junto. Por eso, en ese segundo intento, `git status --short` ya no sale vacío: muestra los archivos del primer intento, y es lo esperado.
7. **Quieres descartar un intento** (el parche quedó aplicado y no sirve): `git stash -u` lo guarda aparte y deja el repo limpio; si ya no lo quieres, `git stash drop`.

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
git apply --check "$env:USERPROFILE\Downloads\T-007-actividades-tests.patch"
if ($LASTEXITCODE -eq 0) { git apply "$env:USERPROFILE\Downloads\T-007-actividades-tests.patch" }
if ($LASTEXITCODE -eq 0) { pytest tests/actividades }   # aquí se ESPERA que falle: lee el mensaje
```

Lee lo que salió (los nombres son de Python; en otro lenguaje busca lo equivalente):

- **Rojo correcto:** el mensaje habla de lo que falta (`NotImplementedError`, o una comprobación que no se cumple: `AssertionError`).
- **Rojo equivocado:** el test ni siquiera llegó a ejecutarse (`ImportError`, `ModuleNotFoundError`, `SyntaxError`, `NameError`). Pega la salida al LLM (el texto «Un test falló») y pídele el parche corregido, que se aplica encima.

Si el rojo es el correcto, pega este segundo bloque (el commit) y sigue con el parche 2:

```powershell
git add -A
git commit -m "test: registrar actividad (rojo)"
if ($LASTEXITCODE -eq 0) { git push }
```

## Al cerrar cada rebanada: prueba de uso y chat de hito

Los tests pueden pasar y la app, aun así, no servir. Al terminar cada rebanada (el grupo de tareas que deja algo usable), haz estas dos cosas, en este orden. *Para qué:* es la inspección de obra de cada piso: antes de levantar el siguiente se comprueba que sirve y que no quedó nada torcido.

**Primero, la prueba de uso.** Corre la app y haz tú mismo un recorrido corto, como lo haría quien la va a usar. *Para qué:* es la única comprobación que no depende de lo que escribió el LLM.

1. Pide el recorrido a un LLM, con `docs/modelo.md` adjunto:

   > Con los flujos principales de este modelo, escríbeme una prueba de uso de 3 a 5 pasos para lo que ya funciona: qué hacer en cada paso y qué debería pasar.

2. Haz los pasos. Si alguno falla, anótalo: es una tarea nueva (con su test), no un parche suelto.

**Después, el chat de hito.** Un chat nuevo por rebanada, de preferencia con otro LLM. *Para qué:* unos ojos frescos revisan lo hecho, miran si el código se está enredando y dejan escritas las tarjetas de la ola siguiente, todo en un solo chat para gastar menos. Adjunta la salida de `git ls-files` (el árbol real), el índice de decisiones, los ADR relacionados con la rebanada, la salida de `git log --oneline`, `docs/plan/backlog.md` y `docs/plantillas/tarjeta.md`, y pega el texto «Chat de hito» (arriba, entre los prompts).

- Si el LLM propone un refactor (una tarjeta `REF-NN`), se ejecuta como cualquier tarea, con la regla extra de que los tests no cambian y siguen verdes, **antes** de escribir las tarjetas de la ola siguiente. *Para qué:* así las tarjetas se escriben sobre un árbol ya ordenado y no sobre uno que va a cambiar. Cuando termine, vuelve al mismo chat con el `git ls-files` nuevo y pídele el paso 3.
- Las tarjetas nuevas se reparten con `python tools/init_plan.py PLAN-ola2.md` (un archivo con solo `## Tarjetas de la ola 2`). *Para qué:* las verifica contra el backlog guardado y no pisa las tarjetas que ya existen.
- Escribir las tarjetas de la ola siguiente es rutina. **Cambiar el backlog** (orden, dependencias, tareas nuevas) es replanificar: se guarda como un archivo nuevo, `PLAN-v2.md`, con las tres secciones, la versión siguiente y su `Motivo del cambio:` (formato en `docs/plantillas/plan.md`), y se reparte con `python tools/init_plan.py PLAN-v2.md`. *Para qué:* reemplaza `backlog.md` y `cobertura.md` por los nuevos y deja como están las tarjetas que ya existen.

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
