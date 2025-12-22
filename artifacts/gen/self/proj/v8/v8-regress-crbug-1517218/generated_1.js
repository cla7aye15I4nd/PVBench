// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax --turboshaft-assert-types

// This test verifies the fix in assert-types-reducer where LoadRootRegister
// should not get materialized/asserted. Prior to the fix, running with
// --turboshaft-assert-types on certain graphs (e.g., from asm.js code paths)
// could try to assert the type of LoadRootRegisterOp and crash. The fix skips
// asserting LoadRootRegister, so the following scenarios should execute without
// crashing in both unoptimized and optimized tiers.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// -------------------------------
// Scenario 1: Original PoC pattern
// -------------------------------
function f() {
  function asmModule() {
    'use asm';
    function x(v) {
      v = v | 0;
      // Intentionally no return (mirrors the original PoC). Historically this
      // exercised the problematic path when assertions were inserted.
    }
    return x;
  }
  const asm = asmModule();
  asm();
}

%PrepareFunctionForOptimization(f);
f();
%OptimizeFunctionOnNextCall(f);
// Should not crash when optimized with --turboshaft-assert-types
f();

// -----------------------------------------------
// Scenario 2: Direct asm.js-style function usage
// -----------------------------------------------
// Build a simple asm module that returns an int32 function so that we can make
// functional assertions as well.
function asmModule1() {
  'use asm';
  function x(v) {
    v = v | 0;
    return v | 0;
  }
  return x;
}
const asm1 = asmModule1();

// Wrap the asm function in a normal JS function so it goes through normal TF
// optimization pipelines (where the assert-types reducer runs).
function g(v) {
  // The wrapper also does a bitwise OR to keep the int32 nature in JS visible
  // and make the check robust.
  return asm1(v) | 0;
}

%PrepareFunctionForOptimization(g);
// Warmup with a typical small int value.
assertEquals(g(0), (0 | 0));
assertEquals(g(1), (1 | 0));
%OptimizeFunctionOnNextCall(g);
// Run optimized and test a variety of values, including edge cases.
const values = [
  0,
  1,
  -1,
  0x7fffffff,
  -0x80000000,
  3.14,
  1e20,
  NaN,
  undefined,
  null
];
for (let i = 0; i < values.length; i++) {
  const v = values[i];
  const expected = v | 0;
  const actual = g(v);
  assertEquals(actual, expected, "asm wrapper result mismatch at index " + i);
}

// ----------------------------------------------
// Scenario 3: Multiple instantiations of asm code
// ----------------------------------------------
function asmModule2() {
  'use asm';
  function y(v) {
    v = v | 0;
    return (v + 1) | 0;
  }
  return y;
}

const asm2a = asmModule2();
const asm2b = asmModule2();

function h(fn, v) {
  // Another wrapper to ensure various graphs are built and optimized; the
  // optimizer should not try to assert LoadRootRegister.
  return fn(v) | 0;
}

%PrepareFunctionForOptimization(h);
assertEquals(h(asm2a, 0), 1);
assertEquals(h(asm2b, -1), 0);
%OptimizeFunctionOnNextCall(h);
assertEquals(h(asm2a, 41), 42);
assertEquals(h(asm2b, 2147483647), (-2147483648 | 0)); // int32 overflow behavior

print("OK");
