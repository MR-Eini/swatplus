#!/usr/bin/env python3
"""Exercise the actual area_calc.out open/write statements with 15,136 inflows."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--compiler", default=os.environ.get("FC", "gfortran"))
    args = parser.parse_args()
    root = args.source_root.resolve()
    compiler = shutil.which(args.compiler)
    if compiler is None:
        raise SystemExit(f"Fortran compiler not found: {args.compiler}")
    basin = (root / "src/proc_bsn.f90").read_text(encoding="utf-8")
    connect = (root / "src/hyd_connect.f90").read_text(encoding="utf-8")
    opens = re.findall(r'^\s*call open_output_file\(9004,.*$', basin, flags=re.MULTILINE)
    if len(opens) != 1:
        raise SystemExit("Expected one area_calc.out open statement")
    marker = "!! write calculated and input drainage areas for all objects except hru's"
    if connect.count(marker) != 1 or connect.count("1002  format") != 1:
        raise SystemExit("Drainage-area output source markers changed")
    output = connect.split(marker, 1)[1].split("1002  format", 1)[0]
    driver = f"""
program large_area_record
  use output_path_module
  implicit none
  integer, parameter :: inflows = 15136
  type object
    character(len=3) :: typ = 'ru'
    integer :: num = 1, rcv_tot = 0
    real :: area_ha = 1., area_ha_calc = 1.
    character(len=3), allocatable :: obtyp_in(:)
    integer, allocatable :: obtypno_in(:), obj_in(:)
    real, allocatable :: frac_in(:)
  end type
  type object_count
    integer :: objs = inflows + 1
  end type
  type(object_count) :: sp_ob
  type(object), allocatable :: ob(:)
  integer :: iob, jj, i, bytes
  allocate(ob(inflows + 1))
  ob(1)%typ = 'aqu'
  ob(1)%rcv_tot = inflows
  allocate(ob(1)%obtyp_in(inflows), ob(1)%obtypno_in(inflows), &
           ob(1)%obj_in(inflows), ob(1)%frac_in(inflows))
  ob(1)%obtyp_in = 'ru'
  ob(1)%frac_in = 1.
  do i = 1, inflows
    ob(1)%obtypno_in(i) = i
    ob(1)%obj_in(i) = i + 1
  end do
  {opens[0]}
  {output}
  close(9004)
  inquire(file='area_calc.out', size=bytes)
  if (bytes <= 80000) error stop 'Fixture did not exceed the old record limit'
  print *, 'PASS: area_calc.out wrote', bytes, 'bytes with', inflows, 'inflows'
end program large_area_record
"""
    with tempfile.TemporaryDirectory(prefix="swatplus-area-record-") as work:
        work = Path(work)
        (work / "driver.f90").write_text(driver, encoding="utf-8")
        exe = work / ("large_area_record.exe" if os.name == "nt" else "large_area_record")
        subprocess.run([compiler, "-O0", "-g", "-fcheck=all", "-ffree-line-length-none",
                        str(root / "src/output_path_module.f90"), str(work / "driver.f90"),
                        "-o", str(exe)], cwd=work, check=True)
        subprocess.run([str(exe)], cwd=work, check=True)
        # Confirm every incoming object ID was written, not merely a long partial record.
        fields = (work / "area_calc.out").read_text().split()
        if len(fields) != 6 + 6 * 15136:
            raise SystemExit(f"Unexpected diagnostic field count: {len(fields)}")
        if [int(fields[6 + 6 * i + 1]) for i in range(15136)] != list(range(1, 15137)):
            raise SystemExit("Incoming routing-unit IDs were truncated or reordered")


if __name__ == "__main__":
    main()
