// Copyright 2024 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This test verifies a parser fix in ParserBase::UseThis where the is_reparsed
// check must be performed on the closure scope rather than the current scope.
// The original bug could cause crashes during parsing when encountering `this`
// inside complex class field/computed-name constructs that are reparsed.
//
// The tests below ensure that such patterns:
//  - do not crash the engine,
//  - evaluate to the expected runtime exceptions (from the intentional code),
//  - cover multiple contexts (function body, arrow function, parameter default)
//    where reparsing and `this` usage are relevant.

function assertThrows(fn, errorConstructor, messageIncludes) {
  let threw = false;
  try {
    fn();
  } catch (e) {
    threw = true;
    if (errorConstructor && !(e instanceof errorConstructor)) {
      throw new Error("Wrong exception type: expected " + errorConstructor.name + ", got " + e);
    }
    if (messageIncludes && ("" + e).indexOf(messageIncludes) === -1) {
      throw new Error("Exception message does not include '" + messageIncludes + "': " + e);
    }
  }
  if (!threw) throw new Error("Expected exception was not raised");
}

// ---------------------
// Original PoC: should not crash; runtime throws (TypeError) due to
// calling a property on undefined. This exercises `this` usage inside a
// computed class field name within a static class field initializer.
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

assertThrows(var_5, TypeError);

// ---------------------
// Variant A: Arrow function context to exercise lexical `this`. The
// initializer throws a custom Error we can match, verifying evaluation order
// without crashes.
function test_arrow_context(){
  let var_1 = {
    trigger_error() { throw new Error("inner"); }
  };
  const arrow = () => {
    class var_3 {
      static '' = new class {
        '' = var_1.trigger_error();
        [class { [this]; }];
      };
    }
  };
  arrow();
}
assertThrows(test_arrow_context, Error, "inner");

// ---------------------
// Variant B: Default parameter initializer. This is a classic reparsing-affected
// context in V8. The default parameter expression evaluates a class with the
// same nested structure. It references `var_1` which is declared in the body,
// hence not visible in the parameter scope. This should deterministically throw
// ReferenceError (and not crash during parsing/reparsing), while still containing
// a `this` usage inside a class computed property name.
function test_param_default_reference_error() {
  function f(a = (class {
    static '' = new class {
      '' = var_1.trigger_error();
      [class { [this]; }];
    };
  })) {
    let var_1 = { trigger_error() { return 0; } };
  }
  f();
}
assertThrows(test_param_default_reference_error, ReferenceError);

print("OK");
