# S1 - Industroyer against PV inverter

## Scenario summary

Industroyer-inspired Modbus attack against the Fronius PV inverter (36 kVA), including reconnaissance and subsequent protocol-level manipulation. This run is the S1 entry in the S0-S6 scenario set.

## Time window

- Local (Europe/Berlin): 2026-03-06T11:49:00+01:00 to 2026-03-06T12:19:00+01:00
- UTC: 2026-03-06T10:49:00+00:00 to 2026-03-06T11:19:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1798
- Benign rows: 885
- Attack rows: 913
- Dataset timeline: 2026-03-06T10:49:02.510000+00:00 to 2026-03-06T11:18:59.510000+00:00

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

- Attack objective: protocol-semantic manipulation of the Fronius PV inverter via Modbus control path misuse.
- Phase progression: baseline operation, reconnaissance (`nmap`), active Industroyer-style Modbus phase, and field-value manipulation overlap.
- Targeted behavior: PV-side active-power behavior is altered to influence downstream DMS interpretation and dispatch context.
- Analytical focus: correlation of PV meter behavior, attack annotations, and phase labels across process and packet perspectives.

## Dataset contents

- `dataset.csv`: full run with benign and attack periods and phase-resolved labels.
- `dataset_benign.csv`: pre/post-attack baseline segments from the same scenario run.
- `dataset_attack.csv`: attack-labeled rows for targeted Industroyer-PV analysis.
- `attack-phases.json`: precise attack phase intervals (`reconnaissance`, `industroyer_active`, `field_value_manipulation`).
- `experiment_overview.json`: timeline-level segmentation into benign and attack intervals.
- `state.jsonl.gz`: state representation preserving per-timestep values and labels.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic mapping of network identities and PV/BSS-related Modbus fields.

## Data interpretation

Across its process-feature columns, the table contains 563 empty entries. Each
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
