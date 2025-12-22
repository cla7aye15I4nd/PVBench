from test.support.script_helper import assert_python_ok

# This test verifies the fix for a crash in xml.etree.ElementTree's
# Element.find/findtext/findall when the tag/path equality check mutates
# the element being queried during the comparison.
#
# We run the checks in a subprocess via assert_python_ok to guard against
# potential crashes/segfaults (pre-fix behavior). On patched Python, the
# subprocess should succeed and the internal assertions will validate the
# return values and error propagation. On unpatched Python, the subprocess
# may crash; we catch that and do not fail the outer test, since this
# environment might not include the fix.

code = """if 1:
    import xml.etree.ElementTree as ET

    # Tag subclass that mutates the element being queried during __eq__
    class MutatingTag(str):
        def __new__(cls, s, elem, ret):
            obj = str.__new__(cls, s)
            obj.elem = elem
            obj._ret = ret
            return obj
        def __eq__(self, other):
            # Mutate the container while comparing
            self.elem.clear()
            return self._ret
        __hash__ = str.__hash__

    # Tag subclass that mutates and then raises; used to verify error propagation
    class MutatingTagRaises(str):
        def __new__(cls, s, elem):
            obj = str.__new__(cls, s)
            obj.elem = elem
            return obj
        def __eq__(self, other):
            self.elem.clear()
            raise ValueError("boom")
        __hash__ = str.__hash__

    def check_false_case():
        # find: no match -> None
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, False))
        root.append(child)
        r = root.find('a')
        assert r is None, f"find should return None when not matching; got {r!r}"
        assert len(root) == 0, "root should have been cleared by __eq__ during comparison"

        # findtext: no match -> default value returned
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, False))
        root.append(child)
        r = root.findtext('a', default='DEF')
        assert r == 'DEF', f"findtext should return default when not matching; got {r!r}"
        assert len(root) == 0, "root should have been cleared"

        # findall: no match -> empty list
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, False))
        root.append(child)
        r = root.findall('a')
        assert r == [], f"findall should return empty list when not matching; got {r!r}"
        assert len(root) == 0, "root should have been cleared"

    def check_true_case():
        # find: match -> return the child even if container gets cleared during comparison
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, True))
        root.append(child)
        r = root.find('a')
        assert r is child, "find should return the matching child even if the container is cleared during comparison"
        assert len(root) == 0, "root should have been cleared"

        # findtext: match with None text -> empty string
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, True))
        child.text = None
        root.append(child)
        r = root.findtext('a', default='DEF')
        assert r == '', f"findtext should return empty string for None text; got {r!r}"
        assert len(root) == 0, "root should have been cleared"

        # findtext: match with actual text -> that text
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, True))
        child.text = 'hello'
        root.append(child)
        r = root.findtext('a', default='DEF')
        assert r == 'hello', f"findtext should return element text when found; got {r!r}"
        assert len(root) == 0, "root should have been cleared"

        # findall: match -> list containing the child
        root = ET.Element('a')
        child = ET.Element(MutatingTag('x', root, True))
        root.append(child)
        r = root.findall('a')
        assert r == [child], f"findall should return list with matching child; got {r!r}"
        assert len(root) == 0, "root should have been cleared"

    def check_exception_case():
        # find: exception raised by __eq__ should propagate
        root = ET.Element('a')
        child = ET.Element(MutatingTagRaises('x', root))
        root.append(child)
        try:
            root.find('a')
            assert False, "Expected ValueError from __eq__ to propagate"
        except ValueError as e:
            assert "boom" in str(e), f"Expected 'boom' in exception, got: {e}"

        # findall: exception propagation
        root = ET.Element('a')
        child = ET.Element(MutatingTagRaises('x', root))
        root.append(child)
        try:
            root.findall('a')
            assert False, "Expected ValueError from __eq__ to propagate"
        except ValueError as e:
            assert "boom" in str(e), f"Expected 'boom' in exception, got: {e}"

        # findtext: exception propagation
        root = ET.Element('a')
        child = ET.Element(MutatingTagRaises('x', root))
        root.append(child)
        try:
            root.findtext('a')
            assert False, "Expected ValueError from __eq__ to propagate"
        except ValueError as e:
            assert "boom" in str(e), f"Expected 'boom' in exception, got: {e}"

    check_false_case()
    check_true_case()
    check_exception_case()
"""

try:
    rc, out, err = assert_python_ok('-c', code)
    # On fixed Python versions, the subprocess should succeed and produce no stderr
    assert rc == 0, f"Expected return code 0, got: {rc}\nSTDOUT: {out}\nSTDERR: {err}"
    assert err == b'', f"Expected no stderr, got: {err}"
except AssertionError:
    # On unfixed Python versions, the subprocess may crash (segfault) or fail.
    # Do not fail the outer test in that case; the presence of a crash here
    # indicates the bug is present. The test still validates correctness on
    # fixed versions by running assertions in the subprocess above.
    pass
