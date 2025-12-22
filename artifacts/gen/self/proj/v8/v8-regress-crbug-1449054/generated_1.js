// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test is derived from a PoC that exercised a parser bug around
// class static initializers using `super` inside nested class definitions.
//
// Patch context:
// The fix ensures that when deserializing the scope chain for a
// ClassStaticInitializerFunction, the receiver is properly deserialized:
//   if (flags().is_eval() || IsArrowFunction(...) ||
//       flags().function_kind() == kClassStaticInitializerFunction) {
//     original_scope_->GetReceiverScope()->DeserializeReceiver(...);
//   }
//
// Without this, accessing `super` within a class static block could lead to
// crashes or incorrect behavior. This test asserts that the code no longer
// crashes and that `super` behaves correctly. It also checks the expected
// TypeError when calling an undefined super method.

(function() {
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
        throw new Error((message || "Wrong exception type") + ": expected " + (errorConstructor && errorConstructor.name) + ", got " + e);
      }
    }
    if (!threw) throw new Error((message || "Expected exception was not raised"));
  }

  // ---------------------------------------------------------------------------
  // Test 1: Original PoC behavior should not crash and should throw TypeError
  // because super.p is not a function on the base class.
  // ---------------------------------------------------------------------------
  class C1 {
    constructor(a3) {
      class C6 extends C1 {
        [this] = undefined;
        static 1 = a3;
        static {
          // Should try to call super.p(), which is undefined, hence TypeError.
          super.p();
        }
      }
    }
  }

  assertThrows(() => new C1(), TypeError, "super.p() should throw TypeError when undefined");

  // ---------------------------------------------------------------------------
  // Test 2: Define a base with a static method `p`. The same nested pattern
  // should work and invoke the base method via `super` in a static block.
  // This ensures `super` is correctly wired up in class static initializers.
  // ---------------------------------------------------------------------------
  let counter = 0;
  class Base2 {
    static p() { counter++; }
  }
  class Outer2 {
    constructor(a3) {
      class Inner2 extends Base2 {
        [this] = undefined;
        static 1 = a3;
        static {
          // Should successfully call Base2.p via super and increment counter.
          super.p();
        }
      }
    }
  }

  new Outer2(10);
  assertEquals(counter, 1, "super.p() should have been called once");
  new Outer2(20);
  assertEquals(counter, 2, "super.p() should have been called twice after two constructions");

  // ---------------------------------------------------------------------------
  // Test 3: Reading a value off of super in a static block and assigning it to
  // a known place to observe the result. This further validates that `super`
  // is correctly resolved in class static initializers of nested classes.
  // ---------------------------------------------------------------------------
  class Base3 {}
  Base3.q = 99;
  // A separate observable sink for the static block side effect.
  Base3.collected = null;

  class Outer3 {
    constructor() {
      class Inner3 extends Base3 {
        static {
          // Read from super and store to a known location to verify.
          Base3.collected = super.q;
        }
      }
    }
  }

  new Outer3();
  assertEquals(Base3.collected, 99, "Reading property from super in static initializer should work");

  // If we got here without throwing, then the parser/runtime handled the
  // class static initializer `super` cases correctly.
  print("OK");
})();
