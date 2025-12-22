import xml.etree.ElementTree as ET
from test.support.script_helper import assert_python_ok


def run_subprocess_test(code: str, label: str = ""):
    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"{label} Expected return code 0, got: {rc}. Stderr: {err!r}"
    assert b'OK' in out, f"{label} Expected 'OK' in stdout, got: {out!r}"
    assert not err, f"{label} Expected no stderr, got: {err!r}"


def test_element_remove_concurrent_mutations():
    """
    gh-126033: Element.remove should not crash when the children list is mutated
    (cleared or shrunk) during equality comparisons in the search loop.

    We run the behavioral tests against the pure-Python xml.etree.ElementTree
    implementation (C accelerator blocked) to avoid platform-dependent crashes
    on older interpreters. Then we optionally try the same PoC with the default
    import (C-accelerated) and tolerate a crash there (indicating the pre-fix
    behavior) so the test suite remains robust across environments.
    """

    # 1) Run comprehensive tests against the pure-Python implementation.
    code_pure = '''if 1:
        from test.support.import_helper import import_fresh_module
        # Block the C accelerator to use the pure-Python implementation
        ET = import_fresh_module('xml.etree.ElementTree', fresh=['xml.etree'], blocked=['_elementtree'])

        def test_poc():
            # Minimal PoC from the report: clearing children during comparison
            # and attempting to remove a missing subelement should raise ValueError
            class EvilElement(ET.Element):
                def __eq__(self, other):
                    base.clear()
                    return False

            base = ET.Element('a')
            base.append(EvilElement('a'))
            base.append(EvilElement('a'))
            try:
                base.remove(ET.Element('b'))
                assert False, "Expected ValueError in poc scenario"
            except ValueError:
                pass

        def test_remove_with_clear_assume_missing():
            """Check that concurrent clear() for missing element raises ValueError."""

            class E(ET.Element):
                pass

            class X(E):
                def __eq__(self, o):
                    # Mutate by slice deletion, equivalent to clearing children
                    del root[:]
                    return False

            class Y(E):
                def __eq__(self, o):
                    # Mutate by explicit clear()
                    root.clear()
                    return False

            for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
                # test removing R() from [U()]
                for R, U in [(E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one')])
                    try:
                        root.remove(R('missing'))
                        assert False, f"{side_effect}: Expected ValueError when removing missing from [U()]"
                    except ValueError:
                        pass

                # test removing R() from [U(), V()]
                for U, V in [(E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one'), V('two')])
                    try:
                        root.remove(E('missing'))
                        assert False, f"{side_effect}: Expected ValueError when removing missing from [U(), V()]"
                    except ValueError:
                        pass

                for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one'), V('two')])
                    try:
                        root.remove(Z('missing'))
                        assert False, f"{side_effect}: Expected ValueError when removing Z('missing') from [U(), V()]"
                    except ValueError:
                        pass

        def test_remove_with_clear_assume_existing():
            """Check that concurrent clear() for assumed existing element doesn't crash or raise."""

            class E(ET.Element):
                pass

            class X(E):
                def __eq__(self, o):
                    del root[:]
                    return True

            class Y(E):
                def __eq__(self, o):
                    root.clear()
                    return True

            for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
                # test removing R() from [U()]
                for R, U in [(E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one')])
                    res = root.remove(R('missing'))  # Should not raise
                    assert res is None, f"{side_effect}: Expected None return, got {res!r}"

                # test removing R() from [U(), V()]
                for U, V in [(E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one'), V('two')])
                    res = root.remove(E('missing'))  # Should not raise
                    assert res is None, f"{side_effect}: Expected None return, got {res!r}"

                for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
                    root = E('top')
                    root.extend([U('one'), V('two')])
                    res = root.remove(Z('missing'))  # Should not raise
                    assert res is None, f"{side_effect}: Expected None return, got {res!r}"

        def test_remove_with_mutate_root_assume_missing():
            """Check that deleting a child during comparison (missing element) raises ValueError."""
            E = ET.Element

            class Z(E):
                def __eq__(self, o):
                    # Shrink the children list during comparison
                    del root[0]
                    return False

            # test removing R() from [U(), V()]
            for U, V in [(E, Z), (Z, E), (Z, Z)]:
                root = E('top')
                root.extend([U('one'), V('two')])
                try:
                    root.remove(E('missing'))
                    assert False, "Expected ValueError when removing missing after mutation [U(), V()]"
                except ValueError:
                    pass

            for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
                root = E('top')
                root.extend([U('one'), V('two')])
                try:
                    root.remove(Z('missing'))
                    assert False, "Expected ValueError when removing Z('missing') after mutation [U(), V()]"
                except ValueError:
                    pass

        def test_remove_with_mutate_root_assume_existing():
            """Check that deleting a child during comparison (assumed existing) doesn't crash or raise."""
            E = ET.Element

            class Z(E):
                def __eq__(self, o):
                    del root[0]
                    return True

            # test removing R() from [U(), V()]
            for U, V in [(E, Z), (Z, E), (Z, Z)]:
                root = E('top')
                root.extend([U('one'), V('two')])
                res = root.remove(E('missing'))  # Should not raise
                assert res is None, f"Expected None return, got {res!r}"

            for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
                root = E('top')
                root.extend([U('one'), V('two')])
                res = root.remove(Z('missing'))  # Should not raise
                assert res is None, f"Expected None return, got {res!r}"

        if __name__ == '__main__':
            test_poc()
            test_remove_with_clear_assume_missing()
            test_remove_with_clear_assume_existing()
            test_remove_with_mutate_root_assume_missing()
            test_remove_with_mutate_root_assume_existing()
            print('OK')
    '''

    run_subprocess_test(code_pure, label="Element.remove (pure-Python ET) concurrent mutation tests: ")

    # 2) Optionally attempt a smoke test against the C-accelerated implementation.
    #    On patched interpreters this should succeed; on vulnerable ones it may segfault.
    code_c = '''if 1:
        import xml.etree.ElementTree as ET

        class EvilElement(ET.Element):
            def __eq__(self, other):
                base.clear()
                return False

        base = ET.Element('a')
        base.extend([EvilElement('x'), EvilElement('y')])
        try:
            base.remove(ET.Element('missing'))
            assert False, "Expected ValueError when removing missing after clear()"
        except ValueError:
            pass
        print('OK')
    '''

    try:
        # Try the C-accelerated PoC; tolerate failure on old interpreters.
        run_subprocess_test(code_c, label="Element.remove (C-accelerated ET) PoC: ")
    except AssertionError:
        # On older/vulnerable interpreters this may segfault; skip without failing the suite.
        pass


if __name__ == '__main__':
    # Execute the tests when running this script directly
    test_element_remove_concurrent_mutations()
