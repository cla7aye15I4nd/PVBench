// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --reuse-scope-infos --expose-gc --stress-flush-code

// This test targets a fix in CompileGlobalEval where scope info reuse should
// not happen in a NativeContext (global eval). The patch adds a guard:
//   if (!Is<NativeContext>(*context) && v8_flags.reuse_scope_infos) { ... }
// We verify that various global-eval scenarios (including across Realms)
// don't crash and preserve correct scoping behavior when reuse-scope-infos
// is enabled, while evals inside non-native contexts (e.g., function scope)
// still behave correctly.

(function() {
  // Basic assertion utilities.
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertThrowsAny(fn, message) {
    let threw = false;
    try { fn(); } catch (e) { threw = true; }
    if (!threw) throw new Error((message || "Expected function to throw"));
  }

  // Utilities preserved from the PoC (lightly cleaned up for clarity).
  function executeCode(code) {
    if (typeof code === 'function') return code();
  }
  var assertThrows = function assertThrows(code) {
    // In PoC this did not assert; here we just execute for no-crash coverage.
    executeCode(code);
  };
  function __getRandomProperty() { /* placeholder for PoC parity */ }
  (function () {
    this.__callGC = function () { gc(); };
  })();

  // 1) No-crash regression from PoC with Realm.eval of code that internally uses global eval.
  // The original PoC attempted to exercise reuse of scope infos for global eval across realms.
  // After the fix, global eval in a NativeContext should not reuse scope infos and must not crash.
  (function testNoCrashRealmGlobalEvalPoC() {
    const scripts = [
      'eval("function NaN() {}\n");',  // May throw depending on semantics, but must not crash.
      '`\n      `.replace()'                   // Whitespace program; should evaluate to undefined.
    ];

    for (let i = 0; i < scripts.length; i++) {
      for (let j = 0; j < 3; j++) {  // Do a few iterations to stress flushing and GC.
        const realm = Realm.create();
        try {
          Realm.eval(realm, scripts[i]);
        } catch (e) {
          // We don't require a specific exception here; the key property is no crash.
        }
        __callGC();
      }
    }
  })();

  // 2) Simple sanity: evaluating a whitespace-only script returns undefined.
  (function testRealmEvalWhitespaceReturnsUndefined() {
    const realm = Realm.create();
    const res = Realm.eval(realm, '        ');
    assertEquals(res, undefined, 'Whitespace Realm.eval should return undefined');
    __callGC();
  })();

  // 3) Global (NativeContext) direct eval should behave correctly. The fix specifically
  // disables scope info reuse for NativeContext, so this should keep working normally.
  (function testGlobalEvalInNativeContext() {
    const out = eval('let x = 100; x');
    assertEquals(out, 100, 'Global eval should evaluate in native context');
    __callGC();

    // Repeat a few times to tick stress-flush-code paths.
    for (let i = 0; i < 10; i++) {
      let v = eval('let t = ' + i + '; t');
      assertEquals(v, i);
    }
    __callGC();
  })();

  // 4) Direct eval inside a function (non-native context) should still have access to lexical bindings.
  // The patch continues to allow reuse when not in a NativeContext. We verify correctness here.
  (function testEvalInsideFunctionHasLexicalAccess() {
    function f(base) {
      let y = base + 23;
      return eval('y');
    }
    for (let i = 0; i < 20; i++) {
      assertEquals(f(i), i + 23);
    }
    __callGC();
  })();

  // 5) Cross-realm isolation: a fresh realm should not see bindings from the current realm.
  // This guards against any accidental scope info reuse across realms.
  (function testCrossRealmIsolation() {
    var secret = 9999;
    const realm = Realm.create();
    const typeInOther = Realm.eval(realm, 'typeof secret');
    assertEquals(typeInOther, 'undefined', 'Other realm must not see bindings from this realm');

    // Additionally verify that eval inside the other realm works and sees its own bindings.
    Realm.eval(realm, 'var a = 7;');
    const aVal = Realm.eval(realm, 'eval("a")');
    assertEquals(aVal, 7, 'Direct eval inside realm should see realm bindings');
    __callGC();
  })();

  // 6) Eval inside a function in a different realm should also see lexical bindings from that function.
  (function testEvalInsideFunctionInOtherRealm() {
    const realm = Realm.create();
    const val = Realm.eval(realm, '(() => { let z = 77; return eval("z"); })()');
    assertEquals(val, 77);
    __callGC();
  })();

  // 7) Re-run the PoC-inspired sequence a few times to ensure stability under stress flags.
  (function repeatPoCSequence() {
    var holder = [];
    function runSequence(scripts) {
      const realm = Realm.create();
      try {
        assertThrows(function () {
          Realm.eval(realm, scripts[scripts.length - 1]);
        });
      } catch (e) {
        // Ignore; only checking for crashes and stability.
      }
      delete holder[__getRandomProperty()];
      __callGC();
    }

    const cases = [
      { scripts: ['eval("function NaN() {}\n");'] },
      { scripts: ['`\n      `.replace()'] },
    ];

    cases.forEach(function (c) {
      runSequence(c.scripts);
      runSequence(c.scripts);
    });
  })();

  print('OK');
})();
