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
  LocalPointer<Calendar> cal(
      Calendar::createInstance(Locale("en@calendar=chinese"), status), status);
  cal->setTime(
      2043071457431218011677338081118001787485161156097100985923226601036925437809699842362992455895409920480414647512899096575018732258582416938813614617757317338664031880042592085084690242819214720523061081124318514531466365480449329351434046537728.000000,
      status);
  cal->set(UCAL_EXTENDED_YEAR, -1594662558);
  cal->get(UCAL_YEAR, status);
  if (U_SUCCESS(status)) {
    std::cout << "Should return success" << std::endl;
  }

  cal->setTime(
      17000065021099877464213620139773683829419175940649608600213244013003611130029599692535053209683880603725167923910423116397083334648012657787978113960494455603744210944.000000,
      status);
  cal->add(UCAL_YEAR, 1935762034, status);
  if (U_FAILURE(status)) {
    std::cout << "Should return falure" << std::endl;
  }

  status = U_ZERO_ERROR;
  cal->set(UCAL_ERA, 1651667877);
  cal->add(UCAL_YEAR, 1935762034, status);
  if (U_FAILURE(status)) {
    std::cout << "Should return falure" << std::endl;
  }

  return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi