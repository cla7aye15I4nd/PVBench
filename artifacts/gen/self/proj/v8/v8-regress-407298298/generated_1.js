// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff --experimental-wasm-jspi

// This test verifies a fix in Wasm TurboShaft where runtime calls inside Wasm
// code used the generic CEntry stub instead of the Wasm-specific
// Builtin::kWasmCEntry. The bug could cause crashes or misbehavior when Wasm
// performed runtime calls on optimized paths, e.g., with JS-PI via
// WebAssembly.promising. We exercise a Wasm function that imports a JS getter
// and wrap the export with WebAssembly.promising to ensure we hit the relevant
// runtime call paths. The test asserts correct resolution/rejection, and that
// multiple invocations are stable and do not crash.

(function(){
  // Minimal self-contained assertions (do not rely on mjsunit harness).
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertInstanceOf(value, Ctor, message) {
    if (!(value instanceof Ctor)) {
      throw new Error((message || "Assertion failed") + ": expected instance of " + (Ctor && Ctor.name) + ", got " + value);
    }
  }
  function assertPromiseResult(promise, onFulfilled, onRejected) {
    return Promise.resolve(promise).then(
      v => { if (onFulfilled) onFulfilled(v); },
      e => { if (onRejected) onRejected(e); else throw e; }
    );
  }

  // Helper to encode ASCII without TextEncoder (keeps test self-contained in d8).
  function ascii(str) {
    const a = new Array(str.length);
    for (let i = 0; i < str.length; i++) a[i] = str.charCodeAt(i) & 0x7F;
    return a;
  }
  function pushU32LEB(out, value) {
    let v = value >>> 0;
    while (v >= 0x80) { out.push((v & 0x7F) | 0x80); v >>>= 7; }
    out.push(v);
  }

  // Build a minimal Wasm module:
  // type (externref)->(f64)
  // import DataView.byteLengthImport : (externref)->(f64)
  // func byteLength(x: externref) -> f64 { return call_import(x); }
  // export "byteLength"
  function makeModuleBytes() {
    const bytes = [];
    // magic + version
    bytes.push(0x00,0x61,0x73,0x6D, 0x01,0x00,0x00,0x00);

    // Type section (id=1)
    {
      const content = [];
      pushU32LEB(content, 1);      // 1 type
      content.push(0x60);          // func type
      pushU32LEB(content, 1);      // 1 param
      content.push(0x6F);          // externref
      pushU32LEB(content, 1);      // 1 result
      content.push(0x7C);          // f64
      bytes.push(0x01);            // section id
      const tmp = [];
      pushU32LEB(tmp, content.length);
      bytes.push(...tmp, ...content);
    }

    // Import section (id=2)
    {
      const mod = ascii("DataView");
      const field = ascii("byteLengthImport");
      const content = [];
      pushU32LEB(content, 1);            // 1 import
      pushU32LEB(content, mod.length);   // module name len
      content.push(...mod);
      pushU32LEB(content, field.length); // field name len
      content.push(...field);
      content.push(0x00);                // kind: func
      pushU32LEB(content, 0);            // type index 0
      bytes.push(0x02);
      const tmp = [];
      pushU32LEB(tmp, content.length);
      bytes.push(...tmp, ...content);
    }

    // Function section (id=3)
    {
      const content = [];
      pushU32LEB(content, 1);  // 1 function
      pushU32LEB(content, 0);  // type index 0
      bytes.push(0x03);
      const tmp = [];
      pushU32LEB(tmp, content.length);
      bytes.push(...tmp, ...content);
    }

    // Export section (id=7)
    {
      const name = ascii("byteLength");
      const content = [];
      pushU32LEB(content, 1);            // 1 export
      pushU32LEB(content, name.length);  // name len
      content.push(...name);
      content.push(0x00);                // kind: func
      pushU32LEB(content, 1);            // func index 1 (after 1 import)
      bytes.push(0x07);
      const tmp = [];
      pushU32LEB(tmp, content.length);
      bytes.push(...tmp, ...content);
    }

    // Code section (id=10)
    {
      const body = [];
      pushU32LEB(body, 0);      // local decls: 0
      body.push(0x20, 0x00);    // local.get 0
      body.push(0x10, 0x00);    // call function idx 0 (import)
      body.push(0x0B);          // end

      const content = [];
      pushU32LEB(content, 1);   // 1 function body

      const func = [];
      pushU32LEB(func, body.length);
      func.push(...body);

      bytes.push(0x0A);
      const tmp = [];
      pushU32LEB(tmp, content.length + func.length);
      bytes.push(...tmp, ...content, ...func);
    }

    return new Uint8Array(bytes);
  }

  const module_bytes = makeModuleBytes();

  // Import that reads DataView.prototype.byteLength via the accessor's getter,
  // bound to Function.prototype.call, mirroring the PoC.
  const kImports = {
    DataView: {
      byteLengthImport: Function.prototype.call.bind(
        Object.getOwnPropertyDescriptor(DataView.prototype, 'byteLength').get)
    }
  };

  const module = new WebAssembly.Module(module_bytes);
  const instance = new WebAssembly.Instance(module, kImports);

  const kLength = 8;
  // Try to create a growable SharedArrayBuffer if supported, else fall back.
  let buffer;
  try {
    buffer = new SharedArrayBuffer(kLength, {maxByteLength: 2 * kLength});
  } catch (e) {
    try {
      buffer = new SharedArrayBuffer(kLength);
    } catch (e2) {
      buffer = new ArrayBuffer(kLength);
    }
  }
  const dataview = new DataView(buffer);

  // Raw (non-promising) call should synchronously return the f64 value.
  const direct = instance.exports.byteLength;
  const directResult = direct(dataview);
  assertEquals(directResult, kLength, 'Direct Wasm call should return byteLength');

  // Promising wrapper exercises JSPI and Wasm runtime call paths under TurboFan.
  const promised = WebAssembly.promising(instance.exports.byteLength);

  // Test 1: Successful resolution with a valid DataView receiver.
  const p1 = assertPromiseResult(
    promised(dataview),
    v => assertEquals(v, kLength, 'byteLength should equal buffer length')
  );

  // Test 2: Rejection path with an invalid receiver (TypeError from getter).
  const p2 = assertPromiseResult(
    promised({}),
    () => { throw new Error('Expected promise rejection for invalid receiver'); },
    e => assertInstanceOf(e, TypeError, 'Expected TypeError on invalid receiver')
  );

  // Test 3: Multiple calls remain stable and continue to return the correct value.
  const anotherView = new DataView(buffer);
  const p3 = assertPromiseResult(
    promised(anotherView),
    v => assertEquals(v, kLength, 'Repeated call should still work')
  );

  // Test 4: Ensure that synchronous JS exception in import translates to rejection.
  const throwingImports = {
    DataView: {
      byteLengthImport: function(x) { throw new RangeError('boom'); }
    }
  };
  const throwingInstance = new WebAssembly.Instance(module, throwingImports);
  const promisedThrowing = WebAssembly.promising(throwingInstance.exports.byteLength);
  const p4 = assertPromiseResult(
    promisedThrowing(dataview),
    () => { throw new Error('Expected rejection from throwing import'); },
    e => assertInstanceOf(e, RangeError, 'Expected RangeError from throwing import')
  );

  Promise.all([p1, p2, p3, p4]).then(() => {
    // If we got here, no crashes occurred and all assertions passed.
    print('OK');
  }, (e) => { throw e; });
})();
