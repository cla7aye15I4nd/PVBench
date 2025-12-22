// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff

// This test verifies a fix in instruction-selector-adapter where the loaded
// representation for atomic loads was incorrectly derived. The patch teaches
// LoadView::loaded_rep() to query AtomicLoadParametersOf(...) for atomic loads
// (and also to handle F64x2PromoteLowF32x4). We exercise atomic i64/i32 8-bit
// loads inside a try/catch with tag throws to ensure correct codegen and no
// crashes under TurboFan.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// Load wasm module builder utilities.
d8.file.execute("test/mjsunit/wasm/wasm-module-builder.js");

(function TestAtomicLoad8URepresentation() {
  let builder = new WasmModuleBuilder();

  // Memory is sufficient for all loads in this test.
  builder.addMemory(1, 10);

  // Tags used for throwing values of specific types inside try/catch.
  let tag_i64 = builder.addTag(kSig_v_l);
  let tag_i32 = builder.addTag(kSig_v_i);

  // i64.atomic.load8_u: value is consumed by throw as i64, then caught.
  builder.addFunction("main", kSig_i_v).exportFunc().addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI64AtomicLoad8U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag_i64,
    kExprCatch, tag_i64,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

  // i32.atomic.load8_u: value is consumed by throw as i32, then caught.
  builder.addFunction("main32", kSig_i_v).exportFunc().addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI32AtomicLoad8U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag_i32,
    kExprCatch, tag_i32,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

  // Instantiate and run both exports. Both should take the catch path and return 42.
  let instance1 = builder.instantiate();
  assertEquals(instance1.exports.main(), 42, "main should return 42");
  assertEquals(instance1.exports.main32(), 42, "main32 should return 42");

  // Re-instantiate to ensure repeated compilation works.
  let instance2 = builder.instantiate();
  assertEquals(instance2.exports.main(), 42, "main (2) should return 42");
  assertEquals(instance2.exports.main32(), 42, "main32 (2) should return 42");
})();

print("OK");
