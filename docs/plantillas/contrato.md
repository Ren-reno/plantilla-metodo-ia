<!--
  Plantilla de contrato: cómo se llaman dos módulos entre sí. Va en docs/contratos/NNNN-slug.md
  Lo que va entre «» se reemplaza. Borra estos comentarios al llenarlo.

  - Un contrato se acuerda ANTES de implementar las dos piezas, y puede tener un stub mientras
    la real no exista. Las tarjetas lo citan en «Contrato:» y lo producen con «Produce:».
  - Ninguna herramienta parsea este archivo: no hay títulos exactos que respetar. Lo que sí hace
    cerrar.py es levantar una bandera cuando un parche toca docs/contratos/, para que una tarea no
    cambie en silencio el acuerdo del que dependen otras.
  - Proporcional: un contrato entre dos módulos de la misma app es una página. Si necesita más,
    probablemente el límite entre los módulos está mal puesto.
  - Un contrato claro también puede estar equivocado. Los «Ejemplos acordados» son lo que impide
    que ambos lados lo interpreten distinto, y van tal cual a los tests de las dos piezas.
-->
# CON-«NNNN» · «Título corto del contrato»

Estado: «propuesto / acordado / reemplazado» · Versión: «1» · Fecha: «fecha»
Ofrece: «módulo responsable, por ejemplo src/dominio»
Consume: «módulos o tareas que lo llaman; al cambiarlo, estos son los que hay que revisar»
Decisiones relacionadas: «ADR-NNNN, o —»

## Para qué existe

«Qué necesita una pieza de la otra, en una o dos frases. No repitas el requisito: enlázalo.»

## Operaciones

### «nombre_de_la_operación»

- Entrada: «campos, tipos, unidades y qué es obligatorio»
- Salida: «qué devuelve, con su forma exacta»
- Errores: «qué puede fallar, cómo se informa y qué debe hacer quien llama»
- No hace: «lo que quien llama no debe esperar de aquí»

## Ejemplos acordados

«2 a 4 casos entrada → resultado esperado, sobre todo si hay números, fechas, dinero o
identificadores. Van tal cual a los tests de las dos piezas; nadie cambia su valor esperado.»

- «entrada» → «resultado esperado»

## Stub mientras no exista la pieza real

«Qué devuelve el stub y en qué se diferencia del real, para que nadie confunda una respuesta
simulada con una implementada. Si no hace falta stub, escribe: no aplica.»

## Compatibilidad

- Versión de los datos que cruzan: «si el contrato lleva una versión en el propio mensaje, dónde va»
- Al cambiar este contrato: «qué pasa con los datos y las llamadas de la versión anterior; qué
  migración hace falta, o por qué no hace falta ninguna»
- Qué se puede añadir sin romper nada, y qué no: «campos opcionales nuevos, sí; renombrar, no»
