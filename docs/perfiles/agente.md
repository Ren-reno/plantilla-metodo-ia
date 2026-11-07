# Perfil `agente`

Anexo de `../00-LEEME-IA.md`, que manda sobre esto. Aquí solo se dice **cómo entregas**.

Tienes acceso declarado al repositorio y a la terminal, y editas los archivos en local. Eso cambia el transporte, no el método: el alcance, la evidencia y el cierre son los del núcleo.

**Antes de empezar, declara qué acceso tienes de verdad**: si puedes leer el repositorio, ejecutar comandos, instalar dependencias y ver imágenes. Si algo de eso no lo tienes, dilo y trabaja como `chat-web` para esa parte.

## Entrega

Tres cosas, y ninguna es un bloque de comandos para pegar:

1. **Los cambios aplicados**, solo en los archivos de `Tocar:`, y un `git diff` que la persona pueda revisar. El commit lo propones con el mensaje del reporte; hacerlo o no lo decide la persona, y el push nunca es tuyo salvo que te lo pida.
2. **El reporte de seis secciones**, igual que en cualquier perfil.
3. **La evidencia de lo que ejecutaste**: la salida de `python tools/comprobar.py` y, si hubo fallos, qué cambió entre intentos. Los logs completos ya quedan en `.comprobaciones/`; en el reporte va el resumen, no el volcado.

**No pidas a la persona comandos que tú puedes ejecutar.** Pedirle que copie y pegue lo que tienes delante es coste sin beneficio, y era una de las fricciones del piloto.

**El parche deja de ser obligatorio.** Un diff verificable y un commit bastan. Entrega un `.patch` solo si la persona lo pide, o si hay que comprobar que el cambio se aplica sobre una copia limpia; antes de quitar esa copia limpia de un flujo que la usaba, pregunta qué riesgo cubría.

## Comprobaciones

- Mientras trabajas: `python tools/comprobar.py rapido`, o `--ruta` con la ruta de la tarjeta.
- Antes de entregar: `python tools/comprobar.py entrega`.
- **Las suites largas no se vigilan con mensajes.** Nada de preguntar cada quince o treinta segundos si terminó: o la ejecutas una vez y esperas su salida, o la corre la persona o el CI y tú recibes el resumen. Esa espera en bucle fue una de las fuentes de coste del piloto, y no la provocaba el modelo sino la forma de conducirlo.
- No reejecutes una suite que ya pasó si nada cambió desde entonces.
- No instales nada que la tarjeta no pida, y declara en el reporte cualquier dependencia nueva.

## Límites que no cambian

- No toques `docs/plan/` ni `docs/decisiones/`: los mantiene `cerrar.py`.
- No modifiques tests que ya existían; si crees que uno está mal, dilo y espera.
- Máximo dos intentos por fallo. Tener la terminal delante no es permiso para insistir diez veces.
- Tú no declaras «hecha» la tarea, ni marcas una ADR como aceptada, ni cierras nada: eso es de la persona.
- Que tengas acceso a todo el repositorio no amplía `Tocar:`. Si necesitas otro archivo, va a *Pendientes*.
