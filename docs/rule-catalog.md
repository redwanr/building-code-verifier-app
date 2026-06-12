# Seed Rule Catalog

Companion to `PRD.md` §7. Rules are **data, not code** — this catalog is the human-readable view of the versioned rule packs.

**Two sources, kept distinct:**
- `BNBC-2020` → life-safety (egress, exits, fire, room sizes, heights). Parts 3 & 4.
- `RAJUK-DAP/Bidhimala` → planning (FAR, MGC, setbacks, parking).

**`[VERIFY]`** marks any threshold depending on the in-flux 2025/2026 rules (DAP 2025 revision / draft Building Construction Rules 2025, gazette pending). Verified *principle*, exact *value* TBD by domain expert.

---

## Schema (each rule)

| Field | Meaning |
|---|---|
| `id` | Stable identifier. |
| `source` | `BNBC-2020` or `RAJUK-DAP/Bidhimala`. |
| `parameters` | Extracted params required. |
| `logic` | Declarative expression (interpreter vocabulary: `gt lt ge le eq`, `param_present`, `compare(a,b)`, `consistency([...])`, `if/then`). |
| `severity` | Critical / High / Medium / Low. |
| `confidence_basis` | Confidence in the **rule** (separate from extraction confidence). |
| `citation` | Clause text/number. |
| `remediation` | Plain-language fix hint. |
| `verify_flag` | True if threshold is in-flux 2025/2026. |
| `input_tier` | **T1 = table/text read (MVP-realistic)** · **T2 = geometry read (deferred)**. |

---

## Seed rules

### BNBC-EGRESS-001 — Minimum two means of egress (high-rise)
- **source:** BNBC-2020 · **input_tier:** T1
- **parameters:** `num_storeys`, `building_height_m`, `num_exit_stairs`
- **logic:** `if (building_height_m > 20 OR num_storeys > 6) then num_exit_stairs >= 2`
- **severity:** Critical · **verify_flag:** [VERIFY] (exact storey/height trigger)
- **confidence_basis:** Verified principle (BNBC Part 3 means of egress). Trigger value to confirm.
- **citation:** BNBC-2020 Part 3 — Means of Egress / number of exits.
- **remediation:** Provide a second independent, fire-separated exit stair.
- *MVP note:* realistic — stair count is usually countable on plan/legend; height/storeys from elevation/section title block.

### BNBC-FIRE-002 — High-rise (>20 m) fire provisions for A-3
- **source:** BNBC-2020 · **input_tier:** T1 (presence-of-provision read) → some items T2
- **parameters:** `building_height_m`, `has_fire_alarm`, `has_fire_hydrant_standpipe`, `has_fire_rated_stair_enclosure`, `has_firefighting_lift`
- **logic:** `if (building_height_m > 20) then param_present(has_fire_alarm) AND param_present(has_fire_hydrant_standpipe) AND param_present(has_fire_rated_stair_enclosure) AND param_present(has_firefighting_lift)`
- **severity:** Critical · **verify_flag:** [VERIFY] (height trigger + exact provision list)
- **confidence_basis:** Verified principle (BNBC Part 4 fire protection). Exact provision set per occupancy to confirm.
- **citation:** BNBC-2020 Part 4 — Fire Protection (alarm, fixed hydrant in stair landings/lift lobby, fire-rated enclosure, fire-fighting lift).
- **remediation:** Add fire alarm + fixed hydrant/standpipe at stair landings & lift lobby; fire-rate the stair enclosure; provide a fire-fighting lift.
- *MVP note:* mixed — presence often shown as notes/legend (T1); whether they meet spec is human-verify.

### RAJUK-FAR-003 — FAR reconciliation
- **source:** RAJUK-DAP/Bidhimala · **input_tier:** T1
- **parameters:** `claimed_far`, `plot_land_use_class`, `dap_ward`, `permissible_far`
- **logic:** `if param_present(permissible_far) then claimed_far <= permissible_far; ALSO consistency([claimed_far, computed_far_from(total_floor_area, plot_area)])`
- **severity:** High · **verify_flag:** [VERIFY] — permissible FAR is ward/density-block specific under DAP 2025; **do NOT** assume legacy katha/road-width table.
- **confidence_basis:** Verified principle (FAR is RAJUK-governed). Permissible value must come from current DAP ward area-FAR per LUC — expert-supplied.
- **citation:** RAJUK DAP 2022–2035 (2025 rev) / Imarat Nirman Bidhimala — area-FAR by ward/LUC.
- **remediation:** Verify claimed FAR against the plot's land-use class and current DAP ward FAR; reconcile floor-area math.
- *MVP note:* read claimed FAR + areas from table (T1). Permissible FAR requires the expert-maintained DAP lookup, not geometry.

### RAJUK-MGC-004 — Ground coverage (MGC) vs allowable
- **source:** RAJUK-DAP/Bidhimala · **input_tier:** T1
- **parameters:** `claimed_mgc_pct`, `plot_size_bracket`, `allowable_mgc_pct`
- **logic:** `if param_present(allowable_mgc_pct) then claimed_mgc_pct <= allowable_mgc_pct`
- **severity:** High · **verify_flag:** [VERIFY] (allowable % per current bracket)
- **confidence_basis:** Verified principle. Allowable % expert-supplied from Bidhimala/DAP.
- **citation:** RAJUK Imarat Nirman Bidhimala — Maximum Ground Coverage by plot bracket.
- **remediation:** Reduce footprint or confirm bracket; reconcile MGC with allowable.
- *MVP note:* claimed MGC usually tabulated (T1). Verifying it against *actual* footprint geometry is T2.

### RAJUK-SETBACK-005 — Setbacks (front/rear/side)
- **source:** RAJUK-DAP/Bidhimala · **input_tier:** T1 if tabulated, else T2
- **parameters:** `front_setback_m`, `rear_setback_m`, `side_setback_m`, `plot_size`, `building_height_m`, `required_setbacks`
- **logic:** `if param_present(required_setbacks) then front_setback_m >= required.front AND rear_setback_m >= required.rear AND side_setback_m >= required.side`
- **severity:** High · **verify_flag:** [VERIFY] against draft Building Construction Rules 2025 setback schedule.
- **confidence_basis:** Verified principle. Schedule (by plot size + height) expert-supplied; in flux.
- **citation:** RAJUK Building Rules 2025 (draft) — setback schedule by plot size/height.
- **remediation:** Confirm setbacks meet the current schedule for this plot size and building height.
- *MVP note:* if setbacks are stated in the data table → T1 (realistic). If they must be *measured* off the plan → T2 (deferred; emit "needs verification").

### RAJUK-PARKING-006 — Parking count sanity
- **source:** RAJUK-DAP/Bidhimala · **input_tier:** T1
- **parameters:** `parking_provided`, `num_units`, `unit_size_distribution`, `required_parking_ratio`
- **logic:** `if param_present(required_parking_ratio) then parking_provided >= required_from(num_units, unit_size_distribution, required_parking_ratio); ALSO consistency([parking_provided_table, parking_count_on_plan])`
- **severity:** Medium · **verify_flag:** [VERIFY] (current ratio per unit size/count)
- **confidence_basis:** Verified principle. Ratio expert-supplied; internal-consistency check is rule-independent and high-value.
- **citation:** RAJUK Bidhimala/DAP — parking provision ratio.
- **remediation:** Reconcile required vs provided parking; fix any mismatch between the parking table and the count shown on plan.
- *MVP note:* both required-ratio check and the internal-consistency check are T1 — and the consistency check (caught in the manual G+9 win) is high-leverage.

### BNBC-ROOM-007 — Minimum habitable room / kitchen / toilet sizes
- **source:** BNBC-2020 · **input_tier:** T1 if tabulated, else T2
- **parameters:** `min_room_area_m2`, `min_room_width_m`, `kitchen_area_m2`, `toilet_area_m2`
- **logic:** `room_area_m2 >= min_room_area_m2 AND room_width_m >= min_room_width_m AND kitchen/toilet >= minimums`
- **severity:** Medium · **verify_flag:** [VERIFY] (exact minimums)
- **confidence_basis:** Verified principle (BNBC Part 3 room sizes). Exact values expert-confirmed.
- **citation:** BNBC-2020 Part 3 — minimum room area/width, kitchen, toilet.
- **remediation:** Confirm habitable room/kitchen/toilet dimensions meet BNBC minimums.
- *MVP note:* room areas sometimes in schedule (T1); otherwise must be measured (T2). Likely "needs verification" in MVP.

### BNBC-STAIRWIDTH-008 — Minimum exit-stair width (apartments)
- **source:** BNBC-2020 · **input_tier:** T1 if tabulated, else T2
- **parameters:** `exit_stair_width_m`, `occupancy`, `min_stair_width_m`
- **logic:** `exit_stair_width_m >= min_stair_width_m`
- **severity:** High · **verify_flag:** [VERIFY] (exact min width for A-3)
- **confidence_basis:** Verified principle (BNBC Part 3 egress width). Value expert-confirmed.
- **citation:** BNBC-2020 Part 3 — minimum exit stair width.
- **remediation:** Confirm stair clear width meets the minimum for residential occupancy.
- *MVP note:* T1 only if width is tabulated; measuring off plan is T2.

### BNBC-LIFT-009 — Lift / fire-lift provision for height
- **source:** BNBC-2020 · **input_tier:** T1
- **parameters:** `building_height_m`, `num_storeys`, `num_lifts`, `has_firefighting_lift`
- **logic:** `if (building_height_m > threshold) then num_lifts >= 1 AND param_present(has_firefighting_lift)`
- **severity:** High · **verify_flag:** [VERIFY] (height threshold for lift / fire-lift)
- **confidence_basis:** Verified principle (BNBC lift/fire-lift for height). Threshold expert-confirmed. Overlaps BNBC-FIRE-002 fire-lift item — keep one canonical source.
- **citation:** BNBC-2020 — lift provision; fire-fighting lift for high-rise.
- **remediation:** Provide required lift(s) and a fire-fighting lift for the building height.
- *MVP note:* lift count typically countable/legended (T1).

---

## MVP realism summary

| Rule | Tier | MVP-realistic? |
|---|---|---|
| BNBC-EGRESS-001 (2 exits) | T1 | ✅ Yes — flagship, reproduces G+9 win |
| BNBC-FIRE-002 (high-rise fire) | T1/T2 | ✅ Presence-read yes; spec-compliance = human-verify |
| RAJUK-FAR-003 (FAR) | T1 | ✅ Yes (needs expert DAP lookup) |
| RAJUK-MGC-004 (MGC) | T1 | ✅ Claimed value yes; vs actual footprint = T2 |
| RAJUK-SETBACK-005 (setbacks) | T1/T2 | ⚠️ Only if tabulated; else defer |
| RAJUK-PARKING-006 (parking) | T1 | ✅ Yes — incl. high-value consistency check |
| BNBC-ROOM-007 (room sizes) | T1/T2 | ⚠️ Mostly needs-verification in MVP |
| BNBC-STAIRWIDTH-008 (stair width) | T1/T2 | ⚠️ Only if tabulated |
| BNBC-LIFT-009 (lift/fire-lift) | T1 | ✅ Yes |

**Recommended MVP rule subset (high-confidence, table-readable):**
EGRESS-001, FIRE-002 (presence only), FAR-003, MGC-004, PARKING-006, LIFT-009.
These six reproduce the validated G+9 findings (egress, fire, FAR, parking) and stay inside Tier-1 extraction. SETBACK-005, ROOM-007, STAIRWIDTH-008 run **only when their inputs are tabulated**; otherwise they emit "needs verification" rather than guessing from geometry.
