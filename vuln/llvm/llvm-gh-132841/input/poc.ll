target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-unknown"

define void @_Z1sv() #0 {
entry:
  br label %"_ZZ1svEN3$_08__invokeEii.exit"

if.then.i.i:                                      ; No predecessors!
  br label %3

"_ZZ1svEN3$_08__invokeEii.exit":                  ; preds = %entry
  %0 = zext i1 false to i64
  %1 = add i64 0, %0
  %2 = add i64 0, 0
  br i1 false, label %3, label %while.cond.while.end_crit_edge

3:                                                ; preds = %"_ZZ1svEN3$_08__invokeEii.exit", %if.then.i.i
  %pgocount51962 = phi i64 [ 0, %"_ZZ1svEN3$_08__invokeEii.exit" ], [ 0, %if.then.i.i ]
  %pgocount62360 = phi i64 [ 0, %"_ZZ1svEN3$_08__invokeEii.exit" ], [ 0, %if.then.i.i ]
  %pgocount83056 = phi i64 [ %1, %"_ZZ1svEN3$_08__invokeEii.exit" ], [ 0, %if.then.i.i ]
  %pgocount93354 = phi i64 [ %2, %"_ZZ1svEN3$_08__invokeEii.exit" ], [ 0, %if.then.i.i ]
  br label %while.cond.while.end_crit_edge

while.cond.while.end_crit_edge:                   ; preds = %3, %"_ZZ1svEN3$_08__invokeEii.exit"
  %pgocount51961 = phi i64 [ %pgocount51962, %3 ], [ 0, %"_ZZ1svEN3$_08__invokeEii.exit" ]
  %pgocount62359 = phi i64 [ %pgocount62360, %3 ], [ 0, %"_ZZ1svEN3$_08__invokeEii.exit" ]
  %pgocount83055 = phi i64 [ %pgocount83056, %3 ], [ %1, %"_ZZ1svEN3$_08__invokeEii.exit" ]
  %pgocount93353 = phi i64 [ %pgocount93354, %3 ], [ %2, %"_ZZ1svEN3$_08__invokeEii.exit" ]
  store i64 %pgocount51961, ptr getelementptr inbounds nuw (i8, ptr null, i64 40), align 8
  store i64 %pgocount62359, ptr getelementptr inbounds nuw (i8, ptr null, i64 48), align 8
  store i64 %pgocount83055, ptr getelementptr inbounds nuw (i8, ptr null, i64 56), align 8
  store i64 %pgocount93353, ptr getelementptr inbounds nuw (i8, ptr null, i64 64), align 8
  ret void
}

; uselistorder directives
uselistorder ptr null, { 3, 2, 1, 0 }

attributes #0 = { "target-cpu"="znver2" }