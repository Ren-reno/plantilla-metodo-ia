# DISENO — Biblioteca de barrio

> Versión 1 · 22-oct-2026 · Fuente: ejemplo ficticio para probar init_diseno.py. Supuestos S-xx, preguntas P-xx, brechas [PENDIENTE P-xx].

## Problema y objetivo

Una biblioteca de barrio presta libros con cuaderno y lápiz, y a veces no sabe quién tiene cada ejemplar. La app registra libros, socios y préstamos para saber qué está disponible y qué está atrasado.

## Actores

- **Bibliotecaria:** registra libros, socios y préstamos.
- **Socio:** consulta el catálogo y sus préstamos.

## Alcance (dentro / fuera)

- Dentro: catálogo de libros, registro de socios, préstamos y devoluciones, lista de atrasos.
- Fuera: multas en dinero, reservas de libros prestados, venta de ejemplares.

## Criterios de éxito

| ID | Criterio | Peso | Fuente (rúbrica / propio) |
|---|---|---|---|
| C1 | Se puede prestar y devolver un libro de punta a punta | 5 | propio |
| C2 | La bibliotecaria ve qué libros están atrasados | 3 | propio |
| C3 | El catálogo se puede buscar por título | 1 | propio |

## Funcionalidades

### RF-001 · Registrar libro
Aporta a: C1, C3
Criterios de aceptación:
- Con título y autor válidos se crea el libro y queda disponible
- No se puede crear un libro sin título

### RF-002 · Prestar libro
Aporta a: C1
Criterios de aceptación:
- Un libro disponible se presta a un socio y pasa a prestado
- Un libro ya prestado no se puede prestar de nuevo
- [PENDIENTE P-02] Máximo de libros prestados por socio

### RF-003 · Listar atrasos
Aporta a: C2
Criterios de aceptación:
- Se listan los préstamos con fecha de devolución vencida
- La lista muestra el nombre del socio y el título del libro

## Datos principales (entidades y relaciones)

Entidades (en MAYÚSCULAS; `*` marca las PK y FK obligatorias):

- LIBRO: *id_libro, título, autor
- SOCIO: *id_socio, nombre
- PRESTAMO: *id_prestamo, *id_libro, *id_socio, fecha_prestamo, fecha_devolucion

Relaciones:

- SOCIO **solicita** PRESTAMO (un socio, muchos préstamos)
- LIBRO **figura en** PRESTAMO (un libro, muchos préstamos a lo largo del tiempo)

### Flujos principales

1. **Prestar:** la bibliotecaria elige socio y libro; el sistema comprueba que el libro esté disponible y registra el préstamo.
2. **Devolver:** la bibliotecaria marca la devolución y el libro vuelve a estar disponible.
3. **Revisar atrasos:** la bibliotecaria abre la lista de atrasos y contacta a los socios.

## Reglas y restricciones

- **RN-01** Un libro solo puede tener un préstamo abierto a la vez.
- **RN-02** El plazo de devolución es de 14 días (supuesto S-01).
- **RNF-01** La lista de atrasos debe cargar de forma fluida con el catálogo completo.

## Tecnología (decidida / pendiente)

- Pendiente: lenguaje y base de datos (ver P-01 y ADR-0001).

## Decisiones

### ADR-0001 · Usar una base de datos relacional
Estado: propuesta · Motivo: los datos son tabulares y se relacionan entre sí (socios, libros, préstamos) · Afecta: modelo de datos, T-001

### ADR-0002 · Interfaz web sencilla, sin app móvil
Estado: propuesta · Motivo: la bibliotecaria trabaja desde un computador de escritorio · Afecta: alcance, T-001

## Preguntas abiertas

- **P-01** ¿Qué lenguaje y framework se usan? [BLOQUEA T-001]
- **P-02** ¿Cuántos libros puede llevar un socio a la vez?
- **P-03** ¿Se necesita una app móvil? [RESUELTA → ADR-0002]

## Supuestos

- **S-01** El plazo de devolución es de 14 días; la bibliotecaria no lo había definido.
- **S-02** Cada persona tiene un solo carnet de socio.
