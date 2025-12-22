// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: -allow-natives-syntax --turboshaft --turboshaft-assert-types

// This test targets a bug in Turboshaft type inference where TupleOp types
// were not handled specially in TypeInferenceReducer::GetType. The fix adds
// a dedicated path to construct a TupleType for TupleOp, instead of falling
// back to Typer::TypeForRepresentation.
//
// The original PoC uses a for-loop with multiplicative update which, under
// Turboshaft, leads to creation/propagation of multi-output (tuple) ops in
// the compiler pipeline. With --turboshaft-assert-types enabled, the buggy
// code path would hit an assertion. This test ensures such patterns do not
// crash and also adds a try/catch+call pattern that is known to generate
// multi-output operations (like CallAndCatchException) in the compiler.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Test 1: Original PoC pattern. Should not crash under --turboshaft-assert-types
  function f() {
    for (let i = 1; i < 100; i *= 4) {
      // Empty body. The loop structure is what matters here.
    }
    // Implicit undefined return.
  }

  %PrepareFunctionForOptimization(f);
  let r1 = f();
  assertEquals(r1, undefined, "f() pre-opt should return undefined");
  %OptimizeFunctionOnNextCall(f);
  r1 = f();
  assertEquals(r1, undefined, "f() post-opt should return undefined");

  // Test 2: Same loop pattern, but return the loop variable to assert a value.
  function g() {
    let i = 1;
    for (; i < 100; i *= 4) {
    }
    return i; // Expect 256 (1 -> 4 -> 16 -> 64 -> 256 and exit)
  }

  %PrepareFunctionForOptimization(g);
  let r2 = g();
  assertEquals(r2, 256, "g() pre-opt expected final value 256");
  %OptimizeFunctionOnNextCall(g);
  r2 = g();
  assertEquals(r2, 256, "g() post-opt expected final value 256");

  // Helper function for try/catch path below.
  function maybeThrow(x) {
    if (x < 0) throw new Error("bad");
    return x + 1;
  }

  // Test 3: Try/catch around a call. This pattern typically lowers to a
  // multi-output operation in the compiler (e.g., CallAndCatchException),
  // exercising TupleOp typing in the type inference reducer.
  function h(fn, x) {
    try {
      return fn(x);
    } catch (e) {
      return -1;
    }
  }

  %PrepareFunctionForOptimization(maybeThrow);
  %PrepareFunctionForOptimization(h);

  // Warm-up along both the success and exception paths.
  assertEquals(h(maybeThrow, 1), 2, "h success path pre-opt");
  assertEquals(h(maybeThrow, -1), -1, "h exception path pre-opt");

  %OptimizeFunctionOnNextCall(maybeThrow);
  maybeThrow(0);

  %OptimizeFunctionOnNextCall(h);
  assertEquals(h(maybeThrow, 2), 3, "h success path post-opt");
  assertEquals(h(maybeThrow, -2), -1, "h exception path post-opt");

  // If we reach here without assertions or crashes, the TupleOp typing fix
  // is working as expected under Turboshaft with assert-types enabled.
  print("OK");
})();
