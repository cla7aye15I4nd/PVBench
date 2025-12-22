// This test verifies the V8 fix for handling ICU locale creation failures
// in CreateICULocale (src/objects/intl-objects.cc). The patch changes the
// behavior to return Nothing (and thus cause a RangeError in JS) when ICU
// parsing reports a failure status (U_FAILURE), in addition to the existing
// bogus-locale check.
//
// The invalid locale tag from the PoC should now reliably cause a RangeError
// when passed to Intl.DateTimeFormat (and when provided as part of a locale
// list). The test also includes a sanity check with a valid locale to ensure
// normal behavior remains intact.

(function(){
  // Minimal assertion helpers compatible with d8.
  function assertThrows(fn, ErrorConstructor, msg) {
    var threw = false;
    try {
      fn();
    } catch (e) {
      threw = true;
      if (ErrorConstructor && !(e instanceof ErrorConstructor)) {
        throw new Error((msg || 'Wrong exception type') + ': expected ' + (ErrorConstructor.name || ErrorConstructor) + ', got ' + e);
      }
    }
    if (!threw) {
      throw new Error((msg || 'Expected exception was not raised'));
    }
  }

  function assertTypeof(value, type, msg) {
    if (typeof value !== type) {
      throw new Error((msg || 'Type assertion failed') + ': expected typeof ' + type + ', got ' + typeof value);
    }
  }

  // Invalid (ICU-rejected) BCP47 language tag from the PoC.
  var invalidTag = 'de-u-22300-true-x-true';

  // 1) Ensure the PoC case throws RangeError rather than silently accepting
  //    or crashing. This exercises the U_FAILURE(status) path added in the fix.
  assertThrows(function(){ new Intl.DateTimeFormat(invalidTag); }, RangeError,
               'DateTimeFormat should reject invalid ICU locale');

  // 2) The same invalid tag should be rejected when provided within a locale list.
  assertThrows(function(){ new Intl.DateTimeFormat([invalidTag]); }, RangeError,
               'DateTimeFormat should reject invalid ICU locale in list');

  // 3) Sanity check: a valid locale should still work and produce a string.
  var validLocale = 'de';
  var dtf = new Intl.DateTimeFormat(validLocale);
  var sample = dtf.format(new Date(0));
  assertTypeof(sample, 'string', 'DateTimeFormat.format should return a string for valid locale');

  print('OK');
})();
