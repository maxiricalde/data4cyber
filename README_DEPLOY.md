# Deploy portable

Predicción sobre un CSV crudo usando los modelos entrenados, sin depender del
proyecto ni de `src2/`. El paquete se compone de dos archivos:

| Archivo | Rol |
| --- | --- |
| `modelo_deploy.pkl` | Datos: modelos XGBoost y Birch + preproceso ya ajustado. **No es un ejecutable.** |
| `deploy_portable.py` | El programa que carga el `.pkl` y predice. Esto es lo que se ejecuta. |

> `modelo_deploy.pkl` no se corre solo: es un objeto Python serializado que el
> script abre. Pensalo como un `.zip` con estructura, no como un `.exe`.

## Requisitos

- Python 3.9 o superior.
- Las librerías `pandas`, `numpy`, `scikit-learn` y `xgboost`.
  Versiones probadas: pandas 3.1.1, numpy 2.5.4, scikit-learn 1.9.1, xgboost 3.4.1.

## Pasos

### 1. Crear una carpeta y copiar los archivos

```bash
mkdir mi_deploy && cd mi_deploy
cp /ruta/al/proyecto/modelo_deploy.pkl .
cp /ruta/al/proyecto/deploy_portable.py .
cp /ruta/al/dataset_que_quiero.csv .        # el CSV crudo a puntuar
```

### 2. Preparar el entorno (una sola vez)

```bash
python -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install pandas numpy scikit-learn xgboost
```

### 3. Ejecutar

```bash
python deploy_portable.py dataset_que_quiero.csv --salida pred.csv
```

También se puede correr sin `--salida` para ver un resumen por pantalla:

```bash
python deploy_portable.py dataset_que_quiero.csv
```

## Salida

`pred.csv` tiene una fila por segundo y tres columnas:

| Columna | Significado |
| --- | --- |
| `prob_ataque_xgb` | Probabilidad de ataque del modelo supervisado (XGBoost). |
| `score_birch` | Distancia al prototipo benigno más cercano (detector no supervisado). |
| `flag_birch` | `1` si el score supera el umbral calibrado (marcado como ataque), `0` si no. |

## Formato del CSV de entrada

- Debe tener el **mismo formato crudo** que `datasetS*.csv`, incluyendo las
  columnas `attack_phase`, `attack_phase_all` y `timestamp`. El preproceso las
  necesita para descartarlas; si falta alguna, el script falla con `KeyError`.
- Las filas deben estar **en orden temporal**: el rango móvil es una ventana de
  120 segundos sobre filas consecutivas, así que un CSV desordenado produce
  resultados sin sentido.

## Uso desde Python

Además de la línea de comandos, se puede importar la función:

```python
from deploy_portable import predecir

pred = predecir("dataset_que_quiero.csv", pkl_path="modelo_deploy.pkl")
print(pred.head())
```
