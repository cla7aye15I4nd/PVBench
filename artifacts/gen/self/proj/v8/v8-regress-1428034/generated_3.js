// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --stress-lazy-source-positions

// This test verifies correct handling of functions defined inside arrow function
// parameter initializers ("arrowheads"). The patch ensures that lazily parsed
// function scopes inside arrowheads are not re-analyzed or have preparse data
// saved twice, which previously could lead to crashes or incorrect scope
// analysis. We validate expected runtime behavior and ensure no crashes occur
// when such functions are present and executed.

(function(){
  function assertEquals(expected, actual, msg) {
    if (expected !== actual) {
      throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  function assertTrue(cond, msg) {
    if (!cond) throw new Error(msg || "Assertion failed: condition is not true");
  }

  // 1) Original PoC scenario: function defined in arrowhead that captures and
  // mutates a parameter binding. We keep it inside eval to match the original
  // reproduction conditions and to exercise parser/analyzer paths through eval.
  eval(`
  var f = (
    a = function in_arrowhead_args() {
      return function inner() {
        b = 42; // Mutate parameter binding from inside the function created in the arrowhead
      };
    },
    b = 1,
  ) => {
    assertEquals(1, b);
    a()();
    assertEquals(42, b);
  };
  f();

  // Call again to ensure fresh parameter environment is created per call and
  // that any preparse data reuse doesn't corrupt bindings across invocations.
  f();
  `);

  // 2) Multiple arrowhead functions, each closing over different parameters.
  // Ensures multiple lazily parsed scopes inside the same arrowhead are handled
  // without re-analysis or duplicate preparse data saves.
  {
    const g = (
      a = function fa() { return function() { c = "x"; }; },
      b = function fb() { return function() { d = "y"; }; },
      c = 0,
      d = 0
    ) => {
      assertEquals(0, c);
      assertEquals(0, d);
      a()();
      b()();
      assertEquals("x", c);
      assertEquals("y", d);
    };
    g();
    // Re-run to check isolation between calls and that repeated parsing/execution
    // does not crash or corrupt state.
    g();
  }

  // 3) Nested creation paths inside arrowhead: an arrow in the initializer
  // returns a function that later mutates a different parameter. This stresses
  // more complex scope chains across arrowhead/body boundary.
  {
    const h = (
      x = (() => function setY() { y = 2; })(),
      y = 1
    ) => {
      assertEquals(1, y);
      x();
      assertEquals(2, y);
    };
    h();
    h();
  }

  // 4) Stress: Create several functions with arrowhead closures in a loop to
  // increase coverage of lazy parsing and preparse data caching across many
  // instances. We verify behavior and ensure no crashes.
  for (let i = 0; i < 20; i++) {
    const mk = (
      mkSetter = function mkSetter() {
        return function() { p = i; };
      },
      p = -1
    ) => {
      assertEquals(-1, p);
      mkSetter()();
      assertEquals(i, p);
    };
    mk();
  }

  // If we reach here without throwing, the fix is working as intended.
  print("OK");
})();
