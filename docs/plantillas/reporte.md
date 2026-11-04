<!--
  Plantilla de reporte de tarea: lo entrega el LLM junto al parche y se guarda en docs/plan/reportes/.
  Las 6 secciones son obligatorias, van en este orden y con estos títulos exactos (los revisa tools/cerrar.py).
  Lo que va entre «» se reemplaza. Borra estos comentarios al llenarlo.
-->
# Reporte T-«NNN»

## Hecho

«Qué se implementó, en pocas líneas. En una corrección: qué fallaba, qué debía pasar, causa encontrada (o desconocida) y solución.»

## Supuestos

«Lo que diste por cierto sin que estuviera escrito. Si no hubo, escribe: ninguno.»

## Decisiones tomadas

«Si no hubo, escribe: ninguna. Si hubo, una línea por decisión: qué decidiste y por qué. Si afecta a otras tareas, termina esa línea con: Afecta a otras tareas.»

- «decisión» · Motivo: «por qué»

## Pendientes

«Lo que quedó fuera y por qué. Incluye los archivos que habrías necesitado tocar y no estaban en `Tocar:`.»

## Cómo probar

«Comando(s), pasos y resultado esperado. Para UI: versión, pantallas/estados/tamaños revisados, referencias o capturas reales y quién comprobó el resultado. Para bugs: reproducción y evidencia de antes/después. Mantener estas seis secciones.»

- Verificado: «lo que comprobaste de verdad, y cómo»
- No verificado: «lo que no pudiste comprobar, por ejemplo el CI de GitHub»

## Mensaje de commit sugerido

`«tipo: T-NNN descripción corta en español»`
