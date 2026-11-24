# Economy Strategy

This file distills CMDR Dubior's colonization guide into decision-oriented
patterns. This file is not the full guide, it only contains enough information
to choose and explain candidate structures.

## Purpose

Use this file to convert a `StrategyIntent` into candidate
`GoalStructureSet` options.

```text
StrategyIntent
  -> economy strategy
  -> candidate GoalStructureSet
  -> feasibility
  -> plan
```

## Core Rule

Colonization has these economy types:

```text
Agriculture
Contraband / Service
Extraction
High Tech
Industrial
Military
Refinery
Terraforming
Tourism
```

A station can have up to two dominant economies. Multiple economies result
in self-cannibalization, an effect where goods produced by one economy
is consumed by another economy in the same station, resulting in product
demand and supply cancelling out, leaving very little products in the market.
However, the top two economies are resistant to self-cannibalization, so pairing matters.

Good economy pairs are generally:

```text
Agriculture / Extraction
Agriculture / Refinery
Extraction / Refinery
Refinery / Tourism
```

Poor or redundant pairs include:

```text
Refinery / Industrial
Industrial / High Tech
Military / High Tech
```

## Agriculture

Objective keywords:

```text
agriculture
farming
food
biowaste
water world agriculture
ELW agriculture
```

Use:

- bodies with bio signals;
- non-tidally-locked Water Worlds;
- non-tidally-locked Earth-like Worlds;
- terraformable HMC or rocky bodies with bio signals.

Avoid:

- tidally locked bodies;
- icy bodies;
- rocky ice bodies;
- bodies with geological signals that add extraction/industrial consumption.

Relevant facilities:

```text
Surface - Settlement - Agriculture T1 S
Surface - Settlement - Agriculture T1 M
Surface - Settlement - Agriculture T2 L
Orbital - Installation - Space Farm
```

Notes:

- Ground agriculture currently has a bug that changes its commodity pool.
- Prefer orbital agriculture when possible.
- Agriculture is one of the few economies with frequent negative modifiers.

## Contraband / Service

Objective keywords:

```text
contraband
black market
smuggling
illegal goods
nerve agents
battle weapons
landmines
```

Use:

- orbital construction only;
- bodies with many orbital slots;
- 4+ orbital slots when possible;
- pirate or criminal outposts.

Relevant facilities:

```text
Orbital - Outpost - Criminal
Orbital - Installation - Pirate Base
```

Notes:

- Contraband adds no ordinary consumption.
- It can unprotect economies for biowaste and other broadly produced goods.
- Contraband constructions significantly reduce security.

## Extraction

Objective keywords:

```text
extraction
mining
ore
raw materials
metals
pristine reserves
```

Use:

- clean High Metal Content or Metal-Rich bodies;
- terraformable HMC or MR with many slots;
- bodies with volcanism for a smaller but easier setup;
- ringed ELW for maximum supply.

Relevant facilities:

```text
Surface - Settlement - Extraction T1 S
Surface - Settlement - Extraction T1 M
Surface - Settlement - Extraction T2 L
Surface - Hub - Extraction
Orbital - Installation - Mining Outpost
```

Notes:

- Extraction is usually one of the easiest economies to build.
- Most extracted commodities are consumed mainly by refinery.
- Gold, silver, and palladium can suffer from industrial/high-tech overlap.

## High Tech

Objective keywords:

```text
high tech
technology
research
scientific
relay
research bio
```

Use:

- Ammonia Worlds;
- Earth-like Worlds;
- Neutron Stars, White Dwarfs, or Black Holes for base high tech;
- bodies with both bio and geo signals.

Relevant facilities:

```text
Orbital - Installation - Relay Station
Orbital - Installation - Medical Installation
Orbital - Installation - Research Station
Orbital - Outpost - Scientific
Surface - Settlement - Research Bio T1 S
Surface - Settlement - Research Bio T1 M
Surface - Settlement - Research Bio T2 L
Surface - Hub - High Tech
Surface - Hub - Scientific
```

Notes:

- No landable body has intrinsic high tech economy.
- `Orbital - Installation - Relay Station` is the orbital T1 high tech
  construction.
- Ground high tech constructions are usually T2 or supporting constructions,
  so orbital relay stations are the cheaper T1 point/economy source.

## Industrial

Objective keywords:

```text
industrial
industry
manufacturing
production
consumer items
machinery
```

Use:

- clean icy bodies;
- large icy bodies with high ground and orbital slot counts;
- pristine or major reserves.

Relevant facilities:

```text
Orbital - Outpost - Industrial
Surface - Settlement - Industrial T1 S
Surface - Settlement - Industrial T1 M
Surface - Settlement - Industrial T2 L
Surface - Hub - Industrial
```

Notes:

- Industrial has few positive modifiers besides reserves.
- Its T1 orbital outpost is tonnage-expensive.
- Industrial overlaps poorly with high tech and refinery.

## Military

Objective keywords:

```text
military
defense
security
combat
weapons
```

Use:

- non-Neutron Star, non-White Dwarf, non-Black Hole stars;
- high-slot HMC or icy bodies for higher military proportion;
- military outposts for security with low economy pollution.

Relevant facilities:

```text
Orbital - Outpost - Military
Orbital - Installation - Military
Orbital - Installation - Security Station
Surface - Settlement - Military T1 S
Surface - Settlement - Military T1 M
Surface - Settlement - Military T2 L
Surface - Hub - Military
```

Notes:

- Military is often built to raise security rather than maximize economy.
- Military weak links can help unlock shipyard and weapon stock.

## Refinery

Objective keywords:

```text
refinery
refining
processing
steel
CMM composite
ceramic composite
```

Use:

- rocky bodies;
- rocky ice bodies;
- high ground slot count;
- terraformable rocky bodies when possible.

Relevant facilities:

```text
Surface - Hub - Refinery
Surface - Planetary Port - Outpost Industrial
Surface - Planetary Port - Port
```

Notes:

- Refinery ground ports are important for Ceramic Composites and CMM
  Composites.
- Refinery pairs well with agriculture, extraction, and tourism.
- Avoid refinery/industrial pairing when possible.

## Terraforming

Objective keywords:

```text
terraforming
terraformable economy
```

Pattern prerequisites:

- A body with bio signals and no geo signals;
- stacked colony weak links;
- usually at least nine terraforming weak links.

Relevant facilities:

```text
Surface - Planetary Port - Port
Orbital - Starport - Coriolis
Orbital - Starport - Ocellus
Orbital - Starport - Orbis
Orbital - Outpost - Commercial
```

Notes:

- Terraforming is consumption-based.
- It produces only hydrogen fuel and biowaste.
- This is an advanced setup; do not propose it without strong evidence from
  the survey and guide.

## Tourism

Objective keywords:

```text
tourism
tourist
passenger
resort
```

Use:

- Earth-like Worlds;
- systems with Neutron Stars, White Dwarfs, or Black Holes;
- O or B class systems where Neutron Stars, White Dwarfs, or Black Holes can
  combine with geo and bio signals.

Relevant facilities:

```text
Orbital - Installation - Tourist
Orbital - Installation - Space Bar
Surface - Settlement - Tourism T1 S
Surface - Settlement - Tourism T1 M
Surface - Settlement - Tourism T2 L
```

Notes:

- Tourism is consumption-based.
- Population and body type matter more than purity for tourism supply.
- O/B systems are useful because they can combine NS/WD/BH modifiers with
  geo+bio modifiers for multiple strong-link bonuses.
- Its effect on passenger missions is still uncertain.

## Example GoalStructureSet

Use this JSON shape in the guide. Replace body placeholders with actual survey
bodies.

```json
{
  "goals": [
    {
      "goal_id": "EX1",
      "body_key": "<primary-orbital-body>",
      "facility": "Orbital - Outpost - Commercial (Primary)",
      "facility_class": null,
      "tier": null,
      "primary": true,
      "layout_variant": null,
      "priority": "must",
      "source": "strategy",
      "note": "primary station",
      "count": 1
    },
    {
      "goal_id": "EX2",
      "body_key": "<surface-body>",
      "facility": "Surface - Settlement - Extraction T1 M",
      "facility_class": null,
      "tier": null,
      "primary": false,
      "layout_variant": null,
      "priority": "prefer",
      "source": "strategy",
      "note": "extraction economy core",
      "count": 1
    },
    {
      "goal_id": "EX3",
      "body_key": "<surface-body>",
      "facility": "Surface - Hub - Refinery",
      "facility_class": null,
      "tier": null,
      "primary": false,
      "layout_variant": null,
      "priority": "prefer",
      "source": "strategy",
      "note": "refinery support",
      "count": 1
    }
  ],
  "strategy_id": "extraction-refinery",
  "rationale": "Use extraction settlements to feed refinery production."
}
```

## System Stat Setups

Useful when the player cares about non-economy outcomes.

```text
Security:
  - Orbital - Installation - Comm Station
  - Orbital - Installation - Government
  - Orbital - Installation - Security Station
  - Orbital - Outpost - Military

Tech Level:
  - Orbital - Outpost - Scientific
  - Surface - Settlement - Research Bio T2 L
  - Surface - Hub - High Tech

Wealth:
  - Orbital - Outpost - Criminal
  - Orbital - Installation - Tourist
  - Surface - Settlement - Extraction T2 L

Standard of Living:
  - Surface - Settlement - Agriculture T1 S
  - Surface - Settlement - Agriculture T1 M
  - Orbital - Installation - Government
  - Orbital - Installation - Medical

Development Level:
  - Orbital - Outpost - Industrial
  - Surface - Settlement - Industrial T1 M
  - Surface - Hub - Industrial
```

## Gameplay Pattern Hints

```text
Trade:
  Prefer pure or dual economies with low self-cannibalization.

Regular mining:
  Prefer extraction, refinery, tourism, or high tech as the local sell market.

Wing mining missions:
  Prefer extraction economy with compatible faction expansion state.

Piracy:
  Prefer anarchy control and contraband/military sell facilities.

Passenger missions:
  Prefer stations near tourist beacons; tourism economy effect is uncertain.

Raw material farming:
  Build landmarks away from collection sites to avoid no-fire-zone issues.
```

## Candidate Generation Rules

When creating candidate `GoalStructureSet` options:

- Preserve explicit player constraints.
- Use body attributes and available slots.
- Prefer patterns supported by this file.
- Mark uncertain or guide-dependent recommendations as advisory.
- Run feasibility before presenting an option as viable.
