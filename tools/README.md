# tools/

Herramientas locales del método. Son scripts de Python que usan solo la biblioteca estándar (no hay nada que instalar) y se corren desde la raíz del repo: `python tools/<nombre>.py`.

**Estado: vacía.** Se construyen de a una, y cada una se prueba en una app real antes de pasar a la siguiente.

| Herramienta | Para qué sirve | Orden |
|---|---|---|
| `init_diseno.py` | Reparte `DISENO.md` tal cual en `docs/` (un archivo por ADR, requisitos, modelo…), guarda el original en `docs/archivo/` y avisa de errores de formato con el número de línea | 1 |
| `init_plan.py` | Reparte el plan en `docs/plan/tareas/T-xxx.md` y escribe la matriz de cobertura en `docs/plan/cobertura.md` | 1 |
| `bundle.py T-007` | Arma el paquete de contexto de una tarea para pegarlo en un LLM | 2 |
| `aplicar.py` | Aplica el parche más reciente de tu carpeta de parches, con reintentos y diagnóstico | 3 |
| `cerrar.py T-007 reporte.md` | Valida el reporte, actualiza `ESTADO.md`, crea propuestas de ADR y avisa de cosas raras | 4 |
| `validar.py` | Revisa que diseño, plan, tarjetas y diagramas sean coherentes entre sí | 5 |

## Si vas a construir una herramienta

- Solo biblioteca estándar de Python; debe funcionar en Windows (PowerShell) y en Linux (el CI).
- `validar.py` debe terminar con código 0 en un repo recién creado desde la plantilla: el CI lo ejecuta apenas el archivo exista.
- `bundle.py` deja sus archivos en `bundles/`, una carpeta que git ignora (son derivados y pesados).
- Las preferencias del usuario (terminal y carpeta de parches) viven fuera del repo, en `~/.metodo-ia.json`: `bundle.py` las vuelca en la sección «Entorno del usuario» y `aplicar.py` las usa.
- `cerrar.py` es el único escritor de `docs/plan/ESTADO.md` y del índice de `docs/decisiones/`.
- Las plantillas en blanco están en `docs/plantillas/`.
