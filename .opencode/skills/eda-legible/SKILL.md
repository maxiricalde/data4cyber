---
name: eda-legible
description: "Trigger: EDA, análisis exploratorio, notebook, comentarios, legibilidad, refactor. Escribe celdas de EDA comentadas por bloque para depurar y refactorizar fácil."
license: Apache-2.0
metadata:
  author: "maxi"
  version: "1.1"
---

# EDA legible

## Activation Contract

Usar al crear o editar celdas de un notebook de análisis exploratorio. Objetivo: entender qué hace cada bloque leyendo solo los comentarios, sin ejecutar.

## Entradas (las da el usuario)

- Notebook objetivo: ruta explícita del `.ipynb` a crear o editar.
- Fuente de datos: ruta o carpeta explícita del dataset.
- Si falta alguna, preguntar y esperar. No adivinar rutas, no escanear el repositorio buscando CSVs, no asumir nombres de archivo ni estructura de carpetas.

## Hard Rules

- Un bloque de código = una intención. Antes del bloque, un comentario que diga PARA QUÉ está.
- El comentario va ARRIBA de lo que explica, nunca al final de la línea.
- Prohibido comentar lo obvio (`# suma 1`, `# importa pandas`). Si el código ya lo dice, no se comenta.
- Si un nombre de variable explica mejor que un comentario, renombrá en vez de comentar.
- Nunca imputar en silencio: si se reemplaza, filtra o descarta algo, el comentario declara el criterio y por qué.
- Cada sección: banner numerado `# === 3. Distribuciones ===`.
- Cada bloque: `# --- qué hace ---`.
- Una celda = un paso verificable. Si hace dos cosas, son dos celdas.
- Toda salida impresa lleva etiqueta (`print("filas:", ...)`), nunca un valor suelto.
- Nada de rutas absolutas ni nombres de archivo del proyecto dentro del notebook: la ruta de datos va en una celda de configuración, en una sola variable.
- No ejecutar el notebook. Se entrega el `.ipynb` **sin salidas** y el usuario lo corre donde quiera. Prohibido nbclient, papermill o kernels propios.
- Entregar compatible con Colab: una sola variable de ruta, sin mounts automáticos ni rutas absolutas de la máquina del agente.

## Decision Gates

| Situación | Acción |
|---|---|
| Cálculo no obvio (agregación, máscara, pivot) | comentario de una línea con la intención |
| Transformación que cambia datos | comentario con criterio + efecto |
| Código autoevidente | sin comentario |
| Bloque de más de ~10 líneas | extraer a función con docstring de una línea |

## Execution Steps

1. Confirmar notebook y fuente de datos. Sin ambos, no se escribe código.
2. Celda de configuración con la ruta de datos en una sola variable.
3. Banner de sección.
4. Comentario de intención del bloque.
5. Código mínimo que cumple esa intención.
6. Salida con etiqueta. Siguiente celda, sin encadenar intenciones.

## Output Contract

Notebook ejecutable, celdas idempotentes, sin estado oculto entre celdas, comentarios en español, secciones numeradas, cada salida etiquetada, una sola fuente de rutas.
