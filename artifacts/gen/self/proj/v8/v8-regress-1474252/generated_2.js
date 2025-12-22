// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises WebAssembly.Table and WebAssembly.Memory constructors
// when property accessors on the descriptor throw. A recent fix changed
// internal DCHECKs to check has_scheduled_exception() instead of
// has_pending_exception() in these code paths.
// The test ensures these constructors propagate the JS exception and do not
// crash.

function assertThrows(fn, ctor) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (ctor && !(e instanceof ctor)) {
      throw new Error("Wrong exception type: " + e);
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// -------------------------------
// 1) Reproduce original PoC shape: throwing getter for 'initial' in Table
//    (exercises wasm-js.cc:GetInitialOrMinimumProperty path)
function __f_3(__v_212, __v_213) {
  var __v_214 = Object.getOwnPropertyNames(__v_212);
  if (__v_214.includes() && __v_17.constructor.hasOwnProperty()) {
  }
  return __v_214[__v_213 % __v_214.length];
}
var __v_239 = {element: 'anyfunc', initial: 10};
__v_239.__defineGetter__(__f_3(__v_239, 1603979645), function() {
  // Call an undefined function to trigger a ReferenceError from the getter.
  return __f_10();
});

assertThrows(() => new WebAssembly.Table(__v_239), ReferenceError);

// Sanity: a valid construction should succeed afterwards (no lingering issues).
var table_ok = new WebAssembly.Table({element: 'anyfunc', initial: 1});
if (!(table_ok instanceof WebAssembly.Table)) throw new Error("Table not constructed");

// -------------------------------
// 2) Throwing getter for 'maximum' in Table descriptor
//    (exercises wasm-js.cc:GetMaximum property handling path)
var opts_max_throw = {element: 'anyfunc', initial: 1};
Object.defineProperty(opts_max_throw, 'maximum', {
  get() { throw new RangeError('boom from maximum'); },
  enumerable: true
});
assertThrows(() => new WebAssembly.Table(opts_max_throw), RangeError);

// -------------------------------
// 3) Throwing getter for 'index' in Memory descriptor
//    (exercises wasm-js.cc:WebAssemblyMemory path where descriptor->Get('index') fails)
var mem_opts_index_throw = {initial: 1};
Object.defineProperty(mem_opts_index_throw, 'index', {
  get() { throw new SyntaxError('boom from index'); },
  enumerable: true
});
assertThrows(() => new WebAssembly.Memory(mem_opts_index_throw), SyntaxError);

// Sanity: a valid Memory construction should succeed afterwards.
var mem_ok = new WebAssembly.Memory({initial: 1});
if (!(mem_ok instanceof WebAssembly.Memory)) throw new Error("Memory not constructed");

print("OK");
