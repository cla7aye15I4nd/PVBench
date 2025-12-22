// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix for the exponential conversion buffer sizing.
// Patch increased kDoubleToExponentialMaxChars by 1 to leave room for:
// one digit before '.', optional minus sign, '.', 'e', exponent sign, and a
// three-digit exponent, plus up to kMaxFractionDigits fractional digits.
// The previous size was off by one, which could lead to truncation or crashes
// when formatting numbers with 100 fractional digits (the maximum) in
// toExponential.

if (typeof print === 'undefined') { function print(x) { console.log(x); } }

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
  }
}

function assertTrue(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

// Helper to validate the format of Number.prototype.toExponential output.
function checkExponentialStringFormat(s, options) {
  var fractionDigits = options.fractionDigits;
  var expectSign = options.expectSign; // optional boolean
  var expectedExp = options.expectedExp; // optional integer

  assertTrue(typeof s === 'string', 'Result must be a string');
  assertTrue(s.length > 0, 'Empty string');

  var hasMinus = (s[0] === '-');
  if (expectSign !== undefined) assertEquals(hasMinus, expectSign, 'Unexpected sign');

  var pos = hasMinus ? 1 : 0;
  var first = s[pos];
  assertTrue(first >= '0' && first <= '9', 'First significand char must be a digit');
  pos++;

  if (fractionDigits > 0) {
    assertEquals(s[pos], '.', 'Missing decimal point for fractionDigits > 0');
    pos++;
    var frac = s.slice(pos, pos + fractionDigits);
    assertEquals(frac.length, fractionDigits, 'Wrong fractional length');
    assertTrue(/^[0-9]+$/.test(frac), 'Fractional part must be digits');
    pos += fractionDigits;
  } else {
    // For fractionDigits === 0 there must be no decimal point.
    assertTrue(s[pos] !== '.', 'Unexpected decimal point for fractionDigits === 0');
  }

  assertEquals(s[pos], 'e', "Missing 'e'");
  pos++;
  var expSignChar = s[pos];
  assertTrue(expSignChar === '+' || expSignChar === '-', 'Bad exponent sign');
  pos++;
  var expDigitsStr = s.slice(pos);
  assertTrue(/^[0-9]+$/.test(expDigitsStr), 'Bad exponent digits');
  assertTrue(expDigitsStr.length >= 1 && expDigitsStr.length <= 3, 'Exponent digits length should be 1..3');

  if (expectedExp !== undefined) {
    var expValue = parseInt(expDigitsStr, 10);
    if (expSignChar === '-') expValue = -expValue;
    assertEquals(expValue, expectedExp, 'Unexpected exponent value');
  }

  // Check the total length matches the exact expected length for this case.
  var expectedLen = (hasMinus ? 1 : 0) + 1 + (fractionDigits > 0 ? (1 + fractionDigits) : 0) + 1 + 1 + expDigitsStr.length;
  assertEquals(s.length, expectedLen, 'Unexpected total length');
}

// 1) Regression test: previously could overflow for 100 fractional digits.
// The following exact value and precision is near the upper exponent bound (308)
// and uses the maximum allowed fraction digits (100).
var expected = '-1.7774352866479959137616855978032470542052397040225939205262400173577628014729345083522107643115812351e+308';
var s1 = (-1.777435286647996e+308).toExponential(100);
assertEquals(s1, expected, 'Exact string mismatch for regression case');
// Also confirm structural properties and length at the boundary (108 chars for negative with 100 digits and 3-digit exponent).
checkExponentialStringFormat(s1, { fractionDigits: 100, expectSign: true, expectedExp: 308 });
assertEquals(s1.length, 108, 'Boundary length check failed');

// 2) Positive largest finite number: should not crash and formatting should be correct.
var s2 = Number.MAX_VALUE.toExponential(100);
checkExponentialStringFormat(s2, { fractionDigits: 100, expectSign: false, expectedExp: 308 });
assertTrue(s2.endsWith('e+308'), 'MAX_VALUE should have exponent +308');

// 3) Smallest magnitude denormal (negative): ensure 3-digit negative exponent and proper length.
var s3 = (-Number.MIN_VALUE).toExponential(100);
checkExponentialStringFormat(s3, { fractionDigits: 100, expectSign: true, expectedExp: -324 });
assertTrue(s3.endsWith('e-324'), 'MIN_VALUE should have exponent -324');

// 4) Two-digit exponent case (to ensure general correctness across exponent lengths).
var s4 = (1.23e12).toExponential(100);
checkExponentialStringFormat(s4, { fractionDigits: 100, expectSign: false, expectedExp: 12 });

// 5) Zero fractional digits: no decimal point should be present, still within bounds.
var s5 = (-Number.MAX_VALUE).toExponential(0);
checkExponentialStringFormat(s5, { fractionDigits: 0, expectSign: true, expectedExp: 308 });
assertTrue(s5.indexOf('.') === -1, 'No decimal point expected for fractionDigits === 0');

print('OK');
