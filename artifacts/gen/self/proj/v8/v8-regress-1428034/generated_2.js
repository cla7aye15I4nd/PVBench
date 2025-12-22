// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --stress-lazy-source-positions

// This test targets a bug fixed in scopes handling for functions inside
// arrow parameter lists ("arrowheads"). The fix ensures that:
// 1) Already lazily parsed inner function scopes inside arrowheads are not
//    re-analyzed during partial analysis (avoids crashes/state corruption).
// 2) Preparse data is not saved twice for such scopes.
//
// The assertions below stress lazy parsing and ensure correct scoping semantics
// and that no crashes occur when compiling/evaluating such patterns repeatedly.

function assertEquals(expected, actual, message) {
  if (expected !== actual) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertTrue(cond, message) {
  if (!cond) throw new Error(message || "Assertion failed: expected true, got false");
}

// Cleanup any possible leftovers from the environment to avoid false positives.
try { delete globalThis.b; } catch (_) {}
try { delete globalThis.y; } catch (_) {}
try { delete globalThis.in_arrowhead_args; } catch (_) {}
try { delete globalThis.outer; } catch (_) {}

// ------------------------------------------------------------
// Test 1: Original PoC semantics plus extra checks.
// Ensures the function inside the arrowhead captures the parameter scope and
// that the named function expression's name does not leak to the outer scope.
// Also checks that no global 'b' is created/modified.
// ------------------------------------------------------------

eval(`
var f = (
  a = function in_arrowhead_args() {
    return function inner() {
      b = 42; // Should capture the parameter 'b', not the global.
    };
  },
  b = 1,
) => {
  assertEquals(1, b, "initial b in f");
  // The name of the named function expression should not be visible here.
  assertEquals("undefined", typeof in_arrowhead_args, "name not in arrow body (f)");
  a()();
  assertEquals(42, b, "updated b in f");
};

f();
`);

assertEquals("undefined", typeof globalThis.b, "b should not leak globally after f()");
assertEquals("undefined", typeof globalThis.in_arrowhead_args, "named function should not leak globally after f()");

// ------------------------------------------------------------
// Test 2: Another variant with different names/values to further stress
// lazy parsing and scope analysis.
// ------------------------------------------------------------

eval(`
var g = (
  x = (function outer() { return function inner() { y = "Y"; }; }),
  y = "y0",
) => {
  assertEquals("y0", y, "initial y in g");
  assertEquals("undefined", typeof outer, "name not in arrow body (g)");
  x()();
  assertEquals("Y", y, "updated y in g");
};

g();
`);

assertEquals("undefined", typeof globalThis.y, "y should not leak globally after g()");
assertEquals("undefined", typeof globalThis.outer, "outer should not leak globally after g()");

// ------------------------------------------------------------
// Test 3: Repeated eval to exercise preparse data saving and partial analysis
// for functions inside arrowheads. This stresses the skip/avoid-double-save
// logic from the patch. Should not crash and semantics must hold.
// ------------------------------------------------------------

for (let i = 0; i < 20; i++) {
  eval(`
    var f${"_"}iter = (
      a = function in_arrowhead_args_${i}() {
        return function() { b = ${i}; };
      },
      b = 0,
    ) => {
      a()();
      if (b !== ${i}) throw new Error("iteration ${i}: wrong b: " + b);
      // The named function expression should not leak into the arrow body.
      if (typeof in_arrowhead_args_${i} !== "undefined") throw new Error("leaked name in iteration ${i}");
    };
    f${"_"}iter();
  `);
}

assertEquals("undefined", typeof globalThis.b, "b should not leak globally after repeated evals");

// ------------------------------------------------------------
// Test 4: Arrow-in-arrowhead variant to ensure arrows are handled similarly.
// ------------------------------------------------------------

eval(`
var z = (
  a = () => () => { b = "Z"; },
  b = "z",
) => {
  assertEquals("z", b, "initial b in z");
  a()();
  assertEquals("Z", b, "updated b in z");
};

z();
`);

assertEquals("undefined", typeof globalThis.b, "b should remain non-global after z()");

print("OK");
