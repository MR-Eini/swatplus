      function wq_semianalyt(tres, tdel, term_m, prock, cprev, cint)
      
!!    ~ ~ ~ PURPOSE ~ ~ ~
!!    This function solves a semi-analytic solution for the QUAL2E equations (cfr Befekadu Woldegiorgis).

!!    ~ ~ ~ INCOMING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
!!    xx          |none          |Exponential argument
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

!!    ~ ~ ~ OUTGOING VARIABLES ~ ~ ~
!!    name        |units         |definition
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
!!    tres        |days          |residence time in reach
!!    tdel        |days          |calculation time step
!!    term_m      |              |constant term in equation
!!    cprev       |mg/l          |concentration previous timestep
!!    cint        |mg/l          |incoming concentration      
!!    ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

!!    ~ ~ ~ SUBROUTINES/FUNCTIONS CALLED ~ ~ ~
!!    Intrinsic: Exp
 
!!    ~ ~ ~ ~ ~ ~ END SPECIFICATIONS ~ ~ ~ ~ ~ ~
      use utils

      implicit none
 
      real, intent (in) :: tres
      real, intent (in) :: tdel
      real, intent (in) :: prock
      real, intent (in) :: term_m
      real, intent (in) :: cprev
      real, intent (in) :: cint
      real :: help1 = 0.
      real :: help2 = 0.
      real :: help3 = 0.
      real :: help4 = 0.
      real :: term1 = 0.
      real :: term2 = 0.
      real :: yy = 0.
      double precision :: product
      real :: wq_semianalyt

      help1 = 1. / tres - prock
      help2 = exp_w(-tdel * help1)
      help3 = cint / tres + term_m
      help4 = help3 / help1
      ! A decayed concentration can be below the normal single-precision range
      ! even though exp_w itself is safe. Test each product in double precision
      ! before converting, so negligible subnormal terms do not trap underflow.
      product = dble(cprev) * dble(help2)
      term1 = 0.
      if (abs(product) >= dble(tiny(term1))) term1 = real(product)
      product = dble(help4) * dble(1. - help2)
      term2 = 0.
      if (abs(product) >= dble(tiny(term2))) term2 = real(product)
      yy = term1 + term2
      wq_semianalyt = term1 + term2
      
    !! if time of residence in reach is less than or eq to timestep don't do this. MJW 2023
      !if (tres <= tdel) then
      !    wq_semianalyt = cint  
      !end if

      return
      end function wq_semianalyt
