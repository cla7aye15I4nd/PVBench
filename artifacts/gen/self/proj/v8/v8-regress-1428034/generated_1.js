// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --stress-lazy-source-positions

// This test targets a bug in scope analysis for lazily parsed functions that
// appear inside arrow function parameter initializers ("arrowheads").
// The fix ensures:
//  - Partially analyzing scopes skips functions that were already lazily parsed
//    inside arrowheads.
//  - Preparse data is not saved twice for such functions.
// We verify correct variable resolution and that no crashes occur when such
// functions capture and mutate parameters defined in the arrowhead.

(function(){
  function assertEquals(expected, actual, msg) {
    if (expected !== actual) {
      throw new Error((msg || "assertEquals failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(cond, msg) {
    if (!cond) throw new Error(msg || "assertTrue failed");
  }

  // Helper to check that no accidental global was created for the name "b".
  function assertNoGlobalB(msg) {
    // Ensure the global object does not have its own property "b".
    assertTrue(!Object.prototype.hasOwnProperty.call(globalThis, "b"), msg || "globalThis.b should not exist");
  }

  // Baseline scenario from the PoC: a function created in the arrowhead returns
  // an inner function that mutates parameter `b`. After calling a()(), `b` in
  // the arrow's body should reflect the mutation.
  (function test_poc_scenario(){
    eval(`
      var f = (
        a = function in_arrowhead_args() {
          return function inner() { b = 42; };
        },
        b = 1,
      ) => {
        if (b !== 1) throw new Error('initial b mismatch');
        a()();
        if (b !== 42) throw new Error('mutated b mismatch');
      };
      f();
    `);
    assertNoGlobalB("No global 'b' should be created by inner assignment");
  })();

  // Variation 1: Swap parameter order, ensure capture works regardless of order.
  (function test_swapped_param_order(){
    eval(`
      var g = (
        b = 1,
        a = function() { return function() { b = 99; }; },
      ) => {
        if (b !== 1) throw new Error('initial b mismatch');
        a()();
        if (b !== 99) throw new Error('mutated b mismatch');
      };
      g();
    `);
    assertNoGlobalB("No global 'b' after swapped param order test");
  })();

  // Variation 2: Use arrow functions inside the arrowhead to produce nested
  // lazily-parsable functions.
  (function test_arrow_inside_arrowhead(){
    eval(`
      var h = (
        a = () => () => { b = 7; },
        b = 1,
      ) => {
        if (b !== 1) throw new Error('initial b mismatch');
        a()();
        if (b !== 7) throw new Error('mutated b mismatch');
      };
      h();
    `);
    assertNoGlobalB("No global 'b' after arrow-inside-arrowhead test");
  })();

  // Variation 3: Deeper nesting to ensure partial analysis and preparse data
  // handling does not get confused by multiple nested function scopes.
  (function test_deep_nesting(){
    eval(`
      var k = (
        a = function() { return function() { return function() { b = 123; }; }; },
        b = 1,
      ) => {
        if (b !== 1) throw new Error('initial b mismatch');
        a()()();
        if (b !== 123) throw new Error('mutated b mismatch');
      };
      k();
    `);
    assertNoGlobalB("No global 'b' after deep nesting test");
  })();

  // Regression robustness: run the baseline multiple times to exercise any
  // caching/preparse paths potentially affected by the fix.
  (function test_repeat_runs(){
    for (let i = 0; i < 5; i++) {
      eval(`
        var f = (
          a = function in_arrowhead_args() {
            return function inner() { b = ${40 + i}; };
          },
          b = 1,
        ) => {
          if (b !== 1) throw new Error('initial b mismatch');
          a()();
          if (b !== ${40 + i}) throw new Error('mutated b mismatch');
        };
        f();
      `);
      assertNoGlobalB("No global 'b' after repeat run iteration " + i);
    }
  })();

  print('OK');
})();
