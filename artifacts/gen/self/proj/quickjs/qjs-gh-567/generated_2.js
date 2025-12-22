// QuickJS test for circular re-export fix in js_build_module_ns
// Patch summary:
// - In js_build_module_ns, when encountering an exported name whose
//   JSVarRef is NULL (which can happen in circular re-export scenarios),
//   QuickJS now throws a resolution error instead of dereferencing NULL
//   and crashing.
//
// Test strategy:
// 1) Create a circular module pair:
//      a.js imports { g } from b.js and exports function f
//      b.js re-exports { f } from a.js and also exports g
//    Building the module namespace for b.js should now reject with an error,
//    whereas previously it could crash. We verify using dynamic import,
//    which returns the module namespace and therefore triggers
//    js_build_module_ns for b.js.
// 2) Verify a non-circular re-export works correctly (control test).
// 3) Verify that a module that performs a star import (import * as ns)
//    from the circular module also rejects, since it also needs the
//    module namespace for b.js.
//
// Notes:
// - We do not assert the specific error type/message to avoid brittleness,
//   only that an exception is raised (the patch explicitly throws).
// - We use try/catch patterns to ensure no unexpected crashes.

import * as std from 'std';
import * as os from 'os';

function assert(cond, msg) {
    if (!cond) throw new Error(msg || 'Assertion failed');
}

function writeFile(path, content) {
    // Use std.open to write text content to a file
    const f = std.open(path, 'w');
    if (!f) throw new Error('Failed to open file for writing: ' + path);
    f.puts(content);
    f.close();
}

(async function main() {
    // Prepare a temporary directory for our test modules
    const dir = `mod_circ_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    try { os.mkdir(dir, 0o755); } catch (e) { /* ignore if exists */ }

    // --- Circular case modules ---
    const a_js = `import { g } from './b.js';\n\nexport function f() {\n  // use g so the import is live and the cycle is real\n  return g();\n}\n\nexport const y = 20;\n`;

    const b_js = `export { f } from './a.js';\nexport function g() { return 42; }\nexport const x = 10;\n`;

    // Module that performs a namespace import from the circular module
    const e_js = `import * as ns from './b.js';\n// Touch the namespace so it's definitely used at runtime\nexport const z = typeof ns.g;\n`;

    writeFile(`${dir}/a.js`, a_js);
    writeFile(`${dir}/b.js`, b_js);
    writeFile(`${dir}/e.js`, e_js);

    // --- Non-circular control modules ---
    const d_js = `export function h() { return 99; }\nexport const k = 5;\n`;
    const c_js = `export { h } from './d.js';\nexport const g = 1;\n`;
    writeFile(`${dir}/d.js`, d_js);
    writeFile(`${dir}/c.js`, c_js);

    // Helper to assert that an async function/rejected promise rejects
    async function expectReject(promise, label) {
        let rejected = false;
        try {
            await promise;
        } catch (e) {
            rejected = true;
        }
        assert(rejected, label + ' did not reject as expected');
    }

    // Test 1: dynamic import of circular re-export module should reject (no crash)
    await expectReject(import(`./${dir}/b.js`), 'Importing circular module b.js');

    // Test 2: non-circular re-export should succeed and provide correct bindings
    try {
        const m = await import(`./${dir}/c.js`);
        assert(typeof m.h === 'function', 'Non-circular re-export should expose function h');
        assert(m.g === 1, 'Non-circular module should export g === 1');
        const v = m.h();
        assert(v === 99, 'h() should return 99');
    } catch (e) {
        throw new Error('Unexpected error importing non-circular module c.js: ' + (e && e.message));
    }

    // Test 3: module that namespace-imports the circular module should also reject
    await expectReject(import(`./${dir}/e.js`), 'Importing module e.js that star-imports circular module b.js');

    print('OK');
})().catch((e) => {
    // Re-throw to fail the test if anything goes wrong
    throw e;
});
