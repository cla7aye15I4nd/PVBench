// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --reuse-scope-infos --expose-gc --stress-flush-code

// This test is derived from a PoC that previously triggered a crash when
// compiling/evaluating code with --reuse-scope-infos in certain contexts.
// The fix (see patch) added a guard to avoid reusing scope infos when the
// current context is a NativeContext. This test ensures:
//  - Global eval at top-level (NativeContext) does not attempt unsafe
//    scope-info reuse and does not crash.
//  - Evaluations in newly created realms remain isolated and stable across
//    GC/code flushing, including executing global eval inside those realms.

(function() {
  function assertEquals(actual, expected, msg) {
    if (actual !== expected) {
      throw new Error((msg || 'assertEquals failed') + ': expected ' + expected + ', got ' + actual);
    }
  }
  function assertTrue(value, msg) {
    if (!value) throw new Error(msg || 'assertTrue failed');
  }

  // Helper to create some allocation/pressure and trigger GC.
  function pumpAndGC() {
    const arr = [];
    for (let i = 0; i < 1000; i++) arr.push({i, s: 'x' + i});
    gc();
    return arr.length; // keep the code alive
  }

  // 1) Direct global eval in the main (native) context should not crash and should behave correctly.
  // This specifically exercises CompileGlobalEval in a NativeContext, the scenario guarded by the fix.
  (function testGlobalEvalInNativeContext() {
    // Previously problematic pattern from the PoC; ensure it does not crash.
    try { eval('function NaN() {}'); } catch (e) { /* Allowed to throw, must not crash. */ }

    // Empty string eval (via replace path from PoC) should return undefined.
    const r2 = (function(){ try { return eval(`\n      `.replace()); } catch (e) { return 'threw'; } })();
    assertTrue(r2 === undefined || r2 === 'threw', 'empty eval is benign (undefined or throws)');

    // A normal eval should work and return its last expression value.
    const r3 = eval('var a = 5; a + 2');
    assertEquals(r3, 7, 'global eval should return the last expression (7)');

    pumpAndGC();
  })();

  // 2) Execution inside a new Realm: ensure isolation and that global eval within that Realm is safe.
  (function testRealmEvalIsolationAndGlobalEval() {
    for (let i = 0; i < 5; i++) {
      const realm = Realm.create();

      // a) Define a lexical binding and a function that closes over it; ensure stability and isolation.
      const v = Realm.eval(realm, 'let x = 42; function g(){ return x; } g();');
      assertEquals(v, 42, 'closure over top-level let should work in realm');

      // Changes in the main realm should not affect the other realm.
      var x = 7; // main realm global, unrelated to realm's lexical x
      const v2 = Realm.eval(realm, 'g()');
      assertEquals(v2, 42, 'realm closure should remain isolated from main realm globals');

      // b) Execute a global eval inside the realm that previously was part of the crashy case.
      const r3 = Realm.eval(realm, 'try { eval("function NaN() {}"); } catch (e) {} 7');
      assertEquals(r3, 7, 'realm global eval should execute and continue');

      // c) Empty string through replace() path as in PoC; should be a no-op returning undefined or throw benignly.
      const r4 = Realm.eval(realm, 'try { eval(`\n      `.replace()); } catch (e) { "threw" }');
      assertTrue(r4 === undefined || r4 === 'threw', 'empty realm eval is benign');

      // d) After stressing GC/code flushing, previously compiled functions should still behave.
      pumpAndGC();
      const v3 = Realm.eval(realm, 'g()');
      assertEquals(v3, 42, 'realm closure should remain valid after GC/code flush');

      // More GC pressure before next iteration.
      pumpAndGC();
    }
  })();

  // 3) Replay the original PoC structure to ensure no crash across multiple invocations.
  (function replayOriginalPoCPattern() {
    function executeCode(code) {
      if (typeof code === 'function') return code();
    }

    function runOnce(scriptArray) {
      const realm = Realm.create();
      try {
        // Use the last element, matching the PoC's indexing pattern.
        executeCode(function () { return Realm.eval(realm, scriptArray[scriptArray.length - 1]); });
      } catch (e) {
        // Swallow any exception; the goal is to ensure no crash.
      }
      gc();
    }

    const cases = [
      { scripts: ['eval("function NaN() {}");'] },
      { scripts: ["\n      ".replace()] },
    ];

    cases.forEach(function (c) {
      runOnce(c.scripts);
      runOnce(c.scripts);
    });
  })();

  print('OK');
})();
