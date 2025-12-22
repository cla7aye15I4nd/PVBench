import xml.etree.ElementTree as ET

class MutationClearElementPath(str):
    def __new__(cls, elem, *args):
        self = str.__new__(cls, *args)
        self.elem = elem
        return self

    def __eq__(self, o):
        self.elem.clear()
        return True

    __hash__ = str.__hash__

# Test find with mutating
e = ET.Element('foo')
e.extend([ET.Element('bar')])
e.find(MutationClearElementPath(e, 'x'))

# Test findtext with mutating
e = ET.Element('foo')
e.extend([ET.Element('bar')])
e.findtext(MutationClearElementPath(e, 'x'))

# Test findall with mutating
e = ET.Element('foo')
e.extend([ET.Element('bar')])
e.findall(MutationClearElementPath(e, 'x'))

# If we reach here without crash, the test passes
assert True
