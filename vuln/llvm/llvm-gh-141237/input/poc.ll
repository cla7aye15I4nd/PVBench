target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

define void @reduced_test_(ptr %0, i64 %1, ptr %.sroa.067.0.copyload) {
._crit_edge103:
  br label %2

2:                                                ; preds = %2, %._crit_edge103
  %indvars.iv = phi i64 [ 0, %._crit_edge103 ], [ %indvars.iv.next, %2 ]
  %3 = phi i64 [ %1, %._crit_edge103 ], [ %10, %2 ]
  %4 = load double, ptr %0, align 8
  %5 = fmul double %4, 0.000000e+00
  %6 = fdiv double %5, 0.000000e+00
  %7 = sub i64 %indvars.iv, %1
  %8 = getelementptr double, ptr %.sroa.067.0.copyload, i64 %indvars.iv
  %9 = getelementptr double, ptr %8, i64 %7
  store double %6, ptr %9, align 8
  %indvars.iv.next = add i64 %indvars.iv, 1
  %10 = add i64 %3, -1
  %11 = icmp sgt i64 %3, 0
  br i1 %11, label %2, label %._crit_edge106

._crit_edge106:                                   ; preds = %2
  ret void
}
