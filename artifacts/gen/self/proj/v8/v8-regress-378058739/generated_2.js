// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test is derived from a PoC that previously could crash V8's parser.
// Patch summary:
//   In ParserBase::UseThis(), the early return to skip marking the receiver
//   variable during reparse now checks the closure scope's is_reparsed() flag
//   instead of the current scope's flag. This matters when a `this` expression
//   appears inside a non-closure scope (e.g., class/computed property scope)
//   while the enclosing closure scope (e.g., an outer function) is being
//   reparsed. The fix prevents incorrect marking of the receiver variable and
//   eliminates a potential crash during reparse.
//
// Test strategy:
//   - Run the original PoC and assert it throws (but does not crash).
//   - Create lazily compiled functions (to ensure preparse -> full parse) that
//     include `this` inside complex class/computed-property contexts similar to
//     the PoC. Execute them to force reparse and evaluation, asserting they
//     throw (without crashing), both in sloppy and strict modes, and for static
//     and instance field initializers. Execute each twice to cover repeated
//     reparsing/compilation paths.
//
// If the test completes without throwing internally, print "OK".

function assertThrows(fn, msg) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
  }
  if (!threw) {
    throw new Error((msg || "Expected function to throw") + " but it did not");
  }
}

// ------------------------ Original PoC ------------------------
function var_5(){
    let var_1;
    class var_3 {
        static '' = new class {
            '' = var_1.trigger_error();
            [class {
                [this];
            }];
        };
    }
}

// The PoC should throw (TypeError due to accessing property on undefined), but
// must not crash.
assertThrows(var_5, "PoC should throw but not crash");

// ------------------------ Additional cases ------------------------
// The following functions are defined so that they are lazily parsed first
// (preparse), and fully parsed on first call (reparse). They embed `this` inside
// nested class computed property names within field initializers, mirroring the
// PoC structure to exercise ParserBase::UseThis on reparse of the enclosing
// closure scope.

function makeLazyCases() {
  // Sloppy-mode variant using a static field initializer.
  function lazy_static_sloppy() {
    let var_1;
    class C {
      static '' = new class {
        '' = var_1.trigger_error();
        [class { [this]; }];
      };
    }
  }

  // Strict-mode variant using a static field initializer (changes `this` value
  // semantics but still exercises UseThis in the parser).
  function lazy_static_strict() {
    'use strict';
    let var_1;
    class C {
      static '' = new class {
        '' = var_1.trigger_error();
        [class { [this]; }];
      };
    }
  }

  // Instance field initializer variant; requires instantiation to run the
  // initializer. Still places `this` in a nested computed name within class
  // element evaluation, under a function closure that gets reparsed.
  function lazy_instance_sloppy() {
    let var_1;
    class C {
      '' = new class {
        '' = var_1.trigger_error();
        [class { [this]; }];
      };
    }
    // Trigger the instance field initializer execution.
    new C();
  }

  // Strict-mode instance field variant.
  function lazy_instance_strict() {
    'use strict';
    let var_1;
    class C {
      '' = new class {
        '' = var_1.trigger_error();
        [class { [this]; }];
      };
    }
    new C();
  }

  return [
    lazy_static_sloppy,
    lazy_static_strict,
    lazy_instance_sloppy,
    lazy_instance_strict,
  ];
}

const lazyCases = makeLazyCases();

// Force full parse and execution; each is expected to throw (due to
// var_1.trigger_error()), but must not crash. Run each twice to exercise the
// path repeatedly.
for (const f of lazyCases) {
  assertThrows(f, "lazy case should throw but not crash (first run)");
  assertThrows(f, "lazy case should throw but not crash (second run)");
}

print("OK");
