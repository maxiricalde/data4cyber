# Data4Cyber — Dispositivos, roles de red y recopilación de datos

Documento complementario de `topology_combined.pdf` y `topology.yaml`. Describe **cada dispositivo** del testbed, cómo se comporta en la capa eléctrica y en la capa de red, cuál es su trabajo principal y su papel concreto en la producción de las métricas del dataset.

> Dos capas, un mismo testbed. La **capa eléctrica** indica *dónde* se toma una medición. La **capa de red** indica *cómo* viaja ese valor. Se documentan por separado a propósito.

---

## 1\. Catálogo de dispositivos

| Dispositivo | Capa | IP | MAC | Protocolo | Perfil Modbus | Units | Trabajo principal |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Controlador DMS/EMS | control \+ red | 192.168.1.11 | `00:13:3b:9d:00:8d` | Modbus/TCP, MQTT | — | — | Maestro Modbus, poller, cliente MQTT |
| Switch OT | red | — | — | Ethernet | — | — | Agregación L2, punto de espejo del TAP |
| Inversor PV (Fronius 36 kVA) | generación \+ red | 192.168.1.88 | `00:03:ac:03:7b:df` | Modbus/TCP | `fronius` | 36/37/38/46/48 (el mapa usa 48\) | Generación PV \+ setpoint escribible |
| Inversor de batería (Sunny Island) | almacenamiento \+ red | 192.168.1.184 | `00:40:ad:9b:3f:25` | Modbus/TCP | `sunny_island` | 3 | Despacho de batería \+ setpoint escribible |
| Janitza UMG508 `umg6c` | medición \+ red | 192.168.1.61 | `00:0e:6b:05:22:52` | Modbus/TCP | `JanitzaUMG508` | 1–4 | Medición BSS \+ Carga A |
| Janitza UMG508 `umg7a` | medición \+ red | 192.168.1.62 | `00:0e:6b:05:64:3f` | Modbus/TCP | `JanitzaUMG508` | 1–3 | Medición Carga B \+ PV |
| Janitza UMG508 `umg_ront` | medición \+ red | 192.168.1.65 | `00:0e:6b:05:25:37` | Modbus/TCP | `JanitzaUMG508` | 1 | Medición subestación (PCC) |
| TAP de red pasivo | observación | — | — | — | — | — | Espeja tráfico, nunca alimenta la tabla de proceso |
| Fuente de señal de precio MQTT | externa | — | — | MQTT | — | — | Entrada económica para el despacho |
| Host atacante | adversario | 192.168.1.20 / 10.0.104.26 | varía | Modbus/TCP, ARP | — | — | Ataque / inyección MITM |

---

## 2\. Detalle por dispositivo

### 2.1 Controlador DMS/EMS — `192.168.1.11`

**Rol eléctrico.** Ninguno directo: no está sobre el camino de potencia. Es el cerebro supervisor que decide setpoints e interpreta el estado de la red.

**Rol de red.** Es el **hub** y el **maestro Modbus/TCP**. Cada dispositivo de campo es un esclavo que solo responde cuando el DMS/EMS pregunta. En los mapeos aparece como `interface_ip: 192.168.1.11`, lo que confirma que es la interfaz de polling de todos los dispositivos.

**Trabajo principal.**

- Hacer polling de los cinco puntos de medición y de ambos inversores por Modbus/TCP.  
- Consumir la señal de precio MQTT y traducirla en decisiones de despacho.  
- Exponer el estado de proceso que luego se convierte en `dataset.csv`.

**Papel en la recopilación de datos.** **Inicia** cada medición. Si el DMS/EMS deja de hacer polling, no existen muestras nuevas. Es además el punto donde la señal económica (MQTT) se encuentra con el estado físico (Modbus).

---

### 2.2 Switch OT — L2 no gestionado

**Rol eléctrico.** Ninguno.

**Rol de red.** Punto de agregación de la LAN OT (`192.168.1.0/24`). No tiene IP de gestión en el inventario, así que es transparente: reenvía Modbus/TCP entre el DMS/EMS y los esclavos.

**Trabajo principal.** Proveer la trama L2 conmutada y actuar como **punto de espejo** para el TAP pasivo.

**Papel en la recopilación de datos.** No crea datos, pero es el lugar físico donde se observa todo el tráfico. La captura del TAP solo es posible porque todo cruza este switch.

---

### 2.3 Inversor PV — Fronius 36 kVA — `192.168.1.88`

**Rol eléctrico.** Rama de generación del feeder de baja tensión. Inyecta hasta 36 kVA y se mide aguas abajo en `PV-Inverter-AC-Meter`.

**Rol de red.** Esclavo Modbus/TCP, perfil `fronius`. El inventario lista las units `36;37;38;46;48`, mientras que el mapa de registros publicado documenta la **unit 48**. Tratá los unit IDs extra como espacio de direccionamiento del equipo, no como medidores adicionales.

**Trabajo principal.** Convertir DC del arreglo PV a AC y aceptar setpoints de potencia activa desde el DMS/EMS.

**Registros (de `endpoint_variable_mapping.csv`).**

| Función | Acceso | Dirección | Cant. | Señal | Unidad | Formato |
| :---- | :---- | ----: | ----: | :---- | :---- | :---- |
| 3 | read | 40091 | 2 | `p_sum3` | W | float |
| 3 | read | 40134 | 1 | `p_max` | W | ushort |
| 3 | read | 40136 | 1 | `s_max` | VA | ushort |
| 3 | read | 40242 | 1 | `p_set_percent` | — | ushort |
| 6 | write | 40242 | 1 | `p_set_percent` | — | ushort |
| 16 | write | 40242 | 1 | `p_set_percent` | — | ushort |
| 6 | write | 40246 | 1 | `p_set_confirm` | — | short |
| 16 | write | 40246 | 1 | `p_set_confirm` | — | short |

**Papel en la recopilación de datos.** Matiz importante: **el inversor no es fuente de columnas de proceso publicadas.** No hay columnas `PV-Inverter.*` en `dataset.csv`. La potencia PV que analizás proviene del **medidor de CA** (`PV-Inverter-AC-Meter`, `.62` unit 3), no de los registros propios del inversor. Los registros del inversor se documentan porque son la **superficie de control y de ataque**.

**Relevancia para el ataque.** `p_set_percent` es escribible por FC 6/16. Ese es el camino Industroyer: escribir un setpoint, confirmarlo, y la salida física PV cambia mientras el medidor reporta el efecto.

---

### 2.4 Inversor de batería — Sunny Island — `192.168.1.184`

**Rol eléctrico.** Rama de almacenamiento. Carga o descarga para balancear el feeder.

**Rol de red.** Esclavo Modbus/TCP, perfil `sunny_island`, unit 3\.

**Trabajo principal.** Despachar potencia activa y reportar el estado del almacenamiento.

**Registros.**

| Función | Acceso | Dirección | Cant. | Señal | Unidad | Formato |
| :---- | :---- | ----: | ----: | :---- | :---- | :---- |
| 3 | read | 30775 | 2 | `p_sum3` | W | int |
| 3 | read | 40149 | 2 | `p_set_string` | W | int |
| 16 | write | 40149 | 2 | `p_set_string` | W | int |
| 16 | write | 40151 | 2 | `power_com` | — | uint |

**Papel en la recopilación de datos.** Mismo matiz que el inversor PV: no se publican columnas de proceso `Battery-Inverter.*`. La potencia AC de la batería proviene de `BSS-Inverter-AC-Meter` (`.61` unit 3). El dataset sí incluye `Battery-SOC-Reference.soc_value` y `Battery-SOC-Reported.soc_value` como contexto de almacenamiento, pero su fuente Modbus exacta **no está documentada** en `endpoint_variable_mapping.csv`; no asumas que son una lectura directa de registro.

**Relevancia para el ataque.** `p_set_string` y `power_com` son escribibles. S2 apunta a este inversor.

---

### 2.5 Medidores Janitza UMG508 — las fuentes reales de medición

Tres medidores físicos exponen **cinco puntos lógicos de medición** mediante unit IDs Modbus. Este es el detalle más importante de toda la topología.

| Medidor físico | IP | Unit | Punto lógico | Ubicación en la grilla |
| :---- | :---- | :---- | :---- | :---- |
| `umg6c` | 192.168.1.61 | 3 | BSS-Inverter-AC-Meter | Conexión AC del inversor BSS |
| `umg6c` | 192.168.1.61 | 4 | Load-A-AC-Meter | Conexión Carga A |
| `umg7a` | 192.168.1.62 | 2 | Load-B-AC-Meter | Conexión Carga B |
| `umg7a` | 192.168.1.62 | 3 | PV-Inverter-AC-Meter | Conexión AC del inversor PV |
| `umg_ront` | 192.168.1.65 | 1 | Substation-AC-Meter | Subestación secundaria / PCC |

**Rol eléctrico.** Miden tensión, corriente, potencia y calidad de energía en cada ubicación de la grilla. Son los instrumentos que convierten el flujo de potencia físico en números.

**Rol de red.** Esclavos Modbus/TCP, perfil `JanitzaUMG508`. Cada punto lógico es un unit ID separado sobre la misma IP. El DMS/EMS los consulta con FC 3 (read holding registers).

**Trabajo principal.** Medición trifásica de calidad de energía: tensión, corriente, potencia activa/reactiva/aparente por fase y total, factor de potencia y frecuencia.

**Papel en la recopilación de datos.** Son la **fuente principal de las columnas de proceso del dataset**: 5 puntos × 28 señales \= **140 columnas**. Cada columna `<Medidor>.<señal>` de `dataset.csv` proviene de aquí.

#### Catálogo de señales (idéntico para los cinco puntos)

| Variable | Dirección | Cant. | Unidad | Significado |
| :---- | ----: | ----: | :---- | :---- |
| `realtime` | 0 | 4 | 2 s | base de tiempo realtime del medidor |
| `uln1` / `uln2` / `uln3` | 19000 / 19002 / 19004 | 2 | V | tensión fase-neutro |
| `ull12` / `ull23` / `ull31` | 19006 / 19008 / 19010 | 2 | V | tensión fase-fase |
| `iln1` / `iln2` / `iln3` | 19012 / 19014 / 19016 | 2 | A | corriente de fase |
| `i_sum3` | 19018 | 2 | A | corriente de neutro / suma vectorial |
| `pln1` / `pln2` / `pln3` | 19020 / 19022 / 19024 | 2 | W | potencia activa por fase |
| `p_sum3` | 19026 | 2 | W | potencia activa total |
| `sln1` / `sln2` / `sln3` | 19028 / 19030 / 19032 | 2 | VA | potencia aparente por fase |
| `s_sum3` | 19034 | 2 | VA | potencia aparente total |
| `qln1` / `qln2` / `qln3` | 19036 / 19038 / 19040 | 2 | var | potencia reactiva por fase |
| `q_sum3` | 19042 | 2 | var | potencia reactiva total |
| `cos_phi1` / `cos_phi2` / `cos_phi3` | 19044 / 19046 / 19048 | 2 | — | factor de potencia por fase |
| `freq` | 19050 | 2 | Hz | frecuencia medida |
| `phase_seq` | 19052 | 2 | — | campo de rotación (1 derecha, 0 ninguna, −1 izquierda) |

Todos los valores son `float` (32 bits, 2 registros). El bloque de reloj en las direcciones 0–12 (`realtime`, `systime`, `day`, `month`, `year`, `hour`, `min`, `sec`, `weekday`) permite el sellado temporal.

---

### 2.6 TAP de red pasivo

**Rol eléctrico.** Ninguno.

**Rol de red.** Recibe un espejo del tráfico del switch OT y lo escribe en `network_tap.pcapng`. Es **pasivo**: no inyecta paquetes ni está en el camino de reenvío.

**Trabajo principal.** Producir la evidencia a nivel de paquete: `packet_labels.csv`, `attacker_only.pcapng`, `benign_only.pcapng`.

**Papel en la recopilación de datos.** **No** es fuente de métricas de proceso. El TAP describe *cómo* se ejecutó un ataque; `dataset.csv` describe *qué pasó físicamente*. Se correlacionan por tiempo, no por derivación.

---

### 2.7 Fuente de señal de precio MQTT (externa)

**Rol eléctrico.** Ninguno.

**Rol de red.** Publicador externo consumido por el DMS/EMS por MQTT.

**Trabajo principal.** Proveer la señal de precio económico que impulsa las decisiones de despacho.

**Papel en la recopilación de datos.** Produce `MQTT-Price-Signal.price_eur_per_kwh` (y, en S6, `MQTT-Price-Signal.event`). Es una señal de **contexto/económica**, no una lectura Modbus de medidor.

**Relevancia para el ataque.** S6 compromete esta cadena de suministro: tres publicaciones de precio manipuladas quedan registradas en `attack_events.csv`, pero la captura del TAP etiqueta todos los paquetes como `benign`.

---

### 2.8 Host atacante

**Rol eléctrico.** Ninguno.

**Rol de red.** Host rogue en el segmento OT. Su ubicación cambia según el escenario:

| Escenarios | Dirección | Vector |
| :---- | :---- | :---- |
| S1, S1-alt, S2 | `192.168.1.20` | Manipulación Modbus/TCP estilo Industroyer |
| S0, S6 | `10.0.104.26` | Host Modbus (S6: cadena de suministro MQTT) |
| S3, S4, S5 | sin IP estable | ARP/MitM en el camino con MAC spoofeada |

**Trabajo principal.** Inyectar el ataque mientras el DMS/EMS sigue haciendo polling con normalidad.

**Papel en la recopilación de datos.** No produce columnas del dataset; produce **efectos** en ellas (cambios de setpoint, valores de medidor falseados) y **evidencia** en la captura de paquetes.

---

## 3\. Cómo se obtienen las métricas

```
1. El medidor/inversor mide internamente
        |
2. El valor queda en registros holding Modbus (dirección conocida)
        |
3. El DMS/EMS hace polling Modbus/TCP (FC 3 = read holding registers)
        |
4. El bloque de registros se decodifica (float / int / ushort)
        |
5. El pipeline ubica la señal en una grilla UTC de 1 segundo
        |
6. dataset.csv  +  state.jsonl.gz
```

### 3.1 Ejemplo concreto

`PV-Inverter-AC-Meter.p_sum3` se produce así:

| Campo | Valor |
| :---- | :---- |
| IP | `192.168.1.62` |
| Unit ID | `3` |
| Código de función | `3` (read) |
| Dirección inicial | `19026` |
| Cantidad | 2 registros |
| Formato | `float` |
| Unidad | `W` |

El DMS/EMS lee dos registros desde la dirección 19026 en la unit 3 de `.62`, los interpreta como float de 32 bits, y el resultado se convierte en la columna `PV-Inverter-AC-Meter.p_sum3`.

### 3.2 Qué contiene una fila de `dataset.csv`

| Bloque | Columnas | Origen |
| :---- | ----: | :---- |
| Etiquetas | 4 | `timestamp`, `attack_active`, `attack_phase`, `attack_phase_all` |
| Mediciones de medidores | 140 | 5 puntos lógicos × 28 señales |
| Contexto de almacenamiento | 2 | `Battery-SOC-Reference`, `Battery-SOC-Reported` |
| Contexto económico | 1–2 | `MQTT-Price-Signal` (S6 agrega `event`) |
| Contexto operativo | 8 | `Profile.*` (irradiancia, temperatura, setpoints PV/carga) |

Total para S1: **155 columnas**.

### 3.3 La grilla de 1 segundo es más densa que el muestreo real

Los medidores no producen un valor nuevo cada segundo. En la corrida S1, una señal de medidor tiene alrededor de **429 timestamps de origen distintos en \~1798 s**, es decir, una muestra real cada **3,5–4,5 s** aproximadamente. Por eso el pipeline:

- crea una fila de salida por segundo,  
- le adjunta la muestra **más reciente**,  
- lo registra en `measurement_alignment.csv.gz`.

Columnas de `measurement_alignment.csv.gz`:

| Columna | Significado |
| :---- | :---- |
| `timestamp` | tiempo de la grilla de salida |
| `feature` | columna del dataset |
| `source_timestamp` | cuándo se midió realmente el valor |
| `age_seconds` | cuántos segundos tiene la muestra en ese paso de salida |
| `observed_at_step` | si coincide exactamente con el paso de la grilla |
| `carried` | si el valor fue arrastrado desde una muestra anterior |

Las celdas vacías significan que **no existía muestra** para esa señal. Se preservan vacías: sin interpolación ni relleno de borde. S1 tiene **563** de esas entradas vacías.

`state.jsonl.gz` guarda la misma información como un estado JSON por fila, con `missing_state_variables` indicando las señales sin valor.

---

## 4\. Lectura vs escritura: la superficie de ataque

| Dispositivo | Señal | Acceso | Uso en el ataque |
| :---- | :---- | :---- | :---- |
| Inversor PV | `p_set_percent` | write FC 6/16 | forzar el setpoint de potencia activa PV |
| Inversor PV | `p_set_confirm` | write FC 6/16 | confirmar el cambio |
| Inversor de batería | `p_set_string` | write FC 16 | forzar el setpoint de batería |
| Inversor de batería | `power_com` | write FC 16 | habilitar control por comunicación |
| Medidores | las 28 señales | read FC 3 | manipulación de medición vía ARP/MitM (S3–S5) |

Los medidores son objetivos **solo de lectura**. Los inversores son los objetivos **escribibles**. Esa distinción explica por qué los escenarios Industroyer (S1, S1-alt, S2) golpean inversores y los escenarios ARP (S3–S5) golpean medidores.

---

## 5\. Productos de datos por capa

| Archivo | Capa | Qué contiene |
| :---- | :---- | :---- |
| `dataset.csv` | proceso | grilla de 1 s, proceso \+ contexto, etiquetas por fila |
| `dataset_benign.csv` / `dataset_attack.csv` | proceso | filtrados por `attack_active` |
| `state.jsonl.gz` | proceso | un registro de estado por fila |
| `measurement_alignment.csv.gz` | proceso | edad de muestra, tiempo de origen, bandera de arrastre |
| `network_tap.pcapng` | red | captura completa de paquetes |
| `packet_labels.csv` | red | `attack` / `benign` por paquete |
| `attacker_only.pcapng` / `benign_only.pcapng` | red | particiones por clase de paquete |
| `attack-phases.json` | etiquetas | intervalos de fase (UTC, semiabiertos) |
| `attack_events.csv` | etiquetas | operaciones de ataque registradas |
| `endpoint_variable_mapping.csv` | mapeo | endpoint → registro → variable |
| `ip_unit_device_mapping.csv` | mapeo | IP \+ unit → punto lógico |

---

## 6\. Advertencias

1. **Una IP no es un medidor.** Tres medidores Janitza físicos exponen cinco puntos lógicos mediante unit IDs.  
2. **Los registros de los inversores no se publican como columnas de proceso.** La potencia PV/BSS del dataset proviene de los medidores de CA, no de los inversores.  
3. **La fuente de `Battery-SOC-*` no está documentada.** Las columnas existen, pero `endpoint_variable_mapping.csv` no las mapea a un registro.  
4. **El TAP no alimenta `dataset.csv`.** Las capas de proceso y de red son paralelas y se correlacionan por tiempo.  
5. **Las etiquetas de paquete de S6 son todas `benign`.** Las publicaciones MQTT manipuladas están en `attack_events.csv`.  
6. **La captura del TAP puede extenderse más allá de la ventana de proceso de 30 minutos.**  
7. **La identidad del atacante varía.** IP y MAC cambian entre escenarios; S3–S5 usan un MITM con MAC spoofeada y sin IP estable.