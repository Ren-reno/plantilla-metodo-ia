<!--
  Plantilla de DISENO.md. Es un solo documento vivo: cada chat de diseño lo recibe y lo devuelve actualizado.
  Los títulos (## y ###) deben quedar EXACTAMENTE así: los scripts (init_diseno.py, validar.py) los usan para repartir y revisar.
  Lo que va entre «» se reemplaza. Borra estos comentarios al llenar el documento.

  Identificadores: C criterio propio (R si viene de rúbrica) · RF requisito funcional · RN regla de negocio ·
  RNF requisito no funcional · ADR decisión · P pregunta abierta · S supuesto · T tarea.
  Lo que el enunciado no dice se marca como supuesto (S-xx) o pregunta (P-xx). No inventes cifras.
-->
# DISENO — «nombre de la app»

> Versión «1» · «fecha» · Fuente: «enunciado, rúbrica, conversación…». Supuestos S-xx, preguntas P-xx, brechas [PENDIENTE P-xx].

## Problema y objetivo

«Qué problema resuelve la app y para quién.»

## Actores

«Quién usa la app o interactúa con ella.»

## Alcance (dentro / fuera)

- Dentro: «…»
- Fuera: «lo que explícitamente no se hará»

## Criterios de éxito

<!-- Con rúbrica: peso = puntaje. En un proyecto propio: 3 a 7 criterios con peso 5 (imprescindible), 3 (importante) o 1 (deseable). -->

| ID | Criterio | Peso | Fuente (rúbrica / propio) |
|---|---|---|---|
| C1 | «criterio» | 5 | propio |

## Funcionalidades

<!-- Un bloque ### por requisito. La línea Aporta a: va inmediatamente bajo el título. Cada criterio de aceptación debe poder comprobarse con un test. -->

### RF-001 · «Nombre del requisito»
Aporta a: C1
Criterios de aceptación:
- «criterio comprobable»
- [PENDIENTE P-01] «criterio que depende de una pregunta abierta»

## Datos principales (entidades y relaciones)

<!-- Entidades con sus atributos de negocio; relaciones con verbo (registra, agrupa). Alimenta docs/modelo.md y los diagramas ER. -->

«Entidades y relaciones.»

### Flujos principales

<!-- Los recorridos clave de punta a punta. Alimentan los diagramas de secuencia y las rebanadas del plan. -->

«Flujos.»

## Reglas y restricciones

<!-- RN-xx: reglas de negocio · RNF-xx: requisitos no funcionales. -->

- **RN-01** «regla»
- **RNF-01** «requisito no funcional»

## Tecnología (decidida / pendiente)

<!-- Lo decidido y lo pendiente. Elegir un stack arrastra decisiones derivadas (base local, versión mínima del lenguaje): regístralas como ADR antes de T-001. -->

«Stack.»

## Decisiones

### ADR-0001 · «Título»
Estado: propuesta · Motivo: «por qué» · Afecta: «qué»

## Preguntas abiertas

<!-- Marcas: [BLOQUEA T-xxx] si impide una tarea · [RESUELTA → ADR-xxxx] cuando ya se resolvió. -->

- **P-01** «pregunta» [BLOQUEA T-001]

## Supuestos

- **S-01** «supuesto»
