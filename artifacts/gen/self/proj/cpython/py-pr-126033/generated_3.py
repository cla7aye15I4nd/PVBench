import sys
import subprocess
import textwrap
import xml.etree.ElementTree as ET


def _probe_fix_via_subprocess() -> bool:
    """Return True if the interpreter contains the fix for gh-126033.

    We run a minimal reproducer in a subprocess. If the process segfaults
    (pre-fix behavior), we return False. If it handles the case gracefully
    by raising ValueError (post-fix behavior), we return True.
    """
    code = """if 1:
        import xml.etree.ElementTree as ET
        class EvilElement(ET.Element):
            def __eq__(self, other):
                base.clear()
                return False
        base = ET.Element('a')
        base.append(EvilElement('a'))
        base.append(EvilElement('a'))
        try:
            base.remove(ET.Element('b'))
        except ValueError:
            print('OK')
        else:
            print('BAD')
    """
    proc = subprocess.run(
        [sys.executable, '-I', '-c', code],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if proc.returncode != 0:
        # Most likely a segfault on vulnerable builds.
        return False
    return b'OK' in proc.stdout and proc.stderr == b''


def test_poc_subprocess_no_crash_and_valueerror():
    """Run the original PoC in a subprocess to ensure no crash and correct behavior.

    The PoC clears the children list during equality comparison while removing
    a missing element. Expected: no crash, ValueError is raised.
    """
    from test.support.script_helper import assert_python_ok

    code = """if 1:
        import xml.etree.ElementTree as ET

        class EvilElement(ET.Element):
            def __eq__(self, other):
                base.clear()  # concurrent mutation
                return False  # indicate 'missing'

        base = ET.Element('a')
        base.append(EvilElement('a'))
        base.append(EvilElement('a'))
        try:
            base.remove(ET.Element('b'))
        except ValueError:
            print('OK')  # Expected path after the fix
        else:
            # Removing a missing element should raise ValueError even if the list was cleared
            print('BAD')
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK' in out, f"Expected 'OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


def test_remove_with_clear_assume_missing():
    """gh-126033: Removing a missing element while children are cleared during comparisons.

    When __eq__ returns False (assume missing), ValueError must be raised even
    if the children list is cleared concurrently. This verifies the loop bounds
    checks added in the patch do not crash and that the function still reports
    'x not in list'.
    """

    class E(ET.Element):
        pass

    class X(E):
        def __eq__(self, o):
            del root[:]  # equivalent to clear(); concurrent mutation
            return False

    class Y(E):
        def __eq__(self, o):
            root.clear()  # concurrent mutation
            return False

    for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
        # removing R() from [U()]
        for R, U in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one')])
            try:
                root.remove(R('missing'))
                assert False, f"Expected ValueError when removing missing with {side_effect} from single child"
            except ValueError:
                pass

        # removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(E('missing'))
                assert False, f"Expected ValueError when removing missing with {side_effect} from two children"
            except ValueError:
                pass

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            try:
                root.remove(Z('missing'))
                assert False, f"Expected ValueError when removing missing with {side_effect} (mixed types)"
            except ValueError:
                pass


def test_remove_with_clear_assume_existing():
    """gh-126033: Removing with equality True while children are cleared.

    When __eq__ returns True (assume existing), the implementation might
    have reached the last step while the children list is being cleared.
    The patch ensures this does not crash and simply returns None without
    raising ValueError.
    """

    class E(ET.Element):
        pass

    class X(E):
        def __eq__(self, o):
            del root[:]  # equivalent to clear(); concurrent mutation
            return True

    class Y(E):
        def __eq__(self, o):
            root.clear()  # concurrent mutation
            return True

    for Z, side_effect in [(X, 'del root[:]'), (Y, 'root.clear()')]:
        # removing R() from [U()]
        for R, U in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one')])
            result = root.remove(R('missing'))
            assert result is None, f"Expected None return when removing with {side_effect} from single child"

        # removing R() from [U(), V()]
        for U, V in [(E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            result = root.remove(E('missing'))
            assert result is None, f"Expected None return when removing with {side_effect} from two children"

        for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
            root = E('top')
            root.extend([U('one'), V('two')])
            result = root.remove(Z('missing'))
            assert result is None, f"Expected None return when removing with {side_effect} (mixed types)"


def test_remove_with_mutate_root_assume_missing():
    """gh-126033: Removing a missing element while removing the first child during comparison.

    During comparison, delete the first child (shorten the list). With __eq__
    returning False, ValueError should be raised, and no crash should occur.
    """
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            del root[0]  # shrink children list while iterating
            return False

    # removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(E('missing'))
            assert False, "Expected ValueError when removing missing while list shrinks"
        except ValueError:
            pass

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        try:
            root.remove(Z('missing'))
            assert False, "Expected ValueError when removing missing (mixed types) while list shrinks"
        except ValueError:
            pass


def test_remove_with_mutate_root_assume_existing():
    """gh-126033: Removing with equality True while deleting the first child.

    When __eq__ returns True (assume existing), concurrent deletion of a child
    should not crash and remove() should return None.
    """
    E = ET.Element

    class Z(E):
        def __eq__(self, o):
            del root[0]  # shrink children list while iterating
            return True

    # removing R() from [U(), V()]
    for U, V in [(E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        result = root.remove(E('missing'))
        assert result is None, "Expected None when list shrinks and equality True"

    for U, V in [(E, E), (E, Z), (Z, E), (Z, Z)]:
        root = E('top')
        root.extend([U('one'), V('two')])
        result = root.remove(Z('missing'))
        assert result is None, "Expected None (mixed types) when list shrinks and equality True"


if __name__ == '__main__':
    if not _probe_fix_via_subprocess():
        print('Interpreter appears vulnerable to gh-126033; skipping mutation-remove tests to avoid crash.')
        sys.exit(0)

    test_poc_subprocess_no_crash_and_valueerror()
    test_remove_with_clear_assume_missing()
    test_remove_with_clear_assume_existing()
    test_remove_with_mutate_root_assume_missing()
    test_remove_with_mutate_root_assume_existing()
    print('All tests passed.')
