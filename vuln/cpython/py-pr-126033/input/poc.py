import xml.etree.ElementTree as ET

class EvilElement(ET.Element):
    def __eq__(self, other):
        base.clear()
        return False

base = ET.Element('a')
base.append(EvilElement('a'))
base.append(EvilElement('a'))
base.remove(ET.Element('b'))