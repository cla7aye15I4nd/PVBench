// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --no-liftoff

// This test verifies that Turbofan correctly handles the load representation
// for atomic loads (and related nodes) when selecting instructions.
// The patch ensures that atomic loads report their proper LoadRepresentation
// which previously could cause miscompilation or crashes when such loads
// appeared in certain contexts (e.g., in try/catch with throws).

// The proof-of-concept used atomic loads as the argument to a thrown tag
// inside a try/catch. If the representation is mishandled, compilation or
// execution could crash. After the fix, all functions should execute and
// return the value from the catch path (42).

d8.file.execute("test/mjsunit/wasm/wasm-module-builder.js");

function assertEquals(expected, actual, msg) {
  if (expected !== actual) {
    throw new Error((msg || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

let builder = new WasmModuleBuilder();

// Memory for atomic loads. (The original PoC used non-shared memory; keep it.)
builder.addMemory(1, 10);

// Tags: one taking an i64, the other taking an i32.
let tag0 = builder.addTag(kSig_v_l);
let tag1 = builder.addTag(kSig_v_i);

// Baseline from PoC: i64 atomic 8-bit load used as throw argument.
builder.addFunction("main", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    // address 0
    kExprI32Const, 0,
    // i64.atomic.load8_u alignment=0, offset=0
    kAtomicPrefix, kExprI64AtomicLoad8U, 0, 0,
    // throw tag0 (takes an i64)
    kExprThrow, tag0,
  kExprCatch, tag0,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  // Fallback (should not reach)
  kExprI32Const, 123,
]);

// Baseline from PoC: i32 atomic 8-bit load used as throw argument.
builder.addFunction("main32", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    // i32.atomic.load8_u alignment=0, offset=0
    kAtomicPrefix, kExprI32AtomicLoad8U, 0, 0,
    // throw tag1 (takes an i32)
    kExprThrow, tag1,
  kExprCatch, tag1,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

// Additional coverage based on the fix: Ensure other atomic load widths are
// also handled correctly by the instruction selector's representation logic.

// i64.atomic.load16_u (alignment exponent 1)
builder.addFunction("main64_16", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    kAtomicPrefix, kExprI64AtomicLoad16U, 1, 0,
    kExprThrow, tag0,
  kExprCatch, tag0,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

// i64.atomic.load32_u (alignment exponent 2)
builder.addFunction("main64_32", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    kAtomicPrefix, kExprI64AtomicLoad32U, 2, 0,
    kExprThrow, tag0,
  kExprCatch, tag0,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

// i64.atomic.load (full width, alignment exponent 3)
builder.addFunction("main64_64", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    kAtomicPrefix, kExprI64AtomicLoad, 3, 0,
    kExprThrow, tag0,
  kExprCatch, tag0,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

// i32.atomic.load16_u (alignment exponent 1)
builder.addFunction("main32_16", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    kAtomicPrefix, kExprI32AtomicLoad16U, 1, 0,
    kExprThrow, tag1,
  kExprCatch, tag1,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

// i32.atomic.load (full width, alignment exponent 2)
builder.addFunction("main32_32", kSig_i_v).exportFunc().addBody([
  kExprTry, kWasmVoid,
    kExprI32Const, 0,
    kAtomicPrefix, kExprI32AtomicLoad, 2, 0,
    kExprThrow, tag1,
  kExprCatch, tag1,
    kExprI32Const, 42,
    kExprReturn,
  kExprEnd,
  kExprI32Const, 123,
]);

let instance = builder.instantiate();

// Validate that all functions execute successfully and return 42 from the
// catch path (i.e., no crash and correct control flow).
assertEquals(42, instance.exports.main());
assertEquals(42, instance.exports.main32());
assertEquals(42, instance.exports.main64_16());
assertEquals(42, instance.exports.main64_32());
assertEquals(42, instance.exports.main64_64());
assertEquals(42, instance.exports.main32_16());
assertEquals(42, instance.exports.main32_32());

print("OK");
