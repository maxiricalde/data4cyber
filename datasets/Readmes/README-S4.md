# S4 - ARP spoofing on load/PV meters (two-phase)

## Scenario summary

Two-phase ARP spoofing against measurement devices behind load 1, load 2 and PV. Phase 1 creates the impression of low load and high PV generation (charging tendency), phase 2 inverts this condition (discharging tendency).

## Time window

- Local (Europe/Berlin): 2026-03-06T16:13:00+01:00 to 2026-03-06T16:43:00+01:00
- UTC: 2026-03-06T15:13:00+00:00 to 2026-03-06T15:43:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1798
- Benign rows: 541
- Attack rows: 1257
- Dataset timeline: 2026-03-06T15:13:02.440000+00:00 to 2026-03-06T15:42:59.440000+00:00

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

- Attack objective: two-phase ARP spoofing to invert DMS residual-load interpretation and force opposite dispatch decisions.
- Phase progression: reconnaissance (`nmap`), then phase 1 (loads forged low and PV forged high), then phase 2 (loads forged high and PV forged low), with overlapping manipulation/impact labels.
- Targeted behavior: the first phase creates a charging tendency. The second phase creates a discharging tendency under the opposite falsified conditions.
- Analytical focus: detection of staged false-data-injection campaigns with deliberate phase transitions.

## Dataset contents

- `dataset.csv`: complete scenario with benign, reconnaissance, and two attack phases in one timeline.
- `dataset_benign.csv`: benign and inter-phase segments for comparative analysis.
- `dataset_attack.csv`: rows belonging to active reconnaissance/manipulation/impact windows.
- `attack-phases.json`: explicit phase boundaries for recon, phase 1, phase 2, and overlapping impact tags.
- `experiment_overview.json`: attack/benign intervals and timeline narrative for this two-phase run.
- `state.jsonl.gz`: state representation for analyzing sequential phase transitions.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic references for targeted load/PV/BSS communication channels.

## Data interpretation

Across its process-feature columns, the table contains 4,417 empty entries.
Each marks a timestamp for which that feature has no source value, and packaging
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
