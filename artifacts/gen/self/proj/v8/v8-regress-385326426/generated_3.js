// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies the fix for the buffer size used by
// Number.prototype.toExponential when formatting with large fraction digits.
//
// Patch summary (conversions.h):
//   kDoubleToExponentialMaxChars increased from kMaxFractionDigits + 7 to +8
//   to account for the one digit before the decimal point. Without this extra
//   space, formatting values like -1.7774e+308 with 100 fraction digits could
//   overflow/truncate and crash.
//
// The test asserts the exact expected string for the original regression case
// and also exercises several additional edge cases to ensure no crashes and
// that the produced strings have the correct shape at the precision boundary.

function assertEquals(actual, expected, message) {
  if (actual !== expected) {
    throw new Error((message || 'Assertion failed') + ': expected\n' + expected + '\n' + 'got\n' + actual);
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
}

// Validate the general shape of toExponential output with a given number of
// fraction digits, without asserting all digits (which may vary due to
// rounding and binary <-> decimal conversions). This primarily checks for
// correct buffer sizing under the fixed logic.
function assertExponentialShape(str, fractionDigits, opts) {
  const m = str.match(/^(-?)(\d)\.(\d+)e([+-])(\d+)$/);
  assert(m !== null, 'Output does not match exponential format: ' + str);
  const sign = m[1];
  const intDigit = m[2];
  const frac = m[3];
  const expSign = m[4];
  const expDigits = m[5];

  assert(intDigit >= '0' && intDigit <= '9', 'Invalid leading digit: ' + intDigit);
  assert(frac.length === fractionDigits, 'Unexpected fraction length: ' + frac.length + ' (expected ' + fractionDigits + ')');

  if (opts) {
    if (Object.prototype.hasOwnProperty.call(opts, 'negative')) {
      assert((sign === '-') === !!opts.negative, 'Unexpected sign: ' + sign);
    }
    if (Object.prototype.hasOwnProperty.call(opts, 'exp')) {
      const expectedExp = String(Math.abs(opts.exp));
      assert(expDigits === expectedExp, 'Unexpected exponent digits: ' + expDigits + ' (expected ' + expectedExp + ')');
      const expectedExpSign = opts.exp >= 0 ? '+' : '-';
      assert(expSign === expectedExpSign, 'Unexpected exponent sign: ' + expSign + ' (expected ' + expectedExpSign + ')');
    }
    if (Object.prototype.hasOwnProperty.call(opts, 'expSign')) {
      assert(expSign === opts.expSign, 'Unexpected exponent sign: ' + expSign + ' (expected ' + opts.expSign + ')');
    }
  }
}

// 1) Regression case from the PoC: ensure exact output and no crash.
// This specifically targets the buffer sizing bug when using 100 fraction digits
// with a very large exponent magnitude.
assertEquals(
  (-1.777435286647996e+308).toExponential(100),
  '-1.7774352866479959137616855978032470542052397040225939205262400173577628014729345083522107643115812351e+308',
  'Regression: toExponential(100) formatting for large negative number'
);

// 2) Simple exact cases that are stable across engines (exactly representable
// binary values) at the precision boundary and just below it.
(function testSimpleExactValues() {
  const z100 = '0.' + '0'.repeat(100) + 'e+0';
  const p100 = '1.' + '0'.repeat(100) + 'e+0';
  const n100 = '-1.' + '0'.repeat(100) + 'e+0';

  const z99 = '0.' + '0'.repeat(99) + 'e+0';
  const p99 = '1.' + '0'.repeat(99) + 'e+0';
  const n99 = '-1.' + '0'.repeat(99) + 'e+0';

  assertEquals((0).toExponential(100), z100, '0 @ 100 digits');
  assertEquals((1).toExponential(100), p100, '1 @ 100 digits');
  assertEquals((-1).toExponential(100), n100, '-1 @ 100 digits');

  assertEquals((0).toExponential(99), z99, '0 @ 99 digits');
  assertEquals((1).toExponential(99), p99, '1 @ 99 digits');
  assertEquals((-1).toExponential(99), n99, '-1 @ 99 digits');
})();

// 3) Shape checks around extreme finite magnitudes with 100 fraction digits
// to ensure no crashes and the exponent/sign fields are correct.
(function testExtremeMagnitudesShape() {
  const sMax = Number.MAX_VALUE.toExponential(100);
  // Expect exponent +308 for MAX_VALUE, three digits and positive sign.
  assertExponentialShape(sMax, 100, { exp: 308 });

  const sMin = Number.MIN_VALUE.toExponential(100);
  // Expect exponent -324 for MIN_VALUE (smallest subnormal), three digits and negative sign.
  assertExponentialShape(sMin, 100, { exp: -324 });
})();

// 4) Additional shape checks at the precision boundary (100) for some random
// finite values to ensure general robustness.
(function testGeneralShapeNoCrash() {
  const values = [
    42,
    -42,
    3.141592653589793,
    -2.718281828459045,
    6.02214076e23,
    -9.10938356e-31
  ];
  for (const v of values) {
    const s = Number(v).toExponential(100);
    // Only assert shape and requested fraction digit count.
    assertExponentialShape(s, 100);
  }
})();

print('OK');
