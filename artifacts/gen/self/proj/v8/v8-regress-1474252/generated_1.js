// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises exception propagation from property accessors used by
// WebAssembly.Table and WebAssembly.Memory constructors. The patch switched
// internal DCHECKs from has_pending_exception() to has_scheduled_exception(),
// which is relevant when property access (via getters) throws while the
// exception is scheduled. We verify that such exceptions are properly
// propagated to JavaScript and that no crashes occur.

(function() {
  function assertThrows(fn, expected) {
    let threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (arguments.length >= 2) {
        if (e !== expected) {
          throw new Error("Unexpected exception: " + e + ", expected: " + expected);
        }
      }
    }
    if (!threw) throw new Error("Expected function to throw, but it did not");
  }

  // 1) WebAssembly.Table: exception from reading 'initial'.
  // Ensure the constructor attempts to read 'initial' and that the thrown
  // exception from its getter is propagated unchanged.
  (function testTableInitialGetterThrows() {
    const sentinel = new Error("sentinel-initial");
    const desc = { element: 'anyfunc' };
    Object.defineProperty(desc, 'initial', { get() { throw sentinel; }, configurable: true });
    assertThrows(() => new WebAssembly.Table(desc), sentinel);
  })();

  // 2) WebAssembly.Table: exception from reading 'maximum'.
  // Provide a valid 'initial' value, expose a throwing getter on 'maximum', and
  // ensure that the exception is propagated.
  (function testTableMaximumGetterThrows() {
    const sentinel = new Error("sentinel-maximum");
    const desc = { element: 'anyfunc' };
    Object.defineProperty(desc, 'initial', { value: 1, writable: true, configurable: true });
    Object.defineProperty(desc, 'maximum', { get() { throw sentinel; }, configurable: true });
    assertThrows(() => new WebAssembly.Table(desc), sentinel);
  })();

  // 3) WebAssembly.Memory: exception while reading non-standard 'index' field.
  // The engine queries 'index' before other fields; ensure a throwing getter
  // here is propagated. Keep a valid 'initial' to avoid unrelated errors.
  (function testMemoryIndexGetterThrows() {
    const sentinel = new Error("sentinel-index");
    const desc = { initial: 1 };
    Object.defineProperty(desc, 'index', { get() { throw sentinel; }, configurable: true });
    assertThrows(() => new WebAssembly.Memory(desc), sentinel);
  })();

  // 4) Regression shape corresponding to the original PoC: dynamically choose
  // a property ("initial") and install a getter that references an undefined
  // function, which should throw when the constructor attempts to read it.
  (function testOriginalPoCShape() {
    function __f_3(__v_212, __v_213) {
      var __v_214 = Object.getOwnPropertyNames(__v_212);
      if (__v_214.includes() && __v_17 && __v_17.constructor && __v_17.constructor.hasOwnProperty()) {
        // Unreachable due to short-circuiting; kept to mirror original PoC.
      }
      return __v_214[__v_213 % __v_214.length];
    }
    var __v_239 = {element: 'anyfunc', initial: 10};
    __v_239.__defineGetter__(__f_3(__v_239, 1603979645), function() {
      return __f_10(); // ReferenceError: __f_10 is not defined
    });

    assertThrows(() => new WebAssembly.Table(__v_239));
  })();

  print("OK");
})();
