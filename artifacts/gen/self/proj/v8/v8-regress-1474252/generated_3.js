// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test exercises error propagation paths in WebAssembly.Table and
// WebAssembly.Memory constructors when property access on the descriptor
// throws. A recent patch replaced DCHECK(has_pending_exception) with
// DCHECK(has_scheduled_exception) in these paths. While DCHECKs are debug-only,
// this test ensures that exceptions thrown by descriptor getters are properly
// propagated (i.e., the constructors do not crash or swallow errors).

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrowsEquals(fn, expected) {
  try {
    fn();
    throw new Error("Expected exception was not raised");
  } catch (e) {
    assertEquals(e, expected, "Wrong thrown value");
  }
}

function pickSupportedTableElement() {
  // Use 'funcref' if available; otherwise fall back to legacy 'anyfunc'.
  try {
    // Some engines may not accept 'funcref'.
    new WebAssembly.Table({ element: 'funcref', initial: 1 });
    return 'funcref';
  } catch (e) {
    return 'anyfunc';
  }
}

const kElemType = pickSupportedTableElement();

(function testTable_initial_getter_throws() {
  // Throw when reading the 'initial' property. This exercises the first path
  // changed in the patch (GetInitialOrMinimumProperty for Table).
  const sentinel = { name: 'sentinel-initial' };
  const desc = { element: kElemType };
  Object.defineProperty(desc, 'initial', { get() { throw sentinel; } });
  assertThrowsEquals(() => new WebAssembly.Table(desc), sentinel);
})();

(function testTable_maximum_getter_throws() {
  // Throw when reading the optional 'maximum' property. This exercises the
  // second changed DCHECK in the patch for Table.
  const sentinel = { name: 'sentinel-maximum' };
  const desc = { element: kElemType, initial: 1 };
  Object.defineProperty(desc, 'maximum', { get() { throw sentinel; } });
  assertThrowsEquals(() => new WebAssembly.Table(desc), sentinel);
})();

(function testMemory_index_getter_throws() {
  // Throw when reading the 'index' property for Memory. The patch changed the
  // DCHECK in this code path as well. Even if the engine doesn't use the value,
  // simply accessing the property must propagate the exception.
  const sentinel = { name: 'sentinel-index' };
  const desc = { initial: 1 };
  Object.defineProperty(desc, 'index', { get() { throw sentinel; } });
  assertThrowsEquals(() => new WebAssembly.Memory(desc), sentinel);
})();

(function sanityValidDescriptorsWork() {
  // Sanity: valid descriptors should construct successfully (no exceptions).
  const t = new WebAssembly.Table({ element: kElemType, initial: 1, maximum: 2 });
  if (!(t instanceof WebAssembly.Table)) throw new Error('Expected a WebAssembly.Table instance');
  const m = new WebAssembly.Memory({ initial: 1 });
  if (!(m instanceof WebAssembly.Memory)) throw new Error('Expected a WebAssembly.Memory instance');
})();

// POC-style minimal reproduction retained and clarified: accessing 'initial' via
// a computed getter that throws.
(function poc_style_repro() {
  function pickKey(obj, n) {
    const keys = Object.getOwnPropertyNames(obj);
    return keys[n % keys.length];
  }
  const desc = { element: kElemType, initial: 10 };
  const key = pickKey(desc, 1603979645);  // deterministically picks 'initial'.
  const sentinel = new Error('poc-sentinel');
  desc.__defineGetter__(key, function() { throw sentinel; });
  assertThrowsEquals(() => new WebAssembly.Table(desc), sentinel);
})();

print('OK');
