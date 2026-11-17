     function wq_k2m (t1, t2, tk, c1, c2)
      
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

      external :: wq_semianalyt

      real, intent (in) :: t1
      real, intent (in) :: t2
      real, intent (in) :: tk
      real, intent (in) :: c1
      real, intent (in) :: c2
      real :: h2 = 0.
      real :: help = 0.
      real :: tm = 0.
      double precision :: tm_full
      real :: wq_k2m
      real :: wq_semianalyt
      
      h2 = wq_semianalyt (t1, t2, 0., tk, c1, c2)
      help = exp_w(-t2 / t1)
         
      ! Keep tiny intermediate products representable until the inverse-rate
      ! calculation is complete; division can bring them back into REAL's range.
      tm_full = (dble(h2) - dble(c1) * dble(help)) / &
          (dble(t1) * (1.d0 - dble(help))) - dble(c2) / dble(t1)
      tm = 0.
      if (abs(tm_full) >= dble(tiny(tm))) tm = real(tm_full)
      ! The old h1/h3 evaluations were unused and could themselves underflow.
      wq_k2m = tm

      return
      end function wq_k2m
