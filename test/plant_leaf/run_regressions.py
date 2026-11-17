#!/usr/bin/env python3
"""Compile the actual leaf-growth routine with extreme and ordinary curve inputs."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--compiler',default=os.environ.get('FC','gfortran'))
    args=parser.parse_args(); root=args.source_root.resolve(); compiler=shutil.which(args.compiler)
    if not compiler: raise SystemExit(f'Compiler not found: {args.compiler}')
    fixture='''
module plant_data_module
  type coefficients
    real :: leaf1=2., leaf2=4.
  end type
  type plant_data
    character(len=18) :: typ='perennial'
    real :: dlai=0.9, laixco_tree=0.3, chtmx=10.
    integer :: mat_yrs=10
  end type
  type(coefficients) :: plcp(1)
  type(plant_data) :: pldb(1)
end module
module basin_module
end module
module hru_module
  integer :: ihru=1, ipl=1
end module
module plant_module
  type current_plant
    real :: phuacc=0.2, phuacc_p=0.2, lai_pot=5.
    integer :: idplt=1, curyr_mat=10
  end type
  type growing_plant
    real :: laimxfr=0., cht=1., leaf_frac=0., lai=0.5, olai=0., dphu=0.
  end type
  type plant_stress
    real :: strsw=1.
  end type
  type community
    integer :: npl=1
    type(current_plant) :: plcur(1)
    type(growing_plant) :: plg(1)
    type(plant_stress) :: plstr(1)
  end type
  type(community) :: pcom(1)
end module
module carbon_module
end module
module organic_mineral_mass_module
end module
'''
    tests='''
program tests
  use plant_module
  implicit none
  real :: expected_f, expected_lai
  ! At high accumulated heat units the logistic function tends to one.
  pcom(1)%plcur(1)%phuacc=1000.
  call pl_leaf_gro()
  if (pcom(1)%plg(1)%laimxfr/=1.) error stop 'High-heat-unit logistic limit failed'
  pcom(1)=community()
  expected_f=0.2/(0.2+exp(1.2))
  expected_lai=0.5+expected_f*5.*(1.-exp(-22.5))
  call pl_leaf_gro()
  if (abs(pcom(1)%plg(1)%laimxfr-expected_f)>1.e-6) error stop 'Normal logistic curve changed'
  if (abs(pcom(1)%plg(1)%lai-expected_lai)>1.e-5) error stop 'Normal LAI increment changed'
  pcom(1)=community()
  pcom(1)%plcur(1)%lai_pot=100.
  pcom(1)%plg(1)%lai=0.
  call pl_leaf_gro()
  if (abs(pcom(1)%plg(1)%lai-100.*expected_f)>1.e-4) error stop 'Strong canopy-gap decay limit failed'
  print *, 'PASS: logistic and canopy-gap limits with underflow traps enabled'
  print *, 'PASS: normal logistic and leaf-area increments preserved'
end program
'''
    with tempfile.TemporaryDirectory(prefix='swatplus-plant-leaf-') as work:
        work=Path(work); (work/'fixture.f90').write_text(fixture); (work/'tests.f90').write_text(tests)
        exe=work/('test.exe' if os.name=='nt' else 'test')
        subprocess.run([compiler,'-cpp','-O0','-g','-fcheck=all','-fbacktrace',
            '-ffpe-trap=invalid,zero,overflow,underflow','-ffree-line-length-none',
            str(root/'src/utils.f90'),str(work/'fixture.f90'),str(root/'src/pl_leaf_gro.f90'),
            str(work/'tests.f90'),'-o',str(exe)],cwd=work,check=True)
        subprocess.run([str(exe)],cwd=work,check=True)


if __name__=='__main__': main()
