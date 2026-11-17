# CREATE fixes for SWAT+ 62.0.0

Baseline: upstream tag [`62.0.0`](https://github.com/swat-model/swatplus/releases/tag/62.0.0),
commit `de210d64db4f1d75e110bd6af33ea9c333d27b8a`.
Primary branch: `MR-Eini/swatplus:main`.
Original fix branch: `MR-Eini/swatplus:swatplus-62.0.0`.
Current build identifier: `62.0.0-create.3` (a candidate identifier, not an upstream release).
The earlier `create.1` includes the two perennial fixes but retains the output-record limit fixed below.
`create.2` also fixes that output limit; `create.3` adds explicit closed-reservoir handling.
`create.3` additionally contains the channel numerical/temperature fixes below,
found while validating the closed-reservoir case with runtime checks enabled.

The source files already contain these fixes. The files under `patches/`
are copies for review or application to a clean baseline; do not apply them
again to this branch. They change different source files and can be applied
independently. Keep future scientific fixes in separate commits and update
this register when the build behavior changes.

## 1. Preserve capped minimum LAI at perennial dormancy

Source: `src/pl_dormant.f90`.
Patch: `patches/0001-perennial-dormancy-lai.patch`.
Related upstream report: [swat-model/swatplus#245](https://github.com/swat-model/swatplus/issues/245).
Based on the supplied LAI-fix patch.

With the existing `rto = 0`, the original routine sets every dormant perennial's
LAI to zero. After this fix, LAI is `min(pre_dormancy_LAI, alai_min)` for
nonnegative inputs. Thus a plant retains up to its configured minimum LAI,
but the fix does not create canopy if its previous LAI was below that minimum.
With a nonzero ratio, the larger ratio-based LAI is retained.

The biomass, nitrogen, phosphorus, seed and residue-transfer statements are
unchanged. This means their immediate dormancy transfers are unchanged; it
does not imply identical subsequent biomass or water-balance outputs.
This patch does not restore `bm_dieoff` handling or every historical rev 61
behavior. `61.0.2.61` also contains the original zero-LAI assignment.

## 2. Initialize each plant's PHU growth start independently

Source: `src/plant_init.f90`.
Patch: `patches/0002-perennial-phu-initialization.patch`.
Based on the reported HRU-order dependence and stale `igrow` diagnosis.
No new upstream issue has been posted as part of this change.

Declaration initialization (`integer :: igrow = 0`) gives a local variable
Fortran's implicit SAVE attribute. Previously, a perennial with positive
`days_mat` could inherit a prior plant's growth start, including one from a
different HRU/weather station. The fix:

- removes that declaration initialization and assigns a valid fallback after
  selecting the current plant's weather generator, on every plant iteration;
- includes `perennial` in the existing `null`/`null1` daylength-dormancy search;
- assigns the detected start day only when the search actually succeeds;
- warns with HRU, plant database ID and fallback day if a planting/dormancy
  search fails, or a positive-days plant type has no supported start rule;
- wraps dates before the final `xmon` call using `ndays(13)`, matching the
  active calendar in both hemispheres and across multiple years.

The fallback follows the existing dormancy search convention: day 1 when
latitude is positive, day 181 otherwise (including latitude zero). This is
a deterministic fallback, not an inferred physiological start date. Review
any warnings before using such a simulation for calibration.

The daylength rule for positive-days perennials is the proposed model choice
and still needs developer/catchment validation. Existing annual planting
thresholds and the inclusive `igrow` through `igrow + days_mat` interval are
retained. The zero/negative-days calculations and their existing 365-day
annual sums are unchanged. Positive-day wrapping deliberately follows
`xmon`'s active month table (365 or 366), rather than an independent fixed
365-day wrap. `xmon` itself is unchanged.

## 3. Allow large drainage-area diagnostic records

Source: `src/proc_bsn.f90`.
Patch: `patches/0003-area-diagnostic-record-length.patch`.

`hyd_connect` writes each object's incoming connections to one list-directed
record in `area_calc.out`. The original OPEN sets `RECL=80000`. An aquifer
receiving 15,136 routing units exceeds that limit and GNU Fortran aborts with
"End of record" while writing the diagnostic, before plant initialization.

The fix omits the explicit record length only for `area_calc.out`, using the
existing output-path wrapper's default sequential formatted OPEN. It preserves
the write format and every incoming connection rather than truncating or
splitting the diagnostic. No routing, drainage-area or plant equations change.

`test/output_records/run_regressions.py` compiles the actual output-path module,
the OPEN statement from `proc_bsn` and the diagnostic WRITE block from
`hyd_connect`. A synthetic object with 15,136 incoming routing units writes
1,195,820 bytes under local GNU Fortran 14.3.0, preserving every incoming ID.
The same test against the unmodified source fails at the old record limit.

## 4. Handle intentionally closed reservoirs without release tables

Sources: `src/res_control.f90`, `src/res_read.f90`, `src/command.f90`.
Patch: `patches/0004-closed-reservoir-null-release.patch`.

An explicit `rel = null` can be intentional for a closed reservoir with no
surface outlet. Previously, reservoir control unconditionally selected table
zero and called `conditions`, which assigns to its unallocated `act_hit` array.

The new explicit null branch does not evaluate a decision table and leaves
controlled surface outflow at zero. It retains the common storage,
precipitation, evaporation, seepage and water-quality calculations, and calls
the existing sediment routine. A previous lagged surface release is reset to
zero. Recharge-only links (`aqu`, `rhg`) remain eligible for the existing
groundwater routing; no new surface release is invented.
The command dispatcher also processes reservoirs with no incoming objects,
so their precipitation, evaporation and seepage balances are not skipped.

The branch is accepted only when there are no outgoing links or all outgoing
links are aquifer recharge. A null reservoir with any other outlet is rejected
explicitly. A misspelled/unmatched named decision table still fails rather
than being silently treated as a closed reservoir. Explicit `null`/`NULL`
references no longer produce the reader's misleading "not found" diagnostic.
Existing named decision-table and conditional-table release paths are retained.

The focused regression compiles the actual release-control and common
water-balance blocks with fixture data. It checks zero surface release,
precipitation/evaporation/seepage and storage, sediment calls, no inherited
lagged outflow, recharge-only outlets, named release paths, and explicit
rejection of surface-outlet nulls and unknown table names. It also compiles
the actual reservoir dispatch block and checks zero-inflow daily processing. This implements
intentional closed-reservoir inputs; it does not assign or calibrate release
rules in a user's model files.

## 5. Avoid negligible underflows in channel decay calculations

Sources: `src/wq_semianalyt.f90`, `src/sd_channel_sediment3.f90`.
Patch: `patches/0005-channel-decay-underflow.patch`.

In QUAL2E, `exp_w` may return a safe normal number that underflows when
multiplied by an already small concentration. The two concentration products
are now evaluated in double precision and set to zero if their magnitude is
below the normal single-precision range before conversion. Normal products
retain their single-precision rounding; the governing equation and exp_w
clamps are unchanged. No floating-point runtime traps are disabled.

The floodplain trapping and channel vegetation decay terms now use the
existing `utils::exp_w` wrapper rather than raw EXP. For very large positive
decay arguments, this takes the intended zero-exponential limit without
raising underflow. Tests compile the actual QUAL2E function, utils module and
sediment expressions with underflow trapping enabled. They check small-product
decay, meaningful incoming concentration, ordinary analytic solutions, zero
concentration, large floodplain/vegetation decay and normal-range results.

## 6. Mix channel tributary temperatures without index zero

Source: `src/ch_temp.f90`.
Patch: `patches/0006-channel-tributary-temperature.patch`.

The old loop accessed `hin_d(in-1)` when the first incoming object was a
channel, producing an index-zero bounds error. It also assumed at most two
adjacent tributaries and reset their mixture when a routing unit appeared
later in the list. The new loop accumulates temperature times nonnegative
flow over all incoming channel tributaries, then divides by their total flow.
Local routing units are still collected separately for the later component
mixing stage. The existing air-temperature fallback and near-zero-flow
threshold are retained. Headwater objects no longer call SIZE on an
unallocated incoming-object array.

The regression compiles the actual count/mixing block and checks a channel
at incoming index one, three tributaries interspersed with a routing unit,
reordered inflows, zero-flow fallback and unallocated headwater inflows.

## Validation and remaining work

`test/perennial/run_regressions.py` compiles the actual PHU calculation and
LAI-update source blocks, together with the unchanged `src/xmon.f90`, against
small fixture structures. It checks:

- HRU and within-community plant order, two weather stations/hemispheres,
  and all four existing annual type branches;
- normal/leap calendars and heat-unit windows longer than two years;
- failed dormancy/annual searches and their fallback days;
- preservation of zero/negative `days_mat` branches;
- dormant LAI minimum, low/zero initial canopy and ratio behavior.

These focused checks passed locally with GNU Fortran 14.3.0 on Windows on
2026-11-17. The complete model also compiled with the unchanged upstream
Windows Release flags. The focused regression fails against the unmodified
baseline, demonstrating that it detects the initialization defect.

The bundled Ames one-year smoke run currently stops in
`src/hyd_read_connect.f90:338` with an `ob(0)` bounds error before plant
initialization. The unmodified baseline, built with the same compiler and
flags, reproduces the same error. See `BUILD.md` for the comparison and limitations.
This is not a successful end-to-end simulation or a validation of catchment
results. No claim is made that the shared third-party executable corresponds
to this source.

The GitHub workflow builds with GCC 13 on Linux and Windows, runs focused
regressions and records a diagnostic smoke outcome alongside each candidate
artifact. A green workflow means the required focused checks/build passed;
the smoke step is diagnostic and can fail. Inspect `SMOKE_OUTCOME.txt` and
`smoke.log` before using an artifact. Full partner-catchment tests and native
SWATdoctR/SWATrunR integration remain required before common-build deployment.

### GitHub Actions results, 2026-11-17

[Run 44046531380](https://github.com/MR-Eini/swatplus/actions/runs/44046531380)
tested source commit `5540b843f34e854dab527079765fcbfaa6084df8` with GCC 13.

| Check | Windows | Linux |
| --- | --- | --- |
| Focused source regressions | Passed | Passed |
| Complete model compilation | Passed | Passed |
| Registered perennial CTest | Passed | Passed |
| Diagnostic Ames smoke run | Failed: `hyd_read_connect.f90:338`, `ob(0)` bounds | Failed: segmentation fault in `hrudb_init` |

The Linux smoke failure has not been compared against an unmodified Linux
baseline. The Windows bounds failure was reproduced with an unmodified
baseline locally under GNU 14.3.0; it also occurs in the patched GCC 13 CI
build. These results do not establish a successful full-model run or console
compatibility. Both CI artifacts include the failed smoke logs and candidate
status; do not interpret the overall workflow success as smoke-test success.

Keep production perennial `days_mat = 0` until a combined executable has
passed the intended catchment checks. Do not remove an existing fort.6 R
workaround based solely on these source changes or compiler selection.
