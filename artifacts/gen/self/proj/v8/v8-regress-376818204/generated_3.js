// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test targets a bug in super property access for String wrapper objects
// (classes extending String) where the compiler incorrectly wired the input
// to StringWrapperLength and missed a proper TypeGuard for StringWrapper maps.
// The patch adds a TypeGuard on the lookup_start_object for super accesses and
// ensures StringWrapperLength receives the lookup_start_object instead of the
// receiver. We verify that reading super.length:
//  - Does not crash in either unoptimized or optimized code paths.
//  - Produces the semantically correct value when accessed via super
//    (String.prototype.length === 0), independently of the instance's string
//    content.
//  - Remains correct after map transitions on the instance.

(function(){
  function assertEquals(expected, actual, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Baseline: direct String wrapper length uses the instance's [[StringData]].
  // This is unrelated to super, but serves as a sanity check for the environment.
  assertEquals(3, new String("abc").length, "Sanity: String wrapper length of 'abc' is 3");

  // 1) Minimal reproduction from the PoC: super.length in a constructor with
  //    default empty string value. Should be 0 and not crash when optimized.
  class C1 extends String {
    constructor() {
      super();
      const len = super.length;
      // Record values to allow observation by the test runner.
      this._len = len;
      this._type = typeof len;
    }
  }

  // Unoptimized call.
  let c1 = new C1();
  assertEquals(0, c1._len, "C1 unoptimized: super.length should be 0");
  assertEquals("number", c1._type, "C1 unoptimized: typeof super.length should be number");

  // Optimize constructor and call again.
  %PrepareFunctionForOptimization(C1);
  new C1();  // warm-up
  %OptimizeFunctionOnNextCall(C1);
  c1 = new C1();
  assertEquals(0, c1._len, "C1 optimized: super.length should be 0");
  assertEquals("number", c1._type, "C1 optimized: typeof super.length should be number");

  // 2) Parameterized subclass: verify super.length stays 0 regardless of the
  //    instance's string content, before and after optimization.
  class C2 extends String {
    constructor(s) {
      super(s);
      this._via_super = super.length;
      this._via_this = this.length;  // normal access still reflects instance length
    }
  }

  // Unoptimized calls.
  let c2a = new C2("");
  assertEquals(0, c2a._via_super, "C2 unoptimized: super.length is 0 for empty string");
  assertEquals(0, c2a._via_this,  "C2 unoptimized: this.length matches instance length 0");

  let c2b = new C2("abc");
  assertEquals(0, c2b._via_super, "C2 unoptimized: super.length is 0 for 'abc'");
  assertEquals(3, c2b._via_this,  "C2 unoptimized: this.length matches instance length 3");

  let c2c = new C2("🙂"); // surrogate pair, length is 2 code units
  assertEquals(0, c2c._via_super, "C2 unoptimized: super.length is 0 for emoji");
  assertEquals(2, c2c._via_this,  "C2 unoptimized: this.length matches instance length 2");

  // Optimize constructor and validate again.
  %PrepareFunctionForOptimization(C2);
  new C2("");
  new C2("z");
  %OptimizeFunctionOnNextCall(C2);
  c2b = new C2("test");
  assertEquals(0, c2b._via_super, "C2 optimized: super.length is 0 for 'test'");
  assertEquals(4, c2b._via_this,  "C2 optimized: this.length matches instance length 4");

  // 3) Instance method reading super.length. Exercises the super access path
  //    outside of constructors as well.
  class C3 extends String {
    constructor(s) { super(s); }
    getSuperLen() { return super.length; }
    getThisLen() { return this.length; }
  }

  // Unoptimized checks.
  const c3a = new C3("hello");
  const c3b = new C3("");
  const c3c = new C3("🙂");
  assertEquals(0, c3a.getSuperLen(), "C3 unoptimized: super.length is always 0");
  assertEquals(0, c3b.getSuperLen(), "C3 unoptimized: super.length is always 0");
  assertEquals(0, c3c.getSuperLen(), "C3 unoptimized: super.length is always 0");
  // Compare with normal access to ensure we aren't masking bugs elsewhere.
  assertEquals(5, c3a.getThisLen(), "C3 unoptimized: this.length reflects instance length 5");
  assertEquals(0, c3b.getThisLen(), "C3 unoptimized: this.length reflects instance length 0");
  assertEquals(2, c3c.getThisLen(), "C3 unoptimized: this.length reflects instance length 2");

  // Optimize the methods and verify stability and correctness.
  %PrepareFunctionForOptimization(C3.prototype.getSuperLen);
  %PrepareFunctionForOptimization(C3.prototype.getThisLen);
  c3a.getSuperLen();
  c3a.getThisLen();
  c3b.getSuperLen();
  c3b.getThisLen();
  %OptimizeFunctionOnNextCall(C3.prototype.getSuperLen);
  %OptimizeFunctionOnNextCall(C3.prototype.getThisLen);
  assertEquals(0, c3a.getSuperLen(), "C3 optimized: super.length remains 0");
  assertEquals(5, c3a.getThisLen(),  "C3 optimized: this.length remains 5");
  assertEquals(0, c3b.getSuperLen(), "C3 optimized: super.length remains 0");
  assertEquals(0, c3b.getThisLen(),  "C3 optimized: this.length remains 0");
  assertEquals(0, c3c.getSuperLen(), "C3 optimized: super.length remains 0 for emoji");
  assertEquals(2, c3c.getThisLen(),  "C3 optimized: this.length remains 2 for emoji");

  // 4) Map transition scenario: add own properties to the wrapper after
  //    optimization. The TypeGuard for StringWrapper maps should remain valid
  //    and the access should still be correct and not crash.
  c3a.extra = 42;  // cause a map transition on the wrapper
  assertEquals(0, c3a.getSuperLen(), "C3 optimized after map transition: super.length remains 0");

  // 5) Cross-instance sanity after optimization.
  const c3d = new C3("qwerty");
  assertEquals(0, c3d.getSuperLen(), "C3 optimized: super.length is 0 for new instance");
  assertEquals(6, c3d.getThisLen(),  "C3 optimized: this.length reflects instance length 6");

  // If we reached here without throwing, the fix works and no crash occurred.
  print("OK");
})();
