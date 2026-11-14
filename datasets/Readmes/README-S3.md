# S3 - ARP spoofing on BSS AC-side meter

## Scenario summary

ARP spoofing on the AC-side measurement path behind the BSS inverter. Manipulation halves monitoring values and targets the DMS power basis used for SoC estimation.

## Time window

- Local (Europe/Berlin): 2026-03-05T17:15:00+01:00 to 2026-03-05T17:45:00+01:00
- UTC: 2026-03-05T16:15:00+00:00 to 2026-03-05T16:45:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1800
- Benign rows: 888
- Attack rows: 912
- Dataset timeline: 2026-03-05T16:15:00.460000+00:00 to 2026-03-05T16:44:59.460000+00:00

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

- Attack objective: ARP-spoof-based manipulation of BSS AC-side metering values, reducing monitored power values to half.
- Phase progression: benign operation, a brief reconnaissance interval, active false-data injection, and recovery.
- Targeted behavior: bias of DMS estimation inputs used for storage-state interpretation and dispatch-related reasoning.
- Analytical focus: detection of semantically plausible but systematically biased telemetry in meter-to-controller data flow.

## Dataset contents

- `dataset.csv`: full run containing benign periods, reconnaissance, and active false-data injection.
- `dataset_benign.csv`: 888 rows outside the reconnaissance and manipulation intervals.
- `dataset_attack.csv`: 912 rows within reconnaissance and manipulation intervals.
- `attack-phases.json`: separate reconnaissance and false-data-injection intervals with exclusive end boundaries.
- `experiment_overview.json`: interval structure, scenario context, and attack objective metadata.
- `state.jsonl.gz`: state-oriented timeline useful for drift and consistency analysis.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic references for affected meter/BSS communication paths.

## Data interpretation

Across its process-feature columns, the table contains 269 empty entries. Each
marks a timestamp for which that feature has no source value, and packaging
preserves it as empty. `measurement_alignment.csv.gz` describes how available
observations were placed on the one-second grid through the output time, source
time, age and alignment flags. State messages contain the available values and
record unavailable feature names in `missing_state_variables`. The count covers
feature columns; timestamps and row-level labels are counted separately.

Attack intervals use half-open boundaries `[start, end)` in UTC. Every tap
packet receives `attack` or `benign`. Packets sent from the recorded attacker
MAC are labelled `attack` even when they target another device or fall outside
an active interval. Labels also cover matching discovery replies,
attacker-opened attack connections and affected transactions on shared
connections. A phase alone does not determine a packet label.
`attacker_only.pcapng` and `benign_only.pcapng` partition the full tap and
retain packets beyond the table timeline. The dataset README describes the
label classes and their limits.

The reconnaissance log reports discovery of `192.168.1.61`. Two ARP requests
from the recorded attacker to `192.168.1.99` fall within the logged interval.
Their attacker source identifies them as reconnaissance traffic even though
the destination is not the meter. The other 14 packets in that interval are
benign. Later forged ARP replies and manipulated Modbus responses also receive
attack labels.

`dataset.csv` contains the process measurements and the row-level
`attack_active`, `attack_phase` and `attack_phase_all` labels. The endpoint
mappings connect IP addresses and Modbus unit IDs to the released signals. The
power plot shows PV, BSS, Load 1, Load 2 and Substation.
