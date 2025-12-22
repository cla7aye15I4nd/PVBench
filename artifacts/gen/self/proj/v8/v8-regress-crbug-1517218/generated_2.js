// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax --turboshaft-assert-types

// This test targets a regression fixed by skipping type assertions for
// LoadRootRegister in the Turboshaft AssertTypesReducer. With
// --turboshaft-assert-types enabled, attempting to assert the type of
// LoadRootRegister used to cause a crash. The fix ensures such assertions are
// not emitted. The scenarios below exercise asm.js modules and wrappers (which
// are known to perform root register operations internally) through various
// calling patterns. The test passes if no crash occurs and basic semantics are
// preserved.

(function() {
  function assertEquals(actual, expected, msg) {
    if (actual !== expected) {
      throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Original PoC scenario: asm.js module inside a wrapper function, called once.
  function f() {
    function asmModule() {
      'use asm';
      function x(v) {
        v = v | 0;  // simple int coercion
        // no return -> undefined
      }
      return x;
    }
    const asm = asmModule();
    asm();
    // f returns undefined
  }

  // Call f a few times to ensure compilation paths don't crash with
  // turboshaft type assertions enabled.
  for (let i = 0; i < 50; i++) {
    const r = f();
    assertEquals(r, undefined, "f() should return undefined");
  }

  // Additional scenario 1: Direct asm.js function at top-level. Call repeatedly.
  function AsmModule1() {
    'use asm';
    function x(v) {
      v = v | 0;  // parameter coercion
      // no return -> undefined
    }
    return x;
  }
  const asm1 = AsmModule1();
  for (let i = 0; i < 200; i++) {
    const r1 = asm1(i);
    assertEquals(r1, undefined, "asm1(i) should return undefined");
  }

  // Additional scenario 2: asm.js function with arithmetic and return value.
  function AsmModule2() {
    'use asm';
    function y(v) {
      v = v | 0;
      v = (v + 1) | 0;
      return v | 0;
    }
    return y;
  }
  const y = AsmModule2();
  for (let i = 0; i < 200; i++) {
    const ry = y(41);
    assertEquals(ry | 0, 42, "y(41) should consistently return 42");
  }

  // Additional scenario 3: Wrapper around asm.js function to create a different
  // compilation context and potential inlining opportunities in callers.
  function wrapperCall(v) {
    const g = AsmModule2();
    return g(v) | 0;
  }
  for (let i = 0; i < 200; i++) {
    const rw = wrapperCall(i);
    assertEquals(rw | 0, (i + 1) | 0, "wrapperCall(i) should return i+1");
  }

  // Additional scenario 4: Mix multiple asm.js modules and cross-call them.
  function AsmModule3() {
    'use asm';
    function inc(v) {
      v = v | 0;
      return (v + 2) | 0;
    }
    return inc;
  }
  const inc1 = AsmModule3();
  const inc2 = AsmModule2();
  for (let i = 0; i < 200; i++) {
    const a = inc1(i);
    const b = inc2(i);
    assertEquals(a | 0, (i + 2) | 0, "AsmModule3 inc should return i+2");
    assertEquals(b | 0, (i + 1) | 0, "AsmModule2 inc should return i+1");
  }

  // If we got here without any assertion failures or crashes, the fix works.
  print("OK");
})();
