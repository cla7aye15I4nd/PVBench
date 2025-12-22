// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: -allow-natives-syntax --allow-natives-syntax --turboshaft --turboshaft-assert-types

// This test targets a bug in TurboShaft type inference where TupleOp types were
// not handled and defaulted to Typer::TypeForRepresentation. With
// --turboshaft-assert-types, this could trigger an assertion/crash when a
// TupleOp's type was requested. The patch introduces explicit handling for
// TupleOp by constructing a TupleType from its input types.
//
// The original PoC exercises a loop whose IR formation in TurboShaft causes a
// TupleOp to be queried for its type during type inference. The test ensures:
//  - No crash during optimization and execution (primary regression signal).
//  - Correct functional behavior is preserved in similar loop patterns.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// Original PoC: empty loop with multiplicative update.
function f() {
  for (let i = 1; i < 100; i *= 4) {
  }
}

%PrepareFunctionForOptimization(f);
f();
%OptimizeFunctionOnNextCall(f);
// Should not crash after fix when optimized.
f();

// Strengthened scenario 1: Use the same multiplicative loop but perform work
// and check the computed sum to ensure semantics are intact.
function sumMul4Limit100() {
  let sum = 0;
  for (let i = 1; i < 100; i *= 4) {
    sum += i;
  }
  return sum;
}

// Warm-up and optimize; verify both unoptimized and optimized results.
%PrepareFunctionForOptimization(sumMul4Limit100);
let r1 = sumMul4Limit100();
assertEquals(r1, 85, "sum before opt");
%OptimizeFunctionOnNextCall(sumMul4Limit100);
let r2 = sumMul4Limit100();
assertEquals(r2, 85, "sum after opt");

// Strengthened scenario 2: Similar structure with different multiplier and limit.
// This keeps the loop/induction pattern that previously tickled the TupleOp path
// in the typer. We verify correctness and no crash.
function sumMul3Limit1000() {
  let sum = 0;
  for (let i = 2; i < 1000; i *= 3) {
    sum += (i & 0xff);  // Add a bitwise op to keep int32 paths interesting.
  }
  return sum;
}

%PrepareFunctionForOptimization(sumMul3Limit1000);
let s1 = sumMul3Limit1000();
// Compute expected: i = 2, 6, 18, 54, 162, 486; next 1458 exceeds 1000.
// (2&0xff)=2, 6, 18, 54, 162, 230 (486&0xff=230). Sum = 2+6+18+54+162+230 = 472.
assertEquals(s1, 472, "sum3 before opt");
%OptimizeFunctionOnNextCall(sumMul3Limit1000);
let s2 = sumMul3Limit1000();
assertEquals(s2, 472, "sum3 after opt");

// Extra coverage: call optimized functions a few times to ensure stability.
for (let k = 0; k < 3; k++) {
  f();
  assertEquals(sumMul4Limit100(), 85, "sum re-run opt " + k);
  assertEquals(sumMul3Limit1000(), 472, "sum3 re-run opt " + k);
}

print("OK");
