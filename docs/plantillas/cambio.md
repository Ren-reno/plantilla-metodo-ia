<!--
  Plantilla de mini-diseño de cambio (camino «cambio»): una página para una funcionalidad nueva en una app que ya existe.
  Va en docs/cambios/NNNN-slug.md (el mismo NNNN del título: CAM-NNNN) y se conserva: el RF guarda el qué; el
  mini-diseño guarda el por qué.
  Lo que va entre «» se reemplaza. Borra este comentario en el documento real.

  - Una página. Si necesitas más (un módulo nuevo, entidades y relaciones nuevas, más de 3 tarjetas), no es un cambio:
    sube al camino completo (DISENO.md).
  - `RF que modifica o crea` mantiene vivo el mapa requisito → tarea. Si el RF todavía no existe, la primera tarjeta lo
    crea (con su línea `Aporta a:`) y lo lista en `Tocar:`.
  - Si cambia el modelo, la primera tarjeta actualiza docs/modelo.md (solo la sección que cambia) y, si existe, el `.puml`.
  - Ejemplos aprobados: solo si hay reglas con números, fechas o dinero (2 a 4, «entrada → resultado»). El LLM los
    propone y tú los apruebas. Si no aplican, borra la sección.
  - De aquí salen 1 a 3 tarjetas (máximo 4 criterios y un solo módulo propio cada una) que citan este archivo en `Leer:`.
    Sus IDs siguen la numeración del proyecto (T-015, T-016…).
  - Las tarjetas se borran al cerrar; la sección `Tarjetas` conserva qué tareas salieron de este cambio.
-->
# CAM-«NNNN» · «Título del cambio»
> «Fecha» · «app y versión sobre la que se cambia»

## Qué se cambia
«Una o dos frases: qué hará distinto la app.»

## Por qué
«El problema o la necesidad que lo motiva.»

## RF que modifica o crea
- «RF-004 · Título (modifica)»
- «RF-012 · Título (nuevo)»

## Fuera de alcance
- «Lo que NO se construye en este cambio, aunque parezca razonable.»

## Criterios de aceptación
- «Criterio comprobable 1»
- «Criterio comprobable 2»

## Ejemplos aprobados
- «entrada» → «resultado esperado»

## Tarjetas
- «T-015, T-016: se completa al escribir las tarjetas»
