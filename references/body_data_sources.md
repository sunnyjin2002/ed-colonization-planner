# Body Data Sources

The planner currently uses EDSM for system and body discovery.

## System API

```text
https://www.edsm.net/api-v1/system
```

Parameters used by `fetch_system_bodies.py`:

```text
systemName
showInformation=1
showPrimaryStar=1
showCoordinates=1
```

Used to determine:

- system name
- coordinates
- allegiance
- government
- faction
- population
- economy
- security
- primary star type

Population presence is stored as:

```text
SystemSurvey.raw_system_data["population_known"]
```

## Bodies API

```text
https://www.edsm.net/api-system-v1/bodies
```

Parameters:

```text
systemName
```

Returns:

```json
{
  "id": 27,
  "name": "Sol",
  "bodyCount": 40,
  "bodies": []
}
```

## Body Normalization

`fetch_system_bodies.py` maps EDSM fields to `BodySurvey`.

Important mappings:

```text
name                    -> BodySurvey.name
type                    -> BodySurvey.body_type
subType                 -> BodySurvey.sub_type
isLandable              -> BodySurvey.is_landable
distanceToArrival       -> BodySurvey.distance_to_arrival
gravity                 -> BodySurvey.gravity
surfaceTemperature      -> BodySurvey.surface_temperature
atmosphereType          -> BodySurvey.atmosphere
volcanismType           -> BodySurvey.volcanism
terraformingState       -> BodySurvey.terraforming_state
```

## Body Key Derivation

EDSM does not directly return Frontier system-map labels.

The planner derives display keys such as:

```text
A
A1
A3
A3a
```

Rules:

- main stars are assigned `A`, `B`, and so on;
- direct star children are numbered by distance;
- moon children use lowercase letter suffixes.

These keys are best-effort. The player's in-game body label is authoritative.

## Missing Information

EDSM does not provide:

- exact orbital construction site counts
- exact surface construction site counts
- primary port placement
- Frontier colonization eligibility

The planner must ask the player for these values.

## Manual Fallback

When EDSM returns no usable data, create an empty `SystemSurvey`:

```text
provider = manual
bodies = []
missing_fields = [
  bodies,
  orbital_construction_sites,
  surface_construction_sites,
  primary_port_body
]
```
