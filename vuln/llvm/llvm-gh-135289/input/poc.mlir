func.func @test_muli() -> (i32) {
  %0 = "test.constant"() {value = 0x7fffffff} : () -> i32
  %1 = "test.constant"() {value = -2147483648} : () -> i32
  %2 = "test.constant"() {value = 0x80000000} : () -> i32
  %3 = "test.constant"() {value = 0xffffffff} : () -> i32
  %4 = arith.muli %0, %1 : i32
  %5 = arith.muli %4, %2 : i32
  %6 = arith.muli %5, %3 : i32
  return %6 : i32
}
