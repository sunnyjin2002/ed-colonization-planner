# Colonization Hard Rules

These rules are enforced by the Python tools. Do not ask the agent to
recalculate them from memory.

## Primary Port

- A colony has exactly one primary port.
- The primary port must be the first construction row.
- The primary port must be an orbital facility.
- The primary port does not consume T2 or T3 points.
- The primary port still produces positive T2 or T3 points when the source
  model assigns a positive value.

## T2 and T3 Points

### Shared Station Count

The station-count price increase uses one shared count for T2 and T3 stations.

Primary stations are excluded from the count.

```text
station_rank = number of non-primary station rows up to the current row
```

### T2

- First two non-primary T2 stations use their base T2 cost.
- From the third non-primary station onward, an extra T2 cost of 2.25 applies.
- The final T2 value is rounded down toward zero, matching the workbook's
  `ROUNDDOWN` function.

Observed Coriolis / Asteroid Station sequence:

```text
rank 1: -3
rank 2: -3
rank 3: -5
rank 4: -7
rank 5: -9
rank 6: -12
```

### T3

- First two non-primary T3 stations use their base T3 cost.
- From the third non-primary station onward, an extra T3 cost applies.
- T3 is not rounded down.

For facilities with an extra T3 cost of `-6`:

```text
rank 1: base
rank 2: base
rank 3: base - 6
rank 4: base - 12
rank 5: base - 18
```

## Station Cost Modifiers

Extracted from `Lists!A3:C13`.

```text
Orbital - Starport - Coriolis
  extra T2 = -2.25

Orbital - Starport - Asteroid Base
  extra T2 = -2.25

Orbital - Starport - Ocellus
  extra T3 = -6

Orbital - Starport - Orbis
  extra T3 = -6

Orbital - Starport - Dodecahedron
  extra T3 = -6

Surface - Planetary Port - Port
  extra T3 = -6
```

## Slots

```text
Orbital facilities consume orbital construction sites.
Surface facilities consume surface construction sites.
```

Exact construction site counts must come from the player. EDSM provides body
information but not the actual number of Frontier construction sites.

## Layout Variants

- A construction must use a layout variant valid for its selected facility.
- If the player does not specify a layout, the current planner may choose one
  automatically, but the final choice should be visible and editable.

## Prerequisites

Some facilities require another facility to exist first.

The current implementation performs a conservative name-match check:

```text
exact match
prerequisite is substring of selected facility
selected facility is substring of prerequisite
```

This is intentionally conservative and may need refinement when the guide
provides a formal prerequisite graph.
