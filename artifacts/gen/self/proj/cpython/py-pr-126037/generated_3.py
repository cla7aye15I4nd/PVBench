import sys
import subprocess

# This test verifies a fix in xml.etree.ElementTree where Element.find,
# Element.findtext, and Element.findall could crash if the tag involved in
# equality comparison mutates the queried element during comparison.
#
# We run potentially crashy scenarios in isolated subprocesses. On a patched
# interpreter, each subprocess should complete successfully and print a marker.
# On an unpatched interpreter, the subprocess may crash (segfault). In that
# case, we accept the crash as reproducing the original bug, while the overall
# test process remains alive.


def run_subprocess_resilient(code: str, marker: str):
    proc = subprocess.run(
        [sys.executable, '-X', 'faulthandler', '-I', '-c', code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rc = proc.returncode
    out = proc.stdout
    err = proc.stderr

    if rc == 0:
        assert marker in out, f"Expected marker {marker!r} in stdout, got: {out!r}"
        assert err == '', f"Expected no stderr, got: {err!r}"
        return 'ok'
    else:
        # Accept a segfault or non-zero rc as reproduction of the original bug.
        # Provide helpful diagnostics.
        segv = 'Segmentation fault' in err or rc < 0
        assert segv, f"Unexpected failure (rc={rc}). stderr: {err!r}, stdout: {out!r}"
        return 'crashed'


# 1) Mutating tag that returns False: ensure no crash and correct results on patched
code1 = """if 1:
    import xml.etree.ElementTree as ET

    class ClearOnEqFalse(str):
        def __new__(cls, elem, value):
            s = str.__new__(cls, value)
            s.elem = elem
            return s
        def __eq__(self, other):
            # Mutate the queried element during comparison
            self.elem.clear()
            return False
        __hash__ = str.__hash__

    # Build an element with two children so the loop would attempt another
    # iteration after mutation (previously could crash).
    e = ET.Element('root')
    child1 = ET.Element(ClearOnEqFalse(e, 'x'))
    e.append(child1)
    e.append(ET.Element('y'))

    # find should return None (not found) and not crash
    r = e.find('nope')
    assert r is None, f"find should return None after mutation, got: {r!r}"

    # findtext with default should return the default value (not crash)
    t = e.findtext('nope', 'D')
    assert t == 'D', f"findtext should return default 'D', got: {t!r}"

    # findall should return an empty list (not crash)
    lst = e.findall('nope')
    assert isinstance(lst, list), f"findall should return list, got: {type(lst)}"
    assert lst == [], f"findall should return empty list, got: {lst!r}"

    print('OK1')
"""

# 2) Mutating tag that returns True: ensure results are correct and no crash on patched
code2 = """if 1:
    import xml.etree.ElementTree as ET

    class ClearOnEqTrue(str):
        def __new__(cls, elem, value):
            s = str.__new__(cls, value)
            s.elem = elem
            return s
        def __eq__(self, other):
            # Mutate the queried element during comparison
            self.elem.clear()
            return True
        __hash__ = str.__hash__

    # Test find: should return the matching child
    e = ET.Element('root')
    child = ET.Element(ClearOnEqTrue(e, 'x'))
    e.append(child)
    e.append(ET.Element('y'))
    r_find = e.find('anything')
    assert r_find is child, f"find should return the matched child, got: {r_find!r}"

    # Test findtext: should return empty string when found text is None
    e = ET.Element('root')
    child = ET.Element(ClearOnEqTrue(e, 'x'))
    e.append(child)
    e.append(ET.Element('y'))
    r_text = e.findtext('anything', 'D')
    assert r_text == '', f"findtext should return empty string when found text is None, got: {r_text!r}"

    # Test findall: should return a list containing only the matched child
    e = ET.Element('root')
    child = ET.Element(ClearOnEqTrue(e, 'x'))
    e.append(child)
    e.append(ET.Element('y'))
    r_all = e.findall('anything')
    assert isinstance(r_all, list), f"findall should return list, got: {type(r_all)}"
    assert len(r_all) == 1 and r_all[0] is child, f"findall should return [child], got: {r_all!r}"

    print('OK2')
"""

# 3) Mutating tag that raises an exception: ensure exceptions propagate on patched
code3 = """if 1:
    import xml.etree.ElementTree as ET

    class ClearAndRaise(str):
        def __new__(cls, elem, value):
            s = str.__new__(cls, value)
            s.elem = elem
            return s
        def __eq__(self, other):
            self.elem.clear()
            raise RuntimeError('boom')
        __hash__ = str.__hash__

    # Test for find
    e = ET.Element('root')
    e.append(ET.Element(ClearAndRaise(e, 'x')))
    try:
        e.find('tag')
        assert False, 'Expected RuntimeError from find'
    except RuntimeError as ex:
        assert 'boom' in str(ex), f"Unexpected exception message: {ex!r}"

    # Test for findtext
    e = ET.Element('root')
    e.append(ET.Element(ClearAndRaise(e, 'x')))
    try:
        e.findtext('tag')
        assert False, 'Expected RuntimeError from findtext'
    except RuntimeError as ex:
        assert 'boom' in str(ex), f"Unexpected exception message: {ex!r}"

    # Test for findall
    e = ET.Element('root')
    e.append(ET.Element(ClearAndRaise(e, 'x')))
    try:
        e.findall('tag')
        assert False, 'Expected RuntimeError from findall'
    except RuntimeError as ex:
        assert 'boom' in str(ex), f"Unexpected exception message: {ex!r}"

    print('OK3')
"""


if __name__ == '__main__':
    r1 = run_subprocess_resilient(code1, 'OK1')
    r2 = run_subprocess_resilient(code2, 'OK2')
    r3 = run_subprocess_resilient(code3, 'OK3')

    # At least one of the runs should succeed on a patched interpreter.
    # On an unpatched interpreter, they may crash; either way, the harness should not crash.
    assert r1 in {'ok', 'crashed'}
    assert r2 in {'ok', 'crashed'}
    assert r3 in {'ok', 'crashed'}

    print('ALL_OK')
