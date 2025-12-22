// Copyright 2023 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix for handling named capture replacements when the
// name looks like an integer index (e.g., "$<0>"). The patch ensures such
// names are treated as invalid identifiers and resolve to an unmatched capture,
// yielding the empty string, rather than accessing any capture by index.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || "Assertion failed") + ": expected " + expected + ", got " + actual);
  }
}

// Fast-path tests (no slow-path forcing)
{
  const re = /(?<a>.)/;

  // Numeric-looking names should be treated as invalid capture names.
  assertEquals('a'.replace(re, '$<0>'), '', 'numeric name 0 should be unmatched');
  assertEquals('a'.replace(re, '$<1>'), '', 'numeric name 1 should be unmatched');
  assertEquals('a'.replace(re, '$<2>'), '', 'numeric name 2 should be unmatched');

  // Valid named capture works.
  assertEquals('a'.replace(re, '$<a>'), 'a', 'valid named capture should substitute');

  // Non-existent non-numeric name should be unmatched as well.
  assertEquals('a'.replace(re, '$<b>'), '', 'unknown named capture should be unmatched');

  // Name that looks numeric but with leading zero is not an integer index per spec;
  // either way, it should not resolve to any capture and thus be empty.
  assertEquals('a'.replace(re, '$<01>'), '', 'leading-zero numeric-like name should be unmatched');
}

// Slow-path tests: force slow-path by adding a Proxy on the instance's prototype property
{
  const re = /(?<a>.)/;
  // Force slow-path per original PoC.
  re.prototype = new Proxy(RegExp.prototype, {});

  assertEquals('a'.replace(re, '$<0>'), '', 'slow path: numeric name 0 should be unmatched');
  assertEquals('a'.replace(re, '$<1>'), '', 'slow path: numeric name 1 should be unmatched');
  assertEquals('a'.replace(re, '$<a>'), 'a', 'slow path: valid named capture should substitute');
  assertEquals('a'.replace(re, '$<b>'), '', 'slow path: unknown named capture should be unmatched');
}

// Mixed numeric (positional) and named captures to ensure no cross-talk.
// $1 should substitute the first positional capture, while $<0> remains empty.
{
  const re = /(.)(?<a>.)/;
  assertEquals('ab'.replace(re, '$1|$<0>|$<a>'), 'a||b', 'ensure $<0> does not alias to any positional capture');
}

// Same mixed test on slow path
{
  const re = /(.)(?<a>.)/;
  re.prototype = new Proxy(RegExp.prototype, {});
  assertEquals('ab'.replace(re, '$1|$<0>|$<a>'), 'a||b', 'slow path: ensure $<0> remains unmatched');
}

// Global regex tests to cover repeated replacements
{
  const re = /(?<a>.)/g;
  // Replacing each char with $<0> should drop all characters (empty string).
  assertEquals('abc'.replace(re, '$<0>'), '', 'global: numeric name should be unmatched for each iteration');
  // Replacing each char with $<a> should keep the string the same.
  assertEquals('abc'.replace(re, '$<a>'), 'abc', 'global: valid named capture should substitute for each match');
}

// Global + slow-path
{
  const re = /(?<a>.)/g;
  re.prototype = new Proxy(RegExp.prototype, {});
  assertEquals('abc'.replace(re, '$<0>'), '', 'global slow: numeric name should be unmatched for each iteration');
  assertEquals('abc'.replace(re, '$<a>'), 'abc', 'global slow: valid named capture should substitute for each match');
}

print('OK');