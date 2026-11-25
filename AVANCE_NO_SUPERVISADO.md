# Avance — Parte no supervisada (Pilar I y Pilar II)

> Documento de continuidad para retomar en otra sesión. Última actualización: 2026-11-24.
> Proyecto: `tpfinal-colab` (TP Data4Cyber, Métodos Cuantitativos).

## 1. Contexto y objetivo

Detección de anomalías (ataques) en una planta fotovoltaica con batería, a partir de la
telemetría de 5 medidores AC. La parte no supervisada se organiza en pilares:

- **Pilar I**: invariantes físicos (consistencia entre magnitudes físicas).
- **Pilar II**: filtro anómalo no supervisado (KMeans, BIRCH, DBSCAN, Isolation Forest),
  entrenado solo con benigno, con umbral EVT/POT.
- **Pilar III**: interpretación de clusters (perfil z-score).
- **Pilar IV**: híbrido no supervisado + supervisado (complementar el supervisado).

**Reglas del proyecto vigentes**:
- Alcance estricto: solo lo pedido; análisis = solo lectura; no crear archivos no pedidos.
- Método/supuestos: declarar supuestos antes de codear; el agente escribe y **el usuario
  ejecuta los notebooks** (convención del proyecto).
- Artefactos técnicos en español neutro/profesional.

## 2. Entorno y datos

- **Python**: usar `.venv/bin/python`. Versiones: pandas 3.1.1, scikit-learn, scipy 1.18.1
  (`genpareto` disponible), nbformat 5.11.1. El `python3` del sistema NO tiene pandas.
  **UMAP no está instalado.**
- **Datos**: 8 escenarios `datasets/datasetS0.csv … datasetS6.csv` + `datasetS1alt.csv`
  (clave `"S1-alt"`). Cada escenario ≈ 30 min de un mismo día en horarios distintos
  (S0 13:19, S1 10:49, S3 16:15, S6 13:48). **Sin ciclo diurno.**
- **Features**: 155 columnas (156 en S6, con `MQTT-Price-Signal.event` extra). Tras
  `eliminar_columnas` quedan **132 features**; la función conserva `attack_active` y descarta
  Profile (irradiancia/temperatura/carga), realtime, phase_seq, MQTT.
- **Semántica ARI** (para clustering): ARI = 1 → el clustering IGUALA la partición de
  referencia (malo para tiempo); ARI ≈ 0 → independiente/desacoplado (bueno).
- **Columnas de entrada para invariantes** (todas presentes): ΔSOC
  (`Battery-SOC-Reported.soc_value` − `Battery-SOC-Reference.soc_value`) y, por cada medidor
  `BSS-Inverter-AC-Meter`, `Load-A-AC-Meter`, `Load-B-AC-Meter`, `PV-Inverter-AC-Meter`,
  `Substation-AC-Meter`:
  - `S_error = sqrt(p_sum3² + q_sum3²) − s_sum3`
  - `imbalance = max(|uln1−uln2|, |uln2−uln3|, |uln3−uln1|)`

## 3. Pilar I — invariantes físicas (HECHO)

**Notebook creado**: `Colab/PILAR1_INVARIANTES.ipynb` (10 celdas, todas compilan;
**NO ejecutado** — lo ejecuta el usuario). Reutiliza `src2` (`eliminar_columnas`,
`imputar_media`, `separar_variables`); no toca `NOSUPERVISADO.ipynb` ni `src2`.

**Pipeline verificado** (replicado en script aparte): invariantes → `SimpleImputer(median)`
→ **RobustScaler** → PCA(0.95) → KMeans (barrido K por silueta).

**Resultado con K = 3 (el mejor)**:
- Silueta **0.969**, Davies–Bouldin **0.118**.
- Tamaños de cluster: **[12389, 602, 1363]**.
- Interpretación (perfil z-score): **C0 = operación normal (~86 %)**;
  **C1 = inconsistencia de Load A/B (602 filas = exactamente S4)**;
  **C2 = inconsistencia de PV (1363 filas = S4+S5)**.
- ARI vs ataque **0.029**, vs escenario **0.036** → el clustering NO separa ataques ni
  escenarios (correcto: describe el régimen de operación).

**Hallazgos sobre invariantes** (importante):
- **ΔSOC es el más acoplado al tiempo** (ARI 0.37/0.35/0.46) → NO es un invariante puro; es
  un diferencial de SOC.
- **S_error** (ARI≈0) e **imbalance** (ARI 0.08–0.19) sí desacoplan el tiempo → son los
  invariantes útiles.
- `RobustScaler` es la escala correcta **para el clustering** (S_error tiene colas pesadas que
  inflan StandardScaler).

## 4. Pilar II — detector no supervisado (INVESTIGADO)

Protocolo común: **LOSO** sobre los 8 escenarios (`entrenar_fold`): se entrena solo con el
benigno de 7 escenarios, se calibra el umbral sobre el último 20 % benigno y se evalúa sobre el
escenario excluido. Score = distancia al prototipo (KMeans/BIRCH/DBSCAN) o `−score_samples`
(iForest). `r@1` / `r@5` = TPR al 1 % / 5 % de FPR (libres de umbral).

### 4.1 Representación × modelo × escala (media sobre 7 escenarios)

| Config | AUC | r@5 | recall | espec |
|---|---|---|---|---|
| rango + Std + Birch (baseline) | 0.710 | 0.198 | 0.415 | 0.863 |
| rango + Std + iForest | 0.635 | 0.143 | 0.467 | 0.745 |
| niveles + Std + Birch | 0.700 | 0.183 | 0.380 | 0.873 |
| invariantes + Std + Birch | **0.742** | 0.203 | 0.567 | 0.732 |
| invariantes + Std + iForest | 0.676 | 0.159 | 0.488 | 0.782 |
| invariantes + **Robust** + Birch | 0.663 | 0.228 | 0.341 | 0.922 |
| invariantes + Robust + iForest | 0.675 | 0.193 | 0.340 | 0.908 |

- **Mejor single**: `invariantes + StandardScaler + Birch` (AUC 0.742).
- **RobustScaler perjudica la DETECCIÓN** (0.663): domar los outliers borra la señal de ataque.
  Contraste clave: **Robust sirve para clustering, NO para detectar.**
- **iForest peor que Birch** en todos los casos.

### 4.2 Umbral EVT/POT — NO mejora

Implementado con `scipy.stats.genpareto` sobre la cola del score de calibración.

| Config | p95 rec/esp | POT q=0.05 | POT q=0.01 |
|---|---|---|---|
| rango (media) | 0.415 / 0.863 | 0.409 / 0.867 | 0.256 / 0.910 |
| invariantes (media) | 0.567 / 0.732 | 0.567 / 0.730 | 0.445 / 0.829 |

- **POT al 5 % ≈ p95** (mismo punto de operación); **POT al 1 % ≈ p99** (solo más estricto,
  uniforme; no se adapta por escenario).
- **Por qué no ayuda**: `r@1` / `r@5` son métricas libres de umbral. El “colapso”
  (S4 y S3 con r@5 = 0) es un problema de **ranking del score**, y ningún corte lo arregla.
  → Resultado honesto para el informe: *se implementó EVT/POT y se demostró que el cuello de
  botella no es el umbral sino el score.*

### 4.3 Fusión de representaciones

| Config | AUC | r@1 | r@5 | recall | espec |
|---|---|---|---|---|---|
| A · invariantes (elementales) | 0.742 | 0.096 | 0.203 | 0.567 | 0.732 |
| B · rango(invariantes) [secuencial] | 0.506 | 0.057 | 0.067 | 0.176 | 0.801 |
| C · rango(crudo)+inv [paralelo] | **0.756** | **0.231** | **0.256** | 0.574 | 0.818 |
| D · rango(crudo)+inv+rango(inv) | 0.719 | 0.200 | 0.218 | 0.532 | 0.821 |

- **Ganador: C (fusión en paralelo)** — AUC 0.756, r@5 0.256, espec 0.818.
  Se arma como `[rango_movil(nivelado, 120) | invariantes(nivelado)]` → imputer →
  **StandardScaler** → PCA(0.95) → Birch → distancia al prototipo.
- **B (secuencial: rango móvil SOBRE los invariantes) = azar** (AUC 0.506). El rango diluye la
  inconsistencia instantánea y retiene ruido benigno.
- **D (agregar lo secuencial a C) empeora** a C.
- Detalle de C por escenario (AUC / r@5):
  S1 0.86/0.32 · S1-alt 0.48/0.00 · S2 0.89/0.45 · S3 0.56/0.00 · S4 0.86/0.09 ·
  S5 0.95/0.75 · S6 0.69/0.18.
- Complementariedad: rango atrapa S6 (AUC 0.74 vs 0.40 de invariantes); invariantes atrapan
  S1/S4/S5.

### 4.4 Los benignos de score alto son REALES

| | S4 | S3 |
|---|---|---|
| % ataque | 70 % (1257/1798) | 51 % (912/1800) |
| Rachas benignas (mediana filas) | 13 | 21 |
| Rachas de ataque (mediana filas) | 389 | 11 |
| Benignos top-5 % aislados | 0 % | 0 % |

- **No se pueden trimear**: son mediciones reales; borrarlos es hacer trampa con la métrica
  (esconde falsos positivos que ocurrirían en producción).
- **Tampoco sirve un debounce/persistencia**: en S3 las rachas benignas (mediana 21) son más
  largas que las de ataque (mediana 11) → filtraría ataques breves y empeoraría.

### 4.5 Conclusión del Pilar II

El no supervisado tiene un **techo real a bajo FPR**: los benignos contienen eventos de score
alto reales que se solapan con ataques. Ni trimear ni persistencia lo arreglan de forma
legítima → **justifica el híbrido (Pilar IV)**.

## 5. Próximos pasos (dónde retomar)

1. **Prototipo del híbrido (Pilar IV)**:
   - **Etapa 1 (no supervisada = C)**: score `rango+invariantes` → banda `SAFE` (score bajo) /
     `DUDOSO` (score alto), calibrada para alta especificidad en `SAFE`.
   - **Etapa 2 (supervisada)**: el clasificador supervisado existente, aplicado **solo a los
     `DUDOSO`**.
   - **Métricas**: cobertura del embudo (¿la etapa 1 deja pasar todos los ataques en `DUDOSO`?),
     carga de la etapa 2 (% `SAFE`), precisión final del híbrido vs cada etapa sola.
2. **Pregunta abierta (pendiente de definir con el usuario)**: ¿la etapa 2 predice el
   **escenario/ataque concreto** (S1…S6) o una **etiqueta binaria ataque/no-ataque**? Define
   cómo se mide la etapa 2.

## 6. Cómo reproducir

- Ejecutar con `.venv/bin/python`. Patrón de imports (los notebooks agregan `Colab/` al path):

  ```python
  import sys; sys.path.insert(0, "Colab")
  from src2.data import eliminar_columnas, imputar_media
  from src2.features import rango_movil
  from src2.split import separar_variables
  from src2.unsupervised import (entrenar_fold, metricas, distancia_al_prototipo,
                                 escala_vecinos, elegir_k)
  ```

- Carga de escenarios: `S1-alt → datasets/datasetS1alt.csv`; el resto `datasets/datasetS{k}.csv`.
- Detector C: `SimpleImputer(median) → StandardScaler → PCA(0.95) → Birch(threshold=escala_vecinos(Z))`;
  score = `distancia_al_prototipo`; umbral = `np.percentile(score(calibración), 95)`.
- Nota: el notebook del Pilar I (`Colab/PILAR1_INVARIANTES.ipynb`) lo ejecuta el usuario
  (no se ejecutó en esta sesión).

## 7. Archivos relevantes

- `Colab/PILAR1_INVARIANTES.ipynb` — **nuevo** (Pilar I: invariantes + RobustScaler + KMeans
  K=3 + perfil z-score).
- `Colab/NOSUPERVISADO.ipynb` — notebook principal de no supervisado (no modificar).
- `Colab/SUPERVISADO.ipynb`, `Colab/EDA.ipynb`.
- `Colab/src2/data.py` — `eliminar_columnas`, `imputar_media`.
- `Colab/src2/split.py` — `separar_variables`, `aplanar_escenarios`.
- `Colab/src2/features.py` — `rango_movil`, `rango_escenarios`.
- `Colab/src2/unsupervised.py` — `Detector`, `entrenar_fold`, `metricas`,
  `distancia_al_prototipo`, `escala_vecinos`, `elegir_k`, `residualizar_tiempo`.
- `Colab/src2/train.py` — `recall_5`.
- `probe_pilar1.py` — probe temporal del Pilar I (raíz).
- `Adicionales/COLUMNS_BY_GROUP.md`, `Adicionales/DEVICES_es.md` — referencia de columnas y
  equipos.
- `datasets/datasetS0..S6.csv`, `datasets/datasetS1alt.csv`, `datasets/diccionario_borrador.csv`.
