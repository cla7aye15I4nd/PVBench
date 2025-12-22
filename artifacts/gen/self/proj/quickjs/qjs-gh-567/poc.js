// This test requires circular module imports between a.js and b.js
// The bug is triggered when building module namespace with circular exports
//
// Files:
// - a.js: imports from b.js and exports function f
// - b.js: imports f from a.js and re-exports it, also exports g
//
// Running b.js triggers the circular export handling in js_build_module_ns
// where var_ref can be NULL, causing a NULL pointer dereference

import {f} from "./a.js"
import {g} from "./b.js"

// If we reach here without crashing, the fix works
print("OK");
