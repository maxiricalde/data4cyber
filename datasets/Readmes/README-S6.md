# S6 - MQTT supply-chain compromise

## Scenario summary

Supply-chain style compromise of the MQTT price server. Price incentives are manipulated, leading to incorrect DMS operational decisions. The attack is comparatively stealthy in process-network traffic but observable in context and process outcomes.

## Time window

- Local (Europe/Berlin): 2026-03-06T14:48:00+01:00 to 2026-03-06T15:18:00+01:00
- UTC: 2026-03-06T13:48:00+00:00 to 2026-03-06T14:18:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1800
- Benign rows: 450
- Attack rows: 1350
- Dataset timeline: 2026-03-06T13:48:00.690000+00:00 to 2026-03-06T14:17:59.690000+00:00

## Final artifacts

- `dataset.csv` (final, time-synchronized)
- `dataset_benign.csv`
- `dataset_attack.csv`
- `attack-phases.json`
- `metadata.json`
- `scenario_definition.json`
- `experiment_overview.json`
- `ip_device_mapping.csv`
- `modbus_variable_mapping.csv`
- `network_tap.pcapng`
- `benign_only.pcapng`
- `attacker_only.pcapng`
- `packet_labels.csv`
- `attack_events.csv`
- `benign_only_meta.json`
- `attacker_only_meta.json`
- `state.jsonl.gz`
- `plots/`
- `ip_unit_device_mapping.csv`
- `endpoint_variable_mapping.csv`
- `network_node_inventory.csv`
- `measurement_alignment.csv.gz`

## Experiment details

- Attack objective: manipulate MQTT-delivered price incentives through supply-chain style compromise of the price source.
- Phase progression: broad attack-active interval with an embedded sub-interval of manipulated price publications.
- Targeted behavior: bias DMS charge/discharge decisions through context-channel manipulation rather than direct Modbus payload tampering.
- Analytical focus: identification of cyber-physical impact when network-level process attack traces are weaker than operational outcome shifts.

## Dataset contents

- `dataset.csv`: full scenario timeline with benign and attack-labeled context-driven manipulation periods.
- `dataset_benign.csv`: benign portions of the same run for in-scenario baseline comparison.
- `dataset_attack.csv`: attack-active rows for targeted context-manipulation analysis.
- `attack-phases.json`: phase intervals for overall MQTT attack activity and price-manipulation subphase.
- `experiment_overview.json`: timeline semantics describing benign and attack interval boundaries.
- `state.jsonl.gz`: state-sequence representation preserving process variables and labels per timestep.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic references for interpreting infrastructure roles and protocol fields.

## Data interpretation

Across its process-feature columns, the table contains 1,057 empty entries.
Each marks a timestamp for which that feature has no source value, and packaging
preserves it as empty. `measurement_alignment.csv.gz` describes how available
observations were placed on the one-second grid through the output time, source
time, age and alignment flags. State messages contain the available values and
record unavailable feature names in `missing_state_variables`. The count covers
feature columns; timestamps and row-level labels are counted separately.

The broker is the compromised component in S6. Broker telemetry and the
receiving client's log record three manipulated price publications, retained
in `attack_events.csv`. The tap contains no MQTT traffic on port 1883 or
price publication payloads. Its ordinary process packets receive `benign`,
including during the compromise. The table's attack activity remains intact.
All tap packets are retained and labelled. The attack subset is empty.

`dataset.csv` contains the process measurements and the row-level
`attack_active`, `attack_phase` and `attack_phase_all` labels. The endpoint
mappings connect IP addresses and Modbus unit IDs to the released signals. The
power plot shows PV, BSS, Load 1, Load 2 and Substation.
