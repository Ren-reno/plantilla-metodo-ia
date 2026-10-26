<!--
  Plantilla de tarjeta de tarea: una orden de trabajo pequeña y autocontenida. Va en docs/plan/tareas/T-NNN.md
  Lo que va entre «» se reemplaza. Borra este comentario en la tarjeta real (las tarjetas viajan en los bundles).
  Este archivo trae tres formatos: la tarjeta normal (abajo), la variante «tarjeta rápida» (un bug o un ajuste) y la
  variante «tarjeta de refactor» (REF-NN). Usa solo el que corresponda.

  - Tamaño: S = hasta 2 criterios y pocos archivos · M = 3 o 4 criterios en un solo módulo propio. Más que eso, se parte.
  - Criterios de aceptación: máximo 4. Cada uno será un test. [verifica: CI] marca los que solo se comprueban en el CI de GitHub.
  - Depende de: solo tareas. Las decisiones (ADR) se declaran en Leer: y actúan de compuerta: si cita un ADR no aceptado, la tarea espera.
  - Leer: todo archivo debe existir ya, o producirlo una tarea previa; indícalo así: (lo produce T-003).
  - Tocar: el * es recursivo. Si la tarea crea un módulo, lista el módulo completo y los archivos compartidos de
    configuración con la parte exacta que toca, por ejemplo src/config/settings.py (solo INSTALLED_APPS).
    Las tareas que tocan un archivo compartido no corren en paralelo.
    Si la tarea cambia comportamiento, Tocar incluye también el RF o la sección de docs/modelo.md que el parche actualiza,
    con la parte exacta: docs/modelo.md (solo la sección Actividad).
  - Fuera de alcance: lo que NO se construye en esta tarea, aunque parezca razonable. Corta el código que nadie pidió.
  - Ejemplos aprobados: para reglas con números, fechas o dinero, 2 a 4 ejemplos «entrada → resultado esperado» que la persona
    aprueba. Los tests los incluyen tal cual y nadie cambia sus valores esperados.
  - Modo: estricto (opcional; si falta, la tarea es normal). La tarea son dos parches: 1) solo los tests (y, si hace falta
    para poder importarlos, un esqueleto que lance «no implementado»); el usuario los corre, comprueba que fallan por
    falta de funcionalidad (no por un error de importación) y hace commit. 2) La implementación, con esos tests en
    Leer: y en No tocar:. Úsalo solo si hubo un primer fallo, si las reglas no caben en 2 a 4 ejemplos aprobados o si lo
    pide el usuario; no por «peso 5».
  - Contrato, Produce, Modo y Ejemplos aprobados son opcionales: borra esas líneas si no aplican.
-->
# T-«NNN» · «Título»
Estado: pendiente · Tamaño: «S o M» · Depende de: «T-xxx, o —» · Cubre: «C1 (peso), RF-001»
Modo: «estricto, o borra esta línea»
Objetivo: «una o dos frases»
Contrato: «qué función de otro módulo llamas; si la pieza real aún no existe, qué stub usar»
Leer (solo esto): docs/00-LEEME-IA.md · «docs/modelo.md#entidad» · «docs/decisiones/NNNN-slug.md»
Produce: «contratos u otros archivos que esta tarea deja a otras»
Tocar: «src/modulo/*» · «tests/modulo/*»
No tocar: «lo que no debe cambiar»
Fuera de alcance: «lo que NO se construye en esta tarea, aunque parezca razonable»
Criterios de aceptación (→ tests):
  - «criterio 1»
  - [verifica: CI] «criterio que solo se comprueba en el CI»
Ejemplos aprobados:
  - «entrada» → «resultado esperado»
Comando de test: ver docs/00-LEEME-IA.md (solo sobre «tests/modulo/*»)
Entrega: un parche (git diff) + reporte + comandos para aplicar

---

<!--
  Variante «tarjeta rápida» (camino rápido: un bug o un ajuste). Es la tarjeta normal reducida: sin Contrato, Produce ni
  No tocar, y solo con los criterios que hacen falta. Los tests se escriben primero, como siempre.
  - Un bug parte con el test que lo reproduce: es el primer criterio. Debe fallar con el código de hoy y pasar cuando esté
    arreglado. Si quieres comprobar de verdad que falla hoy, agrega la línea «Modo: estricto» (dos parches).
  - Sigue valiendo todo lo de arriba: máximo 4 criterios, un solo módulo propio y «Fuera de alcance». Si no cabe, el
    trabajo no es rápido: sube al camino «cambio» (mini-diseño en docs/plantillas/cambio.md).
  - Si el arreglo cambia el comportamiento descrito en un RF, el parche actualiza ese RF: ponlo en Tocar.
-->
# T-«NNN» · «Título corto del bug o ajuste»
Estado: pendiente · Tamaño: S · Depende de: «T-xxx, o —» · Cubre: «RF-001»
Objetivo: «Bug o Ajuste: qué pasa hoy y qué debería pasar»
Leer (solo esto): docs/00-LEEME-IA.md · «archivo donde ocurre» · «RF afectado»
Tocar: «src/modulo/*» · «tests/modulo/*» · «docs/requisitos/RF-001-titulo.md (solo si cambia el comportamiento)»
Fuera de alcance: «lo que NO se arregla aquí»
Criterios de aceptación (→ tests):
  - Reproduce el bug: «el caso que falla hoy» (el test falla antes del arreglo y pasa después)
  - «el comportamiento correcto, si el criterio anterior no lo cubre»
Comando de test: ver docs/00-LEEME-IA.md (solo sobre «tests/modulo/*»)
Entrega: un parche (git diff) + reporte + comandos para aplicar

---

<!--
  Variante «tarjeta de refactor» (REF-NN): ordenar el código sin cambiar lo que hace. Nace en el chat de hito, cuando la
  pregunta de estructura encuentra algo (un archivo enorme, código repetido o un módulo que debió separarse). No va en el
  backlog ni en la matriz, y se ejecuta ANTES de escribir las tarjetas de la ola siguiente.
  - Un solo módulo. Tocar trae solo código de src/ (nunca tests ni documentos); los tests van en No tocar y en Leer, para
    que el LLM vea qué debe seguir pasando.
  - Criterio único: los tests no cambian y siguen verdes. cerrar.py tratará como error que el parche toque un test
    (pendiente).
-->
# REF-«NN» · «Título»
Estado: pendiente · Tamaño: S · Depende de: — · Cubre: — (ordena código; no agrega comportamiento)
Objetivo: «qué se ordena y por qué (lo que señaló el chat de hito o validar.py)»
Leer (solo esto): docs/00-LEEME-IA.md · «tests/modulo/* (solo para ver qué debe seguir pasando)»
Tocar: «src/modulo/*»
No tocar: tests/* · docs/*
Fuera de alcance: cambiar comportamiento · agregar funciones · escribir o cambiar tests · tocar otro módulo
Criterios de aceptación (→ tests):
  - Los tests no cambian y siguen verdes.
Comando de test: ver docs/00-LEEME-IA.md («Tests, todos»)
Entrega: un parche (git diff) + reporte + comandos para aplicar
