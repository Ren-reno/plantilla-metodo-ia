<!--
  Complemento manual: guardar como EXPERIENCIA.md durante diseño; después copiar a docs/experiencia.md.
  No se pasa a init_diseno.py. Quitar los comentarios y completar los campos.
  Backend sin UI: indicar No aplica con motivo; no inventar pantallas.
  El catálogo de actores/roles vive en DISENO.md y luego en docs/requisitos/contexto.md.
-->
# Experiencia — «app»

> Versión «1» · «fecha» · Estado: «propuesta / aprobada para alcance indicado»
> Diseño relacionado: «versión» · Alcance: «recorridos»

## Recorridos y navegación

«Entrada → acciones → resultado; destinos, vuelta, cancelación y recuperación cuando apliquen.»

| Recorrido | Actores y roles | RF relacionados | Pantallas | Resultado esperado |
|---|---|---|---|---|
| «nombre» | «ACT-001 / ROL-001 o No aplica» | «RF-001» | «nombres» | «resultado» |

## Reglas visuales comunes

- Jerarquía, densidad y vocabulario: «…»
- Tipografía, colores, espaciado y componentes compartidos: «…»
- Adaptación a tamaños de uso: «qué se reorganiza y por qué»
- Teclado, foco, etiquetas, mensajes y ampliación de texto: «comportamiento esperado»
- Layout y componentes comunes: «responsabilidad del módulo; decisión pendiente si aún no se eligió stack»

## Pantallas

### «Nombre de pantalla»

- Objetivo y RF: «…»
- Acceso y acciones según actor/rol: «citar reglas vigentes; no duplicar permisos»
- Entrada: «desde dónde llega y precondiciones»
- Contenido realista: «datos, etiquetas y ejemplos»
- Acción principal: «etiqueta → resultado»
- Acciones secundarias y navegación: «acción → destino o resultado»
- Jerarquía: «qué debe ver primero»
- Adaptación: «diferencias según tamaño de uso»
- Teclado y mensajes: «orden, foco, identificación y explicación de errores»
- Referencia visual y versión: «ruta o pendiente»
- Preguntas: «P-xx y qué bloquea»
- Evidencia de aceptación prevista: «tests, revisión visual o prueba de uso»

| Estado aplicable | Qué se muestra | Qué puede hacer la persona | Resultado |
|---|---|---|---|
| «vacío / carga / contenido / error / éxito / permisos…» | «…» | «…» | «…» |

«Marcar los estados no aplicables con motivo; repetir la ficha para otras pantallas.»

## Referencias y prototipo

Las rutas de esta tabla son relativas a este documento. Adjuntar los archivos reales al LLM que deba verlos.

| Archivo y versión | Pantalla/estado/tamaño | Qué se acepta | Estado de revisión y fecha |
|---|---|---|---|
| «visual/pantalla-v1.png» | «…» | «inspiración / estructura / apariencia concreta» | «pendiente / aprobado por…» |

- Prompt de generación o archivo que lo contiene: «…»
- Cómo abrir el prototipo: «…»
- Funciones simuladas y límites: «…»
- Diferencias pendientes respecto de las referencias: «…»

## Prueba de uso y cambios

| Caso | Acción y resultado esperado | Resultado observado | Versión y quién lo probó | Pendiente/corrección |
|---|---|---|---|---|
| «caso normal o error relevante» | «…» | «no probado / observación» | «…» | «…» |

«Actualizar fichas y referencias al corregir; conservar una versión vigente inequívoca. La evidencia prevista no cuenta como prueba realizada.»
