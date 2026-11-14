# S1-alt - Industroyer against PV inverter

## Scenario summary

Industroyer-style Modbus run against the Fronius PV inverter recorded on 2026-03-05. The run captures inverter ramp-up behavior during early Modbus interaction.

## Time window

- Local (Europe/Berlin): 2026-03-05T15:22:00+01:00 to 2026-03-05T15:52:00+01:00
- UTC: 2026-03-05T14:22:00+00:00 to 2026-03-05T14:52:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1792
- Benign rows: 882
- Attack rows: 910
- Dataset timeline: 2026-03-05T14:22:08.330000+00:00 to 2026-03-05T14:51:59.330000+00:00

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

- Attack objective: protocol-semantic manipulation of the Fronius PV inverter using the same attack family as S1.
- Phase progression: reconnaissance (`nmap`) followed by active Industroyer-style Modbus activity with overlapping field-value manipulation.
- Scenario role: separate PV attack run that can be compared with `S1_industroyer_pv`.
- Analytical focus: comparison of PV-side power response and label structure across two PV-targeting run instances.

## Dataset contents

- `dataset.csv`: complete run with benign and attack windows.
- `dataset_benign.csv`: benign portions extracted from the same run timeline.
- `dataset_attack.csv`: attack-labeled portions for direct phase-focused analysis.
- `attack-phases.json`: phase intervals for reconnaissance and active manipulation stages.
- `experiment_overview.json`: interval-level segmentation and scenario context metadata.
- `state.jsonl.gz`: state-based representation for temporal modeling and replay-style analysis.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: role/register semantics required for packet-to-process interpretation.

## Data interpretation

Across its process-feature columns, the table contains 286 empty entries. Each
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
