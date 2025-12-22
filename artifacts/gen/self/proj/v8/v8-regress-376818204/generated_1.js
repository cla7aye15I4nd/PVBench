// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --allow-natives-syntax

// This test verifies correct handling of super property access for
// String wrapper objects, specifically for `super.length`.
//
// The patch adds two key changes:
// 1) For super property accesses starting from String wrapper maps, insert a
//    TypeGuard(StringWrapper) so the compiler can safely use
//    StringWrapperLength.
// 2) When using StringWrapperLength for super access, use the lookup_start_object
//    (i.e., the object where property lookup starts, in this case String.prototype)
//    instead of the receiver. Previously using receiver could lead to wrong
//    semantics or crashes.
//
// We assert that super.length reads the length from String.prototype (which is 0)
// regardless of the receiver's wrapped string value, and that this holds both in
// unoptimized and optimized code paths.

(function() {
  function assertEquals(expected, actual, msg) {
    if (expected !== actual) {
      throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  // Sanity: String.prototype behaves like an empty string wrapper.
  assertEquals(0, String.prototype.length, "String.prototype.length should be 0");

  // Baseline from the original PoC: reading super.length in a String subclass
  // constructor should not crash and should equal 0.
  class C1 extends String {
    constructor() {
      super();
      assertEquals(0, super.length, "super.length in C1 should be 0");
    }
  }

  %PrepareFunctionForOptimization(C1);
  new C1();
  %OptimizeFunctionOnNextCall(C1);
  new C1();

  // Verify semantics when the receiver has a non-zero length. The value of
  // super.length must still come from String.prototype (0), while this.length
  // reflects the actual wrapped string's length.
  class C2 extends String {
    constructor(s) {
      super(s);
      assertEquals(0, super.length, "super.length in C2 should be 0 regardless of input");
      assertEquals((s === undefined ? 0 : ('' + s).length), this.length,
                   "this.length should match the wrapped string length");
    }
  }

  %PrepareFunctionForOptimization(C2);
  new C2("abc");  // warmup with non-empty
  new C2("");     // warmup with empty
  %OptimizeFunctionOnNextCall(C2);
  new C2("abcdef");

  // Exercise super.length in an instance method (not only constructor).
  class C3 extends String {
    constructor(s) { super(s); }
    getSuperLen() { return super.length; }
    getThisLen() { return this.length; }
  }

  const o1 = new C3("hello");
  const o2 = new C3("world!");

  // Unoptimized checks.
  assertEquals(0, o1.getSuperLen(), "super.length via method should be 0 (o1)");
  assertEquals(0, o2.getSuperLen(), "super.length via method should be 0 (o2)");
  assertEquals(5, o1.getThisLen(), "this.length via method should reflect string length (o1)");
  assertEquals(6, o2.getThisLen(), "this.length via method should reflect string length (o2)");

  // Optimize the methods and re-check.
  %PrepareFunctionForOptimization(C3.prototype.getSuperLen);
  %PrepareFunctionForOptimization(C3.prototype.getThisLen);
  o1.getSuperLen();
  o1.getThisLen();
  o2.getSuperLen();
  o2.getThisLen();
  %OptimizeFunctionOnNextCall(C3.prototype.getSuperLen);
  %OptimizeFunctionOnNextCall(C3.prototype.getThisLen);
  assertEquals(0, o1.getSuperLen(), "optimized super.length via method should be 0 (o1)");
  assertEquals(0, o2.getSuperLen(), "optimized super.length via method should be 0 (o2)");
  assertEquals(5, o1.getThisLen(), "optimized this.length via method should reflect length (o1)");
  assertEquals(6, o2.getThisLen(), "optimized this.length via method should reflect length (o2)");

  // Additional coverage: ensure that calling the optimized constructor and
  // methods repeatedly doesn't crash and preserves semantics.
  for (let i = 0; i < 5; i++) {
    new C2("repeat-" + i);
    assertEquals(0, o1.getSuperLen());
    assertEquals(0, o2.getSuperLen());
  }

  print("OK");
})();
