#include <fstream>
#include <cstring>
#include <cassert>
#include <sys/time.h>
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
    assert(result != nullptr);
    int i = 0;
    while (!infile.eof())
    {
        char byte[3];
        memset(byte, 0, 3);
        infile.read(byte, 2);
        assert(i < bufferLength); // prevent overflow; buffer has +2 slack
        result[i] = (uint8_t)strtol(byte, nullptr, 16);
        i++;
    }
    infile.close();
    bufferLength -= 2; // account for eof loop extra iteration
    assert(bufferLength > 0);
    return result;
}

#define READ_FILE_INTO_BUFFER(num, filename) \
    int bufferLength##num = 0; \
    uint8_t* buffer##num = readFileIntoBuffer(filename, bufferLength##num);

#define READ_FILE_AND_CREATE_PACKET(num, filename) \
    READ_FILE_INTO_BUFFER(num, filename); \
    pcpp::RawPacket rawPacket##num(static_cast<const uint8_t*>(buffer##num), bufferLength##num, time, true)

int main(int argc, char* argv[])
{
    timeval time;
    gettimeofday(&time, nullptr);

    READ_FILE_AND_CREATE_PACKET(1, "Tests/Packet++Test/PacketExamples/TcpPacketWithOptions3.dat");

    // Validate buffer read
    assert(buffer1 != nullptr);
    assert(bufferLength1 > 0);

    // RawPacket invariants
    assert(rawPacket1.getRawData() != nullptr);
    assert(rawPacket1.getRawDataLen() == bufferLength1);

    pcpp::Packet packet1(&rawPacket1, pcpp::OsiModelTransportLayer);

    // Packet constructed successfully with associated raw packet
    assert(packet1.getRawPacket() != nullptr);
    assert(packet1.getRawPacket() == &rawPacket1);

    // Layers must exist and have valid data
    pcpp::Layer* firstLayer = packet1.getFirstLayer();
    assert(firstLayer != nullptr);
    assert(firstLayer->getData() != nullptr);
    assert(firstLayer->getDataLen() > 0);

    pcpp::Layer* lastLayer = packet1.getLastLayer();
    assert(lastLayer != nullptr);
    assert(lastLayer->getData() != nullptr);
    assert(lastLayer->getDataLen() > 0);

    // Accessing OSI model layer should be valid for an existing layer
    auto osiLayer = lastLayer->getOsiModelLayer();
    (void)osiLayer; // ensure the call is made; value existence implies success

    return 0;
}
