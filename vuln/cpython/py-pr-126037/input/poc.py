import xml.etree.ElementTree as ET

class EvilTag(str):
    def __eq__(self, other):
        base.clear()
        return False

base = ET.Element('a')
base.append(ET.Element(EvilTag('x')))
base.find('a')