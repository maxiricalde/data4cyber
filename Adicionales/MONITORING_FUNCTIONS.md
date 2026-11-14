# Funciones de monitoreo Modbus — SMA Sunny Island, Fronius PV y Janitza UMG 508

Los tres equipos del testbed se monitorean con **una sola función Modbus: FC3 (read holding registers)**, sobre el puerto 502, con el maestro ubicado en `192.168.1.11` (DMS/EMS). Todo lo que no sea FC3 es escritura o control, no monitoreo.

Este documento complementa `DEVICES_AND_METRICS.md`: allí está el inventario completo de dispositivos y el catálogo de señales; aquí está la vista operativa, es decir, qué se puede leer por equipo y qué se escribe.

Fuente de los datos: `endpoint_variable_mapping.csv` y `modbus_variable_mapping.csv` (idénticos en S0-S6 para el lado de los dispositivos).

## 1\. Janitza UMG 508 — el que más monitorea

FC3, bloque eléctrico **contiguo**: de 19000 a 19053, 27 señales de 2 registros cada una, sin huecos. Una sola lectura FC3 de 54 registros entrega todas las métricas eléctricas de un punto de medición.

| Bloque | Registros | Señales |
| :---- | :---- | :---- |
| Tensión | 19000-19010 | `uln1/2/3`, `ull12/23/31` |
| Corriente | 19012-19018 | `iln1/2/3`, `i_sum3` |
| Potencia activa | 19020-19026 | `pln1/2/3`, `p_sum3` |
| Potencia aparente | 19028-19034 | `sln1/2/3`, `s_sum3` |
| Potencia reactiva | 19036-19042 | `qln1/2/3`, `q_sum3` |
| Factor de potencia | 19044-19048 | `cos_phi1/2/3` |
| Red | 19050-19052 | `freq`, `phase_seq` |

Estado respecto del dataset: las 27 señales eléctricas están exportadas en `dataset.csv`, más `realtime`, que también aparece como columna pero es constante. El bloque de fecha y hora (`systime`, `day`, `month`, `year`, `hour`, `min`, `sec`, `weekday`) se puede leer por FC3 pero **no se exporta** al dataset.

Cinco puntos de medición comparten este esquema, cada uno con su propio unit ID:

| Punto lógico | IP | Unit ID |
| :---- | :---- | :---- |
| BSS-Inverter-AC-Meter | 192.168.1.61 | 3 |
| Load-A-AC-Meter | 192.168.1.61 | 4 |
| Load-B-AC-Meter | 192.168.1.62 | 2 |
| PV-Inverter-AC-Meter | 192.168.1.62 | 3 |
| Substation-AC-Meter | 192.168.1.65 | 1 |

## 2\. Fronius PV — 4 lecturas documentadas

| Señal | FC | Registro | Formato | Unidad | Para qué sirve |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `p_sum3` | 3 | 40091 | float (2 reg.) | W | Potencia activa CA real del inversor |
| `p_max` | 3 | 40134 | ushort | W | Potencia nominal de placa |
| `s_max` | 3 | 40136 | ushort | VA | Potencia aparente nominal de placa |
| `p_set_percent` | 3 | 40242 | ushort | % | Consigna de potencia activa vigente (lectura) |

Los registros no son contiguos: cada uno requiere una lectura separada.

Estado respecto del dataset: **ninguna de estas 4 señales está exportada como columna de `dataset.csv`**. Para monitorear el inversor hay que hacer el polling directamente; el dataset solo refleja el efecto en el medidor AC del lado PV.

Unit ID documentado: 48\. El inventario de nodos también lista los units 36, 37, 38 y 46, pero sin registros documentados.

## 3\. SMA Sunny Island — 2 lecturas documentadas

| Señal | FC | Registro | Formato | Unidad | Para qué sirve |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `p_sum3` | 3 | 30775 | int (2 reg.) | W | Potencia activa CA del BSS |
| `p_set_string` | 3 | 40149 | int (2 reg.) | W | Consigna de potencia activa por fase (lectura) |

Estado respecto del dataset: tampoco están exportadas como columnas. Mismo criterio que en el Fronius.

Unit ID documentado: 3\.

## 4\. Lo que no es monitoreo

Estos registros son de control, y son justamente la superficie de ataque de S1 y S2:

| Dispositivo | FC | Registro | Efecto |
| :---- | :---- | :---- | :---- |
| Fronius | 6 | 40242 | Escribe `p_set_percent` (limita potencia) |
| Fronius | 6 | 40246 | `p_set_confirm` — confirma el cambio de consigna |
| Sunny Island | 16 | 40149 | Escribe `p_set_string` |
| Sunny Island | 16 | 40151 | `power_com` — habilita control de potencia por comunicación |

La diferencia de función (FC6 en Fronius, FC16 en Sunny Island) sirve como fingerprint para separar las dos rutas de ataque al filtrar tráfico o al escribir un detector de escrituras.

## 5\. Consecuencias para una arquitectura de monitoreo

1. **Leer no es lo mismo que monitorear.** La lectura de la consigna (`p_set_percent` / `p_set_string` por FC3) es la única ventana de monitoreo sobre la intención de control. Leyendo solo potencia no se puede distinguir "el EMS mandó reducir" de "un tercero mandó reducir". Para S1/S2 el detector es la comparación entre la consigna leída y lo que efectivamente entrega el medidor AC.  
2. **El dataset no contiene telemetría nativa de inversores.** Solo medidores AC. Cualquier afirmación sobre detección a nivel de inversor debe apoyarse en los medidores AC o en la captura de paquetes, nunca en columnas inexistentes.  
3. **Costo de polling.** Una lectura FC3 de 54 registros por medidor por segundo cubre los 5 puntos de medición completos: 5 requests por segundo, totalmente viable, y es el patrón que usa el EMS.

## 6\. Resumen operativo

| Equipo | Función de monitoreo | Registros legibles documentados | ¿Exportado en `dataset.csv`? |
| :---- | :---- | :---- | :---- |
| Janitza UMG 508 | FC3 | 27 señales eléctricas (19000-19053) \+ bloque fecha/hora | Sí, las 27 eléctricas \+ `realtime` constante |
| Fronius PV | FC3 | 4 | No |
| SMA Sunny Island | FC3 | 2 | No |

## Lista de verificación

- [ ] Se usa FC3 para lectura y se reservan FC6/FC16 para control.  
- [ ] La lectura de consigna se contrasta contra la medición del medidor AC correspondiente.  
- [ ] No se asume que la telemetría de inversores está en `dataset.csv`.  
- [ ] Las lecturas se indexan por `(IP, unit_id)`, nunca solo por IP.  
- [ ] El bloque de fecha/hora del Janitza se lee aparte y no se espera en el dataset.