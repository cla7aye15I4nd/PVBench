// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --expose-gc --trace-gc-object-stats

// This test verifies the fix in json-parser.cc where the initial number of
// elements for objects constructed by JSON.parse is set from the parsed
// continuation's `elements` count instead of the total property `length`.
// The bug could lead to incorrect elements metadata, which in turn could
// surface as crashes or accounting issues during GC object stats collection.
// We stress JSON.parse on objects with a mix of string-named properties and
// array-index-like keys (including very large indices), then trigger GC and
// assert the JSON round-trip equality and some semantic properties.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }
  function assertTrue(v, message) {
    if (!v) throw new Error(message || "Assertion failed");
  }

  function roundTripJSONAndAssert(obj, message) {
    // JSON.stringify should exercise property enumeration order rules:
    // - Integer index properties in ascending order
    // - Then string keys in insertion order
    // Accessor properties' getters are invoked to obtain values.
    var s1 = JSON.stringify(obj);
    var parsed = JSON.parse(s1);
    // Force GC stats collection paths in between to exercise the accounting.
    if (typeof gc === 'function') gc();
    var s2 = JSON.stringify(parsed);
    assertEquals(s2, s1, (message || "") + " JSON round-trip mismatch");
    return { parsed: parsed, json: s1 };
  }

  // 1) Original PoC scenario: few string keys, one numeric element, and an
  //    enumerable accessor property that returns a value when stringified.
  (function testOriginalPoC() {
    var obj = { a: 1, b: 2, q: 3 };
    obj[44] = 44;  // Single numeric element key distinct from named keys.
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    var res = roundTripJSONAndAssert(obj, "PoC");
    var parsed = res.parsed;

    // The accessor should have been materialized as a data property in the
    // parsed result with the getter's value.
    var desc = Object.getOwnPropertyDescriptor(parsed, 'c');
    assertTrue(!!desc && desc.enumerable === true && !('get' in desc),
               "Parsed property 'c' should be a data property");
    assertEquals(parsed.c, 7, "Parsed accessor value mismatch");

    // The numeric key should be preserved as a string key in the parsed result.
    assertEquals(parsed["44"], 44, "Numeric key 44 should be preserved");

    if (typeof gc === 'function') gc();
  })();

  // 2) Many string-named properties but only one numeric element key to make
  //    cont.elements << length. This stresses the accounting that previously
  //    used the total length instead of the number of element keys.
  (function testManyNamedFewElements() {
    var o = {};
    for (var i = 0; i < 50; i++) {
      o["k" + i] = i;
    }
    o[123] = 999;  // Only one element key.
    Object.defineProperty(o, "acc", { get: () => 5, enumerable: true });
    var res = roundTripJSONAndAssert(o, "ManyNamedFewElements");
    var p = res.parsed;
    assertEquals(p["123"], 999, "Numeric key 123 should be preserved");
    assertEquals(p.acc, 5, "Accessor value should be preserved in parsed data");
    if (typeof gc === 'function') gc();
  })();

  // 3) Multiple numeric-like keys, including very large array index to stress
  //    cont.max_index handling and dictionary elements. Also mix in some
  //    string-named properties to ensure elements != length.
  (function testSparseLargeIndices() {
    var o = { a: 1, z: 2 };
    var big = 4294967294; // 2^32 - 2, still a valid array index.
    var keys = [1, 7, 1000, 65536, big];
    for (var i = 0; i < keys.length; i++) {
      o[keys[i]] = keys[i] + 1;
    }
    Object.defineProperty(o, "getv", { get: () => 42, enumerable: true });

    var res = roundTripJSONAndAssert(o, "SparseLargeIndices");
    var p = res.parsed;

    for (var i = 0; i < keys.length; i++) {
      var k = String(keys[i]);
      assertEquals(p[k], keys[i] + 1, "Numeric key " + k + " should be preserved");
    }
    assertEquals(p.getv, 42, "Accessor value should be preserved in parsed data");
    if (typeof gc === 'function') gc();
  })();

  // 4) Keys that look numeric but are out of array-index range should be
  //    treated as string-named properties by the parser (elements count zero).
  //    This stresses the opposite edge: elements == 0, length > 0.
  (function testNonIndexNumericStrings() {
    var o = {};
    // Not an array index: 2^32 - 1
    var notIndex = 4294967295;
    // Also include a negative-looking key via string form.
    Object.defineProperty(o, String(notIndex), { value: 1, enumerable: true, configurable: true, writable: true });
    Object.defineProperty(o, "-1", { value: 2, enumerable: true, configurable: true, writable: true });
    o["name"] = "x";

    var res = roundTripJSONAndAssert(o, "NonIndexNumericStrings");
    var p = res.parsed;
    assertEquals(p[String(notIndex)], 1, "Non-index numeric-like key should be preserved as string");
    assertEquals(p["-1"], 2, "Negative-like key should be preserved as string");
    assertEquals(p["name"], "x", "Named key preserved");
    if (typeof gc === 'function') gc();
  })();

  // 5) Ensure non-enumerable properties are not included in JSON, and parsing
  //    therefore doesn't try to account them as elements either.
  (function testNonEnumerableIgnored() {
    var o = { a: 1 };
    Object.defineProperty(o, "hidden", { value: 99, enumerable: false });
    o[5] = 5;

    var s1 = JSON.stringify(o);
    assertTrue(s1.indexOf('hidden') === -1, "Non-enumerable property should be omitted in JSON.stringify");
    var parsed = JSON.parse(s1);
    if (typeof gc === 'function') gc();
    var s2 = JSON.stringify(parsed);
    assertEquals(s2, s1, "Round-trip with non-enumerable omitted");
    assertEquals(parsed["5"], 5, "Numeric key 5 should be preserved");
  })();

  if (typeof gc === 'function') gc();
  print("OK");
})();
