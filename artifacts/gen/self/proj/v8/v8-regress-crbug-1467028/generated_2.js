// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that parsing and reparsing of class members initializer
// functions (which include static initialization blocks) does not trigger
// internal parser DCHECKs and that normal JavaScript semantics are preserved.
// The original issue was a debug-mode DCHECK in Parser::ParseFunction for
// IsClassMembersInitializerFunction, which has been removed. This test ensures:
//  - Code patterns that used to hit the DCHECK now run without crashing.
//  - Exceptions thrown from static blocks propagate correctly when uncaught.
//  - When caught, execution continues and side effects occur as expected.

// Helpers
function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorConstructor /*, optionalMessageRegex */) {
  var threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error("Wrong exception type: expected " + (errorConstructor && errorConstructor.name) + ", got " + e);
    }
    // Optionally check message via regex if provided.
    if (arguments.length >= 3 && arguments[2]) {
      var re = arguments[2];
      if (!re.test(String(e))) {
        throw new Error("Exception message did not match " + re + ": " + e);
      }
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Global used by the static blocks below.
var o;  // Intentionally left undefined for the first tests.

// Test 1: Uncaught error from a static block should throw a TypeError when
// accessing a property of undefined. This ensures the static block executes at
// class evaluation time and that the exception propagates.
function f_no_catch() {
  "use strict";
  class C {
    static {
      // Accessing a property on undefined should throw TypeError.
      o.boom;
    }
  }
  return C;
}
// Accept either legacy or modern error message variants by only checking type.
assertThrows(f_no_catch, TypeError);

// Test 2: The original PoC pattern: catch the error inside the static block.
// Ensure no exception escapes and that the static block executed exactly once
// per class definition.
var counter = 0;
function f_with_catch() {
  "use strict";
  class C {
    static {
      try {
        o.boom;
      } catch (e) {
        // Side effect to prove the static block executed.
        counter++;
      }
    }
  }
  return C;
}

var C1 = f_with_catch();
assertEquals(typeof C1, "function", "Class should be created even if static block error is caught");
assertEquals(counter, 1, "Static block should execute once per class definition");
var C2 = f_with_catch();
assertEquals(counter, 2, "Static block should execute again for each new class");

// Test 3: When the access is valid (o is an object), static block runs
// without throwing and can perform side effects.
o = { boom: 42 };
var side_effect = 0;
function f_ok() {
  "use strict";
  class C {
    static {
      side_effect = o.boom;  // Should read 42 without throwing.
    }
  }
  return C;
}
var C3 = f_ok();
assertEquals(typeof C3, "function");
assertEquals(side_effect, 42, "Static block should run and set side effect when no error");

// If we reached here without throwing, the parser handled class member
// initializer functions correctly (no internal crashes) and runtime semantics
// are preserved.
print("OK");
