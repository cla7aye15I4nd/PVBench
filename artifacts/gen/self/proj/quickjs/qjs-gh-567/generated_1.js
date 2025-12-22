// Generated test for QuickJS module circular export fix
// This test verifies the fix in js_build_module_ns that now throws a proper
// error when encountering a circular export during module namespace construction
// (instead of crashing due to a NULL JSVarRef).

'use strict';

function assert(cond, msg) {
    if (!cond) throw new Error(msg || 'Assertion failed');
}

async function main() {
    // Use QuickJS built-in std module to create the test modules on disk
    const std = await import('std');

    function writeFile(path, content) {
        const f = std.open(path, 'w');
        assert(!!f, 'Failed to open ' + path + ' for writing');
        f.puts(content);
        f.close();
    }

    // Create modules with circular dependencies:
    // - a.js imports {g} from b.js and exports function f
    // - b.js imports {f} from a.js, re-exports it, and also exports g
    // Building the module namespace for b.js should detect a circular export
    // and throw an exception (js_resolve_export_throw_error with CIRCULAR).

    const a_js = `
        import { g } from './b.js';
        export function f() {
            // touch g so b.js is actually linked/evaluated
            if (typeof g !== 'function') return 'f:' + String(g);
            return 'f';
        }
    `;

    const b_js = `
        import { f } from './a.js';
        export { f }; // re-export from a.js -> part of the circular dependency
        export function g() { return 'g'; }
    `;

    // c.js imports the namespace of b.js, which forces building b's namespace
    // and should therefore throw due to the circular re-export.
    const c_js = `
        import * as bns from './b.js';
        export const x = 42;
    `;

    writeFile('a.js', a_js);
    writeFile('b.js', b_js);
    writeFile('c.js', c_js);

    // Test 1: Directly importing b.js as a module namespace via dynamic import.
    // The resolved value of dynamic import is the module namespace object, so
    // constructing it must detect the circular export and throw. We assert that
    // the promise rejects with an Error and does not crash.
    let threwCircular = false;
    try {
        await import('./b.js');
    } catch (e) {
        threwCircular = true;
        // We don't rely on a specific error type/message, just that it's an Error.
        assert(e instanceof Error, 'Expected an Error for circular export, got: ' + e);
    }
    assert(threwCircular, 'Importing ./b.js must throw due to circular export when building namespace');

    // Test 2: Importing a.js should succeed because it does not require building
    // b.js namespace. It only imports a named binding from b.js, which is allowed
    // even in a cycle. Verify the export is available and callable.
    const a = await import('./a.js');
    assert(typeof a.f === 'function', 'a.f should be a function');
    const fr = a.f();
    assert(fr === 'f' || fr.startsWith('f:'), 'Unexpected return from a.f(): ' + fr);

    // Test 3: Static namespace import of b.js via another module (c.js). Linking
    // c.js should attempt to create the b.js namespace object and thus throw the
    // circular export error. Ensure it rejects and does not crash.
    let threwCircularStatic = false;
    try {
        await import('./c.js');
    } catch (e) {
        threwCircularStatic = true;
        assert(e instanceof Error, 'Expected an Error for circular export via static namespace import, got: ' + e);
    }
    assert(threwCircularStatic, 'Importing ./c.js must throw because it imports the namespace of b.js with a circular export');

    // If we reached here, the engine did not crash and behaved as expected
    print('OK');
}

main().catch(e => {
    // Surface unexpected errors
    throw e;
});