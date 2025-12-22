// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test targets a bug in double-to-exponential string conversion where the
// maximum buffer size was underestimated by one character. The fix increases
// kDoubleToExponentialMaxChars by 1 (from kMaxFractionDigits + 7 to + 8),
// accounting for the leading digit before the decimal point. This test verifies
// correct formatting for edge cases near the limits (fractionDigits = 100 and
// large magnitude exponents) and that no crash or truncation occurs.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || 'Assertion failed') + ': expected ' + expected + ', got ' + actual);
  }
}

function assertTrue(cond, message) {
  if (!cond) throw new Error(message || 'Assertion failed: expected true');
}

function assertThrows(fn, ctor, message) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (ctor && !(e instanceof ctor)) {
      throw new Error((message || 'Wrong exception type') + ': ' + e);
    }
  }
  if (!threw) throw new Error((message || 'Expected exception was not raised'));
}

// Helper to validate the general shape of toExponential output without relying on
// exact mantissa digits (useful for multiple inputs). It verifies:
// - Optional leading minus sign
// - Exactly one digit before '.'
// - Exactly fracDigits digits after '.'
// - 'e' followed by sign and the expected exponent digits
// - Optional total length check
function validateExponentialString(s, {
  negative,
  exp, // integer exponent (e.g., 308 or -308)
  fracDigits,
  expectedLength,
  expectedFirstDigit // optional, e.g., '1' or '0'
}) {
  if (negative) {
    assertTrue(s[0] === '-', 'Expected leading minus sign');
    s = s.slice(1);
  } else {
    assertTrue(s[0] !== '-', 'Did not expect leading minus sign');
  }
  // Now s should be like D.F...Fe+/-E
  assertTrue(s.length >= 5, 'String too short for exponential format');
  assertTrue(s[1] === '.', 'Expected decimal point after first digit');
  if (expectedFirstDigit !== undefined) {
    assertEquals(s[0], expectedFirstDigit, 'First digit mismatch');
  }
  const epos = s.indexOf('e');
  assertTrue(epos > 1, 'Missing exponent marker e');
  // Check fraction digits count
  const actualFracDigits = epos - 2; // after D.
  assertEquals(actualFracDigits, fracDigits, 'Fraction digits count mismatch');

  // Check exponent sign and digits
  const expSign = s[epos + 1];
  assertTrue(expSign === '+' || expSign === '-', 'Exponent sign must be + or -');
  const expDigits = s.slice(epos + 2);
  assertTrue(/^[0-9]+$/.test(expDigits), 'Exponent must be digits');
  const expValue = (expSign === '-' ? -1 : 1) * parseInt(expDigits, 10);
  assertEquals(expValue, exp, 'Exponent value mismatch');

  if (expectedLength !== undefined) {
    const computedLen = (negative ? 1 : 0) + 1 + 1 + fracDigits + 1 + 1 + String(Math.abs(exp)).length;
    assertEquals(s.length + (negative ? 1 : 0), expectedLength,
                 'Reported length mismatch');
    // Also verify our computed length formula matches provided expectedLength.
    assertEquals(computedLen, expectedLength, 'Computed length mismatch');
  }
}

// Core regression: extremely large magnitude with maximum fraction digits.
// This was the minimal reproducer for the buffer size underestimate.
const neg = (-1.777435286647996e+308).toExponential(100);
assertEquals(
  neg,
  '-1.7774352866479959137616855978032470542052397040225939205262400173577628014729345083522107643115812351e+308'
);
validateExponentialString(neg, { negative: true, exp: 308, fracDigits: 100, expectedLength: 108, expectedFirstDigit: '1' });

// The corresponding positive value should have the same formatting sans the minus.
const pos = (1.777435286647996e+308).toExponential(100);
validateExponentialString(pos, { negative: false, exp: 308, fracDigits: 100, expectedLength: 107, expectedFirstDigit: '1' });

// Check a very small magnitude with a negative exponent to ensure coverage of the
// 'e-' path and three-digit exponent width.
const tinyPos = (1.234e-308).toExponential(100);
validateExponentialString(tinyPos, { negative: false, exp: -308, fracDigits: 100, expectedFirstDigit: '1' });
const tinyNeg = (-5.678e-308).toExponential(100);
validateExponentialString(tinyNeg, { negative: true, exp: -308, fracDigits: 100, expectedFirstDigit: '5' });

// Out-of-range fractionDigits should still throw RangeError.
assertThrows(() => (1).toExponential(-1), RangeError);
assertThrows(() => (1).toExponential(101), RangeError);

// Non-finite values should remain unaffected by exponential formatting limits.
assertEquals((NaN).toExponential(), 'NaN');
assertEquals((Infinity).toExponential(), 'Infinity');
assertEquals((-Infinity).toExponential(), '-Infinity');

print('OK');
