# Data4Cyber Dataset

## 1) Purpose and Scope

This release contains process measurements and network traffic from a
distributed-energy management testbed. The scenarios cover normal operation,
Modbus control attacks, ARP/MitM measurement manipulation and an MQTT broker
compromise. Process measurements, activity labels, attack phases, packet
classes and device mappings are organized by scenario.

Each process table uses a one-second UTC time grid. Network captures retain
their recorded packet timestamps and can extend beyond the process-table
window.

## 2) Dataset Composition

The release contains eight scenario folders: S0 through S6 and a second PV
Industroyer run, S1-alt. Across the eight process tables there are 14,354 rows:
6,768 benign rows and 7,586 rows marked active by the process activity labels.

The scenario windows span 5 March 2026 through 6 March 2026. The earliest
window begins at 14:19 Europe/Berlin on 5 March. The latest ends at 17:26
Europe/Berlin on 6 March.

## 3) Scenario Catalog

| Scenario | Folder | Attack family | Local window (Europe/Berlin) | UTC window | Rows (total / benign / attack-active) |
|---|---|---|---|---|---:|
| S0 | `S0_benign_baseline` | Benign operation | 2026-03-05 14:19-14:49 | 2026-03-05 13:19-13:49 | 1798 / 1798 / 0 |
| S1 | `S1_industroyer_pv` | Industroyer Modbus | 2026-03-06 11:49-12:19 | 2026-03-06 10:49-11:19 | 1798 / 885 / 913 |
| S1-alt | `S1_industroyer_pv_alt` | Industroyer Modbus | 2026-03-05 15:22-15:52 | 2026-03-05 14:22-14:52 | 1792 / 882 / 910 |
| S2 | `S2_industroyer_bss` | Industroyer Modbus | 2026-03-05 16:04-16:34 | 2026-03-05 15:04-15:34 | 1768 / 865 / 903 |
| S3 | `S3_arp_spoof_bss_meter_half_values` | ARP/MitM measurement manipulation | 2026-03-05 17:15-17:45 | 2026-03-05 16:15-16:45 | 1800 / 888 / 912 |
| S4 | `S4_arp_spoof_loads_pv_two_phase` | Two-phase ARP/MitM manipulation | 2026-03-06 16:13-16:43 | 2026-03-06 15:13-15:43 | 1798 / 541 / 1257 |
| S5 | `S5_arp_spoof_loads_pv_bss_two_phase` | Two-phase ARP/MitM manipulation | 2026-03-06 16:56-17:26 | 2026-03-06 15:56-16:26 | 1800 / 459 / 1341 |
| S6 | `S6_mqtt_supply_chain_compromise` | MQTT price-signal manipulation | 2026-03-06 14:48-15:18 | 2026-03-06 13:48-14:18 | 1800 / 450 / 1350 |

## 4) Directory Layout

```text
data4cyber_dataset/
├── README.md
├── CHANGES.md
├── LICENSE.txt
├── SHA256SUMS.json
├── S0_benign_baseline/
├── S1_industroyer_pv/
├── S1_industroyer_pv_alt/
├── S2_industroyer_bss/
├── S3_arp_spoof_bss_meter_half_values/
├── S4_arp_spoof_loads_pv_two_phase/
├── S5_arp_spoof_loads_pv_bss_two_phase/
└── S6_mqtt_supply_chain_compromise/
```

Each scenario folder has its own README with its timeline, row counts,
measurements and network data.

## 5) Standard Artifacts in Each Scenario Folder

| Artifact | Description |
|---|---|
| `README.md` | Scenario description, timing and contents. |
| `dataset.csv` | Synchronized process and context measurements with row-level activity and phase fields. |
| `dataset_benign.csv` | Rows with `attack_active=False`. |
| `dataset_attack.csv` | Rows with `attack_active=True`. |
| `state.jsonl.gz` | One state record for each row in `dataset.csv`. |
| `attack-phases.json` | Attack phase names, categories, targets and UTC intervals. |
| `metadata.json` | Scenario identifiers, time window, timezone and sampling interval. |
| `scenario_definition.json` | Scenario title and description. |
| `experiment_overview.json` | Scenario timeline and activity intervals. |
| `network_tap.pcapng` | Complete network tap capture for the scenario. |
| `packet_labels.csv` | One binary class and associated context for each packet in the tap capture. |
| `attack_events.csv` | Recorded attack operations, including the S6 price-publication events. |
| `attacker_only.pcapng` | Packets with `label=attack` in `packet_labels.csv`. |
| `benign_only.pcapng` | Packets with `label=benign` in `packet_labels.csv`. |
| `attacker_only_meta.json`, `benign_only_meta.json` | Packet count, selected class and time information for each packet subset. |
| `ip_device_mapping.csv` | Network addresses and their associated device roles. |
| `modbus_variable_mapping.csv` | Modbus register details associated with process signals. |
| `ip_unit_device_mapping.csv` | IP address and Modbus unit ID associated with each logical measurement point. |
| `endpoint_variable_mapping.csv` | Endpoint, unit, function code and register range linked to dataset variables and their units. |
| `network_node_inventory.csv` | Network nodes with their roles and available network addresses. |
| `measurement_alignment.csv.gz` | Output-grid time, observed sample time, sample age and carry-forward status for each feature. |
| `plots/01_power_timeseries.pdf` | PV, BSS, Load 1, Load 2 and Substation power traces. |
| `plots/02_context_and_communication.pdf` | Scenario context and communication activity. |

## 6) Data Model and Label Semantics

The process tables use timestamps on a one-second UTC grid. Device and signal
columns follow the `<Device>.<Signal>` form, such as
`BSS-Inverter-AC-Meter.p_sum3` and
`MQTT-Price-Signal.price_eur_per_kwh`.

`attack_active` marks process-row activity. `attack_phase` gives the phase
at that time, and `attack_phase_all` lists overlapping phases when more than
one applies. In `state.jsonl.gz`, `malicious` represents the same
process-row activity. The `state` object contains the measured values
available for that row; `missing_state_variables` names the measurements
without values. Empty measurement cells remain empty and are not replaced by
interpolated or boundary-filled values.

The state logs contain 14,354 records across 8 scenarios, one for each
process-table row. The CSV tables contain 7,569 empty feature entries.
Scenario READMEs give the corresponding counts for each table.

## 7) Cyber-Physical Semantics by Scenario Family

### Benign operation (S0)

S0 records normal operation and provides measurements of PV generation,
battery dispatch, load demand and substation exchange.

### Industroyer-style Modbus control attacks (S1, S1-alt and S2)

S1 and S1-alt record attacks directed at the PV inverter. S2 records an attack
directed at the battery storage system. Their process tables contain the
associated PV, battery, load and substation measurements.

### ARP/MitM measurement manipulation (S3, S4 and S5)

S3 records manipulation of the BSS AC-side meter values. S4 records a
two-phase manipulation involving the load and PV meters. S5 extends the
two-phase scenario to include BSS-side measurements. Their tables include
power measurements and, where recorded, reference and reported state of
charge.

### MQTT supply-chain compromise (S6)

S6 records a compromise of the MQTT broker that supplies the price signal.
Three manipulated price publications are listed in `attack_events.csv`, and
the process table records the related scenario activity. All packets in the
S6 tap capture have the packet label `benign`; the capture contains no MQTT
publication matching those events.

## 8) Attack Phase Ontology and Label Meaning

The phase records in `attack-phases.json` describe reconnaissance, control
operations, measurement manipulation, impact and scenario-specific activity.
Intervals use UTC and half-open boundaries, `[start, end)`. The process-table
fields `attack_active`, `attack_phase` and `attack_phase_all` describe
activity at each one-second timestamp.

Packet labels describe individual network frames. In
`packet_labels.csv`, `label` is either `attack` or `benign`.
`attack_type`, `attack_phase` and `event_id` provide context for the
packet. The packet-level `attack_active` and `attack_phase` fields describe
whether the packet timestamp falls inside a recorded phase; they do not by
themselves determine the packet's binary label.

Packets from the identified attacker host are labelled `attack`. Packets
associated with recorded attack operations and their protocol exchanges also
receive that label. Other captured packets are labelled `benign`. The
`attacker_only.pcapng` and `benign_only.pcapng` files correspond to these
two values of `packet_labels.csv`'s `label` column. Together they contain
each tap packet once, with its recorded bytes, timestamp and order preserved.

## 9) Signal Semantics and Device-Role Groups

The process measurements cover five power-flow locations: PV, BSS, Load 1,
Load 2 and Substation. Every scenario's `01_power_timeseries.pdf` displays
all five. Storage signals include reference and reported state of charge.
The MQTT price signal records the economic input associated with S6, and
`Profile.*` columns describe operating context.

The mapping files connect these measurements to the network. The
`ip_unit_device_mapping.csv` identifies the device and logical measurement
point for each IP address and Modbus unit ID.
`endpoint_variable_mapping.csv` links endpoint and register details to the
corresponding dataset variables, grid locations, units and data formats.
`modbus_variable_mapping.csv` describes the register semantics of those
signals, while `network_node_inventory.csv` lists the network nodes and
their roles.

`measurement_alignment.csv.gz` relates each output timestamp and feature to
its observed sample time. Its `age_seconds`, `observed_at_step` and
`carried` columns describe the sample's timing on the one-second grid.

## 10) Cross-Layer Scenario Context

The release pairs process measurements with activity phases, network packets,
packet labels and device mappings. S1 and S2 contain Modbus control activity
alongside PV or battery measurements. S3 through S5 contain meter
manipulation scenarios alongside power-flow and state-of-charge measurements.
S6 pairs the broker's price-publication events with price and dispatch
measurements.

## 11) Research Questions

The scenarios support study of questions such as:

- How do process-state detectors respond to attacks on control, measurement and economic-context signals?
- Which measurement groups show the operational effects of each scenario?
- How do reported and reference state-of-charge values differ during meter manipulation?
- How do packet-level classes and process-row activity describe different parts of the same scenario?
- How well do findings transfer between the two PV runs and the other scenario families?

## 12) License and Citation

The dataset is licensed under the Creative Commons Attribution 4.0
International License (CC BY 4.0). The complete license text is in
`LICENSE.txt`.

When using this dataset, please cite the companion publication and the dataset
record.

Companion publication:

> Ö. Sen, L. Bader, M. Emara, M. Serror, B. Schwalm, J. Tsurumi, T. Oba, T. Izawa, and Y. Ujiie, "Data4Cyber: Labeled Cyber-Physical Datasets for Distribution-Grid Management Systems Under Representative OT Attacks," in Proc. 2026 IEEE International Conference on Cyber Security and Resilience (IEEE CSR), 2026.

Dataset record:

> Sen, Ö., Bader, L., Emara, M., Serror, M., Schwalm, B., Tsurumi, J., Oba, T., Izawa, T., and Ujiie, Y. (2026). Data4Cyber: Labeled Cyber-Physical Dataset for Distribution-Grid Management Systems Under Representative OT Attacks [Data set]. Zenodo. https://doi.org/10.5281/zenodo.19965384
