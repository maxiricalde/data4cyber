# S5 - ARP spoofing incl. BSS meter (two-phase)

## Scenario summary

Extended two-phase ARP spoofing with additional BSS-side manipulation. The objective is increased divergence between inverter-reported SoC and storage-side computed SoC.

## Time window

- Local (Europe/Berlin): 2026-03-06T16:56:00+01:00 to 2026-03-06T17:26:00+01:00
- UTC: 2026-03-06T15:56:00+00:00 to 2026-03-06T16:26:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1800
- Benign rows: 459
- Attack rows: 1341
- Dataset timeline: 2026-03-06T15:56:00.430000+00:00 to 2026-03-06T16:25:59.430000+00:00

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

- Attack objective: extend the two-phase ARP spoofing concept by additionally manipulating BSS-side measurements.
- Phase progression: reconnaissance (`nmap`), phase 1 load/PV falsification, and phase 2 with reduced BSS power readings (10% profile) under continued manipulation.
- Targeted behavior: induce wrong charge/discharge decisions and increase divergence between inverter-reported SoC and storage-side interpreted SoC.
- Analytical focus: multi-target MitM/FDI behavior where control-impact and state-estimation impact occur simultaneously.

## Dataset contents

- `dataset.csv`: complete timeline including reconnaissance and multi-phase attack behavior.
- `dataset_benign.csv`: benign segments before/after attack activity.
- `dataset_attack.csv`: attack-active rows including both falsification phases.
- `attack-phases.json`: detailed phase labels for recon, manipulation, impact-active periods, and phase shift to BSS-value reduction.
- `experiment_overview.json`: interval-level scenario narrative and attack objective descriptors.
- `state.jsonl.gz`: per-timestep state sequence suitable for divergence tracking and temporal modeling.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic mapping required to interpret manipulated measurement paths.

## Data interpretation

Across its process-feature columns, the table contains 211 empty entries. Each
marks a timestamp for which that feature has no source value, and packaging
preserves it as empty. `measurement_alignment.csv.gz` describes how available
observations were placed on the one-second grid through the output time, source
time, age and alignment flags. State messages contain the available values and
record unavailable feature names in `missing_state_variables`. The count covers
feature columns; timestamps and row-level labels are counted separately.

Attack intervals use half-open boundaries `[start, end)` in UTC. Every tap
packet receives `attack` or `benign`. Attack labels cover recorded operations,
matching discovery replies, attacker-opened attack connections, and affected
transactions on shared connections. All remaining traffic receives `benign`,
including traffic during active phases. `attacker_only.pcapng` and
`benign_only.pcapng` partition the full tap and retain packets beyond the table
timeline. The dataset README defines the matching rules and limits.

`dataset.csv` contains the process measurements and the row-level
`attack_active`, `attack_phase` and `attack_phase_all` labels. The endpoint
mappings connect IP addresses and Modbus unit IDs to the released signals. The
power plot shows PV, BSS, Load 1, Load 2 and Substation.
