// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises a parser/scoping bug fixed by:
// In Parser::DeserializeScopeChain, also deserialize the receiver for
// FunctionKind::kClassStaticInitializerFunction. This ensures that 'this' and
// 'super' are correctly bound inside class static initialization blocks even
// when scope information is deserialized (e.g., in nested/complex constructs),
// and that such code does not crash.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(condition, message) {
    if (!condition) throw new Error(message || "Assertion failed: expected true but got false");
  }
  function assertThrows(fn, errorConstructor) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (errorConstructor && !(e instanceof errorConstructor)) {
        throw new Error("Wrong exception type: expected " + errorConstructor.name + ", got " + e);
      }
    }
    if (!threw) {
      throw new Error("Expected exception was not thrown");
    }
  }

  // Test 1: Original PoC scenario should NOT crash and should throw a TypeError
  // due to calling an undefined super method inside a class static block.
  // This specifically hits class static initializer semantics.
  (function testPoCDoesNotCrashAndThrowsTypeError() {
    class C1 {
      constructor(a3) {
        class C6 extends C1 {
          [this] = undefined;   // Use of 'this' in computed instance field name.
          static 1 = a3;         // Static field reading from outer constructor param.
          static {
            // 'super.p' is undefined; calling it should throw a TypeError, not crash.
            super.p();
          }
        }
      }
    }
    assertThrows(() => new C1(), TypeError);
  })();

  // Test 2: 'this' inside a class static initializer should be bound to the class
  // constructor. This validates correct receiver deserialization/binding.
  (function testThisBindingInStaticBlock() {
    class A {
      static {
        assertEquals(this, A, "'this' inside static block should be the class constructor");
      }
    }
  })();

  // Test 3: Using eval inside a static block should also see the correct 'this'.
  // Although direct eval already had special handling, this also exercises that
  // the surrounding static initializer has a proper receiver.
  (function testEvalSeesCorrectThisInStaticBlock() {
    class E {}
    class D extends E {
      static {
        eval('if (this !== D) throw new Error("this mismatch in eval inside static block")');
      }
    }
  })();

  // Test 4: Arrow capturing 'this' inside a static block should observe the class.
  (function testArrowThisFromStaticBlock() {
    let getter;
    class G {
      static {
        getter = () => this;
      }
    }
    assertEquals(getter(), G, "Arrow captured 'this' from static block should be the class");
  })();

  // Test 5: 'super' resolution inside a static block should work. If the superclass
  // has a static method, calling it via super should succeed and see the current class
  // as 'this'.
  (function testSuperCallInStaticBlock() {
    class Base {
      static getTag() { return this.tag; }
    }
    class Sub extends Base {
      static tag = 99;
      static {
        // super.getTag will be called with 'this' bound to Sub, so it should see tag=99.
        const v = super.getTag();
        assertEquals(v, 99, "super call in static block should see current class as 'this'");
      }
    }
  })();

  print("OK");
})();
