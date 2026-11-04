<!--
  Plantilla de DISENO.md. Es el documento principal de diseño: cada chat de diseño lo recibe y lo devuelve actualizado.
  Los títulos (## y ###) deben quedar EXACTAMENTE así: los scripts (init_diseno.py, validar.py) los usan para repartir y revisar.
  Lo que va entre «» se reemplaza. Borra estos comentarios al llenar el documento.

  Identificadores: C criterio propio (R si viene de rúbrica) · RF requisito funcional · RN regla de negocio ·
  RNF requisito no funcional · ADR decisión · P pregunta abierta · S supuesto · T tarea.
  Lo que el enunciado no dice se marca como supuesto (S-xx) o pregunta (P-xx). No inventes cifras.

  Sigue docs/DISENAR.md; usa el complemento experiencia.md si hay UI y el inventario de diagramas.
  No añadas nuevos títulos ##: los complementos se copian manualmente. D16 no limita el diseño.
  Antes de dar el diseño por cerrado, pregunta (hasta 3 preguntas por tanda, ampliables hasta 5) por lo que cuesta cambiar después:
  ¿un usuario o varios?, ¿hay login?, ¿idiomas?, ¿datos sensibles o privados?, ¿dónde corre (web, escritorio, móvil)?,
  ¿cuántos datos o usuarios? Lo que quede sin resolver va como pregunta P-xx con [BLOQUEA T-xxx], o como ADR propuesto.
-->
# DISENO — «nombre de la app»

> Versión «1» · «fecha» · Fuente: «enunciado, rúbrica, conversación…». Supuestos S-xx, preguntas P-xx, brechas [PENDIENTE P-xx].

## Problema y objetivo

«Qué problema resuelve la app y para quién.»

## Actores

<!-- ACT y ROL son referencias documentales, no categorías admitidas en Cubre. Usa IDs estables y No aplica con motivo donde corresponda. -->
**Actores**

| ID | Nombre | Tipo (persona / sistema externo) | Objetivo | Roles aplicables | RF relacionados |
|---|---|---|---|---|---|
| ACT-001 | «nombre» | «tipo» | «objetivo» | «ROL-001 o No aplica» | «RF-001» |

**Roles y permisos, si aplican**

| ID | Nombre | Responsabilidad | Alcance de datos |
|---|---|---|---|
| ROL-001 | «nombre» | «responsabilidad» | «datos propios / compartidos / condición» |

| Rol | Acción | Recurso | Condición | Permitido | Regla relacionada |
|---|---|---|---|---|---|
| ROL-001 | «acción» | «recurso» | «condición explícita» | «sí / no» | «RN-01» |

«Si no hay roles o control de acceso, sustituye las tablas no aplicables por el motivo. Una persona puede desempeñar varios roles; no inventar cuentas.»

## Alcance (dentro / fuera)

- Dentro: «…»
- Fuera: «lo que explícitamente no se hará»

**Revisión para planificar**

- Versión revisada y complementos: «DISENO.md, EXPERIENCIA.md si aplica, inventario y referencias»
- Alcance listo: «recorridos»
- Evidencia revisada: «prototipo, referencias, ejemplos o exploraciones; distinguir lo pendiente»
- Pendientes y bloqueos: «P-xx → impacto → cuándo resolver»
- Dictamen propuesto: «LISTO / LISTO PARA ALCANCE ACOTADO / FALTA RESOLVER»
- Decisión del usuario: «confirmación de versión y alcance, o pendiente»

## Criterios de éxito

<!-- Con rúbrica: peso = puntaje. En un proyecto propio: 3 a 7 criterios con peso 5 (imprescindible), 3 (importante) o 1 (deseable). -->

| ID | Criterio | Peso | Fuente (rúbrica / propio) |
|---|---|---|---|
| C1 | «criterio» | 5 | propio |

## Funcionalidades

<!-- Un bloque ### por requisito. La línea Aporta a: va inmediatamente bajo el título. Cada criterio tiene evidencia definida: test para lo automatizable, revisión visual o prueba de uso cuando corresponda. No declarar como realizada una comprobación prevista. -->

### RF-001 · «Nombre del requisito»
Aporta a: C1
Criterios de aceptación:
- «comportamiento observable; evidencia prevista: test / revisión visual / prueba de uso»
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

«Stack y decisiones que condicionan el primer incremento.»

- Ejecución y operación mínima: «dónde corre, cómo arrancar y comprobar; despliegue y recuperación si aplica»
- Convenciones previstas: «estructura, comandos por servicio, idioma y formato de docstrings según el stack; T-001 los concreta»
- Experiencia: «EXPERIENCIA.md durante diseño → docs/experiencia.md al incorporar; o No aplica con motivo»
- Diagramas: «inventario diagramas/README.md → docs/diagramas/README.md; tipos elegidos y omitidos con motivo»

## Decisiones

### ADR-0001 · «Título»
Estado: propuesta · Motivo: «por qué» · Afecta: «qué»

## Preguntas abiertas

<!-- Marcas: [BLOQUEA T-xxx] si impide una tarea · [RESUELTA → ADR-xxxx] cuando ya se resolvió. -->

- **P-01** «pregunta» [BLOQUEA T-001]

## Supuestos

- **S-01** «supuesto»
