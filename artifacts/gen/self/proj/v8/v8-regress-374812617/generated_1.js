// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --expose-gc --trace-gc-object-stats

// This test targets a bug in JSON object parsing where the initial number of
// dictionary elements for numeric-indexed properties was set incorrectly.
// Patch changes:
//   elms->SetInitialNumberOfElements(length);
// to
//   elms->SetInitialNumberOfElements(cont.elements);
//
// The incorrect value could cause GC/accounting issues and potential crashes
// when objects had a mix of string-named properties and numeric index keys.
//
// The tests below exercise JSON.stringify/JSON.parse round trips for such
// mixed objects, trigger GC, and then validate structure, property order, and
// values to ensure stability and correctness.

(function() {
  // Basic assertion helpers.
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(v, message) { if (!v) throw new Error(message || "Assertion failed: expected true"); }
  function assertFalse(v, message) { if (v) throw new Error(message || "Assertion failed: expected false"); }
  function assertArrayEquals(actual, expected, message) {
    if (!Array.isArray(actual) || !Array.isArray(expected) || actual.length !== expected.length) {
      throw new Error((message || "Array length mismatch") + ": expected [" + expected + "], got [" + actual + "]");
    }
    for (let i = 0; i < actual.length; i++) {
      if (actual[i] !== expected[i]) {
        throw new Error((message || "Array contents mismatch") + ": index " + i + ": expected " + expected[i] + ", got " + actual[i]);
      }
    }
  }

  function roundTripAndAssert(obj, expectedKeys, info) {
    // JSON round-trip should preserve the JSON string exactly.
    const s1 = JSON.stringify(obj);
    const parsed = JSON.parse(s1);
    // Stress GC to surface any accounting issues related to elements metadata.
    if (typeof gc === 'function') {
      gc();
      gc();
    }
    const s2 = JSON.stringify(parsed);
    assertEquals(s2, s1, (info || "round-trip") + ": JSON string must be stable after parse");

    // Check that parsed is a plain object.
    assertFalse(Array.isArray(parsed), (info || "round-trip") + ": parsed result must be an object, not an array");

    // Check key order: integer index properties first in ascending order,
    // then string keys in insertion order. JSON.stringify follows this order
    // and JSON.parse constructs the object from the JSON text produced in that order.
    const keys = Object.keys(parsed);
    assertArrayEquals(keys, expectedKeys, (info || "round-trip") + ": key order mismatch");

    return parsed;
  }

  // Test 1: POC scenario (one numeric index + named props + enumerable accessor)
  (function testSingleIndexWithAccessor() {
    const obj = { a: 1, b: 2, q: 3 };
    obj[44] = 44;
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    const parsed = roundTripAndAssert(obj, ["44", "a", "b", "q", "c"], "single-index+accessor");

    // After parse, accessor becomes a data property with the getter value.
    const desc = Object.getOwnPropertyDescriptor(parsed, "c");
    assertTrue(!!desc, "descriptor for 'c' should exist");
    assertEquals(desc.value, 7, "parsed.c should be 7 as a data value");
    assertEquals(desc.get, undefined, "parsed.c should not be an accessor after parse");
    assertTrue(desc.enumerable, "parsed.c enumerable");
    assertTrue(desc.configurable, "parsed.c configurable");
    assertTrue(desc.writable, "parsed.c writable");

    // Ensure the numeric index property exists and has the correct value.
    assertEquals(parsed[44], 44, "numeric index 44 must be preserved");
  })();

  // Test 2: Multiple sparse numeric indices + named props + accessor
  (function testSparseIndices() {
    const obj = { a: 10, b: 20, q: 30 };
    obj[3] = 33;
    obj[0] = 0;
    obj[44] = 44;
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    const parsed = roundTripAndAssert(obj, ["0", "3", "44", "a", "b", "q", "c"], "sparse-indices");

    assertEquals(parsed[0], 0, "index 0 preserved");
    assertEquals(parsed[3], 33, "index 3 preserved");
    assertEquals(parsed[44], 44, "index 44 preserved");
  })();

  // Test 3: No numeric indices (regression guard for elements=0 path)
  (function testNoIndices() {
    const obj = { a: 1, b: 2, q: 3 };
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    const parsed = roundTripAndAssert(obj, ["a", "b", "q", "c"], "no-indices");
    assertEquals(parsed.c, 7, "parsed.c should be 7");
  })();

  // Test 4: Large max index combined with small ones, mixed with named props
  (function testLargeIndex() {
    const obj = { a: 1, b: 2, q: 3 };
    obj[1000000] = 1;   // large array-index property
    obj[44] = 44;       // smaller index
    obj[0] = 0;         // smallest index
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    const parsed = roundTripAndAssert(obj, ["0", "44", "1000000", "a", "b", "q", "c"], "large-index");
    assertEquals(parsed[0], 0, "index 0 preserved");
    assertEquals(parsed[44], 44, "index 44 preserved");
    assertEquals(parsed[1000000], 1, "index 1000000 preserved");
  })();

  // Explicitly run GC again after all tests to ensure stability.
  if (typeof gc === 'function') {
    gc();
    gc();
  }

  print("OK");
})();
