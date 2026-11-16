---
name: metodo-supuestos
description: "Trigger: modelo, método estadístico, supuestos, regresión, test, antes de codear. Verifica los supuestos de un método con evidencia antes de generar código."
license: Apache-2.0
metadata:
  author: "maxi"
  version: "1.0"
---

# Método con supuestos verificados

## Activation Contract

Usar SIEMPRE antes de escribir código que aplique un modelo o método estadístico/ML. Su función es frenar: ningún método corre sin declarar sus supuestos y mostrar la evidencia de que se cumplen.

## Hard Rules

- Primero el plan, después el código. No hay código de modelado hasta que el plan esté aprobado.
- Cada método declarado trae su lista de supuestos. "Asumimos normalidad" NO es válido: va con el test o gráfico que lo verifica.
- Cada supuesto tiene veredicto explícito: cumple / no cumple / dudoso. Sin veredicto, el método no corre.
- Un supuesto que no cumple se reporta ANTES de modelar. Nunca se cambia de método en silencio.
- Distinguir supuesto del método de propiedad deseable. Ej.: OLS no exige normalidad de residuos para estimar; la exige para inferencia en muestras chicas.
- Declarar n y cantidad de parámetros. Si n no alcanza, decirlo.
- Toda transformación (log, escala, winsor) se declara con su efecto sobre la interpretación.
- Si un chequeo no se puede correr, se dice. No se inventa el resultado.
- El agente escribe el código; **nunca ejecuta** el notebook ni los modelos. La ejecución la hace el usuario en la herramienta que elija (Colab, Jupyter, VS Code). Prohibido usar nbclient, papermill o un kernel propio para correr celdas.
- No agregar supuestos, métodos ni secciones nuevas por iniciativa propia: solo se agrega lo que el usuario pida explícitamente y en el lugar que indique.

## Decision Gates

| Situación | Acción |
|---|---|
| Usuario pide un método | devolver plan + supuestos + chequeos; esperar OK |
| Supuesto no cumple | frenar, mostrar evidencia, proponer alternativas con tradeoffs |
| Supuesto dudoso | seguir solo con decisión explícita del usuario |
| Método sin supuestos formales (árboles) | declararlo y chequear lo que sí importa: leakage, balance, split |
| Usuario pide crear o editar el notebook | escribir el código y detenerse; no ejecutar |

## Execution Steps

1. Pregunta en una frase: qué decisión sostiene el análisis.
2. Método propuesto + por qué encaja con el tipo de datos y la estructura.
3. Tabla: supuesto → cómo se verifica → qué hacer si falla.
4. Esperar aprobación. Sin aprobación no hay código de modelado.
5. Una celda por chequeo, con veredicto impreso y etiquetado.
6. Recién entonces el ajuste, comentado según la skill `eda-legible`.

## Output Contract

Plan aprobado antes del código, tabla de supuestos con veredicto, evidencia ejecutada por cada uno, y ninguna decisión metodológica tomada sin confirmación.

## References

- `references/supuestos-por-metodo.md` — checklist por familia de métodos.
