// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct handling of large numeric-looking property names
// after fixes in string hashing and index parsing (see patch to
// string-hasher-inl.h). In particular, it ensures that:
//  - Numeric strings greater than the max array index (2^32 - 2) are NOT
//    treated as array indices and behave as normal string property names.
//  - Integer-index hashing path works for values > 2^32 - 2 but <= 2^53 - 1.
//  - No crashes or mis-retrieval occur for many such properties.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertTrue(v, msg) { if (!v) throw new Error(msg || "Expected true"); }
function assertFalse(v, msg) { if (v) throw new Error(msg || "Expected false"); }

// Constants used for boundary testing.
const MAX_ARRAY_INDEX = 0xFFFFFFFF - 1; // 4294967294
const NON_ARRAY_INDEX_1 = 0xFFFFFFFF;   // 4294967295, not an array index
const ABOVE_U32 = 0x100000000;          // 4294967296

// A much larger non-array-index that fits within Number safe integer range.
// This is around 2^33 and was used in the PoC.
const LARGE_NON_ARRAY_BASE = 8589933568; // 2^33 - 1024

// Max safe integer and one above (still exactly representable as Number but > MaxSafeInteger for integer index parse logic).
const MAX_SAFE_INT = 9007199254740991;  // 2^53 - 1
const ABOVE_MAX_SAFE_INT = 9007199254740992; // 2^53

// 1) Original PoC scenario: Set and get many properties with large numeric keys.
(function testManyLargeNumericKeys() {
  let o = {};
  for (let i = 0; i < 10000; i++) {
    o[LARGE_NON_ARRAY_BASE + i] = i;
  }
  for (let i = 0; i < 10000; i++) {
    assertEquals(o[LARGE_NON_ARRAY_BASE + i], i, "PoC retrieval mismatch at i=" + i);
  }
})();

// 2) Ensure number and string access refer to the same property for various edge values.
(function testNumberStringKeyEquivalence() {
  const keys = [
    MAX_ARRAY_INDEX - 1, // still array index if used on arrays, but should be same string key on objects
    MAX_ARRAY_INDEX,
    NON_ARRAY_INDEX_1,   // not array index
    ABOVE_U32,           // not array index, but valid integer index value
    LARGE_NON_ARRAY_BASE,
    LARGE_NON_ARRAY_BASE + 1,
    MAX_SAFE_INT,
    ABOVE_MAX_SAFE_INT
  ];

  for (const k of keys) {
    // Assign via number and read via both number and string.
    let o1 = {};
    o1[k] = 1;
    assertEquals(o1[k], 1, "o1 number->number");
    assertEquals(o1[String(k)], 1, "o1 number->string");

    // Assign via string and read via both number and string.
    let o2 = {};
    o2[String(k)] = 2;
    assertEquals(o2[k], 2, "o2 string->number");
    assertEquals(o2[String(k)], 2, "o2 string->string");
  }
})();

// 3) Array boundary behavior: writing at indices beyond max array index must NOT affect length.
(function testArrayIndexBoundaries() {
  let a = [];
  // Setting non-array indices should not change length.
  a[NON_ARRAY_INDEX_1] = 'x';
  assertEquals(a.length, 0, "length changed for non-array index 2^32-1");
  a[ABOVE_U32] = 'y';
  assertEquals(a.length, 0, "length changed for non-array index 2^32");
  a[LARGE_NON_ARRAY_BASE] = 'z';
  assertEquals(a.length, 0, "length changed for large non-array index ~2^33");

  // Verify values are retrievable as properties.
  assertEquals(a[NON_ARRAY_INDEX_1], 'x');
  assertEquals(a[ABOVE_U32], 'y');
  assertEquals(a[LARGE_NON_ARRAY_BASE], 'z');

  // For completeness, setting at max array index should affect length by spec.
  // We avoid setting/checking this here to prevent creating extremely large array length,
  // which can be slow in some environments. The above checks are sufficient to catch
  // misclassification of large indices as array indices.
})();

// 4) Leading zero cases: ensure that strings with leading zeros are not conflated with numeric keys.
(function testLeadingZerosDoNotAlias() {
  let o = {};
  const k = ABOVE_U32; // 4294967296
  const s = "0" + String(k); // leading zero -> different property name string

  o[k] = 123;
  assertEquals(o[k], 123);
  assertEquals(o[String(k)], 123);
  assertFalse(Object.prototype.hasOwnProperty.call(o, s), "numeric key should not alias zero-prefixed string");

  // Now set the zero-prefixed string and ensure it is distinct.
  o[s] = 456;
  assertEquals(o[s], 456);
  assertEquals(o[k], 123);
})();

print("OK");