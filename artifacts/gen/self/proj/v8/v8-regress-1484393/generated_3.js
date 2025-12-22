// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff

// This test verifies a fix in Turbofan's instruction selection adapter where
// the loaded representation for atomic loads (and a SIMD op) was not correctly
// derived. The bug could surface during exception handling with atomic loads.
// We ensure atomic loads of various widths inside try/catch do not crash and
// produce the expected control flow/values.

// Load the wasm module builder utilities.
d8.file.execute("test/mjsunit/wasm/wasm-module-builder.js");

function assertEquals(expected, actual, msg) {
  if (expected !== actual) {
    throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

let builder = new WasmModuleBuilder();

// Add a memory so we can perform atomic loads. Keep it small; we only access offset 0.
builder.addMemory(1, 10, false);  // min, max, shared=false is fine for atomics in tests.

// Add tags that carry the loaded value types as payloads (i64 and i32).
let tag0 = builder.addTag(kSig_v_l);  // For i64 atomic loads.
let tag1 = builder.addTag(kSig_v_i);  // For i32 atomic loads.

// The following functions perform an atomic load and immediately throw the
// loaded value via a tag. We catch it and return 42. This exercises the code
// path where the load's representation is queried under exception handling.

// i64.atomic.load8_u in try/catch.
builder.addFunction("main", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI64AtomicLoad8U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag0,
    kExprCatch, tag0,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// i32.atomic.load8_u in try/catch.
builder.addFunction("main32", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI32AtomicLoad8U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag1,
    kExprCatch, tag1,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// Additional atomic variants to cover the generic fix for atomic load representation.
// i64.atomic.load16_u in try/catch.
builder.addFunction("main64_16u", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI64AtomicLoad16U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag0,
    kExprCatch, tag0,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// i64.atomic.load32_u in try/catch.
builder.addFunction("main64_32u", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI64AtomicLoad32U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag0,
    kExprCatch, tag0,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// i64.atomic.load (64-bit) in try/catch.
builder.addFunction("main64_full", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI64AtomicLoad, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag0,
    kExprCatch, tag0,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// i32.atomic.load16_u in try/catch.
builder.addFunction("main32_16u", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI32AtomicLoad16U, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag1,
    kExprCatch, tag1,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// i32.atomic.load (32-bit) in try/catch.
builder.addFunction("main32_full", kSig_i_v)
  .exportFunc()
  .addBody([
    kExprTry, kWasmVoid,
      kExprI32Const, 0,
      kAtomicPrefix, kExprI32AtomicLoad, 0 /*align*/, 0 /*offset*/,
      kExprThrow, tag1,
    kExprCatch, tag1,
      kExprI32Const, 42,
      kExprReturn,
    kExprEnd,
    kExprI32Const, 123,
  ]);

// Instantiate the module once and call all functions multiple times to stress
// different compilation tiers and inlining decisions in Turbofan.
let instance = builder.instantiate();
let e = instance.exports;

// The functions should all catch the thrown tag and return 42. Also call twice
// to ensure stability across repeated invocations.
const fns = [
  e.main,
  e.main32,
  e.main64_16u,
  e.main64_32u,
  e.main64_full,
  e.main32_16u,
  e.main32_full,
];

for (let fn of fns) {
  assertEquals(42, fn());
  assertEquals(42, fn());
}

print("OK");