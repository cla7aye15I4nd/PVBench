// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax --turboshaft-assert-types

// This test ensures that the AssertTypesReducer in the Turboshaft pipeline
// does not attempt to assert the type of LoadRootRegister operations.
// The patch adds a special-case to skip asserting for LoadRootRegister,
// which previously could cause crashes when running with
// --turboshaft-assert-types. The PoC uses an asm.js module, which exercises
// compilation paths that materialize the root register in Turboshaft.

(function(){
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Test case 1: Original PoC scenario wrapped with checks and optimization.
  // Verifies that optimizing the function that creates and calls an asm.js
  // module does not crash and behaves consistently.
  function f() {
    function asmModule() {
      'use asm';
      function x(v) {
        v = v | 0;
      }
      return x;
    }
    const asm = asmModule();
    return asm();
  }

  %PrepareFunctionForOptimization(f);
  let r = f();
  assertEquals(r, undefined, "f() before optimization");
  %OptimizeFunctionOnNextCall(f);
  r = f();
  assertEquals(r, undefined, "f() after optimization");

  // Run a few more times to ensure stability in optimized code paths.
  for (let i = 0; i < 3; i++) {
    r = f();
    assertEquals(r, undefined, "f() repeated run " + i);
  }

  // Test case 2: Heavier use inside a loop to potentially expose additional
  // uses of LoadRootRegister during compilation with --turboshaft-assert-types.
  function g(n) {
    function asmModule() {
      'use asm';
      function x(v) {
        v = v | 0;
      }
      return x;
    }
    const asm = asmModule();
    let last;
    for (let i = 0; i < n; i++) {
      last = asm(i);
    }
    return last;
  }

  %PrepareFunctionForOptimization(g);
  r = g(5);
  assertEquals(r, undefined, "g(5) before optimization");
  %OptimizeFunctionOnNextCall(g);
  r = g(10);
  assertEquals(r, undefined, "g(10) after optimization");

  // More runs to ensure no latent crashes in optimized code.
  for (let i = 0; i < 3; i++) {
    r = g(100 + i);
    assertEquals(r, undefined, "g() repeated run " + i);
  }

  // Test case 3: Create multiple asm modules in one optimized function and
  // call them in sequence. This stresses materialization across multiple calls.
  function h() {
    function asmModule() {
      'use asm';
      function x(v) {
        v = v | 0;
      }
      return x;
    }
    const a1 = asmModule();
    const a2 = asmModule();
    const a3 = asmModule();
    a1(1);
    a2(2);
    return a3(3);
  }

  %PrepareFunctionForOptimization(h);
  r = h();
  assertEquals(r, undefined, "h() before optimization");
  %OptimizeFunctionOnNextCall(h);
  r = h();
  assertEquals(r, undefined, "h() after optimization");

  // If we reached here without throwing, the reducer correctly skipped
  // asserting on LoadRootRegister, and the program remains stable.
  print("OK");
})();