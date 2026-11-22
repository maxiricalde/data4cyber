# Metodos Cuantitativos — Trabajo Integrador (Data4Cyber)

Detección de ataques en una planta fotovoltaica con batería a partir de las
mediciones de los ocho escenarios de Data4Cyber.

## Notebooks del trabajo

| Notebook | Qué hace |
| --- | --- |
| `notebooks/01_eda.ipynb` | Estructura del dataset, nulos, fugas y control temporal |
| `notebooks/02_supervisado.ipynb` | Columna vertebral: LOSO vs CV aleatoria y cuatro modelos sobre `block_pca` |
| `notebooks/02a_ventana.ipynb` | Rama: por qué rango móvil de 120 s y contraste con los dos papers |
| `notebooks/02b_reduccion.ipynb` | Rama: la escalera de reducción, RFE, PCA, `block_pca` y contexto |
| `notebooks/02c_hiperparametros.ipynb` | Rama: tuneo de CatBoost por LOSO anidado (no mejora) |
| `notebooks/03_no_supervisado.ipynb` | Detección de anomalías entrenada solo con tráfico benigno |
| `notebooks/04_identificar_escenarios.ipynb` | ¿El clustering identifica los escenarios? Contraste niveles vs dinámica |

## Cómo abrirlos en Google Colab

1. En Colab: *Archivo → Abrir notebook → GitHub*.
2. Pegá la URL de este repo y elegí el notebook.
3. Ejecutá la primera celda: clona el repo en `/content/data4cyber` y se para
   ahí. Una sola vez por sesión.

Los notebooks usan rutas relativas a la raíz del proyecto, así que también
funcionan clonando el repo y abriéndolos en Jupyter local.

## Contenido

```
datasets/    los 8 CSV de escenarios + README por escenario
src/         build_matrices, detrend, reducción de features y scripts
notebooks/   los notebooks del trabajo (columna vertebral + ramas)
resultados/  CSV con los resultados que los notebooks leen como evidencia
modelos/     modelos entrenados que se cargan con joblib
Colab/       notebooks de la cursada (material de referencia)
Adicionales/ documentación de dispositivos y métricas de Data4Cyber
```

## Entorno

Colab ya trae `pandas`, `numpy`, `scikit-learn`, `scipy`, `matplotlib`, `joblib`
y `xgboost`. **`catboost` no viene preinstalado**: la primera celda del notebook
02 lo instala sola (`pip install catboost`). `requirements.txt` documenta las
versiones usadas para reproducir el entorno en una máquina local.
