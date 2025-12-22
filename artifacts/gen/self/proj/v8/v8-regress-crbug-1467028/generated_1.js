// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test targets a bug fixed in parser.cc where a DCHECK incorrectly
// assumed `maybe_outer_scope_info` is non-null when reparsing class
// members initializer functions (including static initialization blocks).
// The PoC involved a class static block inside a strict function that
// tried to access a property of `undefined` inside a try/catch. In debug
// builds this used to hit the DCHECK during parsing/reparsing.
//
// The assertions below verify that:
// 1) Such code does not crash and does not throw (the error is caught),
// 2) The same patterns throw the correct error when not caught,
// 3) Related class members initializer scenarios (instance fields,
//    private fields, and static fields) behave correctly.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorType, regex) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorType && !(e instanceof errorType)) {
      throw new Error("Wrong exception type: " + e);
    }
    if (regex && !regex.test(String(e))) {
      throw new Error("Exception message mismatch: " + e);
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// Global `o` remains undefined; accessing `o.boom` should throw if not caught.
var o;

// ===== Test 1: PoC scenario (strict mode + static block with try/catch) =====
// Must not throw and must not crash. Should return the class value.
function f() {
  "use strict";
  class C {
    static {
      try {
        // Triggers a TypeError if not caught.
        o.boom;
      } catch (e) {
        // Swallow the error.
      }
    }
  }
  return C;
}

// Should not throw; ensure we get a function (the class constructor).
var C1 = f();
assertEquals(typeof C1, "function", "Expected class value from f()");

// ===== Test 2: Same as above but without try/catch: should throw on class eval =====
function g() {
  "use strict";
  class C {
    static {
      o.boom;
    }
  }
  return C;
}
assertThrows(g, TypeError, /Cannot read properties of undefined/);

// ===== Test 3: Non-strict surrounding function, same static block with try/catch =====
function h() {
  class C {
    static {
      try {
        o.boom;
      } catch (e) {}
    }
  }
  return C;
}
var C2 = h();
assertEquals(typeof C2, "function", "Expected class value from h()");

// ===== Test 4: Instance field initializer with try/catch via IIFE =====
// Ensures class members initializer function path also handles reparsing safely.
class E {
  x = (() => { try { o.boom; } catch (e) { return 42; } })();
}
assertEquals(new E().x, 42, "Instance field initializer should catch and return 42");

// ===== Test 5: Private field initializer with try/catch via IIFE =====
class F {
  #x = (() => { try { o.boom; } catch (e) { return 7; } })();
  get x() { return this.#x; }
}
assertEquals(new F().x, 7, "Private field initializer should catch and return 7");

// ===== Test 6: Instance field initializer without catch: should throw on construction =====
class G {
  x = o.boom;
}
assertThrows(() => new G(), TypeError, /Cannot read properties of undefined/);

// ===== Test 7: Static field initializer with try/catch via IIFE =====
// Evaluated at class definition time; must not throw and must set the value.
class H {
  static x = (() => { try { o.boom; } catch (e) { return 99; } })();
}
assertEquals(H.x, 99, "Static field initializer should catch and set 99");

// ===== Test 8: Static field initializer without catch: should throw on class evaluation =====
function makeI() {
  class I { static x = o.boom; }
  return I;
}
assertThrows(makeI, TypeError, /Cannot read properties of undefined/);

print("OK");
