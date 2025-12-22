// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct receiver (this) deserialization for
// class static initializer functions. The patch ensures that when
// deserializing scope chains for class static initializers, the
// receiver binding is restored, preventing crashes and ensuring
// proper TypeError behavior when calling undefined super methods.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorConstructor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error((message || "Wrong exception type") + ": expected " + errorConstructor.name + ", got " + e);
    }
  }
  if (!threw) {
    throw new Error((message || "Expected exception was not raised"));
  }
}

// -----------------------------------------------------------------------------
// Test 1: Original PoC should not crash and should throw a TypeError.
// The static block calls super.p(), which is undefined, so invoking it should
// raise a TypeError. Prior to the fix, this could crash due to missing receiver
// deserialization for the class static initializer.
class C1 {
  constructor(a3) {
    class C6 extends C1 {
      [this] = undefined;
      static 1 = a3;
      static {
        super.p();
      }
    }
  }
}

assertThrows(() => new C1(), TypeError, "PoC should throw TypeError and not crash");

// -----------------------------------------------------------------------------
// Test 2: Receiver ('this') should be correctly bound inside a static block and
// when invoking a super static method. The super call returns the receiver and
// must equal the subclass constructor.
class Base {
  static who() { return this; }
}
let staticBlockRan = false;
class Sub extends Base {
  static {
    const r = super.who();
    if (r !== Sub) throw new Error("Incorrect receiver in static block super call");
    staticBlockRan = true;
  }
}
assertEquals(staticBlockRan, true, "Static block in subclass should run exactly once");

// -----------------------------------------------------------------------------
// Test 3: Same as Test 2 but inside eval to exercise scope (de)serialization
// paths that involve eval flags. The patch added the receiver deserialization
// for class static initializer functions similarly to eval/arrow functions.
(function testInEval() {
  const B = eval(`(() => {\n    class A { static who() { return this; } }\n    class B extends A {\n      static { if (super.who() !== B) throw new Error('bad this in eval static block'); }\n    }\n    return B;\n  })()`);
  // Ensure the class is usable and the static block already executed.
  assertEquals(typeof B, "function", "Eval should return the class constructor");
})();

// -----------------------------------------------------------------------------
// Test 4: 'this' inside a static block without super should refer to the class
// itself. This also relies on correct receiver binding.
let ran = false;
class SelfRef {
  static {
    if (this !== SelfRef) throw new Error("'this' in static block should be the class constructor");
    ran = true;
  }
}
assertEquals(ran, true, "SelfRef static block should execute and have correct 'this'");

print("OK");
