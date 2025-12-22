// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct handling of 'this' access and TDZ checks in
// switch statements inside derived class constructors, particularly when the
// bytecode generator uses a jump table for dense integer case labels.
// The patch ensures that comparisons executed after a jump table fallback
// properly open a hole-check elision scope so that TDZ checks (like for 'this')
// are not incorrectly elided.

function assertEquals(actual, expected, message) {
  if (!Object.is(actual, expected)) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorConstructor) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error("Wrong exception type: " + e);
    }
  }
  if (!threw) {
    throw new Error("Expected exception was not raised");
  }
}

class B {}

// 1) Original PoC scenario: the matched case body references 'this' before super.
//    With correct semantics, constructing C must throw ReferenceError.
class C extends B {
  constructor() {
    let x = 0;
    switch (0) {
      // Dense integer cases trigger a jump table.
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
        x += this; // Accessing 'this' before super => ReferenceError
        break;
      case this:
        // Not evaluated because case 0 matches in the jump table.
        break;
    }
  }
}
assertThrows(() => { new C(); }, ReferenceError);

// 2) Exercise the patch-specific path: no jump-table match, so the engine
//    evaluates subsequent comparisons (including 'case this'). The evaluation
//    of 'this' in the case label must still perform a TDZ check and throw.
class D extends B {
  constructor() {
    let x = 0;
    switch (100) { // 100 is not in the 0..9 jump table
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
        x += 1;
        break;
      case this: // Evaluated after jump-table fallback => must throw
        x += 2;
        break;
      default:
        x += 3;
    }
  }
}
assertThrows(() => { new D(); }, ReferenceError);

// 3) Sanity check: after calling super(), using 'this' in a case label/body
//    is allowed and should not throw, regardless of jump table usage.
class E extends B {
  constructor() {
    super();
    let y = 0;
    switch (100) { // Ensure we take the comparison path past the jump table
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
        y += 1;
        break;
      case this: // Safe now; not equal to 100, so won't match
        y += 2;
        break;
      default:
        y += 3;
    }
    this.y = y;
  }
}
const e = new E();
assertEquals(e.y, 3);

// 4) Additional positive case: after super(), using 'this' as the discriminant
//    should match 'case this' and execute that branch.
class F extends B {
  constructor() {
    super();
    this.z = 0;
    const d = this;
    switch (d) {
      // Include dense numeric cases to keep parity with jump table setup; they
      // won't match here but ensure similar compilation paths.
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
        this.z = -1;
        break;
      case this:
        this.z = 42; // Should match and execute
        break;
      default:
        this.z = 1;
    }
  }
}
const f = new F();
assertEquals(f.z, 42);

print("OK");
