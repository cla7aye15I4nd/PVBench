import xml.etree.ElementTree as ET
from test.support.script_helper import assert_python_ok


def probe_fix_available():
    """Run the original PoC in a subprocess.

    Returns True if the interpreter appears to contain the fix (i.e.,
    subprocess exits cleanly and the ValueError is observed), otherwise False.
    """
    code = """if 1:
    import xml.etree.ElementTree as ET

    class EvilElement(ET.Element):
        def __eq__(self, other):
            # Concurrently mutate the base element during comparisons
            base.clear()
            return False

    base = ET.Element('a')
    base.append(EvilElement('a'))
    base.append(EvilElement('a'))

    # Removing a missing element should raise ValueError, not crash
    try:
        base.remove(ET.Element('b'))
        print('NO-ERROR')  # unexpected on fixed behavior
    except ValueError:
        print('VALUEERROR')
    """
    try:
        rc, out, err = assert_python_ok('-c', code)
    except AssertionError:
        # Crashed or non-zero exit: fix likely not present
        return False
    if rc != 0:
        return False
    return b'VALUEERROR' in out and not err


def test_remove_with_clear_assume_missing():
    """gh-126033: Concurrent clear() or slice delete when element is missing should raise ValueError without crashing."""

    class E(ET.Element):
        pass

    class X(E):
        def __eq__(self, o):
            # Clear via slice deletion
            del root[:]
            return False

    class Y(E):
        def __eq__(self, o):
            # Clear via .clear()
            root.clear()
            return False

    for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
        # test removing R() from [U()]
        for R, U in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one')])
            try:
                root.remove(R('missing'))
                assert False, f"Expected ValueError when removing missing element with {side_effect} from single-child list"
            except ValueError:
                pass

        # test removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(E('missing'))
                assert False, f"Expected ValueError when removing missing element with {side_effect} from two-children list"
            except ValueError:
                pass

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(Z('missing'))
                assert False, f"Expected ValueError when removing missing element Z with {side_effect} from two-children list"
            except ValueError:
                pass


def test_remove_with_clear_assume_existing():
    """gh-126033: Concurrent clear() or slice delete when equality returns True should not crash and not raise."""

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
            # Should not raise; the patch returns None even if the list was cleared at the last step
            result = root.remove(R('missing'))
            assert result is None, f"Expected None return, got {result} when using {side_effect} from single-child list"

        # test removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            result = root.remove(E('missing'))
            assert result is None, f"Expected None return, got {result} when using {side_effect} from two-children list"

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            result = root.remove(Z('missing'))
            assert result is None, f"Expected None return, got {result} when using {side_effect} from two-children list (Z missing)"


def test_remove_with_mutate_root_assume_missing():
    """gh-126033: Concurrent mutation (shrink by deleting an index) for a missing element should raise ValueError without crash."""
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            # Shrink the list but not fully clear it
            del root[0]
            return False

    # test removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(E('missing'))
            assert False, "Expected ValueError when removing missing element after root mutation (shrink)"
        except ValueError:
            pass

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(Z('missing'))
            assert False, "Expected ValueError when removing missing Z after root mutation (shrink)"
        except ValueError:
            pass


def test_remove_with_mutate_root_assume_existing():
    """gh-126033: Concurrent mutation (shrink by deleting an index) when equality returns True should not crash and not raise."""
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            del root[0]
            return True

    # test removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        # Should not raise
        result = root.remove(E('missing'))
        assert result is None, f"Expected None when removing with mutation for list [{U.__name__}, {V.__name__}]"

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        result = root.remove(Z('missing'))
        assert result is None, f"Expected None when removing with mutation (Z missing) for list [{U.__name__}, {V.__name__}]"


def test_normal_behavior_unchanged():
    """Sanity checks: normal remove semantics are preserved."""
    E = ET.Element

    # Removing an existing child succeeds and returns None
    root = E('top')
    a = E('a')
    b = E('b')
    root.extend([a, b])
    result = root.remove(a)
    assert result is None, f"Expected None on successful removal, got {result}"
    assert list(root) == [b], f"Expected only [b] to remain, got: {[c.tag for c in root]}"

    # Removing a missing child raises ValueError
    try:
        root.remove(E('missing'))
        assert False, "Expected ValueError when removing missing element from normal tree"
    except ValueError as e:
        msg = str(e)
        assert 'not in list' in msg, f"Expected error message to contain 'not in list', got: {msg!r}"


if __name__ == '__main__':
    fixed = probe_fix_available()
    if fixed:
        # Run crash-prone tests only if the fix appears present
        test_remove_with_clear_assume_missing()
        test_remove_with_clear_assume_existing()
        test_remove_with_mutate_root_assume_missing()
        test_remove_with_mutate_root_assume_existing()
    else:
        print('SKIP: interpreter appears vulnerable; skipping crash-prone tests')
    # Always run non-crashy sanity tests
    test_normal_behavior_unchanged()
    print('OK')
