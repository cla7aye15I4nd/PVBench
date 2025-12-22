// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flags: --expose-gc --trace-gc-object-stats

// This test validates a fix in JsonParser::BuildJsonObject where
// SetInitialNumberOfElements was incorrectly using the total property count
// instead of the count of element-indexed properties (cont.elements).
// The bug could lead to inconsistencies in internal accounting for objects
// that have a mix of named properties and element-indexed properties when
// created via JSON.parse, which was observable/crashing under
// --trace-gc-object-stats during GC.
//
// The test performs multiple round-trips (JSON.stringify + JSON.parse) across
// objects that mix named properties, getters, and a variety of element indices.
// After each parse, we force GC to exercise the object statistics paths, and we
// assert that the JSON representations remain stable. If the bug regresses, the
// engine may crash during GC with --trace-gc-object-stats, or object behavior
// may be inconsistent.

(function() {
  function assertEquals(actual, expected, message) {
    if (actual !== expected) {
      throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
    }
  }

  function assertTrue(value, message) {
    if (!value) throw new Error(message || "Assertion failed: expected true but got " + value);
  }

  // Helper that stringifies, parses, triggers GC, and re-stringifies.
  function roundTripAndCheck(obj, msg) {
    var s1 = JSON.stringify(obj);
    var parsed = JSON.parse(s1);
    // Exercise GC object stats on freshly parsed objects.
    if (typeof gc === 'function') gc();
    var s2 = JSON.stringify(parsed);
    assertEquals(s2, s1, msg || "Round-trip JSON mismatch");
    return parsed;
  }

  // Test 1: Original PoC scenario
  // Object with named props, one numeric index, and an enumerable getter.
  (function testOriginalPoC() {
    var obj = { a: 1, b: 2, q: 3 };
    obj[44] = 44; // element-indexed property
    Object.defineProperty(obj, "c", { get: () => 7, enumerable: true });

    // Round-trip through JSON and ensure stability.
    var parsed = roundTripAndCheck(obj, "PoC round-trip should preserve JSON");

    // Sanity checks on parsed object values (getter should be materialized to value 7).
    assertEquals(parsed.a, 1);
    assertEquals(parsed.b, 2);
    assertEquals(parsed.q, 3);
    assertEquals(parsed.c, 7);
    assertEquals(parsed[44], 44);
  })();

  // Test 2: Many named properties + sparse element indices.
  (function testManyNamedFewElements() {
    var obj = {};
    // Add many named properties.
    for (var i = 0; i < 100; i++) {
      obj["p" + i] = i;
    }
    // Add a few element-indexed properties (sparse and out-of-order).
    obj[0] = 0;
    obj[5] = 5;
    obj[1234] = 1234;

    var parsed = roundTripAndCheck(obj, "Many-named/few-elements round-trip");
    // Spot-check a few values.
    assertEquals(parsed.p0, 0);
    assertEquals(parsed.p99, 99);
    assertEquals(parsed[0], 0);
    assertEquals(parsed[5], 5);
    assertEquals(parsed[1234], 1234);
  })();

  // Test 3: Only elements (all numeric indices) to exercise element dictionaries
  // with higher max_index.
  (function testOnlyElementsHighIndex() {
    var obj = {};
    obj[1] = 1;
    obj[20] = 20;
    obj[255] = 255;
    obj[4096] = 4096;

    var parsed = roundTripAndCheck(obj, "Only-elements round-trip");
    assertEquals(parsed[1], 1);
    assertEquals(parsed[20], 20);
    assertEquals(parsed[255], 255);
    assertEquals(parsed[4096], 4096);
  })();

  // Test 4: Only named properties (no elements). This ensures that when
  // cont.elements == 0, the object is still well-formed and GC stats work.
  (function testOnlyNamed() {
    var obj = { a: 1, b: 2 };
    Object.defineProperty(obj, "c", { value: 3, enumerable: true });
    var parsed = roundTripAndCheck(obj, "Only-named round-trip");
    assertEquals(parsed.a, 1);
    assertEquals(parsed.b, 2);
    assertEquals(parsed.c, 3);
  })();

  // Test 5: Numeric-looking keys that are not valid array indices remain named
  // properties, alongside true element indices. This ensures cont.elements is
  // accounted correctly when mixed with such keys.
  (function testNonArrayIndexNumericKeys() {
    // Keys like "-1" and "4294967295" (2^32-1) are not valid array indices.
    var obj = { "-1": 1, "4294967295": 2, normal: 3 };
    obj[5] = 5; // true element index

    var parsed = roundTripAndCheck(obj, "Non-array-index numeric keys round-trip");
    assertEquals(parsed["-1"], 1);
    assertEquals(parsed["4294967295"], 2);
    assertEquals(parsed.normal, 3);
    assertEquals(parsed[5], 5);
  })();

  // Test 6: Multiple mixed objects to increase coverage and exercise GC stats
  // multiple times in succession.
  (function testMultipleMixedObjects() {
    var cases = [];
    for (var i = 0; i < 5; i++) {
      var o = { a: i, b: i + 1 };
      // Add a few named props per case.
      for (var j = 0; j < 10; j++) {
        o["k" + j] = j + i;
      }
      // Add a couple of element indices.
      o[i] = i;
      o[i * 10 + 7] = i * 10 + 7;
      cases.push(o);
    }
    for (var k = 0; k < cases.length; k++) {
      roundTripAndCheck(cases[k], "Mixed case " + k);
    }
  })();

  if (typeof gc === 'function') gc();
  print("OK");
})();
