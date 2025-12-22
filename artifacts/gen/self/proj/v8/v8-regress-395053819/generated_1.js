// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies correct handling and hashing of large numeric property
// names, especially values beyond the 32-bit array index range. It is based on
// a bug where parsing large numeric strings for hashing could mis-handle
// overflow during array-index detection, leading to inconsistent hashing and
// wrong lookups.
//
// The patch switches the array-index parsing to use a 64-bit accumulator on
// 64-bit hosts and fixes overflow handling on 32-bit hosts, ensuring:
//  - Large numeric keys above kMaxArrayIndex (2^32-2) are treated as
//    integer-index strings (or non-index where applicable), not misparsed.
//  - Hashing is consistent between property set and get using number vs string
//    forms of the same key.

(function() {
  function assertEquals(actual, expected, msg) {
    if (actual !== expected) {
      throw new Error((msg || "assertEquals failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(cond, msg) {
    if (!cond) throw new Error(msg || "assertTrue failed");
  }

  // 1) Original PoC scenario: many large numeric keys well above 32-bit range.
  // These should round-trip correctly without collisions or lookup failures.
  {
    let o = {};
    const base = 8589933568;  // ~2^33, 10 digits, > kMaxArrayIndex.
    for (let i = 0; i < 10000; i++) {
      o[base + i] = i;
    }
    for (let i = 0; i < 10000; i++) {
      const got = o[base + i];
      assertEquals(got, i, "PoC large index round-trip");
    }
  }

  // 2) Boundary around kMaxArrayIndex (UInt32Max - 1 = 4294967294).
  // We cross the array-index boundary and ensure consistent behavior on both
  // sides of the limit.
  {
    let o = {};
    const start = 4294967290; // Approaches and crosses the array-index limit.
    for (let i = 0; i < 10; i++) {
      const key = start + i; // 4294967290..4294967299 (includes 4294967294/5)
      o[key] = "v" + i;
    }
    for (let i = 0; i < 10; i++) {
      const key = start + i;
      assertEquals(o[key], "v" + i, "Boundary retrieval @" + key);
      // Also check numeric vs string access equivalence for exact-representable keys.
      const s = String(key);
      assertEquals(o[s], "v" + i, "String lookup mismatch @" + s);
    }
  }

  // 3) Mixed numeric and string set/gets for large indices (integer-index path).
  // These keys must behave identically regardless of number or string form.
  {
    let o = {};
    const keys = [
      4294967294,        // max array index
      4294967295,        // just above array index range
      4294967296,        // 2^32
      8589933568,        // ~2^33
      8589933999,
      9007199254740990,  // max safe integer - 1
      9007199254740991   // max safe integer
    ];

    // Set using string form, read via number and string.
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const s = String(k);
      const val = "S" + i;
      o[s] = val;
      assertEquals(o[s], val, "string->string get failed @" + s);
      assertEquals(o[k], val, "string->number get failed @" + s);
    }

    // Overwrite using number form, read via number and string.
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const s = String(k);
      const val = "N" + i;
      o[k] = val;
      assertEquals(o[k], val, "number->number get failed @" + k);
      assertEquals(o[s], val, "number->string get failed @" + s);
    }
  }

  // 4) Ensure that leading-zero strings are NOT considered the same as the
  // canonical numeric form. This also touches the non-index hashing path.
  {
    let o = {};
    const num = 8589933568; // Large 10-digit number (> array index)
    const s = String(num);
    const withZeros = "000" + s; // Leading zeros => different property key

    o[num] = "numeric";
    o[withZeros] = "withZeros";

    assertEquals(o[num], "numeric", "numeric key value changed unexpectedly");
    assertEquals(o[s], "numeric", "string of numeric key mismatch");
    assertEquals(o[withZeros], "withZeros", "leading-zero string key mismatch");
    // Make sure they are distinct properties
    assertTrue(o[num] !== o[withZeros], "distinct keys must hold distinct values");
  }

  // 5) Dense verification: a small cluster of consecutive large keys to ensure
  // there is no accidental collision in hashing near the boundary and far away.
  {
    let o = {};
    const clusters = [
      { base: 4294967288, count: 16 }, // spans below and above 4294967294
      { base: 8589933500, count: 64 }  // >> array index max
    ];
    for (const {base, count} of clusters) {
      for (let i = 0; i < count; i++) {
        o[base + i] = base ^ i; // unique simple pattern
      }
      for (let i = 0; i < count; i++) {
        const key = base + i;
        assertEquals(o[key], (base ^ i), "cluster mismatch @" + key);
      }
    }
  }

  print("OK");
})();
