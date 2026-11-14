# Referencia de dispositivos y métricas — Testbed Data4Cyber

Cada medición de este dataset proviene de cinco dispositivos físicos: tres analizadores de red Janitza UMG 508 y dos inversores (Fronius PV y SMA Sunny Island BSS). Este documento relaciona cada dispositivo con su identidad de red, sus registros Modbus y las columnas del dataset que produce, de modo que al leer el nombre de una columna se pueda saber con exactitud qué hardware, qué registro y qué magnitud física la generaron.

Los archivos de referencia son `ip_device_mapping.csv`, `network_node_inventory.csv`, `ip_unit_device_mapping.csv`, `endpoint_variable_mapping.csv` y `modbus_variable_mapping.csv`. En el lado de los dispositivos, los cinco tienen contenido idéntico en S0-S6; solo cambia la identidad del atacante en cada escenario.

## Ruta rápida

1. Partir de una columna: dividir `BSS-Inverter-AC-Meter.p_sum3` en dispositivo (`BSS-Inverter-AC-Meter`) + señal (`p_sum3`).
2. Cruzar el dispositivo con `ip_unit_device_mapping.csv` para obtener IP + Modbus unit ID + ubicación en la red eléctrica.
3. Cruzar `(IP, unit, designation)` con `endpoint_variable_mapping.csv` para obtener código de función, dirección de inicio, cantidad, unidad y descripción.
4. Verificar: `endpoint_variable_mapping.csv` tiene una columna `dataset_variable` que debe coincidir exactamente con el nombre de la columna del CSV. Si está vacía, el registro existe pero no se registra como feature del dataset.

## 1. Dispositivos de medición

| Punto lógico          | Dispositivo físico         | IP            | Unit ID        | MAC               | Ubicación en la red                              |
| --------------------- | -------------------------- | ------------- | -------------- | ----------------- | ------------------------------------------------ |
| BSS-Inverter-AC-Meter | Janitza UMG 508 `umg6c`    | 192.168.1.61  | 3              | 00:0e:6b:05:22:52 | Conexión AC del inversor BSS                     |
| Load-A-AC-Meter       | Janitza UMG 508 `umg6c`    | 192.168.1.61  | 4              | 00:0e:6b:05:22:52 | Conexión de la carga A                           |
| Load-B-AC-Meter       | Janitza UMG 508 `umg7a`    | 192.168.1.62  | 2              | 00:0e:6b:05:64:3f | Conexión de la carga B                           |
| PV-Inverter-AC-Meter  | Janitza UMG 508 `umg7a`    | 192.168.1.62  | 3              | 00:0e:6b:05:64:3f | Conexión AC del inversor PV                      |
| Substation-AC-Meter   | Janitza UMG 508 `umg_ront` | 192.168.1.65  | 1              | 00:0e:6b:05:25:37 | Subestación secundaria / punto de conexión común |
| PV-Inverter           | Inversor Fronius PV        | 192.168.1.88  | 36;37;38;46;48 | 00:03:ac:03:7b:df | Generación PV (DC + AC)                          |
| BSS-Inverter          | SMA Sunny Island           | 192.168.1.184 | 3              | 00:40:ad:9b:3f:25 | Almacenamiento en baterías                       |

### El detalle que arruina el análisis

Tres IPs, cinco puntos de medición. Un mismo equipo Janitza expone MÚLTIPLES puntos lógicos de medición mediante distintos Modbus unit IDs en el puerto 502. `192.168.1.61` atiende tanto el medidor del BSS (unit 3) como la carga A (unit 4); `192.168.1.62` atiende tanto la carga B (unit 2) como el medidor PV (unit 3).

Consecuencia: indexar solo por IP fusiona dos flujos de medición independientes. La clave correcta es siempre `(IP, unit_id)`. Esto es crítico en S3, donde el ataque reescribe `192.168.1.61:502 unit 3` y no debe confundirse con el unit 4 del mismo host.

## 2. Nodos que no miden

| Nodo | Rol | Dirección | Protocolos | Observaciones |
|---|---|---|---|---|
| DMS/EMS | Controlador / SCADA | 192.168.1.11, `00:13:3b:9d:00:8d` | modbus/tcp, mqtt | Consulta cada medidor, ejecuta el lazo del EMS y se suscribe a la señal de precio |
| Atacante | Host de ataque / MITM | variable (`10.0.104.26` en las capturas) | modbus/tcp, arp | La MAC cambia por escenario; no figura en `network_node_inventory.csv` con IP fija |
| OT switch | Switch L2 | sin IP | ethernet | Punto de pivote para ARP/MITM en S3-S5 |
| MQTT broker | Publicador de la señal de precio | no inventariado | mqtt | Implícito en S6; no hay entrada de nodo ni IP del broker en ningún archivo de mapeo |

## 3. Métricas del Janitza UMG 508 (36 señales)

Las cinco posiciones de medición comparten el mismo esquema de 36 señales. Código de función 3 (lectura de holding registers); `float` = par IEEE-754 que ocupa 2 registros.

### Bloque de fecha y hora

| Señal | Registro | Cant. | Formato | Unidad | Significado |
|---|---|---|---|---|---|
| `realtime` | 0 | 4 | long64 | epoch (grilla de 2 s) | Reloj del equipo, UTC. Es la marca temporal de origen alineada en `measurement_alignment.csv.gz` |
| `systime` | 4 | 2 | int | s | Reloj interno de tipo uptime |
| `day` | 6 | 1 | short | - | Día 1..31 |
| `month` | 7 | 1 | short | - | Mes, **0 = enero** |
| `year` | 8 | 1 | short | - | Año |
| `hour` | 9 | 1 | short | h | Hora 1..24 |
| `min` | 10 | 1 | short | min | Minuto 1..59 |
| `sec` | 11 | 1 | short | s | Segundo 1..59 |
| `weekday` | 12 | 1 | short | - | 0 = domingo |

### Tensión y corriente

| Señal | Registro | Unidad | Significado |
|---|---|---|---|
| `uln1/2/3` | 19000/19002/19004 | V | Tensión fase-neutro, L1/L2/L3 |
| `ull12/23/31` | 19006/19008/19010 | V | Tensión entre fases (de línea) |
| `iln1/2/3` | 19012/19014/19016 | A | Corriente de fase, L1/L2/L3 |
| `i_sum3` | 19018 | A | Suma vectorial de las tres corrientes de fase (proxy de corriente de neutro/tierra) |

### Bloque de potencia

| Señal | Registro | Unidad | Significado | Identidad |
|---|---|---|---|---|
| `pln1/2/3` | 19020/19022/19024 | W | Potencia activa por fase | - |
| `p_sum3` | 19026 | W | Potencia activa trifásica | P = P1+P2+P3 |
| `sln1/2/3` | 19028/19030/19032 | VA | Potencia aparente por fase | - |
| `s_sum3` | 19034 | VA | Potencia aparente trifásica | S = S1+S2+S3 |
| `qln1/2/3` | 19036/19038/19040 | var | Potencia reactiva por fase, solo componente fundamental | - |
| `q_sum3` | 19042 | var | Potencia reactiva trifásica, componente fundamental | Q = Q1+Q2+Q3 |
| `cos_phi1/2/3` | 19044/19046/19048 | - | Factor de potencia por fase | cos φ = P / S |
| `freq` | 19050 | Hz | Frecuencia de red | - |
| `phase_seq` | 19052 | - | Secuencia de fases | 1 = derecha, 0 = ninguna, -1 = izquierda |

Notas prácticas de lectura:

- `p_sum3` es la feature principal en `01_power_timeseries.pdf` y en la mayor parte del trabajo de detección. El signo sigue la convención propia del medidor en cada punto de instalación: conviene comparar contra el valor de la subestación en lugar de asumir que la generación es positiva.
- `q_sum3` y `cos_phi*` se calculan SOLO sobre la componente fundamental, mientras que `s_sum3` es total. Por eso `S² = P² + Q²` no cierra exactamente cuando hay armónicos. No usar esa identidad como verificación de integridad de los datos.
- `phase_seq` es una señal de integridad barata: una reescritura ARP/MITM que inyecte valores implausibles puede dejar `phase_seq` en un valor imposible o clavado en `1` todo el tiempo. Sin embargo, el spoofing por mitad de valor en S3 lo preserva, así que no sirve como detector de spoofing. Además, en los datos liberados es constante, por lo que aporta cero información temporal.
- En S3 el medidor del BSS se reporta falseado. Ojo: en la tabla liberada el efecto no es un factor 0.5 limpio — la mediana de `BSS-Inverter-AC-Meter.p_sum3` pasa de −54,5 W en operación normal a −11,8 W en la fase de impacto, con la consigna del BSS moviéndose en paralelo. La única verificación cruzada disponible en ese escenario es el balance con la subestación o la comparación contra `Profile.*`.

## 4. Telemetría de los inversores

### Inversor Fronius PV (192.168.1.88)

El inventario de nodos lista los unit IDs `36;37;38;46;48`; el mapeo de endpoints solo documenta el unit 48.

| Señal | Unit ID | FC | Registro | Cant. | Formato | Acceso | Unidad | Significado |
|---|---|---|---|---|---|---|---|---|
| `p_sum3` | 48 | 3 | 40091 | 2 | float | lectura | W | Potencia activa CA trifásica |
| `p_max` | 48 | 3 | 40134 | 1 | ushort | lectura | W | Potencia nominal del inversor (placa) |
| `s_max` | 48 | 3 | 40136 | 1 | ushort | lectura | VA | Potencia aparente nominal del inversor (placa) |
| `p_set_percent` | 48 | 3 | 40242 | 1 | ushort | lectura | % | Consigna de potencia activa, porcentaje de la nominal |
| `p_set_percent` | 48 | 6 | 40242 | 1 | ushort | **escritura** | % | El mismo registro, escrito por el EMS para limitar potencia |
| `p_set_confirm` | 48 | 6 | 40246 | 1 | short | **escritura** | - | Confirma el cambio de consigna |

Este es el objetivo de S1 y S1-alt. La ruta del ataque es: escribir `p_set_percent` (FC6, registro 40242) y luego `p_set_confirm` (40246), forzando al inversor a un nivel de salida manipulado, lo que después aparece como un cambio real en las lecturas del medidor AC. Al analizar S1, buscar que `PV-Inverter-AC-Meter.p_sum3` se separe de `Profile.pv_active_kw` / `Profile.pv_input_kw`.

Los units 36, 37, 38 y 46 aparecen en el inventario de nodos pero no tienen registros documentados aquí. Deben tratarse como no documentados salvo que se encuentren en la documentación Modbus de Fronius para el modelo específico.

### Inversor BSS SMA Sunny Island (192.168.1.184, unit 3)

| Señal | FC | Registro | Cant. | Formato | Acceso | Unidad | Significado |
|---|---|---|---|---|---|---|---|
| `p_sum3` | 3 | 30775 | 2 | int | lectura | W | Potencia activa CA trifásica |
| `p_set_string` | 3 | 40149 | 2 | int | lectura | W | Consigna de potencia activa por fase |
| `p_set_string` | 16 | 40149 | 2 | int | **escritura** | W | La misma consigna, escrita por el EMS |
| `power_com` | 16 | 40151 | 2 | uint | **escritura** | - | Habilita el control de potencia activa/reactiva por comunicación |

Este es el objetivo de S2. Nótese FC16 (escritura de múltiples registros) aquí frente a FC6 (escritura de un solo registro) en el Fronius. Esa diferencia de protocolo es un fingerprint utilizable al filtrar `packet_labels.csv` por `attack_type`, o al escribir un detector propio de escrituras Modbus.

## 5. Señales sin mapeo Modbus

Existen tres familias de columnas en `dataset.csv` que no aparecen en ningún archivo de mapeo:

| Columna | Procedencia probable | Advertencia |
|---|---|---|
| `Battery-SOC-Reference.soc_value` | Consigna interna de referencia del BSS | Sin registro documentado; no afirmar que proviene de Modbus |
| `Battery-SOC-Reported.soc_value` | SOC reportado internamente por el BSS | Ídem. La divergencia entre Reference y Reported es la señal a estudiar en S3-S5 |
| `MQTT-Price-Signal.price_eur_per_kwh` | Topic MQTT `energy/price_signals` | S6 manipula este topic; ver `attack_events.csv` |
| `Profile.*` (8 columnas) | Contexto del escenario / perfil de laboratorio | `ambient_temperature`, `total_irradiance`, `pv_input_kw`, `pv_active_kw`, `pv_reactive_kvar`, `load1_kw`, `load2_kw`, `timestamp`. Contexto tipo verdad de referencia, no salida de medidor |

`Profile.timestamp` duplica la marca temporal de la fila. No tratar `Profile.*` como evidencia independiente de lo que vieron los medidores: en los escenarios de spoofing los medidores discrepan del perfil POR DISEÑO.

## 6. Base temporal y alineación

- `dataset.csv` está remuestreado sobre una grilla UTC estricta de 1 s (`step-size-seconds: 1.0` en `metadata.json`). Los relojes de los dispositivos no están sobre esa grilla.
- Los dispositivos de origen reportan con su propia cadencia (el `realtime` del Janitza está marcado como `2 s`), por lo que la capa de alineación tuvo que ubicar las muestras en los escalones de la grilla.
- `measurement_alignment.csv.gz` entrega, por (timestamp, feature): `source_timestamp`, `age_seconds`, `observed_at_step` y `carried`. Usar las filas con `carried=True` cuando haga falta saber que un valor fue arrastrado hacia adelante; usar `observed_at_step=True` cuando se necesite una muestra realmente fresca.
- Las celdas vacías nunca se imputan. S0 tiene 482 entradas vacías; la liberación completa tiene 7.569. Vacío significa "no hay valor de origen para ese escalón de la grilla", no cero ni valor interpolado. Tratarlo como cero fabrica saltos que se parecen exactamente a ataques.
- `state.jsonl.gz` tiene un registro por fila con los mismos valores, más `missing_state_variables` con los nombres de las features ausentes. `malicious` equivale a `attack_active`.

## 7. Qué archivo responde qué pregunta

| Pregunta | Archivo |
|---|---|
| ¿Qué dispositivo produjo esta columna? | `ip_unit_device_mapping.csv`, `endpoint_variable_mapping.csv` |
| ¿Qué significa este registro y en qué unidad? | `modbus_variable_mapping.csv`, `endpoint_variable_mapping.csv` |
| ¿Qué rol de dispositivo está en esta IP? | `ip_device_mapping.csv`, `network_node_inventory.csv` |
| ¿Qué se atacó, cuándo y en qué IP/unidad? | `attack-phases.json` (`attack_point`, `target`, intervalos UTC semiabiertos) |
| ¿Qué paquetes pertenecen al ataque? | `packet_labels.csv` (`label`, `attack_type`, `attack_phase`, `event_id`) |
| ¿Qué hizo realmente el atacante? | `attack_events.csv` |
| ¿Un valor fue arrastrado o muestreado fresco? | `measurement_alignment.csv.gz` |

## 8. Escenario -> dispositivo objetivo

| Escenario | Objetivo | Dispositivo / endpoint |
|---|---|---|
| S1, S1-alt | Control del inversor PV | Fronius 192.168.1.88 unit 48, `p_set_percent` + `p_set_confirm` |
| S2 | Control del inversor BSS | Sunny Island 192.168.1.184 unit 3, `p_set_string` + `power_com` |
| S3 | Lectura del medidor AC del BSS | Janitza `umg6c` 192.168.1.61 unit 3, respuestas manipuladas |
| S4 | Lecturas de medidores de cargas y PV | Cargas (192.168.1.61 unit 4 para carga A, 192.168.1.62 unit 2 para carga B) y PV (192.168.1.62 unit 3). `attack-phases.json` no nombra un `attack_point` explícito; los objetivos exactos deben derivarse de la captura de paquetes |
| S5 | Medidores de cargas, PV y BSS | Objetivos de S4 más las lecturas del lado del BSS (192.168.1.61 unit 3), reducidas a ~10 % en la fase 2 |
| S6 | Señal de precio MQTT | broker -> DMS/EMS 192.168.1.11, `energy/price_signals` |

## 9. Dónde leer más

Documentación de fabricante (buscar el título del documento en el sitio del fabricante; la numeración de registros cambia según firmware y variante de modelo, así que siempre conviene confirmarla contra la versión disponible):

- **Janitza UMG 508** — nota de aplicación "Modbus address list" / "Modbus Register". Contiene el bloque completo de la serie 19000, el escalado y la notación 4xxxx que usa Janitza en sus propias tablas. Confirmar cómo se corresponde esa notación 4xxxx con las direcciones crudas guardadas en `endpoint_variable_mapping.csv` antes de reutilizar cualquier registro con un cliente de terceros.
- **Fronius** — "Modbus register map" de la serie de inversores (disposición derivada de SunSpec alrededor de 40071-40260). Explica los units 36/37/38/46 que este dataset deja sin documentar.
- **SMA Sunny Island** — información técnica "Modbus interface" / "Modbus register" de la serie SI (bloques 30000 y 40000), incluidos `power_com` y la semántica de las consignas.
- **Modbus** — Modbus Application Protocol Specification (modbus.org) para la semántica de FC3, FC6 y FC16, que es la diferencia entre las rutas de ataque del Fronius y del Sunny Island.
- **Contexto de los ataques** — Industroyer/CrashOverride (aviso CISA AA17-112A) para la familia de ataques de control de S1/S2; ARP spoofing + manipulación de mediciones por MITM para S3-S5; compromiso del broker MQTT / inyección de datos falsos para S6.

## Lista de verificación

- [ ] Cada columna utilizada se resuelve a una terna `(IP, unit_id, designation)`.
- [ ] Las mediciones nunca se indexan solo por IP.
- [ ] Se distingue entre valores reportados por el medidor y valores de contexto `Profile.*`.
- [ ] Las celdas vacías se tratan como faltantes, no como cero.
- [ ] Se revisaron `carried` y `age_seconds` antes de tratar un escalón como muestra fresca.
- [ ] `Battery-SOC-*` y `MQTT-Price-Signal` se tratan como fuentes sin mapeo Modbus.

## Siguiente paso

Elegir un escenario, cruzar `packet_labels.csv` con `endpoint_variable_mapping.csv` por `(IP, unit)` y listar qué registros recibieron escrituras FC6/FC16 durante la fase de impacto. Eso da el fingerprint de verdad de referencia del ataque, útil para construir o validar un detector.
