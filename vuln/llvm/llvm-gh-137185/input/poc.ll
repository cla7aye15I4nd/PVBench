source_filename = "reduced.ll"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128-ni:1-p2:32:8:8:32-ni:2"
target triple = "x86_64-unknown-linux-gnu"

define void @widget() {
bb:
  %sitofp = sitofp i32 0 to double
  br label %bb1

bb1:                                              ; preds = %bb1, %bb
  %phi = phi i32 [ %add, %bb1 ], [ 0, %bb ]
  %phi2 = phi double [ %fsub, %bb1 ], [ 0.000000e+00, %bb ]
  %fsub = fsub double %phi2, %sitofp
  %add = add i32 %phi, 1
  %icmp = icmp ult i32 %phi, 252
  br i1 %icmp, label %bb1, label %bb3

bb3:                                              ; preds = %bb1
  %phi4 = phi double [ %phi2, %bb1 ]
  %phi5 = phi double [ %fsub, %bb1 ]
  ret void
}