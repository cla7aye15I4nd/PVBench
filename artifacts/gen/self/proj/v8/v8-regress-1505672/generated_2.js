// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix in runtime-regexp.cc where named replacement
// patterns of the form $<name> must treat names that are integer indices
// (e.g., "0", "1", "01", etc.) as invalid identifiers, i.e., as unmatched
// named captures that substitute an empty string. The patch adds a check using
// AsIntegerIndex and returns empty string for such names.

function assertEquals(expected, actual, message) {
  if (expected !== actual) {
    throw new Error((message || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
  }
}

function runBasicChecks(re, label) {
  // Sanity: named capture works.
  assertEquals('a', 'a'.replace(re, '$<a>'), label + ': named capture works');

  // Non-existent named capture => empty string.
  assertEquals('', 'a'.replace(re, '$<b>'), label + ': non-existent named capture => empty');

  // Numeric backreference still works (named capture also counts as group 1).
  assertEquals('a', 'a'.replace(re, '$1'), label + ': numeric backref $1 works');

  // Core of the regression: $<...> with integer-like names must be treated as
  // invalid identifiers -> unmatched -> empty string.
  assertEquals('', 'a'.replace(re, '$<0>'), label + ': $<0> => empty');
  assertEquals('', 'a'.replace(re, '$<1>'), label + ': $<1> => empty');
  assertEquals('', 'a'.replace(re, '$<01>'), label + ': $<01> => empty');
  assertEquals('', 'a'.replace(re, '$<123>'), label + ': $<123> => empty');

  // Mixed replacement shows that $<1> is empty while $1 is the first capture.
  assertEquals('[|a]', 'a'.replace(re, '[$<1>|$1]'), label + ': mixed replacement $<1> vs $1');
}

// Fast-path: No prototype trickery.
{
  const re = /(?<a>.)/;
  runBasicChecks(re, 'fast-path');
}

// Slow-path: Force runtime path by adding a Proxy as an own 'prototype' prop on the RegExp instance.
{
  const re = /(?<a>.)/;
  // Force slow-path.
  re.prototype = new Proxy(RegExp.prototype, {});
  runBasicChecks(re, 'slow-path');
}

print('OK');
