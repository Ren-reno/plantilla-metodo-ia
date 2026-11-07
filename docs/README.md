# Mapa de la documentación

Si necesitas saber **X**, mira **Y**:

| Necesitas saber… | Mira |
|---|---|
| Cómo usar las siete herramientas y entender sus códigos de salida | `../tools/README.md` |
| Qué comandos tiene el proyecto y qué se comprueba antes de entregar | `../comprobaciones.json` y `../tools/README.md` |
| Quién va a instalar esto y qué exige entregarlo | La etapa 5 de [COMO-TRABAJAR.md](COMO-TRABAJAR.md) |
| Cómo diseñar antes de planificar | [DISENAR.md](DISENAR.md) |
| Actores, roles y permisos | Sección Actores de `requisitos/contexto.md` |
| Pantallas, navegación, estilo y evidencia de uso | `experiencia.md` y referencias en `visual/`, si hay UI |
| Qué diagramas se eligieron y su estado | `diagramas/README.md` |
| Qué se corrigió y cómo se comprobó | `plan/reportes/` y commits de la tarea |
| Qué debe hacer la app | `requisitos/` |
| Por qué se eligió algo | `decisiones/` |
| Por qué se hizo un cambio y cómo se pensó (su mini-diseño) | `cambios/` |
| Qué datos maneja | `modelo.md` y `diagramas/` |
| Cómo se comunican las partes | `contratos/` |
| Qué está hecho, qué falta y **cuál es el siguiente comando** | `plan/ESTADO.md`: abre con etapa, siguiente acción y la decisión que te espera |
| Qué tareas forman el plan y qué cubre cada una | `plan/backlog.md` y `plan/cobertura.md` |
| Cómo escribir código y qué comandos usar | `00-LEEME-IA.md` |
| Cómo entrega el LLM según dónde corra (chat web o agente) | `perfiles/`, y «Elegir el perfil» en [COMO-TRABAJAR.md](COMO-TRABAJAR.md) |
| Cómo trabajar con este repo (guía para ti) | `COMO-TRABAJAR.md` |
| Entender el proyecto entero, para aprender o para que entre alguien | [prompts/informe-de-diseno.md](prompts/informe-de-diseno.md) |
| Los formatos en blanco (diseño, experiencia, inventario de diagramas, plan, tarjeta, ADR, contrato, reporte, cambio) | `plantillas/` |
| El diseño original, antes de repartirlo | `archivo/` (solo histórico) |

## Qué aparece y cuándo

Una plantilla recién creada no trae varios de esos archivos: algunos los generan las herramientas de `tools/` y otros se incorporan manualmente.

| Archivo o carpeta | Lo genera |
|---|---|
| `requisitos/` (un archivo por requisito, más `contexto.md`), `decisiones/` (una decisión por archivo), `modelo.md` | `tools/init_diseno.py`, a partir de `DISENO.md` |
| `experiencia.md`, `visual/` si aplican, y `diagramas/README.md` con fuentes .puml | Incorporación manual del paquete de diseño; ver [DISENAR.md](DISENAR.md#documentos-y-entrega-al-repo) |
| `plan/backlog.md`, `plan/cobertura.md`, `plan/tareas/` | `tools/init_plan.py`, a partir del plan |
| `comprobaciones.json` (en la raíz del repo): los comandos del proyecto, declarados una sola vez | T-001, al decidir el stack; los leen `tools/comprobar.py`, el CI y los bundles |
| `.comprobaciones/` (en la raíz del repo; git la ignora) | `tools/comprobar.py`, un log por paso de cada ejecución |
| `bundles/` (en la raíz del repo, no en `docs/`; git la ignora) | `tools/bundle.py`, un archivo por tarea |
| `plan/ESTADO.md`, `plan/reportes/` (un reporte por tarea cerrada) y el índice de `decisiones/` (`decisiones/README.md`) | `tools/cerrar.py` |

`plan/ESTADO.md` y el índice de decisiones **no se editan a mano**: los escribe siempre `tools/cerrar.py`, para que nunca choquen dos escritores. `cerrar.py` también crea las propuestas de decisión (`Estado: propuesta`) que salen de los reportes: tú las aceptas o las rechazas.

## Nombres

- Decisiones: `decisiones/NNNN-slug.md` (por ejemplo, `0003-auth.md`). Un archivo por decisión.
- Tareas: `plan/tareas/T-NNN.md`. Reportes: `plan/reportes/T-NNN.md` (`T-NNN-parche1.md` para el parche 1 del modo estricto), uno por tarea cerrada.
- Módulos: una carpeta por módulo en `src/`, con sus tests en `tests/<módulo>/`.
- Cambios: `cambios/NNNN-slug.md`, un mini-diseño por cambio (su ID es `CAM-NNNN`, con el mismo número).
- Bundles: `bundles/T-NNN.md`, uno por tarea. Son derivados: no se editan, y se regeneran cuando quieras.

## Identificadores

`C` criterio de éxito propio (`R` si viene de una rúbrica) · `RF` requisito funcional · `RN` regla de negocio · `RNF` requisito no funcional · `ADR` decisión · `P` pregunta abierta · `S` supuesto · `T` tarea.

`ACT-xxx` y `ROL-xxx` identifican actores y roles en los documentos y diagramas. Son referencias documentales: los scripts no validan sus relaciones ni los admiten como categorías de `Cubre:`.
