# DaftMav Workbook Map

This file maps the DaftMav workbook to the generated machine-readable model and
to the planner's runtime objects.

## Source Workbook

```text
references/Colonization Construction v3.4 (By DaftMav).xlsx
```

The workbook is the upstream authority. `scripts/extract_workbook.py` reads its
cached values and writes:

```text
assets/colonization_model.json
```

## Sheet Mapping

### Changelog

Used for:

- workbook version
- lists data version
- upstream source references

Mapped to:

```json
{
  "source": {
    "workbook_version": 3.4,
    "lists_data_version": 2.0
  }
}
```

### Settings

Used for:

- default cargo capacities
- Inara/Ardent search parameters
- colony tab names
- system names
- orbital slot counts
- planetary slot counts

Important input ranges:

```text
B18:B37  Colony tab name
C18:C37  System name
D18:D37  Orbital slots
E18:E37  Planetary slots
```

The planner uses these columns only when exporting a DaftMav copy. Runtime
state is stored separately from the workbook.

### Stats

Used for the facility catalogue.

Mapped to model field:

```json
{
  "structures": []
}
```

Columns:

```text
A  Structure name
B  Max landing pad
C  Prerequisites
D  System unlock
E  Strong link unlock
F  T2
G  T3
I  Security
J  Tech level
K  Wealth
L  Standard of living
M  Development level
N  Facility economy
O  Economy influence
P  Initial population increase
Q  Maximum population increase
```

Primary variants are represented by names ending in `(Primary)`.

### Lists

Used for:

- facility layout variants
- layout score
- influence
- population effects
- station point-cost modifiers
- initial station regex percentages

Mapped to:

```json
{
  "structure_layouts": [],
  "station_cost_modifiers": [],
  "initial_station_regex": []
}
```

Main static ranges:

```text
A3:C13     Station point-cost modifiers
A16:B21    Initial station regex percentages
A48:L210   Structure layout variants
B213:EE229 Dynamic layout-variant dropdown data
```

The dynamic dropdown data is not stored directly in the model. The runtime
derives layout options from `structure_layouts`.

### Commodities

Used for commodity requirements per facility.

Mapped to:

```json
{
  "commodities": []
}
```

Rows:

```text
1        Facility headers
9:74     Commodity rows
```

Columns:

```text
A       Commodity display name
B       Inara ID
C       Internal key
D       Category header
E       Commodity name
F       Produced by
G       Consumed by
P:CK    Normal facility requirements
CM:CW   Primary facility requirements
```

Primary requirements are stored as comma-formatted text in some workbook
versions, so `extract_workbook.py` normalizes them to numeric values.

## Runtime Objects

```text
SystemSurvey       Body data from EDSM or manual entry
StrategyIntent     High-level economic or strategic objective
GoalStructureSet   Concrete construction goals
Plan               Resolved facility/layout construction rows
```

The workbook is not the runtime state. It is only an upstream rule source and
an optional export target.
