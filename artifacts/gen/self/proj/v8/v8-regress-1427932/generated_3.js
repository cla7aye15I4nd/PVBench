// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies that invalid BCP47 language tags that cause ICU to
// report a failure are handled correctly by V8 and result in a RangeError
// instead of proceeding with a bogus locale or crashing. The patch added
// a check for U_FAILURE(status) when creating ICU locales.

// Helper assertions
function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

function assertThrows(fn, errorConstructor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error((message || "Wrong exception type") + ": expected " + (errorConstructor && errorConstructor.name) + ", got " + e);
    }
  }
  if (!threw) throw new Error((message || "Expected exception was not raised"));
}

// Original PoC scenario: this invalid tag previously triggered an ICU failure
// that V8 did not check, potentially leading to incorrect behavior. After the
// fix, it should throw a RangeError.
assertThrows(() => Intl.DateTimeFormat("de-u-22300-true-x-true"), RangeError,
             "Invalid BCP47 tag should throw RangeError");

// Also test when the invalid tag appears inside a locales list. Per ECMA-402,
// any invalid element in the list should cause a RangeError.
assertThrows(() => new Intl.DateTimeFormat(["de-u-22300-true-x-true", "en-US"]), RangeError,
             "Invalid tag in locales list should throw RangeError");

// Sanity check: a valid locale should not throw and should produce a working formatter.
let dtf = new Intl.DateTimeFormat("de");
let sample = dtf.format(new Date(0));
assertEquals(typeof sample, "string", "Formatting should return a string");

// Repeat the invalid-tag checks across a couple of Intl constructors that
// consult ICU locale creation to ensure the fix is applied consistently.
// Keep the surface minimal to avoid environmental differences.
assertThrows(() => Intl.NumberFormat("de-u-22300-true-x-true"), RangeError,
             "NumberFormat should also reject invalid BCP47 tags");
assertThrows(() => new Intl.NumberFormat(["de-u-22300-true-x-true", "en"]), RangeError,
             "NumberFormat list with invalid entry should throw");

// Valid NumberFormat should work.
let nf = new Intl.NumberFormat("de");
let formatted = nf.format(1234.5);
assertEquals(typeof formatted, "string", "Number formatting should return a string");

// Ensure calling the constructors without locales still works.
new Intl.DateTimeFormat();
new Intl.NumberFormat();

print("OK");