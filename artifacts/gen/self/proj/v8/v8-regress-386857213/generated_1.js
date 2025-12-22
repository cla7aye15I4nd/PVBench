// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// This test verifies the fix for parsing offset time zones in
// Intl.DateTimeFormat's timeZone option. The patch adds an early error when a
// trailing ':' appears with no following minute digits (e.g., "+09:"). Such
// inputs must throw a RangeError.

function assertThrows(fn, errorConstructor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error((message ? message + ": " : "") + "Wrong exception type: " + e);
    }
  }
  if (!threw) {
    throw new Error((message || "Assertion failed") + ": Expected exception was not raised");
  }
}

// Original PoC: trailing ':' without minutes must be rejected.
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+09:" }), RangeError, "+09: should throw RangeError");

// Additional edge cases around the same parsing point: various hour values and signs
// ending with a trailing ':' must also be rejected.
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "-00:" }), RangeError, "-00: should throw RangeError");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+00:" }), RangeError, "+00: should throw RangeError");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "-12:" }), RangeError, "-12: should throw RangeError");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+23:" }), RangeError, "+23: should throw RangeError");

print("OK");
