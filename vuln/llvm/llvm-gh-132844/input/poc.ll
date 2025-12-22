target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

define swiftcc { ptr, i8 } @julia_try_compute_fieldidx_stmt_92847.3(<4 x ptr> %0, <4 x ptr> %1) #0 {
  %3 = alloca [35 x ptr], i32 0, align 16
  %4 = load <4 x ptr>, ptr null, align 8
  %5 = getelementptr i8, ptr %3, i64 216
  %6 = extractelement <4 x ptr> %4, i64 3
  store ptr %6, ptr %5, align 8
  %7 = getelementptr i8, ptr %3, i64 208
  %8 = extractelement <4 x ptr> %0, i64 0
  store ptr %8, ptr %7, align 8
  %9 = getelementptr i8, ptr %3, i64 200
  %10 = extractelement <4 x ptr> %0, i64 3
  store ptr %10, ptr %9, align 8
  %11 = getelementptr i8, ptr %3, i64 192
  %12 = extractelement <4 x ptr> %1, i64 0
  store ptr %12, ptr %11, align 8
  ret { ptr, i8 } zeroinitializer
}

attributes #0 = { "target-cpu"="x86-64-v4" }