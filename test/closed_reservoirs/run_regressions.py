#!/usr/bin/env python3
"""Compile actual reservoir release/balance blocks with small fixture data."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--compiler', default=os.environ.get('FC', 'gfortran'))
    args = parser.parse_args()
    root = args.source_root.resolve()
    compiler = shutil.which(args.compiler)
    if not compiler:
        raise SystemExit(f'Compiler not found: {args.compiler}')
    source = (root/'src/res_control.f90').read_text(encoding='utf-8')
    markers = ['!! perform reservoir water/sediment balance', '!! calculate water balance for day',
               '!! subtract sediment leaving from reservoir']
    if any(source.count(marker) != 1 for marker in markers):
        raise SystemExit('Reservoir source block markers changed')
    release = source.split(markers[0], 1)[1].split(markers[1], 1)[0]
    balance = source.split(markers[1], 1)[1].split(markers[2], 1)[0]
    command = (root/'src/command.f90').read_text(encoding='utf-8')
    dispatch = command.split('case ("res")   ! reservoir', 1)[1].split('case ("recall")   ! recall hydrograph', 1)[0]
    routine = f'''
subroutine run_reservoir()
  use fixture_data
  implicit none
  integer :: jres, iob, idat, irel, ictbl, ii, iwst
  real :: pvol_m3, evol_m3, dep, weir_hgt, alpha_up, alpha_down
  jres = 1
  iob = 1
  iwst = 1
  wbody => res(1)
  ht2%flo = 0.
  {release}
  {balance}
end subroutine run_reservoir
subroutine dispatch_reservoir()
  use fixture_data
  implicit none
  integer :: ires, icmd
  icmd = 1
  {dispatch}
end subroutine dispatch_reservoir
'''
    tests = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='swatplus-closed-reservoir-') as work:
        work = Path(work)
        (work/'routine.f90').write_text(routine, encoding='utf-8')
        exe = work/('test.exe' if os.name == 'nt' else 'test')
        subprocess.run([compiler, '-O0', '-g', '-fcheck=all', '-fbacktrace',
                        '-ffpe-trap=invalid,zero,overflow', '-ffree-line-length-none',
                        str(tests/'fixtures.f90'), str(work/'routine.f90'),
                        str(tests/'regressions.f90'), '-o', str(exe)], cwd=work, check=True)
        subprocess.run([str(exe)], cwd=work, check=True)
        for mode, message in [('bad_outlet', 'surface outlet requires a release rule'),
                              ('unknown_table', 'Reservoir release table was not found')]:
            result = subprocess.run([str(exe), mode], cwd=work, capture_output=True,
                                    text=True, errors='replace')
            if result.returncode == 0 or message not in result.stdout + result.stderr:
                raise SystemExit(f'{mode} did not produce the expected validation error:\n{result.stdout}\n{result.stderr}')
            print(f'PASS: {mode} is rejected explicitly')


if __name__ == '__main__':
    main()
