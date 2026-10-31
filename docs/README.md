# Mapa de la documentación

Si necesitas saber **X**, mira **Y**:

| Necesitas saber… | Mira |
|---|---|
| Qué debe hacer la app | `requisitos/` |
| Por qué se eligió algo | `decisiones/` |
| Por qué se hizo un cambio y cómo se pensó (su mini-diseño) | `cambios/` |
| Qué datos maneja | `modelo.md` y `diagramas/` |
| Cómo se comunican las partes | `contratos/` |
| Qué está hecho y qué falta | `plan/ESTADO.md` |
| Qué tareas forman el plan y qué cubre cada una | `plan/backlog.md` y `plan/cobertura.md` |
| Cómo escribir código y qué comandos usar | `00-LEEME-IA.md` |
| Cómo trabajar con este repo (guía para ti) | `COMO-TRABAJAR.md` |
| Los formatos en blanco (diseño, plan, tarjeta, ADR, reporte, cambio) | `plantillas/` |
| El diseño original, antes de repartirlo | `archivo/` (solo histórico) |

## Qué aparece y cuándo

Una plantilla recién creada no trae varios de esos archivos: los generan las herramientas de `tools/`.

| Archivo o carpeta | Lo genera |
|---|---|
| `requisitos/` (un archivo por requisito, más `contexto.md`), `decisiones/` (una decisión por archivo), `modelo.md` | `tools/init_diseno.py`, a partir de `DISENO.md` |
| `plan/backlog.md`, `plan/cobertura.md`, `plan/tareas/` | `tools/init_plan.py`, a partir del plan |
| `bundles/` (en la raíz del repo, no en `docs/`; git la ignora) | `tools/bundle.py`, un archivo por tarea |
| `plan/ESTADO.md` y el índice de `decisiones/` | `tools/cerrar.py` |

`plan/ESTADO.md` y el índice de decisiones **no se editan a mano**: los escribe siempre `tools/cerrar.py`, para que nunca choquen dos escritores.

## Nombres

- Decisiones: `decisiones/NNNN-slug.md` (por ejemplo, `0003-auth.md`). Un archivo por decisión.
- Tareas: `plan/tareas/T-NNN.md`. Reportes: `plan/reportes/`, uno por tarea cerrada.
- Módulos: una carpeta por módulo en `src/`, con sus tests en `tests/<módulo>/`.
- Cambios: `cambios/NNNN-slug.md`, un mini-diseño por cambio (su ID es `CAM-NNNN`, con el mismo número).
- Bundles: `bundles/T-NNN.md`, uno por tarea. Son derivados: no se editan, y se regeneran cuando quieras.

## Identificadores

`C` criterio de éxito propio (`R` si viene de una rúbrica) · `RF` requisito funcional · `RN` regla de negocio · `RNF` requisito no funcional · `ADR` decisión · `P` pregunta abierta · `S` supuesto · `T` tarea.
