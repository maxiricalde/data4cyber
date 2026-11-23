# SUPERVISADO_holdout — correcciones para justificar la entrega

**Objetivo:** dejar el informe del modelo supervisado defendible con el mínimo trabajo, sin reentrenar nada.
**Archivo:** `Colab/SUPERVISADO_holdout.ipynb` · **Estado:** plan, nada implementado · **Fecha:** 2026-11-22

> **Alcance vigente (L4):** el supervisado queda fuera de alcance. No se modifica `SUPERVISADO_holdout.ipynb`
> ni `SUPERVISADO.ipynb`. El trabajo editorial pasa a `EDA_we.ipynb` y `03_no_supervisado.ipynb`.
> Las tareas T1–T6 quedan congeladas como referencia, no como trabajo pendiente.

Todo lo de abajo es aritmética o edición de markdown sobre valores que ya están en los outputs.
Ninguna tarea requiere volver a correr LOSO, salvo que el kernel esté muerto (ver nota en T5).

---

## Evidencia ya disponible

### Transformaciones — mismo fold set, 7 folds, mismo `PARAMS_RF`

Comparación limpia dentro del notebook de holdout. No requiere cómputo nuevo.

| Representación | features | acc test | F1 | recall | recall@5 | espec S0 |
|---|---|---|---|---|---|---|
| Crudo (cell 5) | 132 | 0.497 | 0.303 | 0.225 | 0.234 | 0.349 |
| Rango 120 por escenario (cell 12, "ninguna") | 132 | 0.719 | 0.722 | 0.626 | 0.457 | 0.561 |

Delta: +22 pp accuracy, +24 pp especificidad S0. Es más fuerte que la tabla anterior y usa el transformador real.

### Transformaciones — corrida previa completa (`SUPERVISADO.ipynb`, cell 7)

| Representación | features | AUC | recall@5 | recall | espec S0 | acc test |
|---|---|---|---|---|---|---|
| Crudo | 132 | 0.833 | 0.257 | 0.319 | 0.442 | 0.545 |
| Rango móvil (**ventana 5**, frame concatenado) | 132 | 0.844 | 0.396 | 0.604 | 0.396 | 0.697 |
| Ventana 20 | 2640 | 0.751 | 0.310 | 0.367 | 0.446 | 0.566 |

Caveat obligatorio si se cita: esa fila de rango usó ventana 5 y 8 folds (con S1-alt dentro), no ventana 120 por escenario con 7 folds.

### Test final S1-alt — especificidad real derivada

S1-alt: n = 1792, 910 positivos / 882 negativos, prevalencia 0.5078.
Especificidad derivada de `(accuracy − recall × p) / (1 − p)`.

| Configuración | acc | recall | espec S1-alt | FPR | balanced real | AUC | recall@5 |
|---|---|---|---|---|---|---|---|
| RF random | 0.777 | 0.926 | 0.624 | 37.6 % | 0.775 | 0.881 | 0.596 |
| RF grid | 0.742 | 0.932 | 0.546 | 45.4 % | 0.739 | 0.868 | 0.481 |
| XGB random | 0.724 | 0.801 | 0.645 | 35.5 % | 0.723 | 0.783 | 0.142 |
| XGB grid | 0.804 | 0.977 | 0.626 | 37.4 % | 0.801 | 0.834 | 0.206 |
| CatBoost random | 0.749 | 0.823 | 0.673 | 32.7 % | 0.748 | 0.884 | 0.592 |
| CatBoost grid | 0.725 | 0.790 | 0.659 | 34.1 % | 0.724 | 0.743 | 0.057 |

Lectura honesta: el modelo ordena razonablemente (AUC 0.88) pero a umbral 0.5 marca como ataque entre 33 % y 45 % de los segundos benignos. A 5 % de FPR el mejor detecta 60 %.

---

## Specs

- **S1** — La elección de rango debe quedar sostenida por una tabla con fold set y transformador idénticos a los usados. Queda prohibido citar la fila de ventana 5 como si fuera la de 120.
- **S2** — Toda decisión de reducción debe justificarse por el atributo que realmente la distingue; si los números están dentro del ruido, se declara así y se justifica por dimensionalidad.
- **S3** — Toda métrica calculada sobre S1-alt debe usar únicamente datos de S1-alt. No se admite mezclar recall de test con especificidad out-of-fold de S0 bajo el nombre de "balanced accuracy".
- **S4** — La tabla final debe incluir todas las configuraciones evaluadas, sin truncamientos silenciosos.
- **S5** — El criterio de selección del modelo final debe declararse y sostenerse con métricas de validación (LOSO), no con la tabla de S1-alt.
- **S6** — El comportamiento del grid (empeora 2 de 3 modelos) se reporta como hallazgo sobre el criterio de selección por gap, con la evidencia de accuracy de train.

---

## Tareas

| ID | Spec | Tarea | Costo | Estado |
|---|---|---|---|---|
| T1 | S1 | Celda nueva: tabla de transformaciones juntando crudo (cell 5) + rango 120 ("ninguna" de cell 12); citar ventana 20 con caveat de 8 folds | 0 fits | pendiente |
| T2 | S2 | Editar markdown cell 16: reemplazar "da mejores resultados" por justificación de dimensionalidad (37 vs 132) + diferencias dentro del ruido | 0 fits | pendiente |
| T3 | S3 | Celda nueva: especificidad y balanced acc reales sobre S1-alt a partir de `accuracy` y `recall`, con `p = dfY_test.mean()` | 0 fits | pendiente |
| T4 | S4 | Extender el loop de la tabla final para incluir `resultado_xgb` y `resultado_cat` (hoy salen 4 de 6 filas) | 0 fits | pendiente |
| T5 | S5 | Declarar el criterio de selección (AUC + recall@5 en LOSO) y mostrar `resultado_rf["tabla"]`, `resultado_xgb["tabla"]`, `resultado_cat["tabla"]` | 0 fits si el kernel vive | pendiente |
| T6 | S6 | Párrafo de discusión: `elegir_por_gap` con `tolerancia=0.02` elige modelos subentrenados (CatBoost grid train acc 0.825; AUC holdout 0.884 → 0.743) | 0 fits | pendiente |

**Nota T5:** `resultado_*["tabla"]` ya contiene `auc` y `recall_5` por fold. Si el kernel se reinició, hay que volver a correr el tuneo (210 + 140 + 140 fits) para reconstruirlos.

---

## Orden sugerido

T2 y T4 primero (ediciones triviales), después T3 y T1 (aritmética), T5 y T6 al final (dependen del kernel vivo).

---

## Riesgo residual declarado

La tabla final evalúa seis configuraciones sobre S1-alt. Si el ganador se elige mirando esa tabla, S1-alt deja de ser holdout. La defensa válida es declarar el criterio en LOSO y verificar que el orden se mantiene; no es lo mismo que haberlo pre-registrado, y conviene decirlo con honestidad en el informe.

---

## Log

- **L1** — Pedido original (verbatim): "analiza el los resultados del ultimo de Supervisado" → luego "analiza el los resultados del ultimo de Supervisado hold out".
- **L2** — Corrección del usuario (verbatim): "no crees que se puede justificar arreglando un par de cosas no tenemos mucho tiempo por otro lado la comparacion de transformaciones ya estaba hecha".
  Verificado: la comparación está completa en `SUPERVISADO.ipynb` cell 7 (usando ventana 5 y 8 folds). En `SUPERVISADO_holdout.ipynb` la cell 8 quedó vacía por `KeyboardInterrupt`.
- **L3** — Pedido (verbatim): "guardalo en plan para verlo despues".
- **L4** — Cambio de alcance (verbatim): "el eda lo vamos a ir modificando ahora del supervisado no vamos a tocar nada unicamente EDA y NOSUPERVISADO".
  Efecto: T1–T6 quedan congeladas. El alcance activo es `Colab/EDA_we.ipynb` y `Colab/03_no_supervisado.ipynb`. Ningún archivo del supervisado se modifica.
- **L5** — Decisión (verbatim): "S0 dentro, S1-alt aparte (Recomendado)". Aplicada en `EDA_we.ipynb`; S1-alt sale del LOSO y pasa a una sección propia de comparación contra S1.
- **L6** — Error reportado (verbatim): "ModuleNotFoundError: No module named 'src2.eda'". Resuelto creando `Colab/src2/eda.py` y `Colab/src2/eval.py`.

---

## Hallazgo previo al trabajo en EDA (2026-11-22)

El EDA principal usa 7 folds LOSO con `S1, S1-alt, S2…S6`, es decir **sin S0 y con S1-alt dentro del entrenamiento**.
El notebook supervisado usa 7 folds con `S0, S1…S6`, es decir **con S0 y sin S1-alt**. Los dos conjuntos de folds no coinciden,
así que las cifras de rango del EDA (acc 0.773, AUC 0.863) no son comparables con las del modelado (acc 0.719).
Alinear el EDA al conjunto de entrenamiento del modelo es la corrección de mayor impacto.

## Ejecutado en `Colab/EDA_we.ipynb` (2026-11-22)

Decisión del usuario (L5): S0 dentro del LOSO, S1-alt aparte.

- Cell 0: título pasa a `S0–S6 + S1-alt` y "ocho escenarios".
- Cell 2: se descomenta la carga de `S0`.
- Nueva sección 9 (`md-sec9` + `code-entreno`): define `ENTRENO`, `dfsX_ent`, `dfsY_ent`, `dfsR_ent`
  como los siete escenarios S0 + S1–S6.
- Secciones 9/10/11 renumeradas a 10/11/12.
- Cells de LOSO (crudo y rango) y demo de split aleatorio usan el conjunto `_ent`.
- Nueva sección 13 (`md-sec13` + `code-s1alt`): comparación S1 vs S1-alt por medianas del rango y
  evaluación de S1-alt como test con los siete escenarios de entrenamiento.
- Cell 9: el reparto de etiquetas ahora nombra S0 sin ataques y el 75 % de S6.

**Pendiente:** los outputs del notebook quedaron viejos (fueron ejecutados sin S0). Hay que re-ejecutar.
**Bloqueante resuelto (L6):** se crearon `Colab/src2/eda.py` (`rango_movil_escenarios`, `primer_ataque_sostenido`,
`tabla_nulos`) y `Colab/src2/eval.py` (`loso`). Las importaciones de la cell 2 resuelven y el notebook corre.
No se tocó la imputación (media global vs mediana por fold), ni la promesa de deriva de la sección 6,
ni la sección de columnas no-medición.
