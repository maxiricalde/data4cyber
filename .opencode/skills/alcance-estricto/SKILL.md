---
name: alcance-estricto
description: "Trigger: no agregues, solo lo pedido, no modifiques, sin pedir, alcance, de más. Impide crear o cambiar archivos, código o config que el usuario no pidió explícitamente."
license: Apache-2.0
metadata:
  author: "maxi"
  version: "1.0"
---

# Alcance estricto

## Activation Contract

Usar SIEMPRE en este proyecto, antes de cualquier escritura. El alcance es exactamente el último pedido textual del usuario: ni una línea, archivo, carpeta, dependencia ni "mejora" más. Ante duda de si algo está incluido, no está incluido.

## Hard Rules

- Pedido de análisis, explicación, revisión, comparación o diagnóstico es **sólo lectura**. Cero cambios en disco.
- Prohibido crear archivos, carpetas, notebooks, scripts, tests, docs, configs o dependencias que el usuario no nombró.
- Prohibido tocar de paso: refactors, renombres, formato, docstrings, type hints, imports, prints, comentarios extra.
- Prohibido "arreglar" algo que funciona solo porque se vio al pasar. Se menciona, no se cambia.
- Si el pedido nombra un archivo, celda o función, ese es el límite. Lo de afuera no se toca.
- Si algo parece faltar para terminar, **se propone en una línea al final** y no se implementa.
- Pedido ambiguo sobre si hay que escribir: una sola pregunta y frenar. No se asume intención de cambio.
- Antes de escribir, una línea con: qué archivos se tocan y por qué entran en el pedido.
- No ejecutar notebooks, modelos ni tests si no lo pidió (ver `eda-paso-a-paso`, `metodo-supuestos`).
- Ninguna decisión de alcance se toma por cuenta propia para "dejar todo consistente".

## Decision Gates

| Pedido | Acción |
|---|---|
| "explicame", "por qué", "revisá", "¿anda?" | responder con evidencia, cero ediciones |
| "arreglá X" | tocar sólo lo mínimo para X, nada alrededor |
| "agregá Y" | crear sólo Y, en el lugar indicado |
| "¿hace falta Z?" | responder sí/no con motivo, no crear Z |
| "dejalo mejor" / "optimizá" | una pregunta de alcance concreto y esperar |
| El cambio pedido obliga a tocar otro archivo | decirlo en una línea y esperar OK |
| Se detecta un bug o mejora no pedida | anotarlo como pendiente, no corregirlo |

## Execution Steps

1. Fijar el alcance en una frase citando el pedido textual.
2. Enumerar los archivos a tocar. Si la lista excede el pedido, frenar y preguntar.
3. Escribir sólo eso, sin adelantar pasos siguientes.
4. No ejecutar nada.
5. Cerrar con: qué se cambió, qué quedó pendiente **sin tocar**, una pregunta si hay ambigüedad real.

## Output Contract

Cambios acotados al pedido literal, sin archivos ni código nuevos no solicitados, sin refactors de arrastre, y una lista explícita de lo detectado que quedó sin tocar.

## References

- `eda-paso-a-paso` — una celda por turno, compila el usuario.
- `metodo-supuestos` — nada de modelado sin plan aprobado.
