# CPS Attack Monitor (`paguina/`)

Aplicación web para visualizar en tiempo real simulado la inferencia de detección de ataques sobre mediciones en formato CSV.

## Estructura

```text
paguina/
├── app.py              # Servidor Flask + SSE (streaming al navegador)
├── inferencia.py       # Motor desacoplado de inferencia
├── modelos/            # Paquetes .pkl (supervisado, nosupervisado, regimenes)
├── data/datas.csv      # Dataset de mediciones
├── templates/index.html
└── requirements.txt
```

---

## Requisitos e instalación

Creá y activá el entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Luego instalá las dependencias eligiendo una de las dos opciones:

**Opción A — Usando `requirements.txt`:**

```bash
pip install -r paguina/requirements.txt
```

**Opción B — Instalando los paquetes por nombre:**

```bash
pip install flask pandas numpy scikit-learn xgboost
```

> Si además querés usar el resto de scripts/notebooks de la raíz del proyecto, instalá el `requirements.txt` raíz (`pip install -r requirements.txt`).

---

## 1. Cómo usar la página web

Desde la carpeta `paguina/`, activando el entorno virtual del proyecto:

```bash
cd paguina
source ../.venv/bin/activate
```

### Con el modelo supervisado (XGBoost)

```bash
python3 app.py --script ../deploy_supervisado.py --pkl modelos/supervisado.pkl
```

### Con el modelo no supervisado (Birch)

```bash
python3 app.py --script ../xd/deploy_nosupervisado.py --pkl modelos/nosupervisado.pkl
```

### Opciones disponibles en `app.py`

| Argumento | Requerido | Default | Descripción |
|-----------|-----------|---------|-------------|
| `--script` | Sí | — | Ruta al script `.py` de deploy (`cargar_paquete` + `predecir_*`) |
| `--pkl` | Sí | — | Ruta al archivo `.pkl` del modelo |
| `--csv` | No | `data/datas.csv` | Ruta al CSV de entrada |
| `--port` | No | `5000` | Puerto del servidor web |

Luego abrí `http://localhost:5000` en el navegador.

### Controles en la interfaz

- **Pause / Resume**: Pausa o reanuda la llegada de mediciones.
- **Reset**: Reinicia la reproducción desde la primera fila.
- **Speed**: Ajusta la velocidad de streaming (`1x` a `50x` filas por segundo).
- **Alarma**: Se activa un banner superior cuando se detectan **5 o más ataques consecutivos**.
- **Scroll inteligente**: Las filas nuevas entran arriba; si estás arriba se mantiene el tope, y si bajaste para inspeccionar filas anteriores no te mueve la vista.

---

## 2. Cómo ejecutar `inferencia.py` de forma independiente

Si querés generar el archivo `resultados.jsonl` sin levantar el servidor web:

```bash
cd paguina
source ../.venv/bin/activate
python3 inferencia.py --script ../deploy_supervisado.py --pkl modelos/supervisado.pkl --csv data/datas.csv --output resultados.jsonl
```

---

## 3. Cómo ejecutar los scripts de deploy originales de manera independiente

Desde la raíz del proyecto (`Trabajo Final/`), podés correr cada script CLI directamente sin usar la web:

```bash
source .venv/bin/activate
```

### Supervisado (`deploy_supervisado.py`)

```bash
# Resumen por consola
python3 deploy_supervisado.py datas.csv --pkl modelo_deploy.pkl

# Guardar predicciones en CSV
python3 deploy_supervisado.py datas.csv --pkl modelo_deploy.pkl --salida salida.csv
```

### No supervisado (`xd/deploy_nosupervisado.py`)

```bash
# Resumen por consola
python3 xd/deploy_nosupervisado.py datas.csv --pkl deploy_nosupervisado.pkl

# Guardar predicciones en CSV
python3 xd/deploy_nosupervisado.py datas.csv --pkl deploy_nosupervisado.pkl --salida pred_nosup.csv
```

### Regímenes (`xd/deploy_regimenes.py`)

```bash
# Resumen por consola
python3 xd/deploy_regimenes.py datas.csv --pkl xd/deploy_regimenes.pkl

# Guardar etiquetas de régimen en CSV
python3 xd/deploy_regimenes.py datas.csv --pkl xd/deploy_regimenes.pkl --salida pred_regimenes.csv
```
