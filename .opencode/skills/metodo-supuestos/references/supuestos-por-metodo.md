# Supuestos por familia de métodos

Checklist operativo. Para cada método: qué supuesto, con qué se verifica, y qué se hace si falla.
Nunca cambiar de método sin decirlo.

## Regresión lineal (OLS)

| Supuesto | Verificación | Si falla |
|---|---|---|
| Linealidad en parámetros | residuos vs. valores ajustados, gráficos de componentes | transformar predictores (log, cuadrático) o splines |
| Independencia de errores | Durbin-Watson, ACF de residuos si hay orden temporal | errores robustos agrupados, modelos de series |
| Homocedasticidad | Breusch-Pagan o White; embudo en residuos vs. ajustados | errores estándar robustos (HC3), WLS |
| Normalidad de residuos | QQ-plot, Shapiro (n<50), Anderson-Darling | bootstrap o errores robustos; NO descartar OLS por esto |
| Ausencia de colinealidad severa | VIF (>10 alerta), número de condición | eliminar/combiner variables, regularización |
| Sin puntos de influencia | distancia de Cook, leverage | reportar; nunca borrar outliers en silencio |
| n suficiente | n vs. cantidad de parámetros (regla: ≥10-15 por parámetro) | reducir modelo o regularizar |

## Tests de medias / ANOVA

| Supuesto | Verificación | Si falla |
|---|---|---|
| Independencia de observaciones | diseño del muestreo | modelo con estructura (mixtos, GEE) |
| Normalidad por grupo | QQ-plot por grupo o Shapiro; con n≥30 por grupo el TCL ayuda | Mann-Whitney / Kruskal-Wallis, bootstrap |
| Homogeneidad de varianzas | Levene o Bartlett | Welch t-test, Welch ANOVA |
| Tamaño de grupo | n por grupo | reportar potencia insuficiente |

## PCA

| Supuesto | Verificación | Si falla |
|---|---|---|
| Escalas comparables | comparar rangos y unidades por columna | estandarizar (media 0, desvío 1) |
| Estructura lineal | matriz de correlación, pares de variables | kernel PCA, o quedarse con descriptivo |
| Correlaciones no triviales | test de esfericidad de Bartlett, KMO | PCA no aporta; usar variables originales |
| Sin outliers extremos | distancia de Mahalanobis, boxplots | PCA robusta |

## Clustering (k-means)

| Supuesto | Verificación | Si falla |
|---|---|---|
| Escalas comparables | rangos por columna | estandarizar |
| Clusters esféricos y de tamaño similar | silhouette, comparar con jerárquico | DBSCAN, GMM, jerárquico |
| k elegido con criterio | codo + silhouette, no a ojo | documentar el criterio usado |

## Series temporales

| Supuesto | Verificación | Si falla |
|---|---|---|
| Estacionariedad | ADF y KPSS (contrastar), gráfico de la serie | diferenciar, transformar, modelar tendencia |
| Autocorrelación | ACF/PACF, Ljung-Box sobre residuos | agregar rezagos (ARIMA, SARIMA) |
| Estacionalidad | ACF estacional, descomposición | componente estacional explícita |
| Rupturas estructurales | test de Chow, inspección visual | modelar por tramos |

## Clasificación / ML supervisado

| Supuesto | Verificación | Si falla |
|---|---|---|
| Sin leakage | split ANTES de cualquier transformación; encoders ajustados dentro del train | rehacer el pipeline |
| Balance de clases | conteo por clase | pesos de clase, remuestreo, métricas adecuadas |
| Split representativo | aleatorio vs. temporal según el problema | split temporal o estratificado |
| n por clase suficiente | conteo por clase | reportar; reducir complejidad del modelo |

## Correlación y tablas de contingencia

| Método | Supuesto | Si falla |
|---|---|---|
| Pearson | relación lineal, sin outliers de peso | Spearman |
| Spearman | relación monótona | reportar como descriptivo |
| Chi-cuadrado | frecuencias esperadas ≥5, categorías excluyentes | test exacto de Fisher, agrupar categorías |

## Agregar un método nuevo

1. Agregar una sección con la misma tabla de tres columnas: supuesto, verificación, qué hacer si falla.
2. Incluir al menos un chequeo ejecutable, no solo conceptual.
3. No tocar `SKILL.md`: alcanza con que la familia esté acá.
4. Si el método no tiene supuestos formales, decirlo explícitamente y listar sus riesgos reales.
