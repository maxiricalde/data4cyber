# AGENTS.md — tpfinal-colab

## Alcance estricto (regla permanente)

El alcance es exactamente el último pedido textual del usuario. Ni un archivo, carpeta, dependencia, función, test, notebook, doc ni "mejora" más.

- Pedido de explicar, revisar, comparar, diagnosticar o "¿anda?" es **sólo lectura**: cero cambios en disco.
- Prohibido el "de paso": refactors, renombres, formato, docstrings, type hints, imports, archivos nuevos.
- Si el pedido nombra un archivo, celda o función, ese es el límite. Lo de afuera no se toca.
- Lo que se detecta de paso se propone en una línea al final; **no se implementa**.
- Si algo parece faltar para terminar, se pregunta y se frena. No se asume intención de cambio.
- No ejecutar notebooks, modelos ni tests si no lo pidió.

Detalle completo: `.opencode/skills/alcance-estricto/SKILL.md`
