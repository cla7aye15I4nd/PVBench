// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test verifies a fix in JSNativeContextSpecialization for super property
// access when the lookup start object is a String wrapper. The fix introduces a
// TypeGuard for StringWrapper maps and ensures that StringWrapperLength uses the
// lookup_start_object (e.g., String.prototype) as input. Previously this could
// crash or produce incorrect graph wiring during optimization.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // 1) Constructor super.length with default super() (empty string)
  //    Expected to read from String.prototype, which is a String wrapper for ''
  //    and thus length === 0. Should not crash before/after optimization.
  class C1 extends String {
    constructor() {
      super();
      const v = super.length;
      assertEquals(v, 0, "super.length in constructor (super())");
    }
  }

  %PrepareFunctionForOptimization(C1);
  new C1();  // warmup
  %OptimizeFunctionOnNextCall(C1);
  new C1();  // optimized call, should not crash and should be 0

  // 2) Constructor super.length with non-empty string argument to super().
  //    Still expected to read from String.prototype (lookup_start_object), so 0.
  class C1b extends String {
    constructor() {
      super("abc");
      const v = super.length;
      assertEquals(v, 0, "super.length in constructor (super('abc'))");
    }
  }

  %PrepareFunctionForOptimization(C1b);
  new C1b();  // warmup
  %OptimizeFunctionOnNextCall(C1b);
  new C1b();  // optimized call, should not crash and should be 0

  // 3) Instance method accessing super.length.
  //    The property access still starts from String.prototype, so the value is 0.
  class C2 extends String {
    constructor(s) { super(s); }
    m() { return super.length; }
  }

  // Interpreted path
  let o = new C2("xyz");
  assertEquals(o.m(), 0, "super.length in method (interpreted)");

  // Optimized path for method m
  %PrepareFunctionForOptimization(C2.prototype.m);
  o.m();  // warmup
  %OptimizeFunctionOnNextCall(C2.prototype.m);
  assertEquals(o.m(), 0, "super.length in method (optimized)");

  // 4) Sanity check: this.length reflects the wrapped string length,
  //    which differs from super.length (0). This ensures we are not
  //    accidentally reading from the receiver for super.length.
  class C3 extends String {
    constructor(s) {
      super(s);
      this._len_this = this.length;
      this._len_super = super.length;
    }
    get len_this() { return this._len_this; }
    get len_super() { return this._len_super; }
  }

  %PrepareFunctionForOptimization(C3);
  const c3_1 = new C3("hello");
  assertEquals(c3_1.len_this, 5, "this.length should reflect instance string length");
  assertEquals(c3_1.len_super, 0, "super.length should reflect String.prototype length");

  %OptimizeFunctionOnNextCall(C3);
  const c3_2 = new C3("world!");
  assertEquals(c3_2.len_this, 6, "this.length should reflect instance string length (optimized)");
  assertEquals(c3_2.len_super, 0, "super.length should reflect String.prototype length (optimized)");

  // If we reached here without throwing, the specialization handled StringWrapper
  // super property access correctly in both interpreted and optimized code.
  print("OK");
})();
