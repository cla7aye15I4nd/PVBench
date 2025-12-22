func.func @float_vector234(%arg0: vector<1xf16>) {
   %0 = arith.constant sparse<[[0, 0], [256, 256], [512, 512]], 0101>:vector<1x2x256xf16>
   return
 }