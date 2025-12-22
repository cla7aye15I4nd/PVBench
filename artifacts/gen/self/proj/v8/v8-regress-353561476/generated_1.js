// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --reuse-scope-infos --expose-gc --stress-flush-code

// This test exercises a regression fixed by:
//   src/runtime/runtime-compiler.cc
//   if (!Is<NativeContext>(*context) && v8_flags.reuse_scope_infos) { ... }
// Prior to the fix, CompileGlobalEval attempted to reuse scope infos even when
// running in a NativeContext (global context), which could lead to crashes when
// eval was executed in a fresh Realm under --reuse-scope-infos, especially
// together with GC/code flushing. The fix prevents reuse in NativeContext.
//
// The test verifies that various global eval scenarios in fresh Realms no longer
// crash and still produce correct results, even when interleaved with GC and
// repeated realm creation/destruction. It also runs an eval that may throw to
// ensure the engine properly surfaces the exception without crashing.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  function assertThrows(fn, message) {
    var threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
    }
    if (!threw) throw new Error(message || "Expected function to throw");
  }

  // Helper to create a new Realm and run a script in that realm.
  function withRealmRun(script) {
    var r = Realm.create();
    try {
      return Realm.eval(r, script);
    } finally {
      // No explicit Realm.dispose in d8; just let it be GC'd.
    }
  }

  // Lightly mimic parts of the PoC to stress GC and code flushing.
  var bag = [];
  function maybeGC() {
    // Access and delete a possibly-undefined property to vary hidden classes.
    delete bag[void 0];
    if (typeof gc === 'function') gc();
  }

  // 1) Basic sanity: eval inside a fresh Realm's global context returns a value.
  //    This exercises CompileGlobalEval in a NativeContext of the new Realm.
  for (var i = 0; i < 10; i++) {
    var res = withRealmRun('eval("var x = 40 + 2; x")');
    assertEquals(res, 42, "global eval should compute and return 42");
    maybeGC();
  }

  // 2) Ensure that creating bindings via global eval in a Realm works repeatedly
  //    and survives GC/code flushing stress.
  (function() {
    var r = Realm.create();
    for (var j = 0; j < 20; j++) {
      // Define/update a global via eval, then read it back.
      var result = Realm.eval(r, 'eval("if (typeof counter === \'undefined\') var counter = 0; counter += 1; counter")');
      assertEquals(result, j + 1, "counter should increase each eval");
      maybeGC();
    }
    // A separate eval that uses builtins to exercise additional code paths.
    var s = Realm.eval(r, 'eval("\'abc\'.replace(\'b\', \'B\')")');
    assertEquals(s, 'aBc', "String.prototype.replace should work in realm eval");
    maybeGC();
  })();

  // 3) Negative path: run an eval that is likely to throw, but must not crash the VM.
  //    We cannot reliably check the error type across realms, only that it throws.
  //    Using a problematic declaration inside eval (e.g., redeclaration with let).
  for (var k = 0; k < 5; k++) {
    assertThrows(function() {
      withRealmRun('eval("let a = 1; let a = 2;")');
    }, "redeclaration in eval should throw");
    maybeGC();
  }

  // 4) Stress realm creation and global eval interleaved with GC, mirroring PoC.
  //    The PoC evaluated a snippet like eval("function NaN() {}"); Historically
  //    this exercised tricky global binding logic. Here we only ensure no crash.
  var scripts = [
    'eval("function NaN() {}")',
    'eval("var q = (1<<5); q")'
  ];
  for (var t = 0; t < 20; t++) {
    for (var si = 0; si < scripts.length; si++) {
      try {
        withRealmRun(scripts[si]);
      } catch (e) {
        // Accept exceptions, but the engine must not crash.
      }
      maybeGC();
    }
  }

  // If we reached here without throwing from our assertions, the regression is fixed.
  print("OK");
})();
