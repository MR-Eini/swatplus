module fixture_data
  implicit none
  type hydrograph
    real :: flo = 0.
  end type
  type water_balance
    real :: area_ha = 1., evap = 0., precip = 0., seep = 0.
  end type
  type reservoir_properties
    integer :: props = 1
    character :: rel_tbl = 'd'
    real :: pvol = 1000., evol = 2000., lag_up = 0., lag_down = 0.
    real :: prev_flo = 99., weir_hgt = 0., br1 = 1., br2 = 0.
  end type
  type reservoir_reference
    character(len=25) :: release = 'null'
  end type
  type reservoir_ids
    integer :: release = 0
  end type
  type decision_table
    character, allocatable :: act_hit(:)
  end type
  type object
    integer :: src_tot = 0
    integer :: num = 1, rcv_tot = 0
    character(len=3), allocatable :: obtyp_out(:), htyp_out(:)
  end type
  type weather
    real :: pet = 1., precip = 2.
  end type
  type station
    type(weather) :: weat
  end type
  type reservoir_hydrology
    real :: evrsv = 1., k = 0.01
  end type
  type basin_codes
    integer :: gwflow = 0
  end type
  type(hydrograph), target :: res(1)
  type(hydrograph), pointer :: wbody
  type(hydrograph) :: ht1, ht2
  type(water_balance) :: res_wat_d(1)
  type(reservoir_properties) :: res_ob(1)
  type(reservoir_reference) :: res_dat_c(1)
  type(reservoir_ids) :: res_dat(1)
  type(decision_table), target :: dtbl_res(0:1)
  type(decision_table), pointer :: d_tbl
  type(object) :: ob(1)
  type(station) :: wst(1)
  type(reservoir_hydrology) :: res_hyd(1)
  type(basin_codes) :: bsn_cc
  integer :: conditions_calls = 0, release_calls = 0, sediment_calls = 0, ctbl_calls = 0
contains
  subroutine reset()
    res(1)%flo = 1100. ! Initial storage 1000 plus incoming water 100.
    res_wat_d(1) = water_balance()
    res_ob(1) = reservoir_properties()
    res_dat_c(1)%release = 'null'
    res_dat(1)%release = 0
    ob(1)%src_tot = 0
    if (allocated(ob(1)%obtyp_out)) deallocate(ob(1)%obtyp_out, ob(1)%htyp_out)
    conditions_calls = 0
    release_calls = 0
    sediment_calls = 0
    ctbl_calls = 0
    ! Table zero deliberately has unallocated arrays, as in the real reader.
    if (.not. allocated(dtbl_res(1)%act_hit)) allocate(dtbl_res(1)%act_hit(1))
  end subroutine
end module fixture_data

subroutine conditions(jres, irel)
  use fixture_data
  integer, intent(in) :: jres, irel
  if (.not. allocated(d_tbl%act_hit)) error stop 'Attempt to evaluate an unallocated table'
  conditions_calls = conditions_calls + 1
end subroutine

subroutine res_control(ires)
  integer, intent(in) :: ires
  call run_reservoir()
end subroutine

subroutine res_hydro(jres, irel, pvol, evol)
  use fixture_data
  integer, intent(in) :: jres, irel
  real, intent(in) :: pvol, evol
  release_calls = release_calls + 1
  ht2%flo = 10.
end subroutine

subroutine res_sediment()
  use fixture_data
  sediment_calls = sediment_calls + 1
end subroutine

subroutine res_rel_conds(ictbl, storage, incoming, extra)
  use fixture_data
  integer, intent(in) :: ictbl
  real, intent(in) :: storage, incoming, extra
  ctbl_calls = ctbl_calls + 1
  ht2%flo = 5.
end subroutine

subroutine gwflow_reservoir(jres)
  use fixture_data
  integer, intent(in) :: jres
  res_wat_d(jres)%seep = 2.4
end subroutine
