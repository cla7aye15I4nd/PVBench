#include <fstream>
#include <cstring>
#include <cassert>
#include <cstdlib>
#include <sys/time.h>
#include "Packet.h"

int getFileLength(const char* filename)
{
    std::ifstream infile(filename, std::ifstream::binary);
    if (!infile)
        return -1;
    infile.seekg(0, infile.end);
    // Stream should be in good state after seek
    assert(infile.good());
    int length = static_cast<int>(infile.tellg());
    // File length should be non-negative
    assert(length >= 0);
    infile.close();
    return length;
}

uint8_t* readFileIntoBuffer(const char* filename, int& bufferLength)
{
    int fileLength = getFileLength(filename);
    // Expecting success: file should exist and be readable
    assert(fileLength != -1);
    if (fileLength == -1)
        return nullptr;

    std::ifstream infile(filename);
    // Expecting success: the file stream should be valid
    assert(infile);
    if (!infile)
        return nullptr;

    bufferLength = fileLength / 2 + 2;
    uint8_t* result = new uint8_t[bufferLength];
    assert(result != nullptr);
    int i = 0;
    while (!infile.eof())
    {
        char byte[3];
        memset(byte, 0, 3);
        infile.read(byte, 2);
        // Ensure we don't write past the allocated buffer
        assert(i < bufferLength);
        result[i] = (uint8_t)strtol(byte, nullptr, 16);
        i++;
    }
    // Ensure we didn't exceed the allocated capacity
    assert(i <= bufferLength);
    infile.close();
    bufferLength -= 2;
    // After adjusting, buffer length should remain positive
    assert(bufferLength > 0);
    return result;
}

#define READ_FILE_INTO_BUFFER(num, filename) \
    int bufferLength##num = 0; \
    uint8_t* buffer##num = readFileIntoBuffer(filename, bufferLength##num);

#define READ_FILE_AND_CREATE_PACKET(num, filename) \
    READ_FILE_INTO_BUFFER(num, filename); \
    assert(buffer##num != nullptr); \
    assert(bufferLength##num > 0); \
    pcpp::RawPacket rawPacket##num(static_cast<const uint8_t*>(buffer##num), bufferLength##num, time, true)

int main(int argc, char* argv[])
{
    timeval time;
    int tvRet = gettimeofday(&time, nullptr);
    assert(tvRet == 0);

    READ_FILE_AND_CREATE_PACKET(1, "Tests/Packet++Test/PacketExamples/TcpPacketWithOptions3.dat");
    pcpp::Packet packet1(&rawPacket1, pcpp::OsiModelTransportLayer);

    // Validate that the packet was parsed and has at least one layer
    pcpp::Layer* lastLayer = packet1.getLastLayer();
    assert(lastLayer != nullptr);

    // Semantic checks on the last layer's data
    uint8_t* layerData = lastLayer->getData();
    size_t layerLen = lastLayer->getDataLen();
    assert(layerData != nullptr);
    assert(layerLen > 0);

    // Access the OSI model layer to ensure method works; value existence already ensured by lastLayer
    (void)lastLayer->getOsiModelLayer();

    return 0;
}
