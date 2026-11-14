---
name: eda-paso-a-paso
description: "Trigger: EDA paso a paso, una celda a la vez, no escribas de más, ir despacio, compilo yo. Entrega una sola celda por turno y espera tu corrida."
license: Apache-2.0
metadata:
  author: "maxi"
  version: "1.0"
---

# EDA paso a paso

## Activation Contract

Usar cuando el usuario avanza un EDA celda por celda: él compila, corrige y decide; el agente propone. Se combina con `eda-legible` (formato de celdas) y `metodo-supuestos` (antes de modelar).

## Hard Rules

- Una sola celda por respuesta. Nunca dos, nunca "y de paso esta otra".
- El alcance es el último pedido textual del usuario. Todo lo demás va a una lista de pendientes al final, jamás al código.
- Se escribe la propuesta y se frena. El usuario compila y responde; no se asume el resultado.
- No hay paso siguiente hasta que el usuario confirme el anterior: corrió / falló / qué mostró.
- Prohibido adelantar: imports, limpieza, gráficos, modelado o conclusiones que nadie pidió.
- Al corregir, devolver SOLO la celda afectada. Nunca el notebook entero ni celdas ya aprobadas.
- El agente no ejecuta el notebook. Si necesita una salida, la pide.
- Una pregunta por respuesta, sin menús de opciones ni alternativas múltiples.
- Respuesta corta: intención en una línea, celda, salida esperada, pregunta.

## Decision Gates

| Pedido del usuario | Acción |
|---|---|
| "dame la próxima celda" | una celda con su intención en una línea y frenar |
| "hacé todo el EDA" | proponer el recorrido en viñetas y avanzar de a una celda con OK |
| "falló / este es el error" | corregir solo esa celda citando el error; pedir el traceback si falta |
| "explicame esto" | explicación, cero código |
| "cambiá X de la celda N" | patch de esa celda, sin tocar las demás |
| "¿qué sigue?" | nombrar el paso siguiente en una línea y esperar OK antes de escribir código |
| No se sabe dónde va la celda | preguntar: ¿bloque para pegar o edito el `.ipynb`? No adivinar. |

## Execution Steps

1. Leer el último pedido y fijar el alcance en una frase.
2. Declarar la intención del paso en un comentario `# --- ... ---`.
3. Escribir UNA celda mínima, comentada según `eda-legible`.
4. Indicar qué salida etiquetada debe aparecer y qué significaría un problema.
5. Frenar con una sola pregunta: ¿corrió?, ¿qué mostró?, ¿seguimos?
6. Con la respuesta, corregir o proponer la celda siguiente. Nunca las dos cosas.

## Output Contract

Cada respuesta: alcance en una línea, una sola celda, salida esperada, una pregunta. Sin celdas extra, sin refactors no pedidos, sin ejecutar nada, sin cerrar el análisis por cuenta propia.
