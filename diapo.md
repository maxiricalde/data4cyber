# Defensa — Bloque no supervisado

**Trabajo Integrador · Métodos Cuantitativos para la Toma de Decisiones 2026 · UNSa**
Cruz, Pablo Danilo · Ricalde, Maximiliano Jeremías

> **9 secciones · ≈10:50 de contenido.** Narrativa: repaso → cambio de objetivo → invariantes → detector mejorado.
> Todos los números salen de la corrida **post-fix** de `NOSUPERVISADO.ipynb`. No usar `AVANCE_NO_SUPERVISADO.md` ni `INFORME_NO_SUPERVISADO.md` (corridas viejas, 11 features).

---

## Mapa de secciones

| # | Sección | Tiempo | Idea central | Fuente |
|---|---|---|---|---|
| 1 | Título | 0:30 | Detectar sin etiquetas, interpretar con física | — |
| 2 | Recordatorio | 1:45 | Detector sobre rango + intentos fallidos de ataque y familia | celdas 13, 19, 22 |
| 3 | Cambio de objetivo | 0:40 | Ya no buscamos clasificar ataques; buscamos conocimiento | — |
| 4 | Primer intento: 132 features | 1:00 | Fallido: silueta 1.000 por artefacto | celdas 25–28 |
| 5 | Leyes físicas → invariantes | 1:15 | Quitan el nivel absoluto y dejan la física | celda 33 |
| 6 | Clustering de invariantes | 1:15 | K=3, solo KMeans interpretable | celdas 34, 36 |
| 7 | Interpretación de clusters | 1:30 | Tres regímenes, dos anómalos | celdas 38, 39 |
| 8 | Detector mejorado | 1:30 | Las invariantes ganan; la fusión no aporta | celda 45 |
| 9 | Cierre | 0:45 | Limitaciones y puente al híbrido | — |

---

## 1 · Título (0:30)

- **Mensaje:** "Detectar sin etiquetas, interpretar con física."
- **Mostrar:** título e integrantes.
- **No mostrar:** números ni figuras.

---

## 2 · Recordatorio (1:45)

Repaso de la presentación anterior, en dos bloques. Rápido, sin re-explicar el protocolo.

### 2.1 · Detector sobre rango

- **Mensaje:** entrenado solo con benigno y evaluado en el escenario que nunca vio, separa en S2/S4/S5 pero se cae en S1-alt y S3.
- **Mostrar:** barras de AUC por escenario (Birch, rango 120 s):
  S1 0.794 · *S1-alt 0.488* · S2 0.919 · S3 0.626 · S4 0.918 · S5 0.912 · S6 0.792.
- **Resumen global:** AUC 0.778 · r@5 0.312 · recall 0.311 · espec S0 1.000.
- **Confusor temporal:** R² posición 0.973–0.986; r@5 = 0 en S1-alt y S3.

### 2.2 · Intentos fallidos: clusterizar ataque y tipo de ataque

- **Mensaje:** el clustering no recupera ni la familia ni el escenario.
- **Mostrar:** ARI familia: KMeans k=3 **0.292** · k=8 0.100 · Birch 0.012 · DBSCAN 0.008; ARI escenario ≤ 0.205; ataque/benigno (k=2) 0.160.
- **No mostrar acá:** la dispersión de balance; pertenece a la interpretación (§7).

---

## 3 · Cambio de objetivo (0:40)

- **Mensaje:** *"Dejamos de pedirle al clustering que separe ataques; le pedimos estructura."*
- **Mostrar:** el giro en una línea: de **clasificar ataque/familia** a **buscar conocimiento** en el dataset.
- **Frase de transición:** *"Si no tipifica ataques, ¿qué nos dice? Vamos a buscar qué conocimiento hay."*

---

## 4 · Primer intento: 132 features (1:00)

- **Mensaje:** sobre las 132 columnas crudas, el clustering no interpreta nada.
- **Mostrar:** K=2, silueta **1.000**, Davies–Bouldin 0.014; un cluster de **231 filas (1.6 %)** domina la partición. KMeans ARI ataque 0.005 · escenario 0.000.
- **Lectura:** la silueta perfecta es artefacto de un cluster diminuto; `peso_min` lo desenmascara. Los grupos no describen ningún régimen físico.
- **Frase:** *"Una silueta alta no es interpretabilidad."*

---

## 5 · Leyes físicas → invariantes (1:15)

- **Mensaje:** reducimos de 132 crudas a **13 invariantes** que quitan el nivel absoluto y dejan la física.
- **Mostrar (las 13):**
  - **ΔSOC**: |reportado − referencia| (1).
  - **S_error** por medidor: √(P²+Q²) − S — ley del triángulo de potencias (5).
  - **imbalance** por medidor: máximo desbalance entre fases (5).
  - **balance_p** y **balance_q**: subestación − suma de ramas (2).
- **Lectura:** el ataque es una inconsistencia **instantánea**; estas magnitudes la exponen.

---

## 6 · Clustering de invariantes (1:15)

- **Mensaje:** con invariantes, K por codo y silueta = **3**, y solo KMeans describe regímenes.
- **Mostrar:** la tabla de modelos sobre invariantes:

| modelo | clusters | silueta | DB | ARI ataque | NMI escenario |
|---|---|---|---|---|---|
| **KMeans** | **3** | **0.971** | 0.117 | 0.029 | 0.204 |
| Birch | 828 | 0.630 | 0.122 | 0.001 | 0.246 |
| DBSCAN | 394 | 0.202 | 1.824 | 0.033 | 0.259 |

- **Lectura:** Birch y DBSCAN fragmentan en cientos de clusters; CH se dispara (Birch 9.1e14), no mide calidad.

---

## 7 · Interpretación de clusters (1:30)

- **Mensaje:** tres regímenes; dos son anomalías físicas concretas.
- **Mostrar:**
  - Heatmap de z del centroide + plano de balance coloreado por cluster.
  - **C0 · 12.389 (86 %)**: operación normal, z ≈ 0.
  - **C1 · 602 (4 %)**: S_error alto en Load A y Load B (z ≈ 3.9 y 3.4). Es exactamente **S4**.
  - **C2 · 1.363 (9.5 %)**: S_error alto en PV (z ≈ 2.5). Se reparte entre **S4 y S5**.
- **Control:** ARI ataque 0.029 · ARI escenario 0.036 → el clustering describe física, no sigue etiquetas.

---

## 8 · Detector mejorado (1:30)

- **Mensaje:** el mismo hallazgo —las invariantes— sirve para detectar, no solo para interpretar.
- **Mostrar:** tres columnas con AUC.

| representación | features | AUC | r@5 | recall | espec S0 |
|---|---|---|---|---|---|
| rango móvil 120 s | 132 | 0.778 | 0.312 | 0.311 | 1.000 |
| **invariantes** | **13** | **0.796** | 0.392 | 0.557 | 0.954 |
| rango + invariantes | 145 | 0.790 | 0.398 | 0.326 | 0.993 |

- **Lectura honesta:** el salto está en rango → invariantes; la fusión suma r@5 (+0.006, ruido) y especificidad, pero pierde AUC y recall. Invariantes solas es el titular.
- **Caveat:** S1-alt sigue en r@5 ≈ 0; ese techo a bajo FPR justifica el híbrido.

---

## 9 · Cierre (0:45)

- **Limitaciones:** S1-alt; el umbral no transfiere; un solo seed; S0 es el único limpio.
- **Propuestas:** híbrido SAFE/DUDOSO con supervisado sobre los DUDOSO; umbral adaptativo; más escenarios limpios.
- **Cierre:** *"Las invariantes sirven para interpretar y para detectar; el techo del no supervisado es lo que pide el híbrido."*

---

## Preguntas probables

1. **"¿Por qué el baseline falla en S3 si el AUC es 0.626?"** → el score no ordena a bajo FPR; no es el umbral.
2. **"¿Por qué el crudo dio silueta 1.000?"** → un cluster de 231 filas; `peso_min` lo desenmascara.
3. **"¿Por qué NMI > 0 si no hay asociación?"** → NMI no está corregida por azar; el control limpio es ARI.
4. **"¿Qué aporta la fusión?"** → r@5 +0.006 (ruido); no justifica 145 features.
5. **"¿Por qué no usan las etiquetas?"** → usarlas sería supervisado; acá son solo control.

---

## Notas de producción

- `presentacion.html` todavía tiene la versión de 7 secciones; **falta regenerarlo** para estas 9 secciones (pendiente).
- El control de tiempo (celda 19) tiene salida vieja: re-ejecutar 13 → 19 antes de usarlo en el repaso.
- Si cambia un número en el notebook, actualizarlo en las secciones 2, 4, 6, 7 y 8 de este archivo.
