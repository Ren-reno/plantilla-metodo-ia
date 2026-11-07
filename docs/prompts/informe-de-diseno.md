# Prompt: informe de diseño

Un informe que explica **este** proyecto: el problema, la solución, el stack, la arquitectura y los conceptos que hacen falta para entenderlo. Se pide cuando tú quieres; no sale de cada tarjeta ni de cada reporte.

*Para qué:* la plantilla ya tiene glosario, actores, decisiones, contratos y diagramas, pero están repartidos por fuerza: cada archivo responde una pregunta. Nada deriva una explicación entera y contrastada del proyecto, y eso es justo lo que hace falta para aprender de lo que estás construyendo o para que entre otra persona.

**El informe es una vista derivada, con fecha.** No es otra autoridad: no decide nada, no sustituye al diseño ni a las decisiones, y envejece. Si contradice a `docs/`, el que manda es `docs/`.

## Cuándo pedirlo

| Momento | Qué puede explicar |
|---|---|
| Terminado el diseño, antes del plan | La arquitectura **prevista**. No hay módulos ni endpoints todavía |
| En medio de las olas | Lo construido hasta aquí, y qué falta del alcance |
| Al cerrar una versión | El proyecto entero, y qué cambió desde el informe anterior |

## Cómo pedirlo

Funciona pegado en cualquier chat y también en un agente; no exige plataforma.

- **Perfil `chat-web`:** adjunta lo que tengas de la lista de abajo. Lo que no adjuntes, el informe lo declara como no visto; no se rellena a ojo.
- **Perfil `agente`:** dale la lista como rutas y que las lea él. Que cite el commit con el que trabajó (`git rev-parse --short HEAD`).

Lo que entra: alcance y versión o commit · `docs/requisitos/` (incluido `contexto.md`, con los actores) · `docs/modelo.md` · `docs/decisiones/` · `docs/contratos/` · `docs/diagramas/` · `docs/plan/backlog.md` y `docs/plan/cobertura.md` · `docs/plan/ESTADO.md` · `comprobaciones.json` · los archivos de dependencias · `docs/experiencia.md` y `docs/visual/` si hay UI · el código relevante, si ya existe.

Si solo quieres una parte, pídela por su número.

## El prompt

```
Escribe un informe de diseño de este proyecto con lo que te doy, para alguien que empieza y quiere
entenderlo de verdad. No es un resumen comercial ni una lista de archivos: explica cómo funciona.

Reglas, antes de escribir:

1. Cada afirmación técnica que importe cita su fuente: archivo y sección, o archivo y símbolo
   (por ejemplo «docs/requisitos/RF-003.md, Criterios» o «src/mapa/consulta.py:buscar_persona»).
   Una afirmación sin fuente no se escribe.
2. Marca cada afirmación sobre el comportamiento con uno de estos cinco estados, tal cual:
   [diseñado] decidido y escrito, no construido · [implementado] el código existe ·
   [probado] hay una prueba que lo cubre y pasó · [inferido] lo deduces de lo que ves, sin que esté
   escrito · [desconocido] no tienes la fuente. Si dudas entre dos, usa el más débil.
3. No inventes nada: ni clases, ni endpoints, ni carpetas, ni cifras, ni actores. Si el proyecto
   está solo diseñado, explica la arquitectura prevista y dilo así.
4. Si encuentras contradicciones entre el diseño y el código, o entre dos documentos, señálalas en
   la Base y sigue. No las resuelvas al redactar ni elijas una en silencio.
5. No me pidas rellenar plantillas nuevas ni crear documentos para poder escribir esto. Trabaja con
   lo que hay.

Estructura, con estos títulos y en este orden:

Base del informe — fecha; versión o commit; qué recibiste y qué no pudiste ver; las contradicciones
que encontraste; y al final, el índice de las fuentes que citas.

1. Problema y recorrido de usuario — qué problema resuelve, de quién es, cómo lo resuelve hoy sin
   esto, y el recorrido completo de la persona que lo usa.
2. Solución y alcance — qué hace y qué deliberadamente no hace. Separa el MVP (lo que comprueba la
   hipótesis) de lo diferido, con el motivo de cada diferimiento.
3. Stack: qué hace cada tecnología y por qué — una fila por pieza: qué responsabilidad tiene, qué
   decisión la eligió y qué alternativa se descartó. Si el motivo no está documentado, dilo.
4. Mapa de módulos y dependencias — qué módulos hay, de qué es responsable cada uno, qué interfaz
   expone y de quién depende. Nombres y rutas verificables, no categorías inventadas. Di también
   qué módulos son previstos y aún no existen.
5. El recorrido de un dato, de punta a punta — elige una operación real y síguela: dónde entra, qué
   la valida, qué la transforma, dónde se guarda, qué se devuelve y qué pasa si falla.
6. Conceptos, con ejemplos de este proyecto — los conceptos que hay que entender para leer este
   código, explicados con sus propios ejemplos, no con ejemplos de manual. Añade los términos
   propios del dominio.
7. Decisiones, alternativas y consecuencias — las decisiones que forman la arquitectura: qué se
   decidió, qué se descartó, qué consecuencia tiene hoy y cuál sigue abierta.
8. Cómo añadir una función — el camino concreto: qué documentos se tocan, qué módulos, qué pruebas
   la protegen y qué contrato no se puede romper.
9. Límites, preguntas y qué aprender después — qué no se ha probado, qué quedó sin decidir, qué te
   resultó confuso al leer el proyecto, y una ruta de aprendizaje corta y ordenada.
```

## Cómo saber si el informe sirve

Tres pruebas, y las tres son de lectura:

- Alguien que empieza puede explicar una funcionalidad **y encontrar sus piezas** en el repo.
- Otra persona puede verificar las afirmaciones contra las fuentes citadas, sin preguntarte.
- Pedido otra vez después de un cambio, el informe muestra diferencias reales, y no presenta como construido lo que solo se planificó.

Si falla la primera, al informe le falta concreción. Si falla la segunda, le faltan citas. Si falla la tercera, se escribió desde el plan y no desde el repo.

## Lo que este prompt no hace

- **No valida nada.** Ninguna herramienta lo lee: los títulos de arriba no están acoplados a ningún parser y puedes cambiarlos. Lo que comprueban las máquinas sigue en `tools/`.
- **No sustituye al diseño.** Si el informe y `docs/requisitos/` no coinciden, es un hallazgo del proyecto: se resuelve en `docs/`, no en el informe.
- **No cierra tareas ni acepta decisiones.** Eso lo hacen `tools/cerrar.py` y tú.
