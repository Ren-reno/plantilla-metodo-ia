<!--
  Plantilla de plan por olas: un solo archivo, PLAN.md, que un LLM llena y que tools/init_plan.py reparte (pendiente).
  Los títulos `## Backlog`, `## Matriz de cobertura` y `## Tarjetas de la ola N` son exactos: las herramientas los buscan.
  Lo que va entre «» se reemplaza. Borra este comentario en el plan real.

  - Ola = rebanada. El backlog trae TODAS las tareas, una línea cada una; solo la ola actual trae tarjetas completas,
    escritas con el código real a la vista. Las demás tareas viven solo como línea hasta que les llega el turno.
  - Rebanadas: ordenadas por peso, riesgo y dependencias; cada una deja algo ejecutable. El hito mínimo (el flujo
    ejecutable más corto de punta a punta) lo dice el título de la rebanada que lo completa.
  - Línea del backlog: `- T-001 · Título · Depende de: T-00x, … (o —) · Cubre: C2 (30), RF-004`. El separador es ` · `:
    el título no puede contenerlo. `Cubre:` usa la misma forma que la tarjeta: criterios y requisitos.
  - Matriz: una fila por cada par criterio–RF, sobre TODO el backlog desde el primer día. Sin RF huérfanos ni tareas
    sin criterio.
  - Tarjetas: formato de docs/plantillas/tarjeta.md, bajo `### T-NNN · Título`. Repiten `Depende de:` y `Cubre:` de su
    línea del backlog (validar.py los compara). Máximo 4 criterios y un solo módulo propio por tarjeta.
  - Las tarjetas REF-NN (refactor) no van en el backlog ni en la matriz: nacen en el chat de hito.
  - Primer archivo (ola 1): lleva las tres secciones. Archivos siguientes (PLAN-ola2.md, PLAN-ola3.md…): solo
    `## Tarjetas de la ola N`, porque escribir las tarjetas de la ola siguiente es rutina.
  - Cambiar el backlog (orden, dependencias, tareas nuevas) es replanificar: archivo nuevo con las tres secciones,
    versión +1 y la línea `Motivo del cambio:`.
-->
# PLAN — «nombre de la app»
> Versión «1» · «fecha» · fuente: «DISENO.md, versión»
> Motivo del cambio: «solo desde la versión 2: qué cambió en el backlog y por qué»

## Backlog
### Rebanada 1 · «flujo ejecutable que queda funcionando»
- T-001 · Esqueleto andante · Depende de: — · Cubre: «C1 (peso), RNF-001»
- T-002 · «Título» · Depende de: T-001 · Cubre: «C2 (peso), RF-004»
### Rebanada 2 · «siguiente flujo ejecutable»
- T-003 · «Título» · Depende de: T-002 · Cubre: «RF-005»

## Matriz de cobertura
| Criterio | RF | Tareas |
|---|---|---|
| «C1» | «RF-001» | «T-001, T-002» |
| «C2» | «RF-004» | «T-002» |

## Tarjetas de la ola 1
### T-001 · Esqueleto andante
«La tarjeta completa, con el formato de docs/plantillas/tarjeta.md y sin su título (el título es la línea de arriba).»

### T-002 · «Título»
«Lo mismo: una tarjeta por cada tarea de la rebanada 1.»
