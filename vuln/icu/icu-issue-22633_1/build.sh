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
      Calendar::createInstance(Locale("en"), status), status);
  if (U_FAILURE(status)) {
    std::cout << "Calendar::createInstance failed" << std::endl;
    return 1;
  }
  for (int32_t i = 0; i < UCAL_FIELD_COUNT; i++) {
    status = U_ZERO_ERROR;
    calendar->setTime(0, status);
    calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX / 2, status);
    calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX, status);
    if ((i == UCAL_ERA) || (i == UCAL_YEAR) || (i == UCAL_YEAR_WOY) ||
        (i == UCAL_EXTENDED_YEAR) || (i == UCAL_IS_LEAP_MONTH) ||
        (i == UCAL_MONTH) || (i == UCAL_ORDINAL_MONTH) ||
        (i == UCAL_ZONE_OFFSET) || (i == UCAL_DST_OFFSET)) {
      if (U_FAILURE(status)) {
        std::cout << "add INT32_MAX should fail" << std::endl;
      }
    } else {
      if (U_SUCCESS(status)) {
        std::cout << "add INT32_MAX should still success" << std::endl;
      }
    }

    status = U_ZERO_ERROR;
    calendar->setTime(0, status);
    calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN / 2, status);
    calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN, status);
    if ((i == UCAL_YEAR) || (i == UCAL_YEAR_WOY) || (i == UCAL_EXTENDED_YEAR) ||
        (i == UCAL_IS_LEAP_MONTH) || (i == UCAL_ZONE_OFFSET) ||
        (i == UCAL_DST_OFFSET)) {
      if (U_FAILURE(status)) {
        std::cout << "add INT32_MIN should fail" << std::endl;
      }
    } else {
      if (U_SUCCESS(status)) {
        std::cout << "add INT32_MIN should still success" << std::endl;
      }
    }
  }
  return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi