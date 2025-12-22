// Copyright 2022 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test targets a bug in SimplifiedLowering for BigInt.as{Uint,Int}N(0, ...)
// where the lowering for the 0-bit case previously replaced the node with a
// generic ZeroConstant without a BigInt-specific type. The fix ensures the
// replacement constant is annotated with a BigInt type to satisfy the verifier
// and to keep downstream operations correctly typed.
//
// We verify:
// 1) BigInt.asUintN(0, x) and BigInt.asIntN(0, x) always produce 0n in both
//    unoptimized and optimized code paths.
// 2) Using the result in further BigInt arithmetic and BigInt.as{Uint,Int}N(64,
//    ...) works and returns correct results (no crash, no type confusion).
// 3) Edge cases with negative and very large values work correctly.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + String(expected) + ", got " + String(actual));
  }
}

function assertBigInt(x, message) {
  if (typeof x !== 'bigint') {
    throw new Error((message || "Expected a BigInt") + ", got typeof " + (typeof x) + ": " + x);
  }
}

// Helper to compute 2^64 as a BigInt
const TWO64 = 1n << 64n;
const TWO63 = 1n << 63n;

// Function from the PoC: uses asUintN(0, ...) result inside BigInt arithmetic.
function foo(a, b, c) {
  let x = BigInt.asUintN(0, a + b);  // Must be 0n (and typed as BigInt) after lowering.
  return BigInt.asUintN(64, x + c);
}

%PrepareFunctionForOptimization(foo);
// Unoptimized checks
assertEquals(foo(9n, 2n, 1n), 1n, 'foo basic');
assertEquals(foo(-9n, 4n, 2n), 2n, 'foo negative a+b');
assertEquals(foo(123n, 456n, TWO64 + 5n), 5n, 'foo wrap around positive');
assertEquals(foo(0n, 0n, -1n), TWO64 - 1n, 'foo wrap around negative');

%OptimizeFunctionOnNextCall(foo);
// Optimized checks
assertEquals(foo(9n, 2n, 1n), 1n, 'foo basic opt');
assertEquals(foo(-9n, 4n, 2n), 2n, 'foo negative a+b opt');
assertEquals(foo(123n, 456n, TWO64 + 5n), 5n, 'foo wrap around positive opt');
assertEquals(foo(0n, 0n, -1n), TWO64 - 1n, 'foo wrap around negative opt');

// Directly test that asUintN(0, x) always yields a BigInt 0n and can be used
// safely in subsequent BigInt arithmetic.
function asUint0(v) {
  return BigInt.asUintN(0, v);
}

%PrepareFunctionForOptimization(asUint0);
assertEquals(asUint0(0n), 0n, 'asUint0 zero');
assertEquals(asUint0(-12345678901234567890n), 0n, 'asUint0 negative');
assertEquals(asUint0(TWO64 * 12345n + 7n), 0n, 'asUint0 large positive');
%OptimizeFunctionOnNextCall(asUint0);
let r1 = asUint0(1n);
let r2 = asUint0(-1n);
let r3 = asUint0(TWO64 - 1n);
assertBigInt(r1, 'asUint0 type r1');
assertBigInt(r2, 'asUint0 type r2');
assertBigInt(r3, 'asUint0 type r3');
assertEquals(r1, 0n, 'asUint0 r1');
assertEquals(r2, 0n, 'asUint0 r2');
assertEquals(r3, 0n, 'asUint0 r3');
// Use in BigInt arithmetic to ensure no type confusion with Number 0
assertEquals(BigInt.asUintN(64, r1 + 5n), 5n, 'asUint0 used in add');
assertEquals(BigInt.asUintN(64, r2 + (TWO64 - 1n)), TWO64 - 1n, 'asUint0 used in add large');

// Symmetric tests for asIntN(0, ...), which should also yield 0n and be usable
// in BigInt arithmetic and asIntN(64, ...)
function bar(a, b, c) {
  let x = BigInt.asIntN(0, a + b);
  return BigInt.asIntN(64, x + c);
}

%PrepareFunctionForOptimization(bar);
assertEquals(bar(5n, -7n, -1n), -1n, 'bar negative');
assertEquals(bar(0n, 0n, TWO64 - 1n), -1n, 'bar wrap to -1');
assertEquals(bar(100n, 200n, TWO63), -TWO63, 'bar 2^63 to -2^63');
%OptimizeFunctionOnNextCall(bar);
assertEquals(bar(5n, -7n, -1n), -1n, 'bar negative opt');
assertEquals(bar(0n, 0n, TWO64 - 1n), -1n, 'bar wrap to -1 opt');
assertEquals(bar(100n, 200n, TWO63), -TWO63, 'bar 2^63 to -2^63 opt');

function asInt0(v) {
  return BigInt.asIntN(0, v);
}

%PrepareFunctionForOptimization(asInt0);
assertEquals(asInt0(0n), 0n, 'asInt0 zero');
assertEquals(asInt0(-99999999999999999999n), 0n, 'asInt0 negative');
assertEquals(asInt0(TWO64 * 42n + 123n), 0n, 'asInt0 large positive');
%OptimizeFunctionOnNextCall(asInt0);
let s1 = asInt0(1n);
let s2 = asInt0(-1n);
let s3 = asInt0(TWO64 - 1n);
assertBigInt(s1, 'asInt0 type s1');
assertBigInt(s2, 'asInt0 type s2');
assertBigInt(s3, 'asInt0 type s3');
assertEquals(s1, 0n, 'asInt0 s1');
assertEquals(s2, 0n, 'asInt0 s2');
assertEquals(s3, 0n, 'asInt0 s3');
// Use in BigInt arithmetic
assertEquals(BigInt.asIntN(64, s1 + (-5n)), -5n, 'asInt0 used in add');
assertEquals(BigInt.asIntN(64, s2 + (TWO63)), -TWO63, 'asInt0 used in add large');

print("OK");