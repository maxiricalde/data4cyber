# Columnas por grupo y por tipo — `dataset.csv`

Agrupación de las 156 columnas de `dataset.csv` por **dispositivo que las genera** y por **tipo de magnitud**. Todos los conteos salen del header real de los archivos.

|  | Columnas |
| :---- | ----: |
| `dataset.csv` en S0–S5 | 155 |
| `dataset.csv` en S6 | **156** |

La diferencia es una sola columna: `MQTT-Price-Signal.event`, que solo existe en S6.

## 1\. Grupos por dispositivo / origen

| Grupo | Columnas | Prefijo | Columnas concretas | Equipo físico | IP | Unit ID |
| :---- | ----: | :---- | :---- | :---- | :---- | :---- |
| Medidor AC del BSS | 28 | `BSS-Inverter-AC-Meter.` | 28 señales Janitza (ver §2) | Janitza UMG 508 `umg6c` | 192.168.1.61 | 3 |
| Medidor de carga A | 28 | `Load-A-AC-Meter.` | 28 señales Janitza (ver §2) | Janitza UMG 508 `umg6c` | 192.168.1.61 | 4 |
| Medidor de carga B | 28 | `Load-B-AC-Meter.` | 28 señales Janitza (ver §2) | Janitza UMG 508 `umg7a` | 192.168.1.62 | 2 |
| Medidor AC del PV | 28 | `PV-Inverter-AC-Meter.` | 28 señales Janitza (ver §2) | Janitza UMG 508 `umg7a` | 192.168.1.62 | 3 |
| Medidor de subestación | 28 | `Substation-AC-Meter.` | 28 señales Janitza (ver §2) | Janitza UMG 508 `umg_ront` | 192.168.1.65 | 1 |
| SOC de referencia | 1 | `Battery-SOC-Reference.` | `soc_value` | BSS (interno) | — | — |
| SOC reportado | 1 | `Battery-SOC-Reported.` | `soc_value` | BSS (interno) | — | — |
| Señal de precio | 1 o 2 | `MQTT-Price-Signal.` | `price_eur_per_kwh` (S0–S6), `event` (**solo S6**) | Broker MQTT | — | — |
| Contexto de escenario | 8 | `Profile.` | `ambient_temperature`, `load1_kw`, `load2_kw`, `pv_active_kw`, `pv_input_kw`, `pv_reactive_kvar`, `timestamp`, `total_irradiance` | Perfil de laboratorio | — | — |
| Control / etiquetas | 4 | *(sin prefijo)* | `timestamp`, `attack_active`, `attack_phase`, `attack_phase_all` | Capa de etiquetado | — | — |

**El grupo de control no tiene prefijo.** Esas 4 columnas son las únicas de `dataset.csv` que no siguen la forma `<Dispositivo>.<Señal>`:

| Columna | Tipo | Qué contiene |
| :---- | :---- | :---- |
| `timestamp` | datetime UTC | Escalón de 1 s de la grilla de salida. Clave primaria de la fila. |
| `attack_active` | bool | La fila cae dentro de alguna fase de ataque. `True`/`False`. |
| `attack_phase` | string | Fase activa en ese instante; `normal` fuera de ataque. Una sola. |
| `attack_phase_all` | string | Fases superpuestas separadas por `;`; `normal` si no hay ninguna. |

## 2\. Tipos de columna dentro de los medidores Janitza

Los cinco medidores comparten el mismo esquema: **28 columnas cada uno**, idénticas en nombre de señal y registro Modbus. Cambia solo el prefijo.

| Tipo | Nº por medidor | Unidad | Señales (sufijo) | Registro Modbus |
| :---- | ----: | :---- | :---- | :---- |
| Tensión fase-neutro | 3 | V | `uln1`, `uln2`, `uln3` | 19000–19004 |
| Tensión fase-fase | 3 | V | `ull12`, `ull23`, `ull31` | 19006–19010 |
| Corriente de fase | 3 | A | `iln1`, `iln2`, `iln3` | 19012–19016 |
| Corriente de neutro | 1 | A | `i_sum3` | 19018 |
| Potencia activa | 4 | W | `pln1`, `pln2`, `pln3`, `p_sum3` | 19020–19026 |
| Potencia aparente | 4 | VA | `sln1`, `sln2`, `sln3`, `s_sum3` | 19028–19034 |
| Potencia reactiva | 4 | var | `qln1`, `qln2`, `qln3`, `q_sum3` | 19036–19042 |
| Factor de potencia | 3 | — | `cos_phi1`, `cos_phi2`, `cos_phi3` | 19044–19048 |
| Frecuencia | 1 | Hz | `freq` | 19050 |
| Secuencia de fases | 1 | — | `phase_seq` | 19052 |
| Marca de tiempo | 1 | s | `realtime` | 0 (4 registros, long64) |
| **Total** | **28** |  |  |  |

## 3\. Totales por tipo en todo el dataset

Multiplicando por los cinco medidores. Esta es la tabla de conteo que cierra contra las 156 columnas.

| Tipo | Nº por medidor | Medidores | Total |
| :---- | ----: | ----: | ----: |
| Tensión fase-neutro | 3 | 5 | 15 |
| Tensión fase-fase | 3 | 5 | 15 |
| Corriente de fase | 3 | 5 | 15 |
| Corriente de neutro | 1 | 5 | 5 |
| Potencia activa | 4 | 5 | 20 |
| Potencia aparente | 4 | 5 | 20 |
| Potencia reactiva | 4 | 5 | 20 |
| Factor de potencia | 3 | 5 | 15 |
| Frecuencia | 1 | 5 | 5 |
| Secuencia de fases | 1 | 5 | 5 |
| Marca de tiempo | 1 | 5 | 5 |
| **Subtotal medidores** | **28** | 5 | **140** |
| SOC de referencia | 1 | 1 | 1 |
| SOC reportado | 1 | 1 | 1 |
| Precio MQTT (S0–S5) | 1 | 1 | 1 |
| Evento MQTT (**solo S6**) | 1 | 1 | 1 |
| Contexto de escenario | 8 | 1 | 8 |
| Control / etiquetas | 4 | 1 | 4 |
| **Total S0–S5** |  |  | **155** |
| **Total S6** |  |  | **156** |

## 4\. Enumeración de columnas por grupo

Para copiar y pegar en código. Los medidores se listan con prefijo completo; el orden es el de la tabla de §2, no el del archivo (que es alfabético).

### Medidor AC del BSS — 28 columnas (`BSS-Inverter-AC-Meter.`)

```
# Tensión fase-neutro (V)
BSS-Inverter-AC-Meter.uln1
BSS-Inverter-AC-Meter.uln2
BSS-Inverter-AC-Meter.uln3
# Tensión fase-fase (V)
BSS-Inverter-AC-Meter.ull12
BSS-Inverter-AC-Meter.ull23
BSS-Inverter-AC-Meter.ull31
# Corriente de fase (A)
BSS-Inverter-AC-Meter.iln1
BSS-Inverter-AC-Meter.iln2
BSS-Inverter-AC-Meter.iln3
# Corriente de neutro (A)
BSS-Inverter-AC-Meter.i_sum3
# Potencia activa (W)
BSS-Inverter-AC-Meter.pln1
BSS-Inverter-AC-Meter.pln2
BSS-Inverter-AC-Meter.pln3
BSS-Inverter-AC-Meter.p_sum3
# Potencia aparente (VA)
BSS-Inverter-AC-Meter.sln1
BSS-Inverter-AC-Meter.sln2
BSS-Inverter-AC-Meter.sln3
BSS-Inverter-AC-Meter.s_sum3
# Potencia reactiva (var)
BSS-Inverter-AC-Meter.qln1
BSS-Inverter-AC-Meter.qln2
BSS-Inverter-AC-Meter.qln3
BSS-Inverter-AC-Meter.q_sum3
# Factor de potencia (—)
BSS-Inverter-AC-Meter.cos_phi1
BSS-Inverter-AC-Meter.cos_phi2
BSS-Inverter-AC-Meter.cos_phi3
# Frecuencia (Hz)
BSS-Inverter-AC-Meter.freq
# Secuencia de fases (—)
BSS-Inverter-AC-Meter.phase_seq
# Marca de tiempo (s)
BSS-Inverter-AC-Meter.realtime
```

### Medidor de carga A — 28 columnas (`Load-A-AC-Meter.`)

```
# Tensión fase-neutro (V)
Load-A-AC-Meter.uln1
Load-A-AC-Meter.uln2
Load-A-AC-Meter.uln3
# Tensión fase-fase (V)
Load-A-AC-Meter.ull12
Load-A-AC-Meter.ull23
Load-A-AC-Meter.ull31
# Corriente de fase (A)
Load-A-AC-Meter.iln1
Load-A-AC-Meter.iln2
Load-A-AC-Meter.iln3
# Corriente de neutro (A)
Load-A-AC-Meter.i_sum3
# Potencia activa (W)
Load-A-AC-Meter.pln1
Load-A-AC-Meter.pln2
Load-A-AC-Meter.pln3
Load-A-AC-Meter.p_sum3
# Potencia aparente (VA)
Load-A-AC-Meter.sln1
Load-A-AC-Meter.sln2
Load-A-AC-Meter.sln3
Load-A-AC-Meter.s_sum3
# Potencia reactiva (var)
Load-A-AC-Meter.qln1
Load-A-AC-Meter.qln2
Load-A-AC-Meter.qln3
Load-A-AC-Meter.q_sum3
# Factor de potencia (—)
Load-A-AC-Meter.cos_phi1
Load-A-AC-Meter.cos_phi2
Load-A-AC-Meter.cos_phi3
# Frecuencia (Hz)
Load-A-AC-Meter.freq
# Secuencia de fases (—)
Load-A-AC-Meter.phase_seq
# Marca de tiempo (s)
Load-A-AC-Meter.realtime
```

### Medidor de carga B — 28 columnas (`Load-B-AC-Meter.`)

```
# Tensión fase-neutro (V)
Load-B-AC-Meter.uln1
Load-B-AC-Meter.uln2
Load-B-AC-Meter.uln3
# Tensión fase-fase (V)
Load-B-AC-Meter.ull12
Load-B-AC-Meter.ull23
Load-B-AC-Meter.ull31
# Corriente de fase (A)
Load-B-AC-Meter.iln1
Load-B-AC-Meter.iln2
Load-B-AC-Meter.iln3
# Corriente de neutro (A)
Load-B-AC-Meter.i_sum3
# Potencia activa (W)
Load-B-AC-Meter.pln1
Load-B-AC-Meter.pln2
Load-B-AC-Meter.pln3
Load-B-AC-Meter.p_sum3
# Potencia aparente (VA)
Load-B-AC-Meter.sln1
Load-B-AC-Meter.sln2
Load-B-AC-Meter.sln3
Load-B-AC-Meter.s_sum3
# Potencia reactiva (var)
Load-B-AC-Meter.qln1
Load-B-AC-Meter.qln2
Load-B-AC-Meter.qln3
Load-B-AC-Meter.q_sum3
# Factor de potencia (—)
Load-B-AC-Meter.cos_phi1
Load-B-AC-Meter.cos_phi2
Load-B-AC-Meter.cos_phi3
# Frecuencia (Hz)
Load-B-AC-Meter.freq
# Secuencia de fases (—)
Load-B-AC-Meter.phase_seq
# Marca de tiempo (s)
Load-B-AC-Meter.realtime
```

Medidor AC del PV — 28 columnas (`PV-Inverter-AC-Meter.`)

```
# Tensión fase-neutro (V)
PV-Inverter-AC-Meter.uln1
PV-Inverter-AC-Meter.uln2
PV-Inverter-AC-Meter.uln3
# Tensión fase-fase (V)
PV-Inverter-AC-Meter.ull12
PV-Inverter-AC-Meter.ull23
PV-Inverter-AC-Meter.ull31
# Corriente de fase (A)
PV-Inverter-AC-Meter.iln1
PV-Inverter-AC-Meter.iln2
PV-Inverter-AC-Meter.iln3
# Corriente de neutro (A)
PV-Inverter-AC-Meter.i_sum3
# Potencia activa (W)
PV-Inverter-AC-Meter.pln1
PV-Inverter-AC-Meter.pln2
PV-Inverter-AC-Meter.pln3
PV-Inverter-AC-Meter.p_sum3
# Potencia aparente (VA)
PV-Inverter-AC-Meter.sln1
PV-Inverter-AC-Meter.sln2
PV-Inverter-AC-Meter.sln3
PV-Inverter-AC-Meter.s_sum3
# Potencia reactiva (var)
PV-Inverter-AC-Meter.qln1
PV-Inverter-AC-Meter.qln2
PV-Inverter-AC-Meter.qln3
PV-Inverter-AC-Meter.q_sum3
# Factor de potencia (—)
PV-Inverter-AC-Meter.cos_phi1
PV-Inverter-AC-Meter.cos_phi2
PV-Inverter-AC-Meter.cos_phi3
# Frecuencia (Hz)
PV-Inverter-AC-Meter.freq
# Secuencia de fases (—)
PV-Inverter-AC-Meter.phase_seq
# Marca de tiempo (s)
PV-Inverter-AC-Meter.realtime
```

### Medidor de subestación — 28 columnas (`Substation-AC-Meter.`)

```
# Tensión fase-neutro (V)
Substation-AC-Meter.uln1
Substation-AC-Meter.uln2
Substation-AC-Meter.uln3
# Tensión fase-fase (V)
Substation-AC-Meter.ull12
Substation-AC-Meter.ull23
Substation-AC-Meter.ull31
# Corriente de fase (A)
Substation-AC-Meter.iln1
Substation-AC-Meter.iln2
Substation-AC-Meter.iln3
# Corriente de neutro (A)
Substation-AC-Meter.i_sum3
# Potencia activa (W)
Substation-AC-Meter.pln1
Substation-AC-Meter.pln2
Substation-AC-Meter.pln3
Substation-AC-Meter.p_sum3
# Potencia aparente (VA)
Substation-AC-Meter.sln1
Substation-AC-Meter.sln2
Substation-AC-Meter.sln3
Substation-AC-Meter.s_sum3
# Potencia reactiva (var)
Substation-AC-Meter.qln1
Substation-AC-Meter.qln2
Substation-AC-Meter.qln3
Substation-AC-Meter.q_sum3
# Factor de potencia (—)
Substation-AC-Meter.cos_phi1
Substation-AC-Meter.cos_phi2
Substation-AC-Meter.cos_phi3
# Frecuencia (Hz)
Substation-AC-Meter.freq
# Secuencia de fases (—)
Substation-AC-Meter.phase_seq
# Marca de tiempo (s)
Substation-AC-Meter.realtime
```

### SOC de referencia — 1 columna

```
Battery-SOC-Reference.soc_value
```

### SOC reportado — 1 columna

```
Battery-SOC-Reported.soc_value
```

### Señal de precio — 1 o 2 columnas

```
MQTT-Price-Signal.price_eur_per_kwh
MQTT-Price-Signal.event          # solo en S6
```

### Contexto de escenario — 8 columnas

```
Profile.ambient_temperature
Profile.load1_kw
Profile.load2_kw
Profile.pv_active_kw
Profile.pv_input_kw
Profile.pv_reactive_kvar
Profile.timestamp
Profile.total_irradiance
```

### Control / etiquetas — 4 columnas (sin prefijo)

```
timestamp
attack_active
attack_phase
attack_phase_all
```

## 5\. Verificación de las sumas

```
28 columnas por medidor × 5 medidores ....... 140
SOC referencia .............................. 1
SOC reportado ............................... 1
Precio MQTT ................................. 1
                                               ---
Total S0-S5 ................................. 155
Evento MQTT (solo S6) ....................... 1
                                               ---
Total S6 .................................... 156
```

Ambos totales coinciden con el conteo real de columnas de los archivos. La única diferencia entre escenarios es `MQTT-Price-Signal.event`.

**Trampa de orden:** el archivo está ordenado alfabéticamente por nombre completo de columna, no por grupo ni por tipo. Las 140 columnas de medidor quedan intercaladas entre sí. Nunca leer por posición.