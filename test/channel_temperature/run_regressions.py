#!/usr/bin/env python3
"""Exercise the actual tributary-mixing block, including a first-position channel."""

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
    source = (root/'src/ch_temp.f90').read_text(encoding='utf-8')
    start, end = '! initialize ruid_array', '!  Step 3. mixing of components'
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit('Channel mixing source markers changed')
    block = source.split(start, 1)[1].split(end, 1)[0]
    # Retain the comment text following the first marker.
    block = '!' + block
    driver = '''
module fixture
  implicit none
  type hydrograph
    real :: flo = 0., temp = 0.
  end type
  type object
    integer :: rcv_tot = 0
    character(len=8), allocatable :: obtyp_in(:)
    integer, allocatable :: obtypno_in(:)
    type(hydrograph), allocatable :: hin_d(:)
    type(hydrograph) :: hd(1)
  end type
  type(object) :: ob(1)
  type(hydrograph) :: ht1
contains
  subroutine setup(n)
    integer, intent(in) :: n
    if (allocated(ob(1)%obtyp_in)) deallocate(ob(1)%obtyp_in, ob(1)%obtypno_in, ob(1)%hin_d)
    ob(1)%rcv_tot = n
    if (n > 0) then
      allocate(ob(1)%obtyp_in(n), ob(1)%obtypno_in(n), ob(1)%hin_d(n))
      ob(1)%obtyp_in = 'ru'
      ob(1)%obtypno_in = 1
    end if
  end subroutine
end module
subroutine mix(nru)
  use fixture
  implicit none
  integer, intent(out) :: nru
  integer :: iob, in, ru_count, ru_index
  integer, allocatable :: ruid_array(:)
  real :: trib1_temp, trib2_temp, trib1_flo, trib2_flo, trib_flo, trib_heat, tw_def
  type weather
    real :: tave = 8.
  end type
  type(weather) :: w
  iob = 1
  tw_def = 5.0 + 0.75*w%tave
''' + block + '''
  nru = ru_count
end subroutine
program tests
  use fixture
  implicit none
  integer :: nru
  real :: mixed
  call setup(1)
  ob(1)%obtyp_in = 'chandeg'
  ob(1)%hin_d(1) = hydrograph(86400., 15.)
  call mix(nru)
  call check(ht1%temp, 15., 'first incoming object is a channel')
  if (nru /= 0) error stop 'Unexpected routing unit'
  call setup(4)
  ob(1)%obtyp_in = ['chandeg ', 'ru      ', 'chandeg ', 'chandeg ']
  ob(1)%hin_d = [hydrograph(86400.,10.), hydrograph(864000.,99.), &
                 hydrograph(259200.,20.), hydrograph(172800.,30.)]
  call mix(nru)
  mixed = ht1%temp
  call check(mixed, 130./6., 'three tributaries and a separate local routing unit')
  if (nru /= 1) error stop 'Routing unit was not collected'
  ob(1)%obtyp_in = ['ru      ', 'chandeg ', 'chandeg ', 'chandeg ']
  ob(1)%hin_d = [hydrograph(864000.,99.), hydrograph(172800.,30.), &
                 hydrograph(86400.,10.), hydrograph(259200.,20.)]
  call mix(nru)
  call check(ht1%temp, mixed, 'tributary order does not change the mixture')
  ob(1)%hin_d%flo = 0.
  call mix(nru)
  call check(ht1%temp, 11., 'zero-flow fallback')
  call setup(0)
  call mix(nru)
  call check(ht1%temp, 11., 'unallocated incoming arrays at a headwater')
  print *, 'PASS: first tributary, multiple tributaries, ordering and headwater fallback'
contains
  subroutine check(actual, expected, label)
    real, intent(in) :: actual, expected
    character(len=*), intent(in) :: label
    if (.not. (abs(actual-expected) < 1.e-5)) then
      print *, 'FAIL: ', label, actual, expected
      error stop 1
    end if
  end subroutine
end program
'''
    with tempfile.TemporaryDirectory(prefix='swatplus-channel-temperature-') as work:
        work = Path(work)
        (work/'driver.f90').write_text(driver, encoding='utf-8')
        exe = work/('test.exe' if os.name == 'nt' else 'test')
        subprocess.run([compiler, '-O0', '-g', '-fcheck=all', '-fbacktrace',
                        '-ffpe-trap=invalid,zero,overflow,underflow', '-ffree-line-length-none',
                        str(work/'driver.f90'), '-o', str(exe)], cwd=work, check=True)
        subprocess.run([str(exe)], cwd=work, check=True)


if __name__ == '__main__':
    main()
