// Generated test for QuickJS fix: handle circular exports when building module namespace
// The patch changes js_build_module_ns to detect a NULL var_ref for normal exported names
// (which can occur with circular re-exports) and throw a circular-resolution error instead
// of dereferencing NULL and crashing.
//
// This test:
// 1) Creates a circular module pair (a.js <-> b.js) where b re-exports a's `f` and a imports b's `g`.
//    Building the namespace for b (via dynamic import or star import) should now throw instead of crash.
// 2) Verifies that a non-circular re-export builds a namespace successfully and exported bindings work.
//
// Note: This file is a module and uses the built-in 'os' module to write auxiliary module files.

import * as os from 'os';

function assert(condition, message) {
    if (!condition) {
        throw new Error(message || 'Assertion failed');
    }
}

function writeFile(path, content) {
    os.writeFile(path, content);
}

async function testCircularDynamicImportRejects() {
    // Prepare circular modules:
    // a.js imports g from b.js and exports f
    // b.js re-exports f from a.js and exports g
    // Building the namespace of b.js should detect a circular export resolution and throw.
    writeFile('a.js', [
        "import { g } from './b.js';", // create cycle but do not use g at evaluation time
        "export function f() { return 'A.f'; }",
        ''
    ].join('\n'));

    writeFile('b.js', [
        "export { f } from './a.js';", // re-export creates the problematic exported name
        "export function g() { return 'B.g'; }",
        ''
    ].join('\n'));

    // Dynamic import returns the module namespace object; building it should now throw
    let threw = false;
    try {
        await import('./b.js');
    } catch (e) {
        threw = true;
        // We only assert that an exception was thrown (the fix), not the exact error text/type
        // to avoid depending on implementation details.
    }
    assert(threw, 'Expected dynamic import("./b.js") to reject due to circular re-export, but it resolved');
}

async function testCircularStarImportRejects() {
    // Create a module that statically imports the namespace of b.js.
    // Building b.js namespace should also detect the circular export and throw.
    writeFile('c.js', [
        "import * as B from './b.js';",
        "export const z = 1;",
        ''
    ].join('\n'));

    let threw = false;
    try {
        await import('./c.js');
    } catch (e) {
        threw = true;
    }
    assert(threw, 'Expected importing module with star import from circular module to reject');
}

async function testNonCircularNamespaceSucceeds() {
    // Prepare non-circular modules with a re-export; building namespace should succeed.
    writeFile('e.js', [
        "export function f() { return 123; }",
        ''
    ].join('\n'));

    writeFile('f.js', [
        "export { f } from './e.js';",
        "export function g() { return 456; }",
        ''
    ].join('\n'));

    // Direct namespace build via dynamic import
    const ns = await import('./f.js');
    assert(typeof ns.f === 'function', 'Expected ns.f to be a function');
    assert(typeof ns.g === 'function', 'Expected ns.g to be a function');
    assert(ns.f() === 123, 'Expected ns.f() to return 123');
    assert(ns.g() === 456, 'Expected ns.g() to return 456');

    // Namespace import from an importer module should also succeed
    writeFile('h.js', [
        "import * as F from './f.js';",
        "export const ok = (typeof F.f === 'function') && (typeof F.g === 'function') && F.f() === 123 && F.g() === 456;",
        ''
    ].join('\n'));
    const nh = await import('./h.js');
    assert(nh.ok === true, 'Expected star import namespace bindings to be available and callable');
}

async function main() {
    // Ensure a clean slate if previous runs left files behind
    try { os.remove('a.js'); } catch (_) {}
    try { os.remove('b.js'); } catch (_) {}
    try { os.remove('c.js'); } catch (_) {}
    try { os.remove('e.js'); } catch (_) {}
    try { os.remove('f.js'); } catch (_) {}
    try { os.remove('h.js'); } catch (_) {}

    await testCircularDynamicImportRejects();
    await testCircularStarImportRejects();
    await testNonCircularNamespaceSucceeds();

    // Cleanup (best effort)
    try { os.remove('a.js'); } catch (_) {}
    try { os.remove('b.js'); } catch (_) {}
    try { os.remove('c.js'); } catch (_) {}
    try { os.remove('e.js'); } catch (_) {}
    try { os.remove('f.js'); } catch (_) {}
    try { os.remove('h.js'); } catch (_) {}

    print('OK');
}

main().catch(e => {
    // Surface any unexpected error clearly
    print('Test failed:', e && e.stack || String(e));
    throw e;
});