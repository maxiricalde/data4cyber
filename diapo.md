# Defensa — Detección y clasificación de ciberataques en un sistema de gestión de energía distribuida

**Trabajo Integrador · Métodos Cuantitativos para la Toma de Decisiones 2026 · UNSa**
Integrantes: Cruz Pablo Danilo · Ricalde Maximiliano Jeremías

> Estructura de defensa oral de **25 minutos · 19 slides · 6 bloques**.
> Métricas supervisadas (recall, espec S0, accuracy train, accuracy test) tomadas de `SUPERVISADO.ipynb`. Sin AUC.

---

## Cronograma (25:00)

| Bloque | Tema | Ventana | Slides |
|---|---|---|---|
| 0 | Apertura | 0:00–0:40 | 1 |
| 1 | Problema y motivación | 0:40–4:00 | 3 |
| 2 | Los datos | 4:00–7:15 | 2 |
| 3 | Metodología | 7:15–12:00 | 4 |
| 4 | Resultados | 12:00–18:15 | 4 |
| 5 | Discusión | 18:15–21:15 | 2 |
| 6 | Cierre | 21:15–25:00 | 3 |

---

## Bloque 0 — Apertura (0:00–0:40)

### Slide 1 — Título
- "Detección y clasificación de ciberataques en un sistema de gestión de energía distribuida mediante aprendizaje automático".
- Integrantes: Cruz, Ricalde · Métodos Cuantitativos 2026 · UNSa.
- Gancho hablado: *"¿Qué pasa cuando alguien le miente al sistema que controla la energía de una planta solar?"*

---

## Bloque 1 — Problema y motivación (0:40–4:00)

### Slide 2 — La amenaza
- Generación distribuida = superficie de ataque: comandos falsos a inversores (Modbus), mediciones falsificadas, manipulación de precio.
- Es un ataque a la **física** de la planta, no solo a los datos.

### Slide 3 — Motivación y el hueco (gap)
- Dataset reciente (Panasonic/Fraunhofer); antecedentes: artículo del dataset + GRIDGUARD-AI (RF, CNN temporal, autoencoder).
- **Aporte propio**: nadie aplicó clustering (K-Means/DBSCAN/BIRCH), SVM ni XGBoost; **nadie hizo reducción de columnas / importancia de variables**; **nadie tuneó hiperparámetros** sobre este dataset.

### Slide 4 — Objetivos
- General: detectar y clasificar ciberataques desde la telemetría.
- Específicos: (1) detectar ataque, (2) clasificar el tipo, (3) comparar aprendizaje supervisado vs no supervisado.

---

## Bloque 2 — Los datos (4:00–7:15)

### Slide 5 — Data4Cyber en una tabla
- **14.354 filas** (1 fila/segundo), **8 escenarios**, **157 columnas → 132 features** tras limpiar.
- Tabla S0–S6 con filas y % de ataque (la del PDF).
- Mensaje: S0 es el único escenario 100% limpio.

### Slide 6 — Calidad y trampas de los datos
- Balance: **6.768 benignas / 7.586 ataques** (≈47/53), sin desbalance fuerte.
- Nulos: **0,89% de celdas**, imputación por media.
- Fugas eliminadas: `attack_phase`, `attack_phase_all`, `timestamp`, `MQTT-Price-Signal`, `Profile.*`.
- Frase: *"los datos esconden el tiempo, y el tiempo predice el ataque"* (detalle en Slide 15).

---

## Bloque 3 — Metodología (7:15–12:00)

### Slide 7 — El protocolo correcto: LOSO
- LOSO (dejar un escenario entero afuera) vs CV aleatoria (mezcla segundos del mismo escenario → fuga temporal).
- Número ancla (Crudo): **accuracy train 0,998 vs accuracy test 0,497**.
- Mensaje: modelo "perfecto" en train que no generaliza.

### Slide 8 — Rango móvil + reducción + RFE
- Rango móvil **120 s** (dinámica, no nivel instantáneo).
- Escalera: crudo (132) → corr (50) → PCA (19) → **block_pca (37)** → RFE (80).
- Tabla B (RF fijo sobre rango):

| Reducción | Features | recall | espec S0 | acc train | acc test |
|---|---|---|---|---|---|
| ninguna | 132 | 0,626 | 0,561 | 0,999 | 0,719 |
| corr | 50 | 0,604 | 0,507 | 0,999 | 0,701 |
| pca | 19 | 0,641 | 0,417 | 0,999 | 0,690 |
| **block_pca** | **37** | 0,629 | 0,461 | 0,999 | **0,705** |

- RFE (80) queda por debajo (acc test ≈0,680) → se descarta.

### Slide 9 — Tuneo de hiperparámetros en dos etapas
- **Etapa 1 — Random Search**: exploración amplia (RF `n_iter=30`, CatBoost `20`) sobre LOSO.
- **Etapa 2 — Grid Search**: refinamiento fino alrededor de la mejor configuración.
- Selección sobre LOSO; validación final en **holdout S1-alt**.

### Slide 10 — Modelos y evaluación
- RF, XGBoost, CatBoost × reducciones de la Slide 8.
- Train LOSO (7 escenarios) + holdout final **S1-alt** (nunca visto).
- Métricas: **recall, espec S0, accuracy train, accuracy test**.

---

## Bloque 4 — Resultados (12:00–18:15)

### Slide 11 — Hallazgo 1: la dinámica gana
- Tabla A (RF, LOSO):

| Configuración | Features | recall | espec S0 | acc train | acc test |
|---|---|---|---|---|---|
| Crudo (niveles) | 132 | 0,225 | 0,349 | 0,998 | 0,497 |
| **Rango móvil 120 s** | 132 | **0,537** | **0,561** | 0,999 | **0,719** |
| Ventana deslizante 20 s | 2640 | 0,249 | 0,333 | 0,999 | 0,510 |

- Mensaje: sube test (0,497 → 0,719) sin subir train → la ventana temporal reduce el sobreajuste.

### Slide 12 — Hallazgo 2: reducir sin matar
- block_pca **132 → 37**: acc test **0,719 → 0,705**, recall **0,626 → 0,629**, espec S0 **0,561 → 0,461**.
- Honestidad: se pierde algo de especificidad, casi nada de accuracy/recall.

### Slide 13 — Supervisado + tuneo
- Tuneo LOSO (Tabla C):

| Modelo (etapa) | recall | espec S0 | acc train | acc test |
|---|---|---|---|---|
| RF (random) | 0,665 | 0,519 | 0,949 | **0,733** |
| XGB (random) | 0,637 | 0,537 | 0,914 | 0,720 |
| CatBoost (random) | 0,610 | 0,511 | 0,984 | 0,706 |
| RF (grid) | 0,656 | 0,512 | 0,884 | 0,729 |
| XGB (grid) | 0,608 | 0,556 | 0,862 | 0,710 |
| CatBoost (grid) | 0,638 | 0,560 | 0,848 | 0,729 |

- Holdout S1-alt (Tabla D):

| Modelo | recall | espec S0 | acc train | acc test |
|---|---|---|---|---|
| RF (random) | 0,926 | 0,519 | 0,930 | 0,777 |
| RF (grid) | 0,932 | 0,512 | 0,878 | 0,742 |
| **XGB (grid)** | **0,977** | 0,556 | 0,851 | **0,804** |
| CatBoost (grid) | 0,790 | 0,560 | 0,825 | 0,725 |

- Mensaje: el tuneo baja el gap train/test y sube test; el "ganador" depende del criterio (acc test LOSO → RF random; recall/holdout → XGB grid).

### Slide 14 — No supervisado: resultado honesto
- K-Means, Birch, DBSCAN entrenados solo con benigno. LOSO (recall / espec S0): Birch **0,416 / 0,925**; DBSCAN **0,405 / 0,934**; K-Means **0,334 / 0,996**.
- **ARI familia ≤ 0,292**, ataque/benigno **0,160** → el clustering **no tipifica ataques**; agrupa regímenes operativos.

---

## Bloque 5 — Discusión (18:15–21:15)

### Slide 15 — El tiempo es el confusor principal
- Las features **reconstruyen la posición temporal con R² 0,974–0,986**: el modelo puede acertar por ubicación, no por ataque.
- Al residualizar el tiempo, el clustering pierde señal en **6 de 7 folds**.
- Mensaje: sin control temporal, cualquier modelo funciona por la razón equivocada.

### Slide 16 — Contraste con los papers
- GRIDGUARD-AI vs vosotros: aportás LOSO honesto, reducción interpretable y el resultado negativo del clustering.
- Lo que tu trabajo demuestra y otros no reportan: el tamaño real del efecto del tiempo.

---

## Bloque 6 — Cierre (21:15–25:00)

### Slide 17 — Limitaciones
- S0 es el único escenario limpio; ataques anclados en franja temporal.
- El umbral **no transfiere** entre escenarios (recall se derrumba en S1-alt).
- Imputación global antes del split (fuga menor de estadísticos); decilo antes de que lo encuentren.

### Slide 18 — Conclusiones
- (1) Es detectable con supervisado + dinámica (acc test ~0,73; recall ~0,67 en LOSO).
- (2) Reducir a 37 features es viable (acc test 0,705).
- (3) El clustering no clasifica ataques y el tiempo domina.

### Slide 19 — Trabajo futuro y cierre
- **Más entrenamientos con la versión actualizada del dataset** (corrige la limitación de un solo escenario limpio).
- Umbral adaptativo por escenario; SVM como línea pendiente.
- Cierre con la frase del inicio + "Gracias, preguntas".

---

## Preguntas probables (preparadas)

1. **"¿Cuál es el mejor modelo?"** → Depende de la métrica: en LOSO, RF random lidera accuracy test (0,733) y recall (0,665); en holdout S1-alt, XGB grid lidera accuracy test (0,804) y recall (0,977).
2. **"¿Sirvió el tuneo?"** → Sí: baja el sobreajuste (RF acc train 0,999 → 0,949) y sube accuracy test (0,719 → 0,733) y recall (0,537 → 0,665) en LOSO.
3. **"¿Cómo evitan la fuga temporal?"** → LOSO + eliminación de `timestamp`/`profile` + rango por escenario. Prueba: acc train 0,998 vs acc test 0,497 en crudo.

---

## Fuente de métricas
- Slides 7, 8, 11 y 13 → `SUPERVISADO.ipynb` (celdas 10, 13, 20–25, 28–32, 34).
- Slide 14 → `NOSUPERVISADO.ipynb`.
- Slide 15 (R²) → EDA / no supervisado.
- **Sin AUC en ninguna slide.**
