#!/usr/bin/env python3
"""Run the actual QUAL2E decay function with underflow trapping enabled."""

import argparse
import os
from pathlib import Path
import re
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
    sediment = (root/'src/sd_channel_sediment3.f90').read_text(encoding='utf-8')
    trap = re.findall(r'^\s*trap_eff = sd_ch\(ich\)%fp_inun_days.*$', sediment, flags=re.MULTILINE)
    vegetation = re.findall(r'^\s*veg = exp.*$', sediment, flags=re.MULTILINE)
    if len(trap) != 1 or len(vegetation) != 1:
        raise SystemExit('Sediment decay source expressions changed')
    driver = '''
program water_quality_regressions
  implicit none
  real, external :: wq_semianalyt, wq_k2m
  real :: actual, tres, tdel, term_m, prock, previous, incoming
  double precision :: rate, exponential, expected
  ! exp(-80) is allowed by exp_w, but multiplying by 1e-5 underflows in REAL32.
  actual = wq_semianalyt(0.0125, 1., 0., 0., 1.e-5, 0.)
  if (actual /= 0.) error stop 'Subnormal decay term was not treated as zero'
  actual = wq_semianalyt(0.0125, 1., 0., 0., 1.e-5, 2.)
  if (abs(actual - 2.) > 1.e-6) error stop 'Meaningful incoming concentration was lost'
  tres = 0.5
  tdel = 0.25
  term_m = 0.3
  prock = -0.2
  previous = 1.
  incoming = 2.
  rate = 1.d0/dble(tres) - dble(prock)
  exponential = exp(-dble(tdel)*rate)
  expected = dble(previous)*exponential + (dble(incoming)/dble(tres)+dble(term_m))/rate*(1.d0-exponential)
  actual = wq_semianalyt(tres, tdel, term_m, prock, previous, incoming)
  if (abs(dble(actual)-expected) > 1.d-6) error stop 'Normal-range analytic solution changed'
  actual = wq_semianalyt(1., 1., 0., 0., 0., 0.)
  if (actual /= 0.) error stop 'Zero concentration changed'
  actual = wq_k2m(0.0125, 1., -0.1, 1.e-5, 0.)
  expected = -dble(1.e-5)*dble(exp(-80.))/(dble(0.0125)*(1.d0-dble(exp(-80.))))
  if (.not. (abs(dble(actual)-expected) <= abs(expected)*1.d-5)) error stop 'Tiny inverse-rate solution changed'
  actual = wq_k2m(tres, tdel, prock, previous, incoming)
  rate = 1.d0/dble(tres)-dble(prock)
  expected = dble(previous)*exp(-dble(tdel)*rate) + (dble(incoming)/dble(tres))/rate*(1.d0-exp(-dble(tdel)*rate))
  expected = (expected-dble(previous)*exp(-dble(tdel)/dble(tres)))/(dble(tres)*(1.d0-exp(-dble(tdel)/dble(tres))))-dble(incoming)/dble(tres)
  if (abs(dble(actual)-expected)>1.d-5) error stop 'Normal inverse-rate solution changed'
  call sediment_decay_regressions()
  print *, 'PASS: decayed subnormal product avoids underflow with traps enabled'
  print *, 'PASS: incoming, normal-range analytic and zero-concentration cases'
end program
subroutine sediment_decay_regressions()
  use utils
  implicit none
  type channel
    real :: fp_inun_days = 1., chd = 200., cov = 0.5
  end type
  type(channel) :: sd_ch(1)
  integer :: ich
  real :: trap_eff, florate_ob, ave_rate, exp_co, veg
  ich = 1
  exp_co = 1000.
  florate_ob = 1.
  ave_rate = 2.
  @TRAP@
  @VEGETATION@
  if (abs(trap_eff - 0.5) > 1.e-6 .or. veg /= 0.) error stop 'Large decay limit failed'
  exp_co = 0.5
  sd_ch(1)%chd = 0.5
  @TRAP@
  @VEGETATION@
  if (abs(trap_eff-0.5*(1.-exp(-0.5))) > 1.e-6) error stop 'Normal floodplain trapping changed'
  if (abs(veg-exp(-2.5)*2250.) > 1.e-5) error stop 'Normal vegetation term changed'
  print *, 'PASS: floodplain/vegetation decay limits and normal-range terms'
end subroutine
'''
    driver = driver.replace('@TRAP@', trap[0]).replace('@VEGETATION@', vegetation[0])
    with tempfile.TemporaryDirectory(prefix='swatplus-water-quality-') as work:
        work = Path(work)
        (work/'driver.f90').write_text(driver, encoding='utf-8')
        exe = work/('test.exe' if os.name == 'nt' else 'test')
        subprocess.run([compiler, '-cpp', '-O0', '-g', '-fcheck=all', '-fbacktrace',
                        '-ffpe-trap=invalid,zero,overflow,underflow', '-ffree-line-length-none',
                        str(root/'src/utils.f90'), str(root/'src/wq_semianalyt.f90'),
                        str(root/'src/wq_k2m.f90'),
                        str(work/'driver.f90'), '-o', str(exe)], cwd=work, check=True)
        subprocess.run([str(exe)], cwd=work, check=True)


if __name__ == '__main__':
    main()
