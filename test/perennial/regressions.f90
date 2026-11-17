program perennial_regressions
  use fixture_data
  use time_module
  implicit none
  interface
    subroutine initialize_phu(j, ipl, idp, start_day)
      integer, intent(in) :: j, ipl, idp
      integer, optional, intent(out) :: start_day
    end subroutine
    subroutine dormant_lai(j, ipl, idp, rto)
      integer, intent(in) :: j, ipl, idp
      real, intent(in) :: rto
    end subroutine
  end interface
  integer :: i, j, start_day, calendar
  real :: initial(2), expected
  character(len=18), parameter :: annual_types(4) = [character(len=18) :: &
      "warm_annual", "cold_annual", "warm_annual_tuber", "cold_annual_tuber"]

  call setup()
  ! The same perennial must not change after an annual at another station,
  ! or when a different plant precedes it within the same community.
  do j = 1, 2
    call initialize_phu(j, 1, 1)
    initial(j) = pcom(j)%plcur(1)%phumat
  end do
  do i = 1, size(annual_types)
    pldb(3)%typ = annual_types(i)
    call initialize_phu(2, 2, 3)
    call initialize_phu(1, 1, 1)
    call assert_close(pcom(1)%plcur(1)%phumat, initial(1), "northern HRU order")
    call initialize_phu(1, 2, 3)
    call initialize_phu(2, 1, 1)
    call assert_close(pcom(2)%plcur(1)%phumat, initial(2), "southern HRU order")
    call initialize_phu(1, 2, 3)
    call initialize_phu(1, 1, 1)
    call assert_close(pcom(1)%plcur(1)%phumat, initial(1), "within-community plant order")
  end do
  print *, "PASS: perennial HRU/plant order, both hemispheres, four annual types"

  ! Force an immediate dormancy exit so the independent start days are known.
  ! Test normal and leap calendars, including windows longer than two years.
  do calendar = 1, 2
    if (calendar == 2) ndays = [0,31,60,91,121,152,182,213,244,274,305,335,366]
    do j = 1, 2
      wgn_pms(j)%daylmn = -100.
      pldb(1)%days_mat = 800
      call initialize_phu(j, 1, 1, start_day)
      if (j == 1) call assert_close(real(start_day), 1., "northern start day")
      if (j == 2) call assert_close(real(start_day), 181., "southern start day")
      expected = reference_heat(j, start_day, pldb(1)%days_mat)
      call assert_close(pcom(j)%plcur(1)%phumat, expected, "calendar wrap over multiple years")
    end do
  end do
  print *, "PASS: year wrapping in both hemispheres, normal and leap calendars"

  ! A failed dormancy search must retain the hemisphere fallback, not the
  ! terminated DO counter (182/362), and report that fallback to stdout.
  do j = 1, 2
    wgn_pms(j)%daylmn = 100.
    pldb(1)%days_mat = 110
    call initialize_phu(j, 1, 1, start_day)
    expected = 1.
    if (j == 2) expected = 181.
    call assert_close(real(start_day), expected, "no dormancy exit fallback")
    call assert_close(pcom(j)%plcur(1)%phumat, reference_heat(j, int(expected), 110), "fallback PHU")
  end do
  print *, "PASS: failed dormancy searches use valid deterministic fallback days"

  ! Preserve the two input branches that never use a growth start day.
  do j = 1, 2
    pldb(1)%days_mat = 0
    call initialize_phu(j, 1, 1)
    call assert_close(pcom(j)%plcur(1)%phumat, 0.95 * reference_heat(j, 1, 364), "days_mat zero")
    pldb(1)%days_mat = -1
    pcom(j)%plcur(1)%phumat = -900.
    call initialize_phu(j, 1, 1)
    call assert_close(pcom(j)%plcur(1)%phumat, 900., "negative days_mat unchanged")
  end do
  print *, "PASS: zero and negative days_mat branches preserved"

  ! Annuals in an entirely cold climate must not inherit a previous start.
  pldb(3)%typ = "warm_annual"
  wgn(1)%tmpmx = -10.
  wgn(1)%tmpmn = -10.
  call initialize_phu(1, 2, 3, start_day)
  call assert_close(real(start_day), 1., "no annual planting threshold fallback")
  call assert_close(pcom(1)%plcur(2)%phumat, 0., "cold-climate heat sum")
  print *, "PASS: unsuccessful annual search cannot inherit another plant's start"

  pldb(1)%alai_min = 0.75
  pcom(1)%plg(1)%lai = 4.
  call dormant_lai(1, 1, 1, 0.)
  call assert_close(pcom(1)%plg(1)%lai, 0.75, "dormant LAI minimum")
  pcom(1)%plg(1)%lai = 0.2
  call dormant_lai(1, 1, 1, 0.)
  call assert_close(pcom(1)%plg(1)%lai, 0.2, "do not create canopy")
  pcom(1)%plg(1)%lai = 0.
  call dormant_lai(1, 1, 1, 0.)
  call assert_close(pcom(1)%plg(1)%lai, 0., "bare canopy stays bare")
  pldb(1)%alai_min = 0.
  pcom(1)%plg(1)%lai = 4.
  call dormant_lai(1, 1, 1, 0.)
  call assert_close(pcom(1)%plg(1)%lai, 0., "zero minimum allows zero LAI")
  pldb(1)%alai_min = 0.75
  pcom(1)%plg(1)%lai = 4.
  call dormant_lai(1, 1, 1, 0.5)
  call assert_close(pcom(1)%plg(1)%lai, 2., "retain larger ratio-based LAI")
  print *, "PASS: dormancy LAI minimum, cap, zero canopy, and ratio behavior"
  print *, "All perennial regression checks passed."
contains
  subroutine assert_close(actual, wanted, label)
    real, intent(in) :: actual, wanted
    character(len=*), intent(in) :: label
    if (.not. (abs(actual - wanted) <= max(0.001, abs(wanted) * 0.00001))) then
      print *, "FAIL: ", label, "; actual=", actual, "; expected=", wanted
      error stop 1
    end if
  end subroutine

  real function reference_heat(station_id, first_day, duration) result(total)
    integer, intent(in) :: station_id, first_day, duration
    integer :: offset, day, month
    total = 0.
    day = first_day
    do offset = 0, duration
      do while (day > ndays(13))
        day = day - ndays(13)
      end do
      month = 1
      do while (day > ndays(month + 1))
        month = month + 1
      end do
      total = total + max(0., (wgn(station_id)%tmpmx(month) + wgn(station_id)%tmpmn(month)) / 2. - pldb(1)%t_base)
      day = day + 1
    end do
  end function
end program perennial_regressions
