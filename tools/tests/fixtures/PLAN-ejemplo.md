# PLAN — Biblioteca de barrio
> Versión 1 · 28-oct-2026 · fuente: DISENO.md, versión 1 (ejemplo ficticio para probar init_plan.py)

## Backlog
### Rebanada 1 · Prestar y devolver un libro de punta a punta
- T-001 · Esqueleto andante · Depende de: — · Cubre: C1 (5)
- T-002 · Registrar libro · Depende de: T-001 · Cubre: C1 (5), RF-001
- T-003 · Prestar y devolver libro · Depende de: T-002 · Cubre: C1 (5), RF-002, RN-01
### Rebanada 2 · Revisar atrasos y buscar en el catálogo
- T-004 · Listar atrasos · Depende de: T-003 · Cubre: C2 (3), RF-003
- T-005 · Buscar libros por título · Depende de: T-002 · Cubre: C3 (1), RF-001

## Matriz de cobertura
| Criterio | RF | Tareas |
|---|---|---|
| C1 | RF-001 | T-001, T-002 |
| C1 | RF-002 | T-003 |
| C2 | RF-003 | T-004 |
| C3 | RF-001 | T-005 |

## Tarjetas de la ola 1
### T-001 · Esqueleto andante
Estado: pendiente · Tamaño: S · Depende de: — · Cubre: C1 (5)
Objetivo: Dejar la app arrancando con un test que pasa y el CI corriendo, sin ninguna funcionalidad todavía.
Leer (solo esto): docs/00-LEEME-IA.md · docs/decisiones/0001-usar-una-base-de-datos-relacional.md · docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md
Tocar: src/* · tests/* · .github/workflows/ci.yml · docs/00-LEEME-IA.md (solo Convenciones y Comandos)
No tocar: docs/requisitos/*
Fuera de alcance: libros, socios y préstamos · inicio de sesión
Criterios de aceptación (→ tests):
  - La app arranca y responde en la página de inicio
  - Un test de humo pasa en local
  - [verifica: CI] El CI corre ese test y sale en verde
Comando de test: ver docs/00-LEEME-IA.md (solo sobre tests/*)
Entrega: un parche (git diff) + reporte + comandos para aplicar

### T-002 · Registrar libro
Estado: pendiente · Tamaño: S · Depende de: T-001 · Cubre: C1 (5), RF-001
Objetivo: Poder registrar un libro con título y autor y encontrarlo disponible.
Leer (solo esto): docs/00-LEEME-IA.md · docs/requisitos/RF-001-registrar-libro.md · docs/modelo.md#libro
Tocar: src/libros/* · tests/libros/*
No tocar: src/prestamos/*
Fuera de alcance: editar o borrar libros · buscar por título
Criterios de aceptación (→ tests):
  - Con título y autor válidos se crea el libro y queda disponible
  - No se puede crear un libro sin título
Comando de test: ver docs/00-LEEME-IA.md (solo sobre tests/libros/*)
Entrega: un parche (git diff) + reporte + comandos para aplicar

### T-003 · Prestar y devolver libro
Estado: pendiente · Tamaño: M · Depende de: T-002 · Cubre: C1 (5), RF-002, RN-01
Modo: estricto
Objetivo: Prestar un libro disponible a un socio y registrar su devolución, con un solo préstamo abierto por libro.
Leer (solo esto): docs/00-LEEME-IA.md · docs/requisitos/RF-002-prestar-libro.md · docs/modelo.md#prestamo
Tocar: src/prestamos/* · tests/prestamos/*
No tocar: src/libros/*
Fuera de alcance: máximo de libros por socio (P-02 sigue abierta) · multas en dinero · reservas
Criterios de aceptación (→ tests):
  - Un libro disponible se presta a un socio y pasa a prestado
  - Un libro ya prestado no se puede prestar de nuevo
  - Al devolver un libro prestado, vuelve a estar disponible
Ejemplos aprobados:
  - Libro disponible, se presta → queda prestado
  - Libro prestado, se intenta prestar otra vez → se rechaza
  - Prestado el 1 de marzo → debe devolverse el 15 de marzo (14 días)
Comando de test: ver docs/00-LEEME-IA.md (solo sobre tests/prestamos/*)
Entrega: un parche (git diff) + reporte + comandos para aplicar
