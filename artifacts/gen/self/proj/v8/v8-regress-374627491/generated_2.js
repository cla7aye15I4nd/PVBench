// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test targets a bug in the bytecode generator for switch statements
// where the hole check elision scope around case label comparisons was
// incorrect when a jump table was used. Specifically, accessing `this` in a
// derived class constructor before `super()` must throw a ReferenceError.
// The patch ensures that label comparisons that are conditionally executed
// (first non-default comparison after jump-table dispatch) open their own
// hole-check elision scope, so `this` (and other TDZ-checked bindings) are
// properly checked.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, expectedErrorCtor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (expectedErrorCtor && !(e instanceof expectedErrorCtor)) {
      throw new Error((message || "Wrong exception type") + ": expected " + (expectedErrorCtor && expectedErrorCtor.name) + ", got " + e);
    }
  }
  if (!threw) {
    throw new Error((message || "Expected exception was not raised"));
  }
}

function assertDoesNotThrow(fn, message) {
  try {
    fn();
  } catch (e) {
    throw new Error((message || "Unexpected exception") + ": " + e);
  }
}

// Base class for derived constructors.
class B {}

// Test 1: Jump-table path finds a match among dense numeric cases.
// The body of the selected case uses `this` before super, which must throw.
class C extends B {
  constructor() {
    let x = 0;
    switch (0) {
      case 0:
      case 1:
      case 2:
      case 3:
      case 4:
      case 5:
      case 6:
      case 7:
      case 8:
      case 9:
        // Using `this` before super must throw ReferenceError in derived ctor.
        x += this;
        break;
      // A non-constant label that would access `this` if evaluated.
      case this:
    }
  }
}
assertThrows(() => { new C(); }, ReferenceError, "Accessing this in matched case body should throw");

// Test 2: Jump-table path does not find a match, so it falls back to
// comparing non-default labels. The first such comparison is conditionally
// executed and must have its own hole check elision scope. Evaluating
// `case this:` must throw before any body executes. Place a super() after
// the switch to ensure that if the label evaluation does not throw, the
// constructor completes (thus making the test fail as intended).
class D extends B {
  constructor() {
    let x = 0;
    switch (42) {
      case 0:
      case 1:
      case 2:
      case 3:
      case 4:
      case 5:
      case 6:
      case 7:
      case 8:
      case 9:
        x += 1;  // Does not touch `this`.
        break;
      case this:  // Evaluating this label must throw (before super).
        x += 2;
        break;
      default:
        x += 3;
    }
    // Legal to call super() here since we haven't touched `this`.
    super();
  }
}
assertThrows(() => { new D(); }, ReferenceError, "Evaluating first non-default label after jump-table must throw on this");

// Test 3: Ensure that when a jump-table match occurs, non-constant labels
// (like `case this:`) are NOT evaluated at all. We avoid touching `this`
// before super() so the constructor can complete successfully.
class E extends B {
  constructor() {
    let marker = 0;
    switch (0) {
      case 0:
      case 1:
      case 2:
      case 3:
      case 4:
      case 5:
      case 6:
      case 7:
      case 8:
      case 9:
        marker = 1;  // Match via jump-table.
        break;
      case this: // Should not be evaluated when 0 matches above.
        marker = 2;
        break;
    }
    // It's legal to call super after code that doesn't use `this`.
    super();
    assertEquals(marker, 1, "Non-constant label must not be evaluated when jump-table finds a match");
  }
}
assertDoesNotThrow(() => { new E(); }, "Jump-table match should not evaluate case label 'this'");

print("OK");