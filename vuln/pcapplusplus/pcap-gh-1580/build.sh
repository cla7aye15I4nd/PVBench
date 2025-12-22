#!/bin/bash -eu
cmake -S . -B build --install-prefix=$PWD/install -DBUILD_SHARED_LIBS=ON
cmake --build build --parallel 16
cmake --install build

cat <<EOF > poc.cpp
#include <iostream>
#include <fstream>
#include <cstring>
#include "Packet.h"

int getFileLength(const char* filename)
{
    std::ifstream infile(filename, std::ifstream::binary);
    if (!infile)
        return -1;
    infile.seekg(0, infile.end);
    int length = infile.tellg();
    infile.close();
    return length;
}

uint8_t* readFileIntoBuffer(const char* filename, int& bufferLength)
{
    int fileLength = getFileLength(filename);
    if (fileLength == -1)
        return nullptr;

    std::ifstream infile(filename);
    if (!infile)
        return nullptr;

    bufferLength = fileLength / 2 + 2;
    uint8_t* result = new uint8_t[bufferLength];
    int i = 0;
    while (!infile.eof())
    {
        char byte[3];
        memset(byte, 0, 3);
        infile.read(byte, 2);
        result[i] = (uint8_t)strtol(byte, nullptr, 16);
        i++;
    }
    infile.close();
    bufferLength -= 2;
    return result;
}

#define READ_FILE_INTO_BUFFER(num, filename)                                                                           \
	int bufferLength##num = 0;                                                                                         \
	uint8_t* buffer##num = readFileIntoBuffer(filename, bufferLength##num);                                

#define READ_FILE_AND_CREATE_PACKET(num, filename)                                                                     \
	READ_FILE_INTO_BUFFER(num, filename);                                                                              \
	pcpp::RawPacket rawPacket##num(static_cast<const uint8_t*>(buffer##num), bufferLength##num, time, true)

int main(int argc, char* argv[]) {
    timeval time;
	gettimeofday(&time, nullptr);

	READ_FILE_AND_CREATE_PACKET(0, "Tests/Packet++Test/PacketExamples/TcpPacketWithOptions3.dat");
	pcpp::Packet packet0(&rawPacket0, pcpp::OsiModelPhysicalLayer);
	packet0.getLastLayer();
    packet0.getFirstLayer();

	READ_FILE_AND_CREATE_PACKET(1, "Tests/Packet++Test/PacketExamples/TcpPacketWithOptions3.dat");
	pcpp::Packet packet1(&rawPacket1, pcpp::OsiModelTransportLayer);
	packet1.getLastLayer()->getOsiModelLayer();

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    $CXX $CXXFLAGS -I install/include/pcapplusplus -L install/lib -lPcap++ -lCommon++ -lPacket++ -Wl,-rpath=install/lib -o poc poc.cpp
fi