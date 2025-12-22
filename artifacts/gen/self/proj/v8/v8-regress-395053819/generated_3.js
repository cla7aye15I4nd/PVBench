// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct handling and hashing of large numeric-looking
// property names. A recent fix changed how V8 parses and hashes potential array
// indices to avoid 32-bit truncation on 64-bit platforms and to correctly
// reject overflow cases. Previously, very large numeric strings could be
// misinterpreted as array indices and truncated to 32 bits, causing collisions
// and incorrect property lookups. This test ensures:
//  - Large numeric keys beyond the array index range are distinct and retrievable
//  - No collisions occur for keys that differ by 2**32 (would collide if truncated)
//  - Boundary behavior around kMaxArrayIndex is correct
//  - Integer-index hashing path (<= kMaxSafeIntegerUint64) works
//  - Non-index hashing path for very long numeric strings works

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(cond, message) {
    if (!cond) throw new Error(message || "Assertion failed: expected true but was false");
  }
  function assertFalse(cond, message) {
    if (cond) throw new Error(message || "Assertion failed: expected false but was true");
  }

  // 1) Original PoC scenario: set and get many large numeric keys
  (function testBulkLargeNumericKeys() {
    let o = {};
    const base = 8589933568; // > 2**32, i.e., definitely non-array-index
    for (let i = 0; i < 10000; i++) {
      o[base + i] = i;
    }
    for (let i = 0; i < 10000; i++) {
      const k = base + i;
      // Access via number
      assertEquals(o[k], i, "bulk numeric get");
      // Access via string
      assertEquals(o[String(k)], i, "bulk string get");
      // Membership check
      assertTrue((String(k)) in o, "in-operator should find property");
    }
  })();

  // 2) Ensure no truncation collision for keys separated by 2**32
  (function testNoCollisionWith2Pow32Offset() {
    let o = {};
    const base = 8589933568; // ~= 2**33 - 1024
    const offset = 2 ** 32;  // 4294967296
    const k1 = base;
    const k2 = base + offset; // Would collide if index were truncated to uint32

    o[k1] = "v1";
    o[k2] = "v2";

    assertEquals(o[k1], "v1", "k1 retrieve via number");
    assertEquals(o[String(k1)], "v1", "k1 retrieve via string");
    assertEquals(o[k2], "v2", "k2 retrieve via number");
    assertEquals(o[String(k2)], "v2", "k2 retrieve via string");

    // Cross-check: ensure values are not mixed up
    assertFalse(o[k1] === "v2", "k1 should not equal v2");
    assertFalse(o[k2] === "v1", "k2 should not equal v1");
  })();

  // 3) Boundary around kMaxArrayIndex (which is 2**32 - 2)
  //    - 4294967294 should behave as an array index name (but on plain object,
  //      semantics are still just properties; this checks consistent hashing).
  //    - 4294967295 and 4294967296 must not be treated as array indices.
  (function testArrayIndexBoundaryOnPlainObject() {
    let o = {};
    const maxArrayIndex = (2 ** 32) - 2; // 4294967294
    const n1 = maxArrayIndex;      // boundary (still an array index value)
    const n2 = maxArrayIndex + 1;  // 4294967295 (not an array index)
    const n3 = maxArrayIndex + 2;  // 4294967296 (not an array index)

    o[n1] = "a";
    o[n2] = "b";
    o[n3] = "c";

    // Verify retrievals via number and string are consistent and distinct
    assertEquals(o[n1], "a", "n1 via number");
    assertEquals(o[String(n1)], "a", "n1 via string");

    assertEquals(o[n2], "b", "n2 via number");
    assertEquals(o[String(n2)], "b", "n2 via string");

    assertEquals(o[n3], "c", "n3 via number");
    assertEquals(o[String(n3)], "c", "n3 via string");

    // Ensure no aliasing among them
    assertFalse(o[n1] === o[n2], "n1 and n2 must not alias");
    assertFalse(o[n1] === o[n3], "n1 and n3 must not alias");
    assertFalse(o[n2] === o[n3], "n2 and n3 must not alias");
  })();

  // 4) Integer index hashing path (<= kMaxSafeIntegerUint64): use Number.MAX_SAFE_INTEGER
  (function testIntegerIndexHashingPath() {
    let o = {};
    const n = Number.MAX_SAFE_INTEGER; // 9007199254740991
    const s = String(n);

    o[n] = "msi";

    assertEquals(o[n], "msi", "MAX_SAFE_INTEGER via number");
    assertEquals(o[s], "msi", "MAX_SAFE_INTEGER via string");
  })();

  // 5) Very long numeric string should take non-index hash path and still work
  (function testVeryLongNumericStringNonIndex() {
    let o = {};
    const s = "1".repeat(100); // Much longer than any index size caps
    o[s] = "long";

    assertEquals(o[s], "long", "very long numeric string retrieval");
  })();

  // 6) Leading zero numeric-like strings should not be treated as array indices
  (function testLeadingZeroNonIndex() {
    let o = {};
    o["01"] = "a";
    o["1"] = "b";

    assertEquals(o["01"], "a", "leading zero key distinctness");
    assertEquals(o["1"], "b", "non-leading zero key distinctness");
  })();

  print("OK");
})();
