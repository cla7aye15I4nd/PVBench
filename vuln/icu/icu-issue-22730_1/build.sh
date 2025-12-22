#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cstdlib>
#include <iostream>

using namespace icu;

int main() {
  UErrorCode status = U_ZERO_ERROR;
  LocalPointer<Calendar> calendar(
      Calendar::createInstance(Locale("en-u-ca-japanese"), status), status);
  calendar->clear();
  calendar->roll(UCAL_EXTENDED_YEAR, -1946156856, status);
  if (status == U_ILLEGAL_ARGUMENT_ERROR) {
    std::cout << "status return without overflow" << std::endl;
  }
  return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi