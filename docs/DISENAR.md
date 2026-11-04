# Diseñar antes de planificar

Esta guía define la fase de diseño del camino completo. Para un cambio o ajuste, revisa solo los pasos afectados. El objetivo es acordar un alcance y una experiencia suficientemente comprobados para planificar el siguiente incremento.

## Conversar e iterar

Empieza contando quién tiene el problema, cómo lo resuelve hoy y un caso concreto. El LLM pregunta primero lo que puede cambiar el enfoque: usuarios, permisos, datos, plataforma, restricciones y resultado esperado. Usa tandas de hasta tres preguntas, ampliables hasta cinco si están relacionadas; explica para qué pregunta y recomienda una opción cuando tenga información suficiente.

Separa hechos, supuestos y propuestas. No inventes cifras, actores ni funcionalidades. Cada iteración debe resolver una duda concreta y terminar con documentos actualizados, decisiones aceptadas y preguntas pendientes. Si varias vueltas no aportan información, prueba un ejemplo o un prototipo. El límite de cuatro criterios pertenece a las tarjetas de implementación; no limita el diseño.

## Recorrido de diseño

| Paso | Trabajo | Condición para avanzar |
|---|---|---|
| 1. Problema | Identificar usuarios, situación actual, dificultad y resultado esperado. | La persona reconoce el problema y aporta un ejemplo concreto. |
| 2. Alcance | Delimitar dentro/fuera y elegir el primer recorrido útil, con comienzo y resultado observable. | Se entiende qué se entrega y qué se pospone. |
| 3. Comportamiento | Definir actores, roles, requisitos, acciones, navegación y errores. | Las acciones importantes tienen resultado y recuperación definidos. |
| 4. Apariencia, si hay UI | Describir pantallas y elegir una dirección visual con contenido realista. | Hay una referencia identificada y reglas comunes para otras pantallas. |
| 5. Prueba del recorrido | Usar un prototipo con datos simulados cuando haya interacción importante; revisar un caso normal y un error relevante. | Se comprende el recorrido; se registran observaciones, límites y correcciones. |
| 6. Viabilidad | Contrastar experiencia, datos, contratos, tecnología y operación mínima; preparar los diagramas necesarios. | Las dudas que pueden invalidar la primera ola están resueltas o han reducido explícitamente su alcance. |
| 7. Cierre de versión | Revisar coherencia, evidencia y pendientes; identificar el alcance que se puede planificar. | La persona confirma la versión y el alcance que servirán de base al plan. |

Los pasos permiten volver atrás. Investiga una restricción técnica crítica desde el inicio. Una app sin interfaz gráfica usa contratos y ejemplos de solicitudes, respuestas o comandos. Para una pantalla informativa sencilla puede bastar una maqueta revisada; registra el motivo. Una interacción importante aún no probada queda como riesgo o exploración pendiente, nunca como verificada.

Las decisiones funcionales y visuales evolucionan juntas. El prototipo sirve para aprender: indica qué está simulado. Su código se revisa y prueba antes de reutilizarlo en producción.

## Actores y roles

Completa las tablas de [la plantilla de diseño](plantillas/diseno.md). Un actor es una persona en una función o un sistema externo que interactúa con la app. Un rol agrupa responsabilidades y, cuando corresponde, permisos. Una persona puede tener varios roles; no toda app necesita cuentas.

Usa IDs estables `ACT-001` y `ROL-001`, nombres consistentes y condiciones explícitas: acción, recurso, alcance de datos y resultado permitido. «Administrador» no significa automáticamente acceso a todo. Las restricciones se comprueban donde se autorizan las operaciones, además de su representación en pantalla.

Tras repartir el diseño, el catálogo vigente está en `docs/requisitos/contexto.md`, sección Actores. Las fichas y diagramas lo citan; no mantienen copias independientes. Los IDs ACT/ROL son referencias documentales: las herramientas actuales no comprueban sus relaciones y no se añaden a `Cubre:`. La cobertura sigue usando los RF y reglas admitidos. Un actor no implica automáticamente una tabla de base de datos.

## Pantallas, imágenes y prototipo

Usa [experiencia.md](plantillas/experiencia.md) para el mapa de navegación, las fichas de pantalla, las reglas comunes y las referencias. Describe vacío, carga, contenido, validación, error, éxito y permisos según apliquen. No necesitas una imagen por estado: representa visualmente aquellos cuya composición requiere discusión.

Las imágenes son opcionales. Si sirven para explorar la apariencia:

1. Prepara la ficha de una pantalla representativa y un prompt autocontenido.
2. Genera la imagen en el modelo que elijas y adjunta el resultado al chat de diseño.
3. Compara contenido, jerarquía y composición con la ficha; decide qué conservar y qué corregir.
4. Guarda la referencia elegida con versión y alcance de aprobación: inspiración, estructura o aspecto concreto.
5. Para formularios o navegación importante, prueba un prototipo del recorrido con datos simulados. Puede ser HTML local o una implementación mínima en el stack elegido si la duda depende de él.

Empieza directamente con el prototipo si ya tienes clara la apariencia. Una pantalla adaptada a móvil requiere decidir cómo se reorganiza el contenido; reducir una captura no comprueba esa adaptación.

### Pedido al LLM diseñador

> A partir de la ficha vigente de esta pantalla, prepara un prompt autocontenido para generar su imagen en otro LLM. Incluye objetivo, contenido y etiquetas reales, estado, jerarquía, composición, tamaño de referencia y reglas comunes. Distingue decisiones fijas y aspecto que exploramos. Si falta una decisión funcional que cambia la pantalla, señálala. Entrega también qué debo mirar al recibir la imagen y qué referencias debo adjuntar.

### Prompt para generar la imagen

El diseñador completa los campos antes de entregar el prompt:

```text
Genera una maqueta de la pantalla [nombre y versión] de [producto].
Usuario y objetivo: [objetivo]. Estado representado: [estado].
Idioma y tamaño de referencia: [idioma, ancho y alto orientativos].
Contenido obligatorio: [etiquetas, datos realistas y mensajes].
Acción principal y secundarias: [etiquetas y prioridad].
Composición: [distribución y navegación compartida].
Dirección visual: [tipografía, colores, densidad y componentes].
Decisiones fijas: [qué conservar]. Duda de esta versión: [qué explorar].
Referencias adjuntas: [archivos y qué tomar de cada uno].
Entrega una sola vista frontal, legible y sin marco de dispositivo.
Conserva el contenido indicado; no añadas funciones decorativas.
```

Los textos, medidas y contraste se comprueban en el resultado y después en el prototipo. Una imagen generada no certifica esos valores ni el funcionamiento.

### Pedido para corregir la imagen

> Compara la imagen adjunta con la ficha vigente. Indica contenido faltante o inventado, jerarquía, coherencia y decisiones pendientes. Distingue lo visible de lo que no puedes comprobar. Incorpora mis comentarios a un prompt de corrección específico, conservando lo aceptado. No registres aprobación por el mero hecho de proponerla.

### Pedido para probar la interacción

> Construye un prototipo del recorrido indicado, con las fichas y referencias adjuntas. Incluye solo las pantallas y acciones acordadas, datos simulados, el caso normal y un error con recuperación. Conserva navegación y reglas visuales, incluyendo la adaptación prevista. Explica cómo abrirlo, qué funciona y qué está simulado. Señala diferencias respecto de las imágenes para revisarlas.

La prueba humana consiste en encontrar la acción, completar el recorrido y recuperarse del error. Anota dudas y pasos innecesarios. Si el prototipo corrige la imagen, actualiza ficha y referencia; sus capturas pueden sustituir a la imagen original. Mantén una única versión vigente.

## Elegir diagramas

La fuente editable es PlantUML (`.puml`). Usa [inventario-diagramas.md](plantillas/inventario-diagramas.md) antes de generarlos.

| Tipo | Cuándo aporta valor | Fuente |
|---|---|---|
| Casos de uso | Diseño completo: objetivos de actores y límites de la app. En cambios, revisar la parte afectada. | Actores y RF |
| Entidades y relaciones | Datos estructurados cuyas relaciones importan. | Modelo y reglas |
| Secuencia | Recorridos principales del incremento, integraciones o fallos que necesitan aclararse. | Flujos y contratos |
| Despliegue lógico | Distribución de procesos, servicios o ubicaciones relevante para entender la app. | Tecnología y operación |
| Navegación | Varias pantallas o transiciones relevantes. | Fichas y roles |
| Estados | Ciclo de vida significativo con transiciones permitidas o prohibidas. | Modelo y reglas |
| Componentes | Responsabilidades y dependencias internas que necesitan aclararse. | Arquitectura |

No necesitas una secuencia por operación trivial. Documenta el motivo de omitir un tipo condicional. Un proceso local sencillo puede describir su despliegue en texto. En cada diagrama conserva las referencias y significados de actores, requisitos y flujos; no inventes permisos al dibujar.

Registra si está pendiente, generado, renderizado o revisado. Renderizar comprueba que se puede producir la imagen; revisar comprueba además su coherencia con las fuentes. `validar.py` no verifica PlantUML ni esta coherencia. Actualiza un diagrama cuando un cambio altere lo que representa.

## Documentos y entrega al repo

Durante el diseño conserva un paquete pequeño: `DISENO.md`, `EXPERIENCIA.md` si aplica, `visual/` con referencias y prototipo, y `diagramas/` con inventario y fuentes. Guarda al terminar cada chat la versión, decisiones aceptadas, pendientes y próxima duda.

Al incorporar el diseño al repo:

1. Ejecuta `init_diseno.py` como indica la guía de trabajo. Conserva los títulos que reconoce; no agregues nuevos títulos `##` para pantallas u operación.
2. Copia manualmente `EXPERIENCIA.md` a `docs/experiencia.md` y `visual/` a `docs/visual/`, si aplican. Usa en el complemento enlaces relativos como `visual/pantalla-v1.png`, que conservan su relación al copiar ambos.
3. Copia el inventario y fuentes de `diagramas/` a `docs/diagramas/`. Su índice vigente será `docs/diagramas/README.md`.
4. Revisa rutas y referencias y guarda los archivos junto al diseño repartido. Los scripts no copian ni validan estos complementos automáticamente. Después del traslado, edita la copia vigente del repo.

En proyectos pequeños, `docs/experiencia.md` agrupa pantallas y estilo; se divide solo si el tamaño lo justifica. Para backend sin UI, indica «No aplica» y conserva los contratos y ejemplos necesarios.

El bundle incluye texto de `Leer:` y `Tocar:`; omite binarios y no garantiza que un modelo vea imágenes citadas en un Markdown. Entrega los archivos visuales reales como adjuntos o mediante una herramienta que pueda abrirlos, comprueba su recepción y registra lo que falta. No incrustes grandes bloques de datos binarios en el bundle.

## Condiciones de salida

Antes del plan comprueba problema y caso real, alcance, actores y roles aplicables, reglas con ejemplos, experiencia revisada, diagramas necesarios, viabilidad y operación mínima. Cada resultado importante debe tener evidencia de aceptación prevista: tests, revisión visual o prueba humana. En este momento se planifican esas comprobaciones; no se afirma haber ejecutado tests de una app que aún no existe.

Registra en «Alcance (dentro / fuera)» del diseño:

```text
Versión revisada: [diseño y complementos].
Alcance listo para planificar: [recorridos].
Evidencia revisada: [prototipo, imágenes, ejemplos o exploraciones].
Pendientes: [duda, impacto, cuándo resolverla y si bloquea].
Dictamen propuesto: LISTO / LISTO PARA ALCANCE ACOTADO / FALTA RESOLVER.
Decisión del usuario: [confirmación de versión y alcance, o pendiente].
```

Un alcance acotado puede avanzar solo si es independiente de las dudas restantes. No se rebaja un bloqueo anotándolo como pendiente. Se acepta una versión para el siguiente trabajo, con posibilidad de revisar decisiones ante nueva evidencia.

## Del diseño a las tarjetas

Planifica recorridos completos y detalla solo la siguiente ola. Una rebanada de UI incluye su integración con datos y lógica; pueden ser tarjetas técnicas distintas. El contrato entre módulos se acuerda antes de implementarlos y puede tener un stub.

El layout y los componentes comunes tienen un módulo responsable. Construye lo necesario para el primer recorrido en T-001 si cabe, o en una tarjeta fundacional previa a las pantallas. Un cambio compartido requiere alcance y consumidores identificados. Si bloquea, se replanifica entonces; no se espera obligatoriamente al hito ni se salta la dependencia con `--forzar`.

Cada criterio de una tarjeta indica evidencia; los automatizables mantienen tests primero. Las referencias comunes no sirven para esconder veinte comportamientos dentro de un único criterio. Si la tarea crece, divídela. Los cambios visuales intencionales y las correcciones usan tarjetas `T-NNN`, no la variante REF que prohíbe cambiar tests y documentos.

La revisión de UI se hace durante la tarea y al cerrar el recorrido. CI verde, uso de tokens o comparación de capturas no demuestran por sí solos una experiencia adecuada. Antes de `cerrar.py --hecha`, la persona confirma también las comprobaciones visuales o manuales exigidas. El script no comprueba esa aprobación ni consulta el CI remoto.
