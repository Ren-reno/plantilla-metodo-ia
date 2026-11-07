<!--
  Plantilla de tarjeta de tarea: una orden de trabajo pequeña y autocontenida. Va en docs/plan/tareas/T-NNN.md
  Lo que va entre «» se reemplaza. Borra este comentario en la tarjeta real (las tarjetas viajan en los bundles).
  Este archivo trae tres formatos: la tarjeta normal (abajo), la variante «tarjeta rápida» (un bug o un ajuste) y la
  variante «tarjeta de refactor» (REF-NN). Usa solo el que corresponda.

  - Tamaño: S = hasta 2 criterios y pocos archivos · M = 3 o 4 criterios en un solo módulo propio. Más que eso, se parte.
  - Criterios de aceptación: máximo 4. Cada uno indica su evidencia: test para lo automatizable; revisión visual o prueba de uso cuando corresponda. [verifica: CI] marca los que solo se comprueban en el CI de GitHub.
  - Depende de: solo tareas. Las decisiones (ADR) se declaran en Leer: y actúan de compuerta: si cita un ADR no aceptado, la tarea espera.
  - Leer: todo archivo debe existir ya, o producirlo una tarea previa; indícalo así: (lo produce T-003).
  - Tocar: el * es recursivo. Si la tarea crea un módulo, lista el módulo completo y los archivos compartidos de
    configuración con la parte exacta que toca, por ejemplo src/config/settings.py (solo INSTALLED_APPS).
    Las tareas que tocan un archivo compartido no corren en paralelo.
    Si la tarea cambia comportamiento, Tocar incluye también el RF o la sección de docs/modelo.md que el parche actualiza,
    con la parte exacta: docs/modelo.md (solo la sección Actividad).
  - UI: Leer cita docs/experiencia.md y las reglas de actores/roles aplicables. Entregar aparte las imágenes reales
    indicadas en el complemento: bundle.py no las incorpora. Los criterios describen qué se revisa y con qué referencia.
    Si cambian experiencia, permisos o diagramas, incluir sus documentos en Tocar. No esconder trabajo nuevo en una
    referencia general. Los cambios visuales usan T-NNN, no REF-NN. Si falta un componente compartido, delimitar una
    tarea y dependencia; no improvisar archivos fuera de Tocar ni esperar al hito si bloquea.
  - Fuera de alcance: lo que NO se construye en esta tarea, aunque parezca razonable. Corta el código que nadie pidió.
  - Ejemplos aprobados: para reglas con números, fechas o dinero, 2 a 4 ejemplos «entrada → resultado esperado» que la persona
    aprueba. Los tests los incluyen tal cual y nadie cambia sus valores esperados.
  - Modo: estricto (opcional; si falta, la tarea es normal). La tarea son dos parches: 1) solo los tests (y, si hace falta
    para poder importarlos, un esqueleto que lance «no implementado»); el usuario los corre, comprueba que fallan por
    falta de funcionalidad (no por un error de importación) y hace commit. 2) La implementación, con esos tests en
    Leer: y en No tocar:. Úsalo solo si hubo un primer fallo, si las reglas no caben en 2 a 4 ejemplos aprobados o si lo
    pide el usuario; no por «peso 5».
  - Contrato, Produce, Modo y Ejemplos aprobados son opcionales: borra esas líneas si no aplican.
  - Entrega de una versión (etapa 5): es una tarjeta T-NNN normal, no hay prefijo nuevo. Sus criterios son los
    de la etapa que apliquen, con su evidencia: instalación desde un entorno limpio en las plataformas
    declaradas, datos de la versión anterior que siguen leyéndose, un fallo que se ve y se puede diagnosticar.
    El empaquetado y la migración son trabajo, así que van en su propia tarjeta, no de propina en otra.
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
Criterios de aceptación:
  - «comportamiento observable; evidencia: test, revisión visual o prueba de uso concreta»
  - [verifica: CI] «criterio que solo se comprueba en el CI»
Ejemplos aprobados:
  - «entrada» → «resultado esperado»
Comando de test: ver docs/00-LEEME-IA.md (solo sobre «tests/modulo/*»)
Entrega: un parche (git diff) + reporte + comandos para aplicar

---

<!--
  Variante «tarjeta rápida» (camino rápido: un bug o un ajuste). Es la tarjeta normal reducida: sin Contrato, Produce ni
  No tocar, y solo con los criterios que hacen falta. Para lo automatizable, los tests se escriben primero.
  - Un bug automatizable parte con el test que lo reproduce: falla antes y pasa después. Para un defecto visual,
    el primer criterio define reproducción y evidencia de antes/después, más los tests pertinentes. Si hay un test automatizado y quieres comprobar su rojo inicial, agrega «Modo: estricto» (dos parches).
  - Sigue valiendo todo lo de arriba: máximo 4 criterios, un solo módulo propio y «Fuera de alcance». Si no cabe, el
    trabajo no es rápido: sube al camino «cambio» (mini-diseño en docs/plantillas/cambio.md).
  - Registrar la nueva T-NNN en el backlog y su cobertura; citar el RF y la tarea de origen si se conoce.
  - Si estaba mal el requisito, actualizarlo y los documentos afectados en Tocar. Si el código incumplía un RF
    correcto, conservar ese RF. Un reintento de una tarea abierta sigue en esa misma tarea.
-->
# T-«NNN» · «Título corto del bug o ajuste»
Estado: pendiente · Tamaño: S · Depende de: «T-xxx, o —» · Cubre: «RF-001»
Objetivo: «Bug o Ajuste: qué pasa hoy y qué debería pasar»
Leer (solo esto): docs/00-LEEME-IA.md · «archivo donde ocurre» · «RF afectado»
Tocar: «src/modulo/*» · «tests/modulo/*» · «docs/requisitos/RF-001-titulo.md (solo si cambia el comportamiento)»
Fuera de alcance: «lo que NO se arregla aquí»
Criterios de aceptación:
  - Reproduce el bug: «caso y resultado incorrecto; test que falla antes y pasa después, o evidencia visual reproducible»
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
  - Criterio único: los tests no cambian y siguen verdes. cerrar.py rechaza cambios en tests bajo tests/. La detección actual no cubre tests colocados junto al código.
-->
# REF-«NN» · «Título»
Estado: pendiente · Tamaño: S · Depende de: — · Cubre: — (ordena código; no agrega comportamiento)
Objetivo: «qué se ordena y por qué (lo que señaló el chat de hito o validar.py)»
Leer (solo esto): docs/00-LEEME-IA.md · «tests/modulo/* (solo para ver qué debe seguir pasando)»
Tocar: «src/modulo/*»
No tocar: tests/* · docs/*
Fuera de alcance: cambiar comportamiento · agregar funciones · escribir o cambiar tests · tocar otro módulo
Criterios de aceptación:
  - Los tests no cambian y siguen verdes.
Comando de test: ver docs/00-LEEME-IA.md («Tests, todos»)
Entrega: un parche (git diff) + reporte + comandos para aplicar
