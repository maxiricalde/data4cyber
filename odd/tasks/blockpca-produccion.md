# blockpca-produccion

Objetivo: `block_pca` pasa a ser la receta que sale a producción en el modelo supervisado, de punta a punta (bundle, `src/predict.py`, cuaderno 02).
Branch: `main` (sin branch propia; los commits son por unidad de trabajo). Entrega: una sola PR/commit chain corto. Runner: `TPFinal/.venv/bin/python` (Python 3.14.4, versiones de `requirements.txt`).

## Specs

- **S1.** El modelo supervisado que sale a producción usa la reducción `block_pca`. Cita del usuario: *"decidimos que el que va a salir a produccion es block PCA"*.
- **S2.** El criterio de la decisión es detectar más ataques, y el cuaderno lo declara así. Cita: *"debido a que las metricas a nuestro parecer son mejores identificando mas ataques que es lo mas importante"*.
- **S3.** La sección 4 del cuaderno 02 (entender las métricas con un ejemplo) se calcula sobre `block_pca`. Cita: *"la parte de de la seccion 4 de supervisado deberia ser sobre blovk PCA"*.
- **S4.** (supuesto de honestidad, no pedido explícitamente) El texto deja escrito el costo de la decisión con números: especificidad en `S0` 0,815 contra 0,996, y recall@1% empatado (0,490 contra 0,489). Sin esto la elección no se puede defender.
- **S5.** Scope: solo el modelo supervisado. El bundle no supervisado (`unsupervised_reduced.joblib`, receta `physical_corr`) y el cuaderno 03 quedan como están.
- **S6.** (hecho) Cuantificar cuánto del rendimiento de `block_pca` depende de `Profile.*`: correr la ablación `block_pca` sin las 7 columnas de perfil con el mismo LOSO y comparar contra el `block_pca` con perfil. Resultado: sacar `Profile.*` no colapsa el modelo — empeora la transferencia a S0 (espec. 0,815→0,507, AUC 0,952→0,902), porque el perfil detrended aporta señal legítima del régimen, no fuga. El colapso real aparece con el crudo (sin `detrend`), no con el perfil.

Criterios de aceptación:
- `python -m src.production --variant block_pca` escribe `modelos/supervised_blockpca.joblib`.
- `python -m src.predict --model supervised --variant block_pca --csv datasets/datasetS6.csv` reproduce las alertas que muestra el cuaderno en la sección 5.
- El cuaderno 02 se ejecuta completo, sin celdas sin salida, y sus tablas coinciden con `resultados/blockpca_*.csv`.
- Chequeos: `python -m src.production --variant block_pca`, `python -m src.predict ...`, re-ejecución del cuaderno con `nbconvert`.

## Tasks

| ID | Spec | Ruta | Estado | Commit / evidencia |
| --- | --- | --- | --- | --- |
| T1 | S1 | inline | hecho | `BlockPCA` (fit/transform) + `block_pca()` como wrapper. Equivalencia con la implementación previa: `max|diff| = 0.0` en train y test para los folds S0, S3 y S6; `fit_transform` idéntico; dos `fit` seguidos dan la misma salida. |
| T2 | S1 | inline | hecho | `python -m src.production --variant block_pca` → `modelos/supervised_blockpca.joblib`, 40 componentes, 28 bloques. |
| T3 | S1 | inline | hecho | `src/predict.py` aplica `bundle["block_pca"].transform`. Smoke test de las variantes `base`, `reduced`, `block_pca` y `unsupervised --variant reduced`: todas corren sin error (sin regresión). |
| T4 | S1,S2 | inline | hecho | `predict --variant block_pca` sobre S6: 1.351 alertas (75,1%). Crosstab del bundle: 1.350 ataques detectados, 449/450 benignas correctas → 1.799/1.800. S0 con el bundle: 0 falsas alarmas (S0 está en el entrenamiento). |
| T5 | S2,S3,S4 | inline | hecho | Celdas 0, 45, 51, 63, 64, 67, 70, 71, 72, 76, 77, 78, 79, 80, 81, 83, 84, 85 reescritas. Números tomados de la corrida, no estimados: TP 952 / FP 11 / FN 398 / TN 439, exactitud 0,773, precisión 0,989, recall 0,705, espec. 0,976, F1 0,823, AUC 0,977, medianas 0,082 / 0,682, recall@5% FPR 0,955, S0 333 de 1.798. |
| T6 | S3 | inline | hecho | Cuaderno 02 re-ejecutado con `nbconvert`: 40/40 celdas de código con `execution_count` (las 2 sin salida son celdas de solo `def`). Las salidas coinciden con el texto nuevo. |
| T7 | S6 | inline | hecho | Ablación `block_pca` sin `Profile.*` (RF, LOSO, 300 árboles): espec. S0 0,507 y AUC 0,902 contra 0,815 / 0,952 con perfil. También `block_pca` + crudo (paper, 1 s): espec. S0 0,478, AUC 0,900. Resultado en `resultados/blockpca_ablacion.csv` y cuaderno 02 (sección 1.0). |

## Log

- **L1 (usuario, textual):** "el cauderno supervisado 2 no esta ejecutado no hay venv tampoco"
- **L2 (usuario, textual):** "creo que la parte de de la seccion 4 de supervisado deberia ser sobre blovk PCA que me dices?"
- **L3 (usuario, textual):** "decidimos que el que va a salir a produccion es block PCA debido a que las metricas a nuestro parecer son mejores identificando mas ataques que es lo mas importante"
- **L4:** Evidencia del estado inicial. Existe venv en `TPFinal/.venv` (un nivel arriba), con las versiones exactas de `requirements.txt`. El cuaderno 02 estaba 32/40 celdas con salida: faltaba la sección 3 entera (block_pca, celdas 51-61). Se ejecutó completo el 2026-11-19 y reproduce exacto los CSV `resultados/blockpca_*.csv`.
- **L5:** Trade-off medido (RF, LOSO, `resultados/reduccion.csv`): `physical_corr` AUC 0,943 / recall@5% 0,637 / recall@1% 0,489 / espec. S0 0,996; `block_pca` AUC 0,952 / 0,752 / 0,490 / 0,815. La ganancia está en la banda de 5% FPR y en el punto 0,5 (recall 0,705 contra 0,676); el costo es calibración en `S0` (~333 falsas alarmas contra 8 en 1.798 filas).
- **L6:** Decisión de scope: el no supervisado no se toca (S5). El cuaderno 03 declara que su variante reducida "no se recomienda", así que moverla sería un cambio sin pedido.
- **L7:** Hallazgo colateral: la celda final "Revisión de esta sección frente a la consigna" dice "tres modelos (Random Forest, SVM y XGBoost)" y "GridSearchCV", cuando la sección 3 ya tiene CatBoost y la 3.2 usa `LeaveOneGroupOut` con búsqueda manual. Se corrige junto con T5.
- **L8:** Risk line de la unidad: item 1 (cambio de formato de un artefacto persistido: el bundle de `modelos/` gana la clave `block_pca` con un transformador ajustado). Verificación: ejecución propia + un verificador independiente al cierre.
- **L9 (verificador independiente, 2026-11-19):** S1–S5 pass, sin bloqueantes. Evidencia: `max|diff| = 0.0` contra la implementación del commit base en los folds S3 y S6; bundle regenerado byte-idéntico; 40/40 celdas sin error; sin leakage (`transform` nunca reajusta; dos `transform` iguales y `fit` con otro subconjunto cambia la salida); `unsupervised_reduced.joblib` y el cuaderno 03 con hash igual al base.
- **L10 (correcciones post-verificación):** (a) el docstring de `src/reduce.py` decía que `physical_corr` era "the chosen recipe" y que `block_pca` "no es la receta que se envía": corregido. (b) `--model unsupervised --variant block_pca` fallaba con `FileNotFoundError`: ahora `parser.error` con mensaje explícito. (c) ayuda de `--variant` decía 41 columnas (promedio LOSO) donde el bundle produce 40. (d) **corrección de fondo**: la conclusión comparaba recall 0,705 contra 0,676 (fold S6) dentro de una lista de promedios. El promedio real de recall a umbral 0,5 es 0,798 (`block_pca`) contra 0,829 (`physical_corr`): con umbral fijo la receta física detecta un poco más, y la ventaja de `block_pca` aparece cuando el punto de operación se fija por presupuesto de falsos positivos (recall@5 % FPR 0,752 contra 0,637). Recalculado con el venv, no tomado del verificador.
- **L11:** Pendiente declarado: el repo no tiene suite de tests ni `pytest` en `requirements.txt`. El verificador dejó probes ejecutables; no se agregaron para no introducir infraestructura que el trabajo no pide.
- **L12 (usuario, textual):** "bien dejemos eso documentado como pendiente". Contexto: tras ver que `block_pca` usa las 7 `Profile.*` (4 en el bloque 9, 3 como singletons) y que la ablación de `physical_corr` colapsa al sacarlas (AUC 0,943→0,811, espec. S0 0,996→0,461), quedó abierta la decisión de si sacar el perfil. Decisión adoptada: **no sacarlo de la matriz comparativa** (cambiaría el input de todas las reducciones y la comparabilidad); agregar como variante honesta la ablación `block_pca` sin perfil y reportar ambos. Queda registrado como S6/T7 pendiente, sin autorizar aún.
- **L13 (2026-11-20):** S6/T7 cerrado. El usuario pidió "la comparación sin profile" y la variante con la ventana del paper (crudo, sin rango móvil). Se corrió con RF (el modelo de referencia; no los 4 modelos): `block_pca` sin `Profile.*` da espec. S0 0,507 y AUC 0,902 (con perfil 0,815/0,952), y `block_pca` + crudo da espec. S0 0,478 y AUC 0,900. Conclusión: el colapso de la transferencia a S0 no viene de `Profile.*` (que detrended aporta señal legítima), viene del **nivel crudo**; `block_pca` no reemplaza al `detrend` (reducción ≠ detrend).
- **L14 (2026-11-20):** Se agregó la sección 6 del cuaderno 02 ("La fuga de `Profile.*`") con la evidencia dura: las 7 columnas `Profile.*` tienen desvío 0.000 en S0 (congeladas) y varían en S1–S6; el rango móvil de `Profile.*` separa S0 de los ataques con AUC 0,988 pero no separa ataque/benigno dentro de un escenario (0,36). Conclusión: `Profile.*` es fuga de identidad de escenario (el paper no las usa: su baseline es un subset de 8 features — 5 potencias activas + SoC ref/reportado + precio MQTT). El número honesto de detección es sin-perfil (AUC 0,902, espec. S0 0,507). Re-ejecutado el cuaderno completo: 49/49 celdas de código, 0 errores (~865 s), incluidas las 3 celdas nuevas (sección 1.0 ventana, ablación block_pca, sección 6).
