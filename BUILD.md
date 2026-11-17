# Building the CREATE rev 62 candidate

## Reproducible source and toolchain

Start from `MR-Eini/swatplus:main` (or the original `swatplus-62.0.0` fix
branch), not the latest upstream main. The official baseline
and individual changes are recorded in [PATCHES.md](PATCHES.md). Record the
exact checked-out commit for every executable:

```bash
git rev-parse HEAD
gfortran --version
cmake --version
```

Use CMake 3.22 or later and Python 3. The upstream rev 62 Windows workflow
uses GCC 13; this branch's candidate workflow uses that same major version
on Windows and Linux. Local checks used Rtools45 GNU Fortran 14.3.0 and
CMake 3.31.8, which is a separate toolchain verification, not an exact
reproduction of the upstream binary. Put the compiler and its assembler /
linker tools on PATH. Existing upstream compiler and floating-point flags
are preserved in `CMakeLists.txt`.

Linux example:

```bash
cmake -S . -B build -DCMAKE_Fortran_COMPILER=gfortran \
  -DCMAKE_BUILD_TYPE=Release -DTAG=62.0.0-create.4
cmake --build build --parallel 4
python3 test/perennial/run_regressions.py --compiler gfortran
python3 test/output_records/run_regressions.py --compiler gfortran
python3 test/closed_reservoirs/run_regressions.py --compiler gfortran
python3 test/water_quality/run_regressions.py --compiler gfortran
python3 test/channel_temperature/run_regressions.py --compiler gfortran
ctest --test-dir build -R '^(Perennial_initialization|Large_area_record|Closed_reservoir|Water_quality_decay|Channel_tributary_temperature)$' --output-on-failure --no-tests=error
```

Windows PowerShell example with gfortran and mingw32-make on PATH:

```powershell
cmake -S . -B build -G 'MinGW Makefiles' `
  '-DCMAKE_Fortran_COMPILER=gfortran' `
  '-DCMAKE_BUILD_TYPE=Release' '-DTAG=62.0.0-create.4'
cmake --build build --parallel 4
python test/perennial/run_regressions.py --compiler gfortran
python test/output_records/run_regressions.py --compiler gfortran
python test/closed_reservoirs/run_regressions.py --compiler gfortran
python test/water_quality/run_regressions.py --compiler gfortran
python test/channel_temperature/run_regressions.py --compiler gfortran
ctest --test-dir build -R '^(Perennial_initialization|Large_area_record|Closed_reservoir|Water_quality_decay|Channel_tributary_temperature)$' --output-on-failure --no-tests=error
```

Quote the complete `-DTAG=...` argument in PowerShell. Rtools' MSYS make
can instead use `-G 'MSYS Makefiles'` and an explicit
`-DCMAKE_MAKE_PROGRAM=.../usr/bin/make.exe`. If CMake does not find Python,
set `-DPython3_EXECUTABLE=.../python.exe` to register the focused CTest.

The current binary name includes `62.0.0-create.4`, the compiler and the platform.
Do not label a GNU build `ifo` (Intel Fortran Classic).

`create.2` removes the explicit 80,000-character record limit for
`area_calc.out`. A synthetic 15,136-inflow case exercises the actual OPEN
and WRITE statements and fails against the original limit. All existing
compiler checks remain enabled. `create.3` additionally supports intentional
`rel = null` for closed reservoirs with no outlets or only aquifer-recharge
links. Their surface release is zero while the normal water balance remains
active. It does not replace nulls with a drawdown rule. Unknown named tables
and null reservoirs with surface outlets are rejected explicitly.

### Verified comparison with the official Windows executable

On 2026-11-17, the Windows candidate from source commit
`5540b843f34e854dab527079765fcbfaa6084df8` was downloaded from
[the completed GitHub build](https://github.com/MR-Eini/swatplus/actions/runs/44046531380)
and checked against its SHA-256 manifest. Its banner reports **GNU 13.2.0,
Windows**, exactly the compiler version/platform reported by the executable
in the [official 62.0.0 Windows ZIP](https://github.com/swat-model/swatplus/releases/download/62.0.0/swatplus-62.0.0-gnu-win_amd64-Rel.zip).
Both PE headers identify x86-64. The candidate uses the upstream GCC 13 /
MinGW Makefiles / Release procedure and unchanged model compiler flags,
with the two scientific patches and a distinct version banner.

Verified SHA-256 values:

- Official ZIP: `05f09dab8f241219113ed715723b674d1dc44900c3bf8c563657b7a4343e5e61`
- Official EXE: `e757daf64a597ca2da80f12ff6a0075c4e8260c6fcf871f8da979aef21a37db3`
- Patched EXE: `94f6270aa6d27451b31aa75b30163b64b4325a6299212dd7c88f7ff14595c911`

The official, downloaded executable itself also fails the isolated Ames
smoke run at `hyd_read_connect.f90:338` with an `ob(0)` bounds error, matching
the patched Windows candidate. This extends the source-baseline comparison
below to the actual upstream distributed binary. Neither early failing run
created fort.6; that does not establish successful full-run or native
SWATdoctR compatibility. The candidate still requires representative-case
validation before deployment.

## Tests and diagnostic smoke run

The focused driver compiles actual source blocks with bounds checking and
floating-point traps. It does not replace a full simulation. To demonstrate
the regression against the official source, create a separate baseline
checkout and point the current driver to it:

```bash
git worktree add --detach ../swatplus-62-baseline de210d64db4f1d75e110bd6af33ea9c333d27b8a
python3 test/perennial/run_regressions.py --source-root ../swatplus-62-baseline
```

That baseline check is expected to fail on HRU-order dependence.

Run an isolated, one-year copy of bundled Ames inputs with a newly built
executable (substitute the actual platform-specific binary name):

```bash
python3 test/perennial/run_smoke.py --exe build/swatplus-62.0.0-create.4-gnu-lin_x86_64-Rel --require-console
```

The driver removes copied completion markers and logs, runs only the first
input year, and requires both exit code zero and a newly written
`success.fin` containing the completion message. With `--require-console`,
it also requires the message in captured stdout. It reports whether fort.6
appeared. It never modifies the repository's reference inputs.

Local Windows testing with the upstream flags stops in
`hyd_read_connect.f90:338` on an `ob(0)` bounds error before the changed
plant routines. A successful full-catchment/console test has therefore not
been established with that toolchain. The unmodified official baseline was
also compiled with the same local compiler and flags, and reproduces that
same bounds failure at line 338. The focused regression driver fails on the
unmodified baseline (northern perennial PHU changes from 80 to 141 after an
annual is initialized), and passes after the source fixes. Do not disable bounds checking or
alter hydrological connectivity merely to mark these two patches verified.
The upstream Ames CTest additionally refers to `data/Ames_sub1`, whereas
the inputs in this release are under `refdata/Ames_sub1`; this branch does
not claim that the existing full reference-output CTest passed.

The `CREATE rev 62 fixes` GitHub Actions workflow checks out the
branch, runs on changes to `main` and `swatplus-62.0.0`, tests and compiles
it on Windows/Linux using GCC 13, then uploads
candidate artifacts with source commit, compiler version, CMake cache,
documentation, smoke log/outcome and SHA-256 checksums. The smoke step is
diagnostic (not a required passing step). Artifact availability is not
production-readiness or SWATdoctR compatibility certification. No release
is automatically published.

This repository uses the CREATE workflow for its required focused tests and
candidate builds. The inherited Intel workflow in `test.yml` is restricted
to the upstream repository; it references the upstream legacy full-model
test configuration rather than this branch's focused validation procedure.

## Before updating the portable workflow

1. Run representative forest/meadow/annual cases with the combined build.
2. Check initialized `phumat` for identical plants/weather after changing
   HRU and plant order; compare the same HRUs, not different weather sites.
3. Check dormant LAI and immediate biomass/residue transfers. Assess effects
   on annual water balance, growth and calibration separately.
4. Test native SWATdoctR and SWATrunR process execution, including failure
   cases and console capture. GNU Fortran alone does not imply fort.6 output;
   the official Windows rev 62 artifact is itself GNU-built.
5. If an R fallback remains necessary, maintain it as an explicit package
   function that checks exit status and a fresh completion marker. Avoid
   stale fort.6 success lines and dynamic rewriting of installed functions.
6. Archive the previous executable, record the new SHA-256/source commit,
   and point all workflow stages at the same candidate only after validation.

Neither the portable workflow repository, its executable configuration nor
production model inputs are changed by committing these source patches.
Keep the temporary fort.6 workaround until its removal is tested. Continue
using `days_mat = 0` for production perennials until catchment checks pass.
