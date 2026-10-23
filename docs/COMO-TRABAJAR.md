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
| 3. Plan | Pides el plan dividido en tarjetas | `docs/plan/tareas/` y la matriz de cobertura |
| 4. Código | Repites el ciclo de abajo, una tarea a la vez | Un parche por tarea y `docs/plan/ESTADO.md` |

Las **decisiones** (`docs/decisiones/`) y los **tests** atraviesan las cuatro etapas.

## Qué funciona hoy y qué falta

Esta plantilla trae la estructura de carpetas, las guías, los formatos en blanco (`docs/plantillas/`) y un CI mínimo. **Las herramientas de `tools/` todavía no existen**: se construyen de a una. Los pasos que dependen de ellas llevan la marca *(pendiente)*; mientras no existan, esos pasos hay que hacerlos a mano. Cuando una herramienta exista, se quita su marca.

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

3. **Copia `DISENO.md` a la raíz del repo y corre `python tools/init_diseno.py DISENO.md`** *(pendiente)*. *Para qué:* reparte el diseño en `docs/` (requisitos, decisiones, modelo…) sin que cortes y pegues, y te avisa con el número de línea si el formato tiene errores.
4. **Revisa con `git status` y `git diff`; luego commit y push.** *Para qué:* ver qué se repartió antes de guardarlo.
5. **Pide el plan, repártelo con `python tools/init_plan.py` y valídalo con `python tools/validar.py`** *(pendiente)*. *Para qué:* el plan queda en tarjetas, y el validador comprueba que no falte ni sobre nada.

## Qué pedirle a un LLM en cada etapa

Textos para copiar y pegar. Si algo te cuesta entender, agrega: «explícame con una analogía».

**Diseño.** Adjunta tu enunciado o tus notas y `docs/plantillas/diseno.md` (o tu `DISENO.md` si ya existe):

> Vamos a diseñar una app. Ordena lo que te cuento en el formato de `diseno.md`. Pregunta solo lo que falte; todo lo que yo no haya dicho márcalo como supuesto (S-xx) o pregunta (P-xx), sin inventar cifras. Cuando terminemos, devuélveme el `DISENO.md` completo y actualizado.

**Diagramas.** Adjunta `DISENO.md`:

> A partir de este `DISENO.md`, genera los diagramas en PlantUML: ER de las entidades, secuencia de los flujos principales, despliegue lógico y casos de uso. Un archivo `.puml` por diagrama.

Con Claude, la skill `puml-diagramas` ya conoce el formato.

**Plan.** Adjunta `DISENO.md`, los diagramas y `docs/plantillas/tarjeta.md`:

> Con esto, arma el plan:
>
> - Una tarjeta por tarea, con el formato de `tarjeta.md`: máximo 4 criterios y un solo módulo propio por tarjeta.
> - Antes de T-001, registra como ADR las decisiones que arrastra el stack (base de datos local, versión mínima del lenguaje).
> - T-001 es el esqueleto andante: la app arranca, un test pasa y el CI corre. También completa las secciones *Convenciones* y *Comandos* de `docs/00-LEEME-IA.md` y adapta `.github/workflows/ci.yml` al stack.
> - Rebanadas verticales ordenadas por peso, riesgo y dependencias; siempre algo ejecutable.
> - Matriz de cobertura: cada criterio → RF → tareas, sin RF huérfanos ni tareas sin criterio.
> - Hito mínimo = el flujo ejecutable más corto de punta a punta; después, el entregable completo.
> - Entre módulos, contratos con stub. Para lo incierto, exploraciones con tiempo acotado.
>
> Si falta decidir el stack, pregúntamelo antes.

**Tarea.** Pega el bundle debajo de este texto:

> Implementa la tarea de este bundle siguiendo las reglas de `00-LEEME-IA.md`. Responde solo con los tres bloques: parche, reporte y comandos.

**Un parche falló.** En el mismo chat:

> Al aplicar el parche me salió este error: (pega aquí el error). Devuélveme solo la parte corregida (el archivo y el bloque `@@` que falló), no el parche entero.

**Revisión de coherencia** (en cada hito). Adjunta el índice de decisiones, los ADR relacionados con el hito y la salida de `git log --oneline`:

> Revisa la coherencia del proyecto. Dime si hay decisiones que se contradicen, decisiones tomadas sin registrar o tareas que se saltaron un contrato.

## El ciclo de cada tarea (etapa 4)

1. **Preparar:** `python tools/bundle.py T-007` *(pendiente)*. *Para qué:* arma un solo archivo con lo justo que el LLM necesita; así gasta pocos tokens y no se confunde. Si se niega a armarlo, es porque la tarea cita una decisión que aún no aceptaste: acéptala primero.
2. **Implementar:** pega el bundle en el LLM que prefieras. Te devuelve **tres bloques**: un parche, un reporte y los comandos.
3. **Aplicar:** guarda el parche en Descargas y pega el bloque de comandos (explicado abajo). *Para qué:* el bloque prueba el parche, lo aplica, corre los tests y recién entonces guarda y sube.
4. **Verificar:** los tests corren en tu computador antes del commit. El CI de GitHub es la red de seguridad, no la primera prueba.
5. **Cerrar:** `python tools/cerrar.py T-007 reporte.md` *(pendiente)*. *Para qué:* registra el reporte, actualiza `ESTADO.md`, convierte las decisiones nuevas en propuestas y te avisa de cosas raras (dependencias nuevas, tests antiguos modificados, cambios en contratos). La tarea queda «en revisión» hasta que pase en tu computador y en el CI.
6. **Decidir:** aceptas o rechazas las decisiones que el LLM propuso, haces commit y sigues.

### El bloque de comandos, línea por línea

Ejemplo en PowerShell. El LLM te lo entrega ya con tus rutas y el nombre real del parche.

```powershell
cd "$env:USERPROFILE\Desktop\mi-app"
git status --short   # debe salir vacío
git apply --check "$env:USERPROFILE\Downloads\T-007-registrar-actividad.patch"
git apply "$env:USERPROFILE\Downloads\T-007-registrar-actividad.patch"
# aquí va el comando de test de la tarjeta, si lo trae
git add -A
git commit -m "feat: registrar actividad"
git push
```

| Línea | Para qué |
|---|---|
| `cd …` | Entra a la carpeta de tu repo. Confirma la ruta con `pwd`: OneDrive a veces mueve el Escritorio. |
| `git status --short` | Lista lo que está sin guardar. **Debe salir vacío**: así el `git add -A` del final solo mete lo del parche. |
| `git apply --check …` | Prueba si el parche encaja, sin tocar nada. Si va a fallar, falla aquí y tu repo queda intacto. |
| `git apply …` | Aplica el parche de verdad. |
| comando de test | Corre los tests de la tarea antes de guardar. |
| `git add -A` | Marca todos los cambios para el commit. |
| `git commit -m …` | Guarda los cambios con un mensaje (viene en el reporte). |
| `git push` | Sube el commit a GitHub. |

Para otras terminales (CMD, Git Bash, macOS, Linux), mira la tabla de equivalentes en `00-LEEME-IA.md`.

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

## Hábitos que ahorran tokens y esperas

- **Un chat por tarea.** Cada mensaje hace que el LLM relea todo el chat: cuanto más largo, más cuesta. Si un chat se alarga, ciérralo y retoma con un bundle o un archivo nuevo.
- **Máximo dos intentos por fallo.** Al segundo, el LLM debe parar y reportar qué probó; seguir insistiendo gasta sesión sin avanzar.
- **Tareas chicas:** una sesión, hasta 4 criterios, un solo módulo propio.
- **Decide pronto lo que afecta a otras tareas.** Un LLM que decide en silencio algo que toca otras tareas es la forma más fácil de que el proyecto se contradiga.

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
