! Minimal data structures for compiling the original PHU and LAI source blocks.
module time_module
  implicit none
  integer :: ndays(13) = [0,31,59,90,120,151,181,212,243,273,304,334,365]
end module time_module

module fixture_data
  implicit none
  type plant_data
    character(len=18) :: typ = "perennial"
    integer :: days_mat = 110
    real :: t_base = 5., alai_min = 0.75
  end type
  type current_plant
    real :: phumat = 0.
  end type
  type growing_plant
    real :: lai = 0.
  end type
  type community
    type(current_plant) :: plcur(2)
    type(growing_plant) :: plg(2)
  end type
  type hru_data
    integer :: obj_no = 1
  end type
  type object_data
    integer :: wst = 1
  end type
  type weather_codes
    integer :: wgn = 1
  end type
  type station
    type(weather_codes) :: wco
  end type
  type generator
    real :: lat = 51., tmpmx(12) = 0., tmpmn(12) = 0.
  end type
  type generator_parameters
    real :: latsin = 0., latcos = 1., daylth = 2., daylmn = 8.
  end type
  type(plant_data) :: pldb(3)
  type(community) :: pcom(2)
  type(hru_data) :: hru(2)
  type(object_data) :: ob(2)
  type(station) :: wst(2)
  type(generator) :: wgn(2)
  type(generator_parameters) :: wgn_pms(2)
contains
  subroutine setup()
    integer :: i
    real :: radians
    do i = 1, 2
      hru(i)%obj_no = i
      ob(i)%wst = i
      wst(i)%wco%wgn = i
    end do
    wgn(1)%lat = 51.
    wgn(2)%lat = -34.
    wgn(1)%tmpmx = [-2.,0.,4.,9.,14.,17.,19.,18.,13.,8.,3.,0.]
    wgn(2)%tmpmx = [24.,24.,20.,16.,12.,9.,8.,10.,13.,16.,19.,22.]
    do i = 1, 2
      wgn(i)%tmpmn = wgn(i)%tmpmx
      radians = wgn(i)%lat * acos(-1.) / 180.
      wgn_pms(i)%latsin = sin(radians)
      wgn_pms(i)%latcos = cos(radians)
    end do
    pldb(3)%typ = "cold_annual"
  end subroutine setup
end module fixture_data
