# Real-photo test set — sources and licences

Downloaded 2026-10-31 from Wikimedia Commons (with the owner's approval), re-encoded to strip EXIF/GPS
metadata and downscaled to ≤ 2048 px on the long side. No other edits.

| File | Source page | Licence | Attribution |
|---|---|---|---|
| usace_cat_generator.jpg | https://commons.wikimedia.org/wiki/File:BC-0260_-_USACE-p15141coll5-19039.jpeg | Public domain (US federal government work) | US Army Corps of Engineers, Portland District |
| fema_forklift_generators.jpg | https://commons.wikimedia.org/wiki/File:FEMA_-_42049_-_Fork_lift_ready_to_unload_aircraft_in_American_Samoa.jpg | Public domain (FEMA) | Casey Deshong / FEMA |
| fema_distribution_warehouse.jpg | Commons file "Emergency Planning and Security - San Juan, Puerto Rico, May 29, 2012 ... DPLA - d2c4633e1ec7478e8b435ea7ddbce4ce.jpg" | Public domain (FEMA) | Eliud Echevarria / FEMA |
| army_forklifts_row.jpg | https://commons.wikimedia.org/wiki/File:Forklifts_load_crates_onto_trailer_trucks_at_the_warehouse_operated_by_the_1st_Logistical_Command_at_Cam_Ranh_Bay.jpg | Public domain (US Army, NARA 111-CCV-527-CC44033) | SSG Alfred Batungbacal, US Army |
| generator_nameplate_ccbysa.jpg | https://commons.wikimedia.org/wiki/File:Nameplate_of_Italian_Generator.jpg | CC BY-SA 4.0 | Photo: Haweroth, CC BY-SA 4.0, via Wikimedia Commons (downscaled; any mask overlays of it are also CC BY-SA 4.0) |

`ledger_real.csv` is a synthetic register written for these photos (no real organisation's data).
It deliberately contains a misleading entry (R-001's "serial" equals the archive caption printed on
the photo, "BC-260") and look-alike candidates (R-002/R-003).

## Labels (assistant visual inspection — NOT independent human ground truth)

| Image | Concept | Expected instances | Notes |
|---|---|---|---|
| usace_cat_generator.jpg | generator | 1 | 1954 archive photo, greyscale; caption "BC-260" is a photo ID, not an asset tag |
| usace_cat_generator.jpg | forklift | 0 | absent-object test |
| army_forklifts_row.jpg | forklift | 2 clearly (left yellow, right Hyster) | historic, low quality |
| fema_forklift_generators.jpg | machine | ambiguous | all-terrain forklift + aircraft in frame |
| fema_distribution_warehouse.jpg | forklift | 1 | small, far, top-down view |
| generator_nameplate_ccbysa.jpg | (Muse only) | — | visible: "No 5735", "AMP 16", "VOLT 70", "GIRI 1000"; no manufacturer, no model |
