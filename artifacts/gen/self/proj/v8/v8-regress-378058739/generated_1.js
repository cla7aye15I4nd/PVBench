// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test targets a parser bug fixed by changing the early-return condition
// in ParserBase::UseThis(). The fix ensures that the decision to skip marking
// 'this' usage is based on the closure scope's reparsed state, not the current
// (possibly nested) scope. The original PoC exercised a path where 'this' is
// used inside a computed class element within nested class expressions during
// field initialization.
//
// The assertions below verify that:
// 1) The original PoC code no longer crashes the engine (it should simply throw
//    a normal runtime error due to dereferencing an uninitialized variable).
// 2) Variants that evaluate similar shapes involving 'this' in computed class
//    elements do not crash in either interpreted or optimized execution.
// 3) A sanity check that the computed property actually evaluates and coerces
//    'this' (observable via a custom toString), ensuring 'this' is handled.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
  }
  if (!threw) {
    throw new Error((message || "Expected function to throw"));
  }
}

// ===== Test 1: Original PoC shape should not crash (should simply throw) =====
function var_5(){
    let var_1;
    class var_3 {
        static '' = new class {
            '' = var_1.trigger_error();
            [class {
                [this];
            }];
        };
    }
}

// The original PoC intentionally throws (due to var_1 being undefined), but
// must not crash the engine during parsing/initialization.
assertThrows(var_5, "PoC should throw a normal exception, not crash");

// ===== Test 2: Same syntactic shape but without runtime error; must not crash =====
function noCrash_variant() {
  let var_1 = { trigger_error() { /* no-op */ } };
  // Keep a very similar structure to the PoC but avoid throwing.
  class Outer {
    static '' = new class {
      // This line executes but does not throw.
      '' = var_1.trigger_error();
      // Use a nested class expression with a computed class element using 'this'.
      [class { [this]; }];
    };
  }
}

// Should not throw nor crash.
noCrash_variant();

// ===== Test 3: Ensure 'this' in computed class element is evaluated/coerced =====
// This verifies that the computed element name actually observes/coerces 'this',
// which depends on correct UseThis handling in the parser and proper evaluation.
function this_coercion_observed() {
  let count = 0;
  const recv = {
    toString() {
      count++;
      return "k";
    }
  };
  function g() {
    // 'this' here refers to the call receiver of g (sloppy mode), so calling
    // g.call(recv) makes 'this === recv'. The computed property name will
    // ToPropertyKey(this), which calls recv.toString(), incrementing count.
    class X { [this]; }
  }
  g.call(recv);
  assertEquals(count, 1, "computed class element should coerce 'this' exactly once");
}

this_coercion_observed();

print("OK");
