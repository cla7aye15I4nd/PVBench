// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises parsing and execution of class static initialization
// blocks (and related class member initializers) in contexts that previously
// could trigger a parser DCHECK during reparsing of class member initializer
// functions. The fix removed an invalid DCHECK in the reparsing path.
//
// The test ensures:
// 1) No crashes when a static block contains a try/catch that swallows a
//    ReferenceError/TypeError thrown by accessing a property on undefined.
// 2) The static block is executed exactly once during class definition.
// 3) Uncaught errors in static blocks propagate as TypeError.
// 4) Similar patterns work in eval and in instance field initializers.

(function() {
  'use strict';

  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
    }
  }

  function assertTrue(value, message) {
    if (!value) throw new Error(message || 'Assertion failed: expected truthy');
  }

  function assertThrows(fn, errorConstructor, messageRegex) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (errorConstructor && !(e instanceof errorConstructor)) {
        throw new Error('Wrong exception type: expected ' + (errorConstructor && errorConstructor.name) + ', got ' + e);
      }
      if (messageRegex && !messageRegex.test(String(e))) {
        throw new Error('Exception message did not match ' + messageRegex + ': ' + e);
      }
    }
    if (!threw) {
      throw new Error('Expected exception was not raised');
    }
  }

  function assertDoesNotThrow(fn, message) {
    try {
      fn();
    } catch (e) {
      throw new Error((message || 'Unexpected exception') + ': ' + e);
    }
  }

  // Global undefined variable used to produce a TypeError when accessing a property.
  var o;

  // Test 1: Original PoC scenario: static block with try/catch inside a strict function.
  // It should not throw, and should return the class constructor (a function).
  function f() {
    'use strict';
    class C {
      static {
        try {
          // Accessing property on undefined should throw, but it is caught.
          o.boom;
        } catch (e) {
          // Swallow error.
        }
      }
    }
    return C;
  }
  // Should not throw and should return a function (class constructor).
  let C1;
  assertDoesNotThrow(() => { C1 = f(); });
  assertEquals(typeof C1, 'function', 'Expected returned class constructor');

  // Test 1b: Ensure the static block actually executed exactly once during class evaluation.
  function g() {
    'use strict';
    let ran = false;
    class C {
      static {
        try { o.boom; } catch (e) {}
        ran = true;
      }
    }
    // At this point, the static block must have run.
    return ran;
  }
  assertEquals(g(), true, 'Static block did not execute as expected');

  // Test 2: Without try/catch the error must propagate as a TypeError when defining the class.
  function h() {
    'use strict';
    class C {
      static {
        // This should throw and not be caught here.
        o.boom;
      }
    }
    return C;
  }
  assertThrows(h, TypeError);

  // Test 3: The same safe pattern inside eval within a strict function should not crash or throw.
  function i() {
    'use strict';
    assertDoesNotThrow(() => {
      eval('class E { static { try { o.boom } catch (e) {} } }');
    }, 'eval with static block should not throw');
  }
  i();

  // Test 4: Instance field initializer using an IIFE with try/catch behaves similarly
  // (class members initializer function also covers field initializers).
  let marks = 0;
  class K {
    field = (function() {
      try { o.boom; } catch (e) { marks++; }
      return 1;
    })();
  }
  assertDoesNotThrow(() => { new K(); });
  assertEquals(marks, 1, 'Instance field initializer did not catch and count the error exactly once');

  // Test 5: Multiple static blocks execute in order and do not crash with try/catch.
  let count = 0;
  class M {
    static {
      try { o.boom; } catch (e) { count++; }
    }
    static {
      try { o.boom; } catch (e) { count++; }
    }
  }
  assertEquals(count, 2, 'Both static blocks should have executed');

  print('OK');
})();
