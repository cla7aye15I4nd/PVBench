// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: -allow-natives-syntax --turboshaft --turboshaft-assert-types

// This test targets a bug in Turboshaft type inference where TupleOp nodes
// were not assigned a proper type. The fix adds explicit handling for
// TupleOp by constructing a TupleType from the types of its inputs.
//
// We cannot directly observe internal Tuple types from JavaScript, but the
// original PoC triggered an assertion/crash in the typer under
// --turboshaft-assert-types. Therefore, this test focuses on ensuring that
// a variety of loop forms (which exercise the original failure path) do not
// crash during optimization and produce correct results.

(function(){
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Original PoC: empty loop with multiplicative update in the for-loop header.
  function f() {
    for (let i = 1; i < 100; i *= 4) {
    }
  }

  // Ensure the original PoC pattern doesn't crash pre/post optimization.
  %PrepareFunctionForOptimization(f);
  f();
  %OptimizeFunctionOnNextCall(f);
  f();

  // Strengthened tests to validate semantics remain correct for similar
  // patterns that previously exercised the bad typing path.

  // Returns the final value of i after the loop finishes.
  function g(limit, mul) {
    let i = 1;
    for (; i < limit; i *= mul) {}
    return i;
  }

  %PrepareFunctionForOptimization(g);
  assertEquals(g(100, 4), 256, "g pre-opt 100,4");
  assertEquals(g(1, 4), 1, "g pre-opt 1,4");
  assertEquals(g(100, 2), 128, "g pre-opt 100,2");
  %OptimizeFunctionOnNextCall(g);
  assertEquals(g(100, 4), 256, "g post-opt 100,4");
  assertEquals(g(1, 4), 1, "g post-opt 1,4");
  assertEquals(g(100, 2), 128, "g post-opt 100,2");

  // Variant with the multiplicative update in a while-loop.
  function h(limit) {
    let i = 1;
    while (i < limit) {
      i *= 4;
    }
    return i;
  }

  %PrepareFunctionForOptimization(h);
  assertEquals(h(256), 256, "h pre-opt 256");
  assertEquals(h(1), 1, "h pre-opt 1");
  %OptimizeFunctionOnNextCall(h);
  assertEquals(h(256), 256, "h post-opt 256");
  assertEquals(h(1), 1, "h post-opt 1");

  // Variant with a double-typed induction variable to stress different
  // representations flowing through the loop and typer.
  function g2(limit) {
    let i = 1.5;
    let count = 0;
    for (; i < limit; i *= 4) {
      count++;
    }
    return count;
  }

  %PrepareFunctionForOptimization(g2);
  assertEquals(g2(100), 4, "g2 pre-opt 100");  // 1.5, 6, 24, 96
  %OptimizeFunctionOnNextCall(g2);
  assertEquals(g2(100), 4, "g2 post-opt 100");

  // The following pattern mixes declaration in the for-header and ensures the
  // loop variable escapes (returned), which exercises phi/loop-carried values.
  function k(limit) {
    for (let i = 1; ; i *= 4) {
      if (!(i < limit)) return i;
    }
  }

  %PrepareFunctionForOptimization(k);
  assertEquals(k(100), 256, "k pre-opt 100");
  %OptimizeFunctionOnNextCall(k);
  assertEquals(k(100), 256, "k post-opt 100");

  // If all the above executed without throwing or crashing, the fix works.
  print("OK");
})();
