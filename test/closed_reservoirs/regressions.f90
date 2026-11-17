program closed_reservoir_regressions
  use fixture_data
  implicit none
  character(len=30) :: mode
  call get_command_argument(1, mode)
  call reset()
  if (trim(mode) == 'bad_outlet') then
    ob(1)%src_tot = 1
    allocate(ob(1)%obtyp_out(1), ob(1)%htyp_out(1))
    ob(1)%obtyp_out = 'sdc'
    ob(1)%htyp_out = 'tot'
    call run_reservoir()
    error stop 'Invalid outlet was accepted'
  else if (trim(mode) == 'unknown_table') then
    res_dat_c(1)%release = 'misspelled_table'
    call run_reservoir()
    error stop 'Unknown table was accepted'
  end if

  ! Intentional null, no outgoing links: retain full water balance and sediment call.
  call run_reservoir()
  call close_to(ht2%flo, 0., 'closed surface release')
  call close_to(res(1)%flo, 1107.6, 'storage includes inflow, precipitation, evaporation and seepage')
  call close_to(res_wat_d(1)%evap, 10., 'evaporation retained')
  call close_to(res_wat_d(1)%seep, 2.4, 'seepage retained')
  if (conditions_calls /= 0 .or. release_calls /= 0) error stop 'Null table was evaluated'
  if (sediment_calls /= 1) error stop 'Closed sediment processing was skipped'
  call close_to(res_ob(1)%prev_flo, 0., 'no stale lagged release')

  ! The actual command dispatcher must process a reservoir with no incoming objects.
  call reset()
  res(1)%flo = 1000.
  ob(1)%rcv_tot = 0
  call dispatch_reservoir()
  call close_to(res(1)%flo, 1007.6, 'headwater reservoir daily water balance is not skipped')
  if (sediment_calls /= 1) error stop 'Headwater reservoir was not dispatched'

  ! Named rules still take the original decision-table and hydrology path.
  call reset()
  res_dat_c(1)%release = 'drawdown_days'
  res_dat(1)%release = 1
  call run_reservoir()
  if (conditions_calls /= 1 .or. release_calls /= 1) error stop 'Named decision table not evaluated'
  call close_to(ht2%flo, 10., 'named release preserved')
  call close_to(res(1)%flo, 1097.6, 'named-rule balance preserved')

  ! Null after a named table cannot inherit its release; recharge-only outlet is allowed.
  call reset()
  res_dat_c(1)%release = 'NULL'
  ob(1)%src_tot = 1
  allocate(ob(1)%obtyp_out(1), ob(1)%htyp_out(1))
  ob(1)%obtyp_out = 'aqu'
  ob(1)%htyp_out = 'rhg'
  call run_reservoir()
  call close_to(ht2%flo, 0., 'recharge-only reservoir has no surface release')
  call close_to(res(1)%flo, 1107.6, 'recharge-only storage balance')
  if (conditions_calls /= 0 .or. release_calls /= 0) error stop 'Prior table leaked into null case'

  call reset()
  res_dat_c(1)%release = 'ctbl_example'
  res_dat(1)%release = 1
  res_ob(1)%rel_tbl = 'c'
  call run_reservoir()
  if (ctbl_calls /= 1) error stop 'Conditional table path changed'
  call close_to(ht2%flo, 5., 'conditional-table release preserved')
  print *, 'PASS: closed/no-outlet and recharge-only reservoirs retain water balance'
  print *, 'PASS: named decision and conditional release paths are preserved'
contains
  subroutine close_to(actual, expected, label)
    real, intent(in) :: actual, expected
    character(len=*), intent(in) :: label
    if (.not. (abs(actual - expected) < 0.001)) then
      print *, 'FAIL: ', label, actual, expected
      error stop 1
    end if
  end subroutine
end program
