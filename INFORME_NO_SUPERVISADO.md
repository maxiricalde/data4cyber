# Clustering no supervisado con invariantes ciberfísicas — proceso y resultados

> Documento de informe de la parte no supervisada. Cubre desde el dataset y la
> transformación de columnas hasta los resultados del clustering y su lectura
> física. Complementa `AVANCE_NO_SUPERVISADO.md` (continuidad de sesión).

## 1. El dataset en una frase

**Data4Cyber** es un testbed de una planta fotovoltaica con batería. Se registra
la telemetría de **5 puntos de medición AC** (tres medidores físicos Janitza UMG508
que exponen cinco puntos lógicos por Modbus) más el estado de carga (SOC) de la
batería. Cada fila es un segundo, y la etiqueta `attack_active` marca si en ese
instante hay un ataque en curso.

- **8 escenarios**: `S0` (limpio, 100 % benigno) y `S1`, `S1-alt`, `S2`, `S3`,
  `S4`, `S5`, `S6` con ataques. Cada escenario son ~30 min de un mismo día.
- **Familias de ataque**: Modbus/Industroyer (`S1`, `S1-alt`, `S2`), ARP/MitM
  (`S3`, `S4`, `S5`) y cadena de suministro MQTT (`S6`).
- **Features**: tras `eliminar_columnas` (descarta `Profile.*`, `realtime`,
  `phase_seq`, `MQTT-Price-Signal`, `timestamp`, fases de ataque) quedan
  **132 features**.

El objetivo de esta parte **no** es detectar ataques (eso es el detector
one-class del Pilar II), sino **clusterizar el dataset completo** (benignos y
ataques) y ver qué estructura emerge, interpretándola en términos físicos.

## 2. Por qué invariantes y no las 132 columnas crudas

Las columnas crudas están dominadas por el **nivel absoluto**: cuánta potencia
fluye, qué tan cargada está la batería, en qué momento del día se está. Si se
clusteriza sobre eso, los grupos resultan **regímenes de operación** (SOC alto,
reactiva baja, etc.) que cruzan el tiempo y los escenarios, pero no cuentan una
historia física limpia.

Las invariantes son cantidades que **deben valer ≈ 0 en operación normal** y se
apartan de 0 cuando una ley física se viola. Al quitar el nivel absoluto, el
clustering se desacopla del tiempo (ARI ≈ 0) y lo que emerge es *dónde* y *qué*
ley se rompe.

## 3. La transformación: de 132 columnas a 11 invariantes

Se reducen las 132 columnas a **11 features** agrupadas en tres familias. Las
columnas fuente son 32: las 6 señales por medidor (`p_sum3`, `q_sum3`, `s_sum3`,
`uln1`, `uln2`, `uln3`) × 5 medidores, más las 2 de SOC.

### 3.1 ΔSOC — consistencia del estado de carga (1 feature)

```
dsoc = | Battery-SOC-Reported.soc_value − Battery-SOC-Reference.soc_value |
```

La batería reporta dos valores de SOC. Si el sistema es consistente, coinciden
y `dsoc ≈ 0`. Un valor grande marca discrepancia en el almacenamiento.

> Nota: el análisis previo mostró que `dsoc` es el invariante **más acoplado al
> tiempo** (ARI 0.37); los útiles para desacoplar son `serror` e `imbalance`.

### 3.2 S_error — residuo de potencia aparente (5 features)

```
S_error = √( p_sum3² + q_sum3² ) − s_sum3
```

Es la **ley del triángulo de potencias** (`S² = P² + Q²`). Un medidor sano la
satisface, así que `S_error ≈ 0` (unos VA de error numérico). Un `|S_error|`
grande significa que P, Q y S no cierran: inconsistencia interna del instrumento
(armónicos, falla o valores falseados).

### 3.3 Imbalance — desequilibrio de fase (5 features)

```
imbalance = max( |uln1 − uln2|, |uln2 − uln3|, |uln3 − uln1| )
```

En una red trifásica balanceada las tres tensiones fase-neutro son iguales. Esto
mide la máxima diferencia entre pares de fases: `≈ 0` V = balanceado; grande =
calidad de tensión degradada en ese punto.

### 3.4 Los 5 medidores

Los 5 puntos lógicos de medición, sobre 3 medidores físicos:

| Punto lógico | Medidor físico | Rama que mide |
| --- | --- | --- |
| `BSS-Inverter-AC-Meter` | umg6c unit 3 | Conexión AC del inversor de **batería** |
| `Load-A-AC-Meter` | umg6c unit 4 | **Carga A** |
| `Load-B-AC-Meter` | umg7a unit 2 | **Carga B** |
| `PV-Inverter-AC-Meter` | umg7a unit 3 | Conexión AC del inversor **PV** |
| `Substation-AC-Meter` | umg_ront unit 1 | **Subestación / PCC** |

Las 11 columnas finales son: `dsoc`, y por cada medidor `{medidor}__serror` y
`{medidor}__imbalance` (1 + 5 + 5).

## 4. Pipeline

```
X_inv (11 features)
  → SimpleImputer(median)
  → RobustScaler
  → PCA(n_components=0.95)
  → Z_inv
```

- **RobustScaler (mediana + IQR) y no StandardScaler**: los invariantes tienen
  colas pesadas (los valores normales rondan 0 y los fallos se disparan).
  StandardScaler se infla con esos outliers y aplasta la estructura; RobustScaler
  es la escala correcta **para clustering** (lo opuesto a detección, donde domar
  los outliers borra la señal de ataque).
- **PCA al 95 %**: sobre 11 features deja pocas componentes y limpia ruido.

## 5. Elección de K

Para KMeans se barre `K = 2..10` con dos criterios:

- **Codo**: la inercia (suma de distancias al centroide) siempre baja al agregar
  grupos; el codo es el K donde la caída deja de ser marcada.
- **Silueta**: calidad de separación (arriba mejor), confirmando el mismo K.

Se elige `K = argmax silueta`. El resultado documentado es **K = 3**.

## 6. Comparación de modelos y métricas

Tres modelos sobre la misma `Z_inv`, con la misma escala para Birch/DBSCAN:

| Modelo | Parámetros |
| --- | --- |
| KMeans | `n_clusters=K`, `n_init=10`, `random_state=42` |
| Birch | `threshold=escala_vecinos(Z)`, `n_clusters=None` |
| DBSCAN | `eps=escala_vecinos(Z)`, `min_samples=5` |

`escala_vecinos` es la distancia típica al 5º vecino (percentil 90). Métricas:

- **Silueta** (arriba mejor) y **Davies–Bouldin** (abajo mejor): calidad del
  agrupamiento.
- **ARI contra ataque y contra escenario**: control de que el clustering **no**
  esté siguiendo esas etiquetas (se espera ≈ 0).
- **`peso_min`** (tamaño del cluster más chico): guardia contra el artefacto en
  que un cluster diminuto y compacto infla la silueta sin describir un régimen.

Se elige el ganador por silueta entre los modelos con al menos dos clusters no
residuales (`peso_min ≥ 1 %`).

## 7. Interpretación de los clusters

La lectura se hace con el **z-score del centroide**:

```
z = (media del cluster − media global) / desvío global
```

Un `|z|` alto marca la variable que **define** el cluster. Se calcula sobre las
unidades originales (no escaladas) y se apoya en tres gráficos:

1. **Heatmap** clusters × invariantes (color = z).
2. **Boxplots** de los 3 invariantes más discriminantes por cluster (escala
   symlog, porque las colas de `S_error` aplastan el eje lineal).
3. **Scatter** de los 2 invariantes más discriminantes, ejes en unidades
   originales y color por cluster.

Además, el **crosstab cluster × escenario** conecta cada grupo con su origen
físico (ej.: "este cluster es S4 puro").

## 8. Resultados obtenidos

### 8.1 Benchmark de representaciones (dataset completo)

KMeans con K óptimo por silueta, comparando representaciones:

| Representación | K | Silueta | ARI ataque | ARI escenario |
| --- | --- | --- | --- | --- |
| Niveles (132 crudas) | 7 | 0.237 | 0.102 | 0.106 |
| Rango móvil 120 s | 2 | 0.238 | 0.161 | 0.030 |
| Diferencias (ΔX) | 2 | 0.826* | 0.001 | 0.000 |
| **Invariantes (RobustScaler)** | **3** | **0.969** | **0.029** | **0.036** |

\* El 0.826 de "diferencias" es un **artefacto**: aísla un 2.8 % de filas con
saltos bruscos de señal, no un régimen, y no está enriquecido en ataque.

Ninguna representación separa ataques (ARI ≤ 0.16 en todas) — correcto y
esperado: el ataque no forma clusters densos, lo que justifica el enfoque
one-class del Pilar II.

### 8.2 Mejor clustering

Con el pipeline de invariantes, el mejor resultado documentado es:

- **Modelo**: KMeans con **K = 3**.
- **Silueta 0.969**, **Davies–Bouldin 0.118**.
- **Tamaños**: `[12389, 602, 1363]` (ningún grupo residual).
- **ARI ataque 0.029**, **ARI escenario 0.036** → el clustering no sigue al
  tiempo ni al escenario; describe el régimen físico.

### 8.3 Los clusters en lectura física

Perfil z-score de los tres grupos:

| Cluster | n | Lectura física |
| --- | --- | --- |
| C0 | 12389 | **Operación normal** (~86 %): todos los invariantes cerca de 0 |
| C1 | 602 | **Inconsistencia de Load A/B** (coincide con S4) |
| C2 | 1363 | **Inconsistencia de PV** (coincide con S4+S5) |

Es decir, el clustering de invariantes separa el tráfico por **qué ley física se
viola y en qué medidor**, no por hora ni por familia de ataque.

### 8.4 Detección (complemento, Pilar II)

Las mismas invariantes, usadas como score one-class, también llevan señal de
ataque: **AUC 0.742** (mejor representación individual), y la fusión
`rango(crudo) + invariantes` alcanza **AUC 0.756**. Para detectar se usa
`StandardScaler` (RobustScaler baja a 0.663 porque doma la señal de ataque).

## 9. Estado y cómo reproducir

- **Notebook**: `Colab/NOSUPERVISADO.ipynb`, sección **6.4 "Mejor clustering con
  invariantes físicas (todo el dataset)"** (celdas de transformación, estudio de
  K, comparación de modelos, perfil z-score y gráficos).
- **Módulo auxiliar**: `Colab/src2/interpretationNS.py` con `zscore_columnas`,
  `perfil_clusters`, `tabla_clusters_escenario`, `resumen_clustering` y
  `nombre_legible`.
- **Ejecución**: con `.venv/bin/python` (el `python3` del sistema no tiene pandas).

> Estado: la sección 6.4 está escrita y lista para ejecutar. Los números de la
> sección 8 provienen del análisis previo documentado en `AVANCE_NO_SUPERVISADO.md`
> (§3 y §4); el usuario ejecuta los notebooks, no el agente.
