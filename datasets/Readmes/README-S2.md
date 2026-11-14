# S2 - Industroyer against BSS inverter

## Scenario summary

Industroyer-inspired Modbus attack against the BSS inverter (Sunny Island, 15 kVA) with focus on unauthorized operational manipulation.

## Time window

- Local (Europe/Berlin): 2026-03-05T16:04:00+01:00 to 2026-03-05T16:34:00+01:00
- UTC: 2026-03-05T15:04:00+00:00 to 2026-03-05T15:34:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1768
- Benign rows: 865
- Attack rows: 903
- Dataset timeline: 2026-03-05T15:04:32.030000+00:00 to 2026-03-05T15:33:59.030000+00:00

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

- Attack objective: Industroyer-style Modbus manipulation targeting the Sunny Island BSS inverter dispatch path.
- Phase progression: baseline operation, reconnaissance (`nmap`), active battery-focused manipulation, and overlapping field-value manipulation.
- Targeted behavior: BSS active-power trajectory and related storage-state interpretation are influenced by protocol-semantic actions.
- Analytical focus: association of BSS-side process changes with attack annotations and Modbus phase annotations.

## Dataset contents

- `dataset.csv`: full run with both benign and attack intervals on a unified time grid.
- `dataset_benign.csv`: benign periods for in-run baseline comparison.
- `dataset_attack.csv`: attack periods for focused BSS manipulation analysis.
- `attack-phases.json`: explicit phase boundaries for recon and battery-targeted manipulation stages.
- `experiment_overview.json`: timeline segmentation and scenario-context descriptors.
- `state.jsonl.gz`: temporal state log suited for sequence models and stateful detection analysis.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: full tap and packet-label selections.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic map from addresses/registers to operational meaning.

## Data interpretation

Across its process-feature columns, the table contains 284 empty entries. Each
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

The reconnaissance log records an Nmap scan of the BSS inverter at
`192.168.1.184`, but the tap contains no packet attributable to that scan in
the 1.75-second interval. Its only ARP request is from `192.168.1.49` to
`192.168.1.47`, which does not match the logged target or recorded attacker
identity. The 230 packets in the interval remain benign. The later Modbus
write attempts and their correlated traffic receive attack labels.

`dataset.csv` contains the process measurements and the row-level
`attack_active`, `attack_phase` and `attack_phase_all` labels. The endpoint
mappings connect IP addresses and Modbus unit IDs to the released signals. The
power plot shows PV, BSS, Load 1, Load 2 and Substation.
