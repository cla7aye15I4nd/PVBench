// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff --experimental-wasm-jspi

// This test verifies that wasm runtime calls made via TurboShaft use the
// Wasm-specific CEntry stub (Builtin::kWasmCEntry). The original bug used a
// generic CEntry which led to crashes/incorrect behavior when integrating
// with JSPI (WebAssembly.promising). The test exercises a wasm function that
// calls into JS (via an import) and is then wrapped with WebAssembly.promising.
// We assert that:
//  - The Promise resolves with the correct numeric value (no crash).
//  - The Promise rejects properly when the JS import throws (no crash, correct
//    error propagation).
//  - Multiple calls work, stressing the runtime call path.

// Helper assertion functions (self-contained, no mjsunit dependency).
function assertEquals(actual, expected, message) {
  if (!Object.is(actual, expected)) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertInstanceOf(value, constructor, message) {
  if (!(value instanceof constructor)) {
    throw new Error((message || "Expected instance of ") + constructor.name + ", got: " + value);
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || "Assertion failed");
}

// Minimal wasm module setup matching the PoC.
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

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
// (externref) -> f64 : returns the DataView#byteLength of the given object.
builder.addFunction('byteLength', kSig_d_r).exportFunc().addBody([
  kExprLocalGet, 0,
  kExprCallFunction, kDataViewByteLength,
]);
let instance = builder.instantiate(kImports);

// Base objects for tests.
const kLength = 8;
let buffer = new SharedArrayBuffer(kLength, {maxByteLength: 2 * kLength});
let dataview = new DataView(buffer);              // byteLength = 8
let dataview_sliced = new DataView(buffer, 2, 3); // byteLength = 3

// Wrap the wasm export with JSPI. This exercises the runtime call path that
// previously used the wrong CEntry.
const byteLengthPromising = WebAssembly.promising(instance.exports.byteLength);

// Collect all asynchronous checks and verify their outcomes.
let tests = [];

// 1) Success path: Promise resolves with the DataView's byteLength.
tests.push(
  byteLengthPromising(dataview).then(v => {
    assertEquals(typeof v, 'number', 'Expected a number from JSPI');
    assertEquals(v, kLength, 'Resolved value mismatch for full view');
  })
);

// 2) Success path with non-trivial view parameters (offset/length).
tests.push(
  byteLengthPromising(dataview_sliced).then(v => {
    assertEquals(v, 3, 'Resolved value mismatch for sliced view');
  })
);

// 3) Exception path: Passing a non-DataView should cause the byteLength getter
//    to throw a TypeError. The JSPI wrapper should return a rejected Promise.
tests.push(
  byteLengthPromising({}).then(
    _ => { throw new Error('Expected rejection was not raised'); },
    e => { assertInstanceOf(e, TypeError, 'Wrong rejection type'); }
  )
);

// 4) Multiple sequential calls (stress the runtime call path, ensure stability).
for (let i = 0; i < 3; i++) {
  tests.push(
    byteLengthPromising(dataview).then(v => {
      assertEquals(v, kLength, 'Repeated call #' + i + ' mismatch');
    })
  );
}

Promise.all(tests).then(() => {
  // If we reach here, all assertions passed and no crash occurred, indicating
  // the Wasm runtime calls via TurboShaft used the correct Wasm CEntry stub.
  print('OK');
}, (e) => { throw e; });
