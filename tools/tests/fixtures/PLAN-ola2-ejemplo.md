## Tarjetas de la ola 2
### T-004 · Listar atrasos
Estado: pendiente · Tamaño: S · Depende de: T-003 · Cubre: C2 (3), RF-003
Objetivo: Que la bibliotecaria vea la lista de préstamos con la devolución vencida.
Leer (solo esto): docs/00-LEEME-IA.md · docs/requisitos/RF-003-listar-atrasos.md · docs/modelo.md#prestamo
Tocar: src/atrasos/* · tests/atrasos/*
No tocar: src/prestamos/*
Fuera de alcance: avisar a los socios por correo · multas en dinero
Criterios de aceptación (→ tests):
  - Se listan los préstamos con fecha de devolución vencida
  - La lista muestra el nombre del socio y el título del libro
Ejemplos aprobados:
  - Préstamo del 1 de marzo, hoy es 16 de marzo → atrasado
  - Préstamo del 1 de marzo, hoy es 15 de marzo → no atrasado
Comando de test: ver docs/00-LEEME-IA.md (solo sobre tests/atrasos/*)
Entrega: un parche (git diff) + reporte + comandos para aplicar

### T-005 · Buscar libros por título
Estado: pendiente · Tamaño: S · Depende de: T-002 · Cubre: C3 (1), RF-001
Objetivo: Poder buscar en el catálogo por una parte del título.
Leer (solo esto): docs/00-LEEME-IA.md · docs/requisitos/RF-001-registrar-libro.md · docs/modelo.md#libro
Tocar: src/libros/* · tests/libros/* · docs/requisitos/RF-001-registrar-libro.md (solo si cambia el comportamiento)
No tocar: src/prestamos/*
Fuera de alcance: buscar por autor · filtros combinados
Criterios de aceptación (→ tests):
  - Buscar un texto devuelve los libros cuyo título lo contiene
  - Una búsqueda sin coincidencias devuelve una lista vacía
Comando de test: ver docs/00-LEEME-IA.md (solo sobre tests/libros/*)
Entrega: un parche (git diff) + reporte + comandos para aplicar
