// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct handling of hole-check elision for switch-case
// comparisons when a jump table is used. In particular, accessing `this` in a
// derived class constructor before calling `super()` must throw a ReferenceError,
// whether the access happens in a case body or during evaluation of a case
// label expression (e.g., `case this:`). The patch ensures an elision scope is
// used for the first non-jump-table comparison and for subsequent comparisons.

function assertThrows(fn, errorCtor) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorCtor && !(e instanceof errorCtor)) {
      throw new Error("Wrong exception type: expected " + (errorCtor && errorCtor.name) + ", got " + e);
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

class B {}

// Test 1: The original PoC scenario.
// A jump table is used for consecutive numeric cases 0..9. The matched case
// (0) body reads `this` before super, which must throw ReferenceError.
class C extends B {
  constructor() {
    // Important: no super() yet — `this` is uninitialized.
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
        // Accessing `this` before super must throw.
        x += this;  // Should trigger ReferenceError.
        break;
      // Ensure there is at least one non-jump-table label that uses `this` to
      // exercise the generator's comparison path as well.
      case this:
        break;
    }
    // Place super() after the switch so that if no earlier error occurs,
    // `this` would be initialized (avoiding unrelated "no super" errors).
    super();
  }
}

assertThrows(() => { new C(); }, ReferenceError);

// Test 2: Ensure the first comparison that is executed only if the jump table
// misses (i.e., the first non-jump-table label) performs the proper hole check
// for `this`.
// We choose a discriminant (42) outside the jump-table range [0..9], so the
// engine will fall back to linear comparisons. The first such comparison here
// is `case this:`, which must throw before reaching super().
class D extends B {
  constructor() {
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
        break;
      case this:  // Must trigger ReferenceError when evaluated.
        break;
      default:
        break;
    }
    super();
  }
}

assertThrows(() => { new D(); }, ReferenceError);

// Test 3: Ensure that subsequent non-jump-table comparisons (not just the
// first) also get an elision scope and thus properly check `this`.
// The first additional label is a safe constant (100) so it doesn't throw;
// the second is `this`, which should throw when evaluated.
class E extends B {
  constructor() {
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
        break;
      case 100:   // Safe, should not throw and not match 42.
        break;
      case this:  // Must trigger ReferenceError when evaluated.
        break;
      default:
        break;
    }
    super();
  }
}

assertThrows(() => { new E(); }, ReferenceError);

// Control test: In a base class (non-derived) constructor, `this` is already
// initialized at entry, so using it in a case label should not throw.
class BaseOK {
  constructor(v) {
    switch (v) {
      case this:
        break;
      default:
        break;
    }
  }
}
// Should not throw.
new BaseOK(0);

print("OK");
