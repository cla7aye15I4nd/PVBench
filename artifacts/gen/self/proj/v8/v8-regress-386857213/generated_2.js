// Copyright 2025 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// This test validates the fix in GetOffsetTimeZone parsing for Intl.DateTimeFormat
// where an offset like "+09:" (colon with no minutes) must be rejected with a
// RangeError instead of being accepted or causing out-of-bounds access.

function assertThrows(fn, ctor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (ctor && !(e instanceof ctor)) {
      throw new Error((message || "Wrong exception type") + ": expected " + (ctor && ctor.name) + ", got " + e);
    }
  }
  if (!threw) throw new Error((message || "Expected exception was not thrown"));
}

// Core regression: timeZone with trailing ':' must throw RangeError.
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+09:" }), RangeError, "'+09:' should be rejected");

// Additional edge cases for the same condition (colon present but no minutes).
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+00:" }), RangeError, "'+00:' should be rejected");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "-00:" }), RangeError, "'-00:' should be rejected");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+23:" }), RangeError, "'+23:' should be rejected");

// Closely-related malformed minute fields around the colon: only one minute digit present.
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "+09:6" }), RangeError, "Single-minute-digit '+09:6' should be rejected");
assertThrows(() => new Intl.DateTimeFormat("en", { timeZone: "-12:3" }), RangeError, "Single-minute-digit '-12:3' should be rejected");

print("OK");
