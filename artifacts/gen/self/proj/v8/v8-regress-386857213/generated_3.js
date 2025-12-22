// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// This test verifies the fix in GetOffsetTimeZone (js-date-time-format.cc)
// where encountering a trailing ':' after the hour in an offset time zone
// string (e.g., "+09:") must be treated as an error. Previously, the parser
// advanced past ':' and could read past the end of input. The patch adds an
// explicit end-of-input check and causes Intl.DateTimeFormat to reject such
// inputs with a RangeError.

function assertThrows(fn, errorCtor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorCtor && !(e instanceof errorCtor)) {
      throw new Error((message || "Wrong exception type") + ": expected " + (errorCtor && errorCtor.name) + ", got " + e);
    }
  }
  if (!threw) {
    throw new Error((message || "Expected exception was not raised"));
  }
}

function assertDoesNotThrow(fn, message) {
  try {
    fn();
  } catch (e) {
    throw new Error((message || "Unexpected exception") + ": " + e);
  }
}

// Core regression: time zone offset strings ending with a trailing ':' should
// be rejected with RangeError.
const trailingColonInvalid = [
  "+09:",
  "+00:",
  "-00:",
  "+14:", // upper-bound hour with trailing ':'
  "-12:", // lower-bound hour with trailing ':'
];

for (const tz of trailingColonInvalid) {
  assertThrows(
    () => new Intl.DateTimeFormat("en", { timeZone: tz }),
    RangeError,
    `Expected RangeError for invalid timeZone '${tz}'`
  );
}

// Sanity check: a clearly valid IANA time zone should not throw to ensure the
// Intl infrastructure is working in the test environment.
assertDoesNotThrow(() => new Intl.DateTimeFormat("en", { timeZone: "UTC" }));

print("OK");
