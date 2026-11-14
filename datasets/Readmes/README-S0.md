# S0 - Benign baseline operation

## Scenario summary

S0 represents baseline operation without intentionally injected cyber attacks. The EMS runs in normal SCO/SCO+ mode using regular measurements from PV, load, and BSS-side metering points and regular price signals.

## Time window

- Local (Europe/Berlin): 2026-03-05T14:19:00+01:00 to 2026-03-05T14:49:00+01:00
- UTC: 2026-03-05T13:19:00+00:00 to 2026-03-05T13:49:00+00:00
- Sampling step: 1.0 s

## Dataset coverage

- Total rows: 1798
- Benign rows: 1798
- Attack rows: 0
- Dataset timeline: 2026-03-05T13:19:02.660000+00:00 to 2026-03-05T13:48:59.660000+00:00

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

- Scenario type: benign reference run without injected cyber attack phases.
- Control behavior: EMS operates with regular metering inputs and regular MQTT price context.
- Process context: PV, loads, BSS, and substation signals reflect nominal closed-loop operation.
- Intended analytical role: baseline profile for normal dynamics and false-positive evaluation.

## Dataset contents

- `dataset.csv`: complete run on a 1-second grid with `attack_active=False` throughout.
- `dataset_benign.csv`: same semantic content as the full run for baseline-only workflows.
- `dataset_attack.csv`: included for schema consistency (empty attack subset for this scenario).
- `attack-phases.json`: intentionally empty, indicating no attack phase intervals.
- `experiment_overview.json`: run timeline and benign interval boundaries for this baseline scenario.
- `state.jsonl.gz`: state-centric representation of the same timeline for sequence/stateful analysis.
- `network_tap.pcapng`, `benign_only.pcapng`, `attacker_only.pcapng`: packet captures aligned to this run.
- `ip_device_mapping.csv` and `modbus_variable_mapping.csv`: semantic mapping of device roles and Modbus fields used in this scenario.

## Data interpretation

Across its process-feature columns, the table contains 482 empty entries. Each
marks a timestamp for which that feature has no source value, and packaging
preserves it as empty. `measurement_alignment.csv.gz` describes how available
observations were placed on the one-second grid through the output time, source
time, age and alignment flags. State messages contain the available values and
record unavailable feature names in `missing_state_variables`. The count covers
feature columns; timestamps and row-level labels are counted separately.

S0 contains no attack phases. Every packet receives `benign`, including
packets beyond the measurement table timeline. The attack subset is empty,
and the benign subset contains all tap packets.

`dataset.csv` contains the process measurements and the row-level
`attack_active`, `attack_phase` and `attack_phase_all` labels. The endpoint
mappings identify meters by IP address and Modbus unit ID. The power plot shows
PV, BSS, Load 1, Load 2 and Substation.
