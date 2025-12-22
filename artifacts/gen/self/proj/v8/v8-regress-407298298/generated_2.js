// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff --experimental-wasm-jspi

// This test verifies a fix where Wasm runtime calls in TurboFan/TurboShaft
// switched from using the generic CEntry stub to the Wasm-specific CEntry
// (Builtin::kWasmCEntry). The bug manifested when using WebAssembly.promising
// with a Wasm function that imports a JS function and returns an f64, leading
// to crashes or incorrect entry/exit handling. The test ensures that
// WebAssembly.promising resolves correctly and does not crash across several
// cases.

// Load the wasm module builder helper.
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

// Minimal assertion helpers (self-contained).
(function(){
  function fail(msg) { throw new Error(msg); }
  this.assertEquals = function(actual, expected, msg) {
    if (actual !== expected) fail((msg || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
  };
  this.assertTrue = function(value, msg) {
    if (!value) fail(msg || 'Assertion failed: expected truthy');
  };
  this.assertInstanceOf = function(value, ctor, msg) {
    if (!(value instanceof ctor)) fail((msg || 'Assertion failed') + ': expected instance of ' + (ctor && ctor.name));
  };
})();

// Build a module that imports a JS function (DataView.prototype.byteLength getter)
// and returns it as an f64. Signature: (externref) -> f64
let kSig_d_r = makeSig([kWasmExternRef], [kWasmF64]);

let kImports = {
  DataView: {
    byteLengthImport: Function.prototype.call.bind(
        Object.getOwnPropertyDescriptor(DataView.prototype, 'byteLength').get)
  },
};

let builder = new WasmModuleBuilder();
let kDataViewByteLength =
    builder.addImport('DataView', 'byteLengthImport', kSig_d_r);
builder.addFunction('byteLength', kSig_d_r).exportFunc().addBody([
  kExprLocalGet, 0,
  kExprCallFunction, kDataViewByteLength,
]);
let instance = builder.instantiate(kImports);

// Helper to create a promising wrapper once.
const promisingByteLength = WebAssembly.promising(instance.exports.byteLength);

// 1) Baseline: DataView on resizable SharedArrayBuffer, full view.
const kLength = 8;
let sab = new SharedArrayBuffer(kLength, {maxByteLength: 2 * kLength});
let view1 = new DataView(sab);

// Ensure the wrapper returns a Promise.
let p1 = promisingByteLength(view1);
assertInstanceOf(p1, Promise, 'WebAssembly.promising should return a Promise');

p1 = p1.then(v => { assertEquals(v, kLength, 'SAB full view byteLength'); });

// 2) DataView on regular ArrayBuffer with offset and explicit length
// to exercise more receiver handling in the imported getter.
let ab = new ArrayBuffer(32);
let explicitLen = 8;
let view2 = new DataView(ab, 4, explicitLen);
let p2 = promisingByteLength(view2).then(v => {
  assertEquals(v, explicitLen, 'AB view with offset/length byteLength');
});

// 3) Error path: invalid receiver (null) should cause a TypeError and the
// promise should reject. This checks that the JSPI plumbing and runtime entry
// do not crash and propagate the exception correctly.
let p3 = promisingByteLength(null).then(
  _ => { throw new Error('Expected rejection for invalid receiver'); },
  e => {
    if (!(e instanceof TypeError)) {
      throw new Error('Expected TypeError, got: ' + e);
    }
  });

// 4) Another SAB view with non-zero offset and shorter explicit length.
let view3 = new DataView(sab, 2, 4);
let p4 = promisingByteLength(view3).then(v => {
  assertEquals(v, 4, 'SAB view with offset/length byteLength');
});

Promise.all([p1, p2, p3, p4]).then(() => {
  // If the bug regresses, we expect crashes or misbehavior before reaching here.
  print('OK');
}, (e) => { throw e; });
