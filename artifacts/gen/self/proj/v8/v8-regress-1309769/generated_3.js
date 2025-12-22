// Copyright 2022 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test targets a bug in SimplifiedLowering for BigInt.asUintN with 0 bits.
// The patch ensures that when lowering asUintN(0, x) to a constant 0n, a
// suitable type override (UnsignedBigInt63) is inserted so the verifier and
// later stages see a precise BigInt type. Without the fix, optimized code paths
// using the 0n result could mis-handle types and potentially crash.
//
// We verify that:
// 1) Using BigInt.asUintN(0, ...) as an input to further BigInt ops works.
// 2) Both interpreted and optimized executions produce correct results.
// 3) Edge cases around 64-bit truncation behave as expected.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// Function mirroring the PoC structure: a zero-bit asUintN feeding into
// a 64-bit asUintN after an addition.
function foo(a, b, c) {
  let x = BigInt.asUintN(0, a + b);  // Always 0n; the bug fix adjusts its type.
  return BigInt.asUintN(64, x + c);
}

// Additional coverage: mix zero-bit asUintN into a 64-bit asIntN path to make
// sure the typed lowering interacts well with signed truncation too.
function bar(a, b, c) {
  let x = BigInt.asUintN(0, a + b);  // Always 0n
  return BigInt.asIntN(64, x + c);
}

%PrepareFunctionForOptimization(foo);
%PrepareFunctionForOptimization(bar);

const TWO64 = 1n << 64n;

// Pre-optimization checks for foo (Unsigned 64-bit wraparound)
assertEquals(foo(9n, 2n, 1n), 1n);
assertEquals(foo(0n, 0n, -1n), TWO64 - 1n);
assertEquals(foo(5n, -5n, 0n), 0n);
assertEquals(foo(1n, -1n, TWO64), 0n);
assertEquals(foo(2n, -2n, TWO64 + 5n), 5n);
assertEquals(foo(3n, -3n, -(TWO64 + 2n)), TWO64 - 2n);

// Pre-optimization checks for bar (Signed 64-bit wraparound)
assertEquals(bar(1n, 2n, -1n), -1n);
assertEquals(bar(0n, 0n, TWO64 - 1n), -1n);  // 2^64-1 sign-truncated to 64-bit is -1
assertEquals(bar(0n, 0n, TWO64), 0n);
assertEquals(bar(0n, 0n, (1n << 63n)), -(1n << 63n));  // -2^63
assertEquals(bar(0n, 0n, (1n << 63n) - 1n), (1n << 63n) - 1n);

%OptimizeFunctionOnNextCall(foo);
%OptimizeFunctionOnNextCall(bar);

// Post-optimization checks for foo
assertEquals(foo(9n, 2n, 1n), 1n);
assertEquals(foo(0n, 0n, -1n), TWO64 - 1n);
assertEquals(foo(5n, -5n, 0n), 0n);
assertEquals(foo(1n, -1n, TWO64), 0n);
assertEquals(foo(2n, -2n, TWO64 + 5n), 5n);
assertEquals(foo(3n, -3n, -(TWO64 + 2n)), TWO64 - 2n);

// Post-optimization checks for bar
assertEquals(bar(1n, 2n, -1n), -1n);
assertEquals(bar(0n, 0n, TWO64 - 1n), -1n);
assertEquals(bar(0n, 0n, TWO64), 0n);
assertEquals(bar(0n, 0n, (1n << 63n)), -(1n << 63n));
assertEquals(bar(0n, 0n, (1n << 63n) - 1n), (1n << 63n) - 1n);

print("OK");
