module {
  llvm.func @powf(f32, f32) -> f32 attributes {memory_effects = #llvm.memory_effects<other = none, argMem = none, inaccessibleMem = none>, sym_visibility = "private"}
  func.func @main() -> memref<2x2xf32> {
    %c1 = arith.constant 1 : index
    %c2 = arith.constant 2 : index
    %c0 = arith.constant 0 : index
    %0 = llvm.mlir.constant(-4.770000e+00 : f32) : f32
    %1 = llvm.mlir.constant(8.751000e+01 : f32) : f32
    %alloc = memref.alloc() {alignment = 64 : i64} : memref<2x2xf32>
    %2 = llvm.mlir.constant(1 : i64) : i64
    %3 = llvm.mlir.constant(4 : i32) : i32
    omp.parallel num_threads(%3 : i32) {
      omp.wsloop {
        omp.loop_nest (%arg0, %arg1) : index = (%c0, %c0) to (%c2, %c2) step (%c1, %c1) {
          memref.alloca_scope  {
            %4 = llvm.call @powf(%1, %0) : (f32, f32) -> f32
            memref.store %4, %alloc[%arg0, %arg1] : memref<2x2xf32>
          }
          omp.yield
        }
      }
      omp.terminator
    }
    return %alloc : memref<2x2xf32>
  }
}
