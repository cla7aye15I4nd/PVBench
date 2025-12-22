// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix for handling $<name> replacements where `name`
// is a string that represents an integer index (e.g., "0", "1").
// After the patch, such names are not treated as valid capture names and
// should be considered unmatched, resulting in an empty string replacement.
// The test also checks that valid named captures still work and that numeric
// backreferences using $1, $2, ... remain unaffected.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// Helper to force the slow path for RegExp replacement, as in the PoC.
function forceSlowPath(re) {
  re.prototype = new Proxy(RegExp.prototype, {});
  return re;
}

// Base regex with a named capture.
const re = forceSlowPath(/(?<a>.)/);

// 1) Core regression: integer-like capture name "$<0>" should be treated as unmatched.
assertEquals('a'.replace(re, '$<0>'), '', 'Numeric-like named capture should be unmatched');

// 2) Control: valid named capture works.
assertEquals('a'.replace(re, '$<a>'), 'a', 'Valid named capture should substitute correctly');

// 3) Ensure numeric backreference via $1 still works (this is separate from $<...> logic).
assertEquals('a'.replace(re, '$1'), 'a', 'Numeric backreference $1 should still work');
// And ensure $<1> does NOT alias to $1.
assertEquals('a'.replace(re, '$<1>'), '', '$<1> must not alias numeric backreference');

// 4) Replacement on a longer string (non-global): only first match replaced; $<0> yields empty string.
assertEquals('abc'.replace(re, '$<0>'), 'bc', 'First match replaced with empty string');

// 5) Global mode: every character match replaced; all become empty.
const reGlobal = forceSlowPath(/(?<a>.)/g);
assertEquals('abc'.replace(reGlobal, '$<0>'), '', 'All matches replaced with empty string globally');

// 6) Leading zeros: "$<01>" is not a valid capture name and should be unmatched.
assertEquals('a'.replace(re, '$<01>'), '', 'Leading zero numeric-like name should be unmatched');

// 7) Large integer-like names should also be treated as unmatched and yield empty string.
assertEquals('a'.replace(re, '$<9999999999999>'), '', 'Large integer-like name should be unmatched');

// 8) Ensure other valid named capture names still work as expected.
const reNamed = forceSlowPath(/(?<abc>.)/);
assertEquals('x'.replace(reNamed, '$<abc>'), 'x', 'Other valid named capture should substitute correctly');
// And again confirm numeric-like names are unmatched on this regex too.
assertEquals('x'.replace(reNamed, '$<0>'), '', 'Numeric-like name remains unmatched regardless of group names');

print('OK');
