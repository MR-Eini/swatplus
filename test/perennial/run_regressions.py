#!/usr/bin/env python3
"""Compile the actual PHU/LAI source blocks and xmon against small fixtures.

The tested routines execute extracted source blocks, not Python translations.
Fixtures supply their required structures; reference sums and invariance checks
provide expectations. This does not replace a complete catchment simulation.
"""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def between(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Source markers changed: {start!r}, {end!r}")
    return text.split(start, 1)[1].split(end, 1)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--compiler", default=os.environ.get("FC", "gfortran"))
    args = parser.parse_args()
    root = args.source_root.resolve()
    compiler = shutil.which(args.compiler)
    if compiler is None:
        raise SystemExit(f"Fortran compiler not found: {args.compiler}")

    plant = (root / "src/plant_init.f90").read_text(encoding="utf-8")
    dormant = (root / "src/pl_dormant.f90").read_text(encoding="utf-8")
    phu = between(plant, "! first compute base0 units for entire year", "! set initial operation for date scheduling")
    lai = between(dormant, "!! lower lai by same ratio", "!! compute leaf biomass drop")
    # Preserve declaration initialization so the original SAVE defect remains
    # observable when this driver is run against the unpatched release.
    igrow = next(line for line in plant.splitlines() if "integer :: igrow" in line)
    found = "logical :: grow_start_found" if "logical :: grow_start_found" in plant else ""
    routines = f"""
subroutine initialize_phu(j, ipl, idp, start_day)
  use fixture_data
  use time_module
  implicit none
  integer, intent(in) :: j, ipl, idp
  integer, optional, intent(out) :: start_day
  integer :: iob, iwst, iwgn, mo, day_mo, iday, iday_sh, iday_sum
  {igrow}
  {found}
  real :: phu0, phutot, tave, phuday, sd, dd, sdlat, h, daylength
  {phu}
  if (present(start_day)) start_day = igrow
end subroutine initialize_phu

subroutine dormant_lai(j, ipl, idp, rto)
  use fixture_data
  implicit none
  integer, intent(in) :: j, ipl, idp
  real, intent(in) :: rto
  real :: lai_init
  {lai}
end subroutine dormant_lai
"""
    tests = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="swatplus-perennial-") as work:
        work = Path(work)
        (work / "routines.f90").write_text(routines, encoding="utf-8")
        exe = work / ("regressions.exe" if os.name == "nt" else "regressions")
        command = [compiler, "-O0", "-g", "-fcheck=all", "-fbacktrace",
                   "-ffpe-trap=invalid,zero,overflow", "-ffree-line-length-none",
                   str(tests / "fixtures.f90"), str(root / "src/xmon.f90"),
                   str(work / "routines.f90"), str(tests / "regressions.f90"),
                   "-o", str(exe)]
        print(shlex.join(command), flush=True)
        subprocess.run(command, cwd=work, check=True)
        subprocess.run([str(exe)], cwd=work, check=True)


if __name__ == "__main__":
    main()
