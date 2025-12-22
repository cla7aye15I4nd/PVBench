; RUN: opt -S -passes=globalopt
@g = internal global ptr null, align 8

define void @init() {
  %alloc = call ptr @malloc(i64 48)
  store atomic ptr %alloc, ptr @g seq_cst, align 8
  ret void
} 

define i1 @check() {
  %val = load atomic ptr, ptr @g seq_cst, align 8
  %cmp = icmp eq ptr %val, null
  ret i1 %cmp
}

declare ptr @malloc(i64) allockind("alloc,uninitialized") allocsize(0)