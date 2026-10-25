<!--
  Plantilla de tarjeta de tarea: una orden de trabajo pequeña y autocontenida. Va en docs/plan/tareas/T-NNN.md
  Lo que va entre «» se reemplaza. Borra este comentario en la tarjeta real (las tarjetas viajan en los bundles).

  - Tamaño: S = hasta 2 criterios y pocos archivos · M = 3 o 4 criterios en un solo módulo propio. Más que eso, se parte.
  - Criterios de aceptación: máximo 4. Cada uno será un test. [verifica: CI] marca los que solo se comprueban en el CI de GitHub.
  - Depende de: solo tareas. Las decisiones (ADR) se declaran en Leer: y actúan de compuerta: si cita un ADR no aceptado, la tarea espera.
  - Leer: todo archivo debe existir ya, o producirlo una tarea previa; indícalo así: (lo produce T-003).
  - Tocar: el * es recursivo. Si la tarea crea un módulo, lista el módulo completo y los archivos compartidos de
    configuración con la parte exacta que toca, por ejemplo src/config/settings.py (solo INSTALLED_APPS).
    Las tareas que tocan un archivo compartido no corren en paralelo.
  - Fuera de alcance: lo que NO se construye en esta tarea, aunque parezca razonable. Corta el código que nadie pidió.
  - Ejemplos aprobados: para reglas con números, fechas o dinero, 2 a 4 ejemplos «entrada → resultado esperado» que la persona
    aprueba. Los tests los incluyen tal cual y nadie cambia sus valores esperados.
  - Contrato, Produce y Ejemplos aprobados son opcionales: borra esas líneas si no aplican.
-->
# T-«NNN» · «Título»
Estado: pendiente · Tamaño: «S o M» · Depende de: «T-xxx, o —» · Cubre: «C1 (peso), RF-001»
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
