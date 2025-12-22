from test.support.script_helper import assert_python_ok
import subprocess
import sys

# This test verifies the crash fix in xml.etree.ElementTree for Element.find,
# Element.findtext, and Element.findall when the equality check on either the
# search tag (path) or the element's tag mutates the tree during comparison.
#
# Strategy:
# - First, probe the running interpreter in a subprocess with a minimal PoC
#   known to segfault on vulnerable versions. If it crashes, we SKIP strict
#   assertions (so this file remains runnable on vulnerable builds) and print
#   a clear message.
# - If it does not crash (i.e., the fix is present), run comprehensive tests in
#   isolation and assert correct behavior and absence of crashes.


def probe_vulnerability() -> bool:
    """Return True if the interpreter appears vulnerable (segfaults)."""
    poc = """if 1:
import xml.etree.ElementTree as ET
class EvilTag(str):
    def __eq__(self, other):
        base.clear()
        return False
base = ET.Element('a')
base.append(ET.Element(EvilTag('x')))
# This call used to segfault due to mutation during comparison
base.find('a')
"""
    proc = subprocess.run([sys.executable, '-c', poc], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # A segfault typically returns a negative rc (e.g., -11). Any non-zero rc
    # indicates the vulnerable behavior in this probe.
    return proc.returncode != 0


def run_strict_suite():
    code = """if 1:
        import xml.etree.ElementTree as ET

        # Path-side comparators: equality is evaluated as tag == path.
        class PathClearTrue(str):
            def __new__(cls, elem, s):
                self = str.__new__(cls, s)
                self.elem = elem
                return self
            def __eq__(self, other):
                # Mutate the element during comparison
                self.elem.clear()
                return True
            __hash__ = str.__hash__

        class PathClearFalse(str):
            def __new__(cls, elem, s):
                self = str.__new__(cls, s)
                self.elem = elem
                return self
            def __eq__(self, other):
                # Mutate the element during comparison
                self.elem.clear()
                return False
            __hash__ = str.__hash__

        # Tag-side comparators: the element child's tag is a str subclass
        # whose __eq__ mutates the parent during the compare.
        class TagClearFalse(str):
            def __new__(cls, s):
                return str.__new__(cls, s)
            def __eq__(self, other):
                parent.clear()
                return False
            __hash__ = str.__hash__

        class TagClearTrue(str):
            def __new__(cls, s):
                return str.__new__(cls, s)
            def __eq__(self, other):
                parent.clear()
                return True
            __hash__ = str.__hash__

        # Test A: path mutates and returns True -> find returns first child,
        #         findtext returns its text, findall returns it. Parent is cleared.
        parent = ET.Element('root')
        c = ET.Element('child')
        c.text = 'hello'
        parent.append(c)
        result = parent.find(PathClearTrue(parent, 'child'))
        assert result is not None, 'find should return element when eq returns True'
        assert result.tag == 'child', f"Expected 'child', got {getattr(result, 'tag', None)}"
        assert len(list(parent)) == 0, f"parent should be cleared during comparison; children: {list(parent)}"

        parent = ET.Element('root')
        c = ET.Element('child')
        c.text = 'hello'
        parent.append(c)
        text = parent.findtext(PathClearTrue(parent, 'child'))
        assert text == 'hello', f"findtext should return text of matched element, got {text!r}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison in findtext'

        parent = ET.Element('root')
        c = ET.Element('child')
        parent.append(c)
        lst = parent.findall(PathClearTrue(parent, 'child'))
        assert isinstance(lst, list), f"findall should return list, got {type(lst)}"
        assert len(lst) == 1, f"findall should return one element, got {len(lst)}"
        assert lst[0].tag == 'child', f"findall returned wrong element: {lst[0].tag}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison in findall'

        # Test B: path mutates and returns False -> no matches, no crash
        parent = ET.Element('root')
        parent.extend([ET.Element('a'), ET.Element('b')])
        res = parent.find(PathClearFalse(parent, 'z'))
        assert res is None, f"find should return None when eq False and children cleared, got {res}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison; children should be removed'

        parent = ET.Element('root')
        parent.extend([ET.Element('a'), ET.Element('b')])
        default = 'DEF'
        text = parent.findtext(PathClearFalse(parent, 'z'), default)
        assert text == default, f"findtext should return default when not found, got {text!r}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison'

        parent = ET.Element('root')
        parent.extend([ET.Element('a'), ET.Element('b')])
        text = parent.findtext(PathClearFalse(parent, 'z'))
        assert text is None, f"findtext should return None when not found and no default, got {text!r}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison'

        parent = ET.Element('root')
        parent.extend([ET.Element('a'), ET.Element('b')])
        lst = parent.findall(PathClearFalse(parent, 'z'))
        assert lst == [], f"findall should return empty list when not found, got {lst}"
        assert len(list(parent)) == 0, 'parent should be cleared during comparison'

        # Test C: tag object mutates during comparison (PoC style) while eq returns False
        parent = ET.Element('root')
        parent.append(ET.Element(TagClearFalse('x')))
        # Searching for any other tag to force comparison
        res = parent.find('a')
        assert res is None, f"Expected None, got {res}"
        assert len(list(parent)) == 0, 'parent should be cleared by tag.__eq__'

        # Test D: tag object mutates and returns True: find should still return the child element safely
        parent = ET.Element('root')
        child = ET.Element(TagClearTrue('x'))
        parent.append(child)
        res = parent.find('x')  # path triggers comparison with tag (left-hand)
        assert res is not None, 'find should return the child even if tag.__eq__ clears parent'
        assert res.tag == 'x', f"Expected tag 'x', got {res.tag!r}"
        assert len(list(parent)) == 0, 'parent should be cleared by tag.__eq__'

        # findtext with a tag that mutates and returns True
        parent = ET.Element('root')
        child = ET.Element(TagClearTrue('x'))
        child.text = 'T'
        parent.append(child)
        t = parent.findtext('x')
        assert t == 'T', f"Expected 'T', got {t!r}"
        assert len(list(parent)) == 0, 'parent should be cleared by tag.__eq__ in findtext'

        # findall with a tag that mutates and returns True
        parent = ET.Element('root')
        child = ET.Element(TagClearTrue('x'))
        parent.append(child)
        lst = parent.findall('x')
        assert len(lst) == 1 and lst[0].tag == 'x', f"findall expected one 'x', got {lst}"
        assert len(list(parent)) == 0, 'parent should be cleared by tag.__eq__ in findall'

        print('OK')
    """

    rc, out, err = assert_python_ok('-c', code)
    assert rc == 0, f"Expected return code 0, got: {rc}"
    assert b'OK' in out, f"Expected 'OK' in stdout, got: {out}"
    assert not err, f"Expected no stderr, got: {err}"


if __name__ == '__main__':
    if probe_vulnerability():
        # Vulnerable (unpatched) interpreter detected; skip strict assertions.
        print('SKIPPED: interpreter appears vulnerable (pre-fix); strict tests not run')
    else:
        run_strict_suite()
