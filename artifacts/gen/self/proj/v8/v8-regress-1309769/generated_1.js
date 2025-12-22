// Copyright 2022 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test targets a bug in Simplified Lowering for BigInt.asUintN/asIntN
// when the bit width is 0. Previously, the compiler replaced the operation
// with a generic ZeroConstant without a BigInt type override, which could
// lead to incorrect typing in the compiler pipeline (e.g., using a Number 0
// where a BigInt 0n was expected) and cause miscompilations or crashes when
// the value flowed into BigInt operations. The fix adds a type override so
// the zero replacement is explicitly treated as a BigInt value for verifier
// and subsequent lowering.
//
// This test verifies that:
// 1) BigInt.asUintN(0, x) consistently behaves as 0n in both interpreted and
//    optimized code paths.
// 2) The 0-bit result can flow into further BigInt arithmetic (e.g., x + c)
//    without crashing and with correct semantics.
// 3) Interactions with BigInt.asUintN(64, ...) (identity modulo 2^64) are
//    preserved when fed values derived from a 0-bit asUintN/asIntN.

// d8 compatibility helpers when not running under d8.
if (typeof print !== 'function') {
  // eslint-disable-next-line no-global-assign
  var print = function(msg) { console.log(msg); };
}

function d8PrepareFunctionForOptimization(fn) {
  try { eval('%PrepareFunctionForOptimization(fn)'); } catch (_) {}
}
function d8OptimizeFunctionOnNextCall(fn) {
  try { eval('%OptimizeFunctionOnNextCall(fn)'); } catch (_) {}
}

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + String(expected) + ", got " + String(actual));
  }
}

function assertBigInt(v, message) {
  if (typeof v !== 'bigint') {
    throw new Error((message || "Type assertion failed") + ": expected bigint, got " + (typeof v));
  }
}

// Original PoC shape: a 0-bit asUintN result flows into BigInt addition, and
// then is wrapped in asUintN(64, ...). This should return c modulo 2^64.
function foo(a, b, c) {
  let x = BigInt.asUintN(0, a + b);
  return BigInt.asUintN(64, x + c);
}

// Variant using asIntN(0, ...), which should also produce 0n and be safe to
// flow into BigInt arithmetic.
function fooInt(a, b, c) {
  let x = BigInt.asIntN(0, a + b);
  return BigInt.asUintN(64, x + c);
}

// Direct 0-bit cases should always return 0n.
function asUintZero(v) { return BigInt.asUintN(0, v); }
function asIntZero(v) { return BigInt.asIntN(0, v); }

// Warmup, optimize, and validate helpers.
function optimizeAndCheck(fn, cases) {
  d8PrepareFunctionForOptimization(fn);
  // Warm up with provided cases.
  for (let i = 0; i < cases.length; i++) fn.apply(null, cases[i].args);
  // Check pre-optimization results.
  for (let i = 0; i < cases.length; i++) {
    const res = fn.apply(null, cases[i].args);
    assertEquals(res, cases[i].expect, cases[i].msg + " (pre-opt)");
  }
  d8OptimizeFunctionOnNextCall(fn);
  for (let i = 0; i < cases.length; i++) {
    const res = fn.apply(null, cases[i].args);
    assertEquals(res, cases[i].expect, cases[i].msg + " (opt)");
  }
}

// 2^64 constant for modulo expectations.
const TWO_64 = 1n << 64n;

// Test suite for foo (asUintN(0, ...) -> +c -> asUintN(64,...)).
optimizeAndCheck(foo, [
  { args: [9n, 2n, 1n], expect: 1n, msg: 'foo basic: 0n + 1n => 1n' },
  { args: [5n, -5n, -1n], expect: TWO_64 - 1n, msg: 'foo negative c: 0n + (-1n) => 2^64-1' },
  { args: [0n, 0n, TWO_64 + 123n], expect: 123n, msg: 'foo large c modulo 2^64' },
  { args: [123456789n, 987654321n, 0n], expect: 0n, msg: 'foo zero c: 0n + 0n => 0n' },
]);

// Test suite for fooInt (asIntN(0, ...) path mirrors asUintN(0, ...)).
optimizeAndCheck(fooInt, [
  { args: [1n, 2n, 7n], expect: 7n, msg: 'fooInt basic: 0n + 7n => 7n' },
  { args: [-10n, 3n, -2n], expect: TWO_64 - 2n, msg: 'fooInt negative c: 2^64-2' },
  { args: [0n, 0n, TWO_64 * 10n + 5n], expect: 5n, msg: 'fooInt large c modulo 2^64' },
]);

// Direct 0-bit conversions return 0n and have the correct type, both before
// and after optimization.

d8PrepareFunctionForOptimization(asUintZero);
assertEquals(asUintZero(123n), 0n, 'asUintN(0, 123n) => 0n (pre-opt)');
assertBigInt(asUintZero(123n), 'asUintN(0, 123n) type');
d8OptimizeFunctionOnNextCall(asUintZero);
assertEquals(asUintZero(-999n), 0n, 'asUintN(0, -999n) => 0n (opt)');
assertBigInt(asUintZero(-999n), 'asUintN(0, -999n) type (opt)');


d8PrepareFunctionForOptimization(asIntZero);
assertEquals(asIntZero(123n), 0n, 'asIntN(0, 123n) => 0n (pre-opt)');
assertBigInt(asIntZero(123n), 'asIntN(0, 123n) type');
d8OptimizeFunctionOnNextCall(asIntZero);
assertEquals(asIntZero(-999n), 0n, 'asIntN(0, -999n) => 0n (opt)');
assertBigInt(asIntZero(-999n), 'asIntN(0, -999n) type (opt)');

print('OK');
