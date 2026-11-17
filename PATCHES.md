# CREATE perennial fixes for SWAT+ 62.0.0

Baseline: upstream tag [`62.0.0`](https://github.com/swat-model/swatplus/releases/tag/62.0.0),
commit `de210d64db4f1d75e110bd6af33ea9c333d27b8a`.
Branch: `MR-Eini/swatplus:swatplus-62.0.0`.
Build identifier: `62.0.0-create.1` (a candidate identifier, not an upstream release).

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
