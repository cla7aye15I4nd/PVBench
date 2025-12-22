define i32 @f(ptr %arg, ptr %arg2) {
  store ptr %arg, ptr %arg2
  %getelementptr = getelementptr float, ptr %arg, i64 2305843009213693951
  %load = load i32, ptr %getelementptr, align 4
  ret i32 %load
}