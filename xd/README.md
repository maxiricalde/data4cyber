# Deploy supervisado (XGBoost) — ejecución independiente

Predictor standalone que carga un `.pkl` con el modelo XGBoost ya entrenado y
escribe un CSV con la probabilidad de ataque. No necesita el repo, `src2/` ni
`datasets/`.

## Camino rápido

1. Copiá estos archivos a una carpeta:

   ```bash
   mkdir mi_deploy && cd mi_deploy
   cp /ruta/a/xd/deploy_supervisado.py .
   cp /ruta/a/xd/modelo_deploy.pkl .
   cp /ruta/a/dataset.csv .
   ```

2. Creá el entorno e instalá dependencias:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install pandas numpy scikit-learn xgboost
   ```

3. Predecí:

   ```bash
   python deploy_supervisado.py dataset.csv --pkl modelo_deploy.pkl --salida pred.csv
   ```

4. Verificá:

   ```bash
   head pred.csv
   ```

   Tiene que tener las columnas `prob_ataque_xgb` y `ataque_xgb`.

## Archivos

| Archivo | Rol |
| --- | --- |
| `deploy_supervisado.py` | Predictor. |
| `modelo_deploy.pkl` | Modelo XGBoost + preproceso ya ajustado. |
| `dataset.csv` | CSV crudo de entrada. |
| `pred.csv` | Salida generada. |

> El script busca `modelo_supervisado.pkl` por defecto. Si tu archivo se llama
> `modelo_deploy.pkl`, pasá `--pkl modelo_deploy.pkl` o renombralo.

## Requisitos

- Python 3.12 o superior (probado con 3.14.4).
- `pandas`, `numpy`, `scikit-learn`, `xgboost`.
- Versiones de referencia: pandas 3.1.1, numpy 2.5.x, scikit-learn 1.9.1,
  xgboost 3.4.1.
- No hace falta `joblib`, `catboost`, `src2/` ni `datasets/`.

El `.pkl` se serializó con scikit-learn 1.9.1 y xgboost 3.4.1. Si usás versiones
muy distintas, el unpickle puede fallar o cambiar los resultados.

## Formato del CSV de entrada

- Mismo formato crudo que `datasetS*.csv`.
- Tiene que incluir `attack_phase`, `attack_phase_all` y `timestamp`; el
  preproceso las descarta y falla con `KeyError` si faltan.
- Filas en orden temporal, una por segundo. La ventana móvil de 120 s depende
  de ese orden.
- Las columnas `MQTT-Price-Signal*`, `realtime*`, `phase_seq*` y `Profile*` se
  descartan si están.
- `attack_active` es opcional: si está, se descarta.

## Salida

| Columna | Significado |
| --- | --- |
| `prob_ataque_xgb` | Probabilidad de ataque del XGBoost. |
| `ataque_xgb` | `1` si la probabilidad supera el umbral del pkl (0.5), `0` si no. |

Sin `--salida`, el script imprime un resumen por pantalla.

## Detalles

| Tema | Decisión |
| --- | --- |
| Modelo | `GroupedPCA + XGBoost`, solo supervisado. |
| Umbral | `xgb_umbral` guardado en el pkl (0.5). No hay override por CLI. |
| Ventana | 120 s, guardada en el pkl. |
| No supervisado | No incluido (Birch quedó afuera). |
| Dependencia del repo | Ninguna para predecir. |

## Problemas comunes

| Error | Causa / solución |
| --- | --- |
| `ModuleNotFoundError: xgboost` | El venv no está activado o faltan dependencias. |
| `FileNotFoundError: modelo_supervisado.pkl` | Pasá `--pkl modelo_deploy.pkl`. |
| `KeyError: 'attack_phase'` | El CSV no tiene el formato crudo completo. |
| `ModuleNotFoundError: src2` | Estás usando el `deploy_portable.py` viejo o un `.joblib`; este script no necesita `src2`. |

## Checklist

- [ ] `python -c "import pandas, numpy, sklearn, xgboost"` funciona.
- [ ] El pkl existe y es el supervisado.
- [ ] El CSV tiene `attack_phase`, `attack_phase_all` y `timestamp`.
- [ ] La salida tiene `prob_ataque_xgb` y `ataque_xgb`.

## Regenerar el pkl

El pkl se genera desde el repo, no desde esta carpeta:

```bash
PYTHONPATH=Colab python -c "from src2.deploy import entrenar_xgboost, exportar_portable; entrenar_xgboost(); exportar_portable()"
```

Después copiá `modelo_deploy.pkl` a la carpeta de deploy.
