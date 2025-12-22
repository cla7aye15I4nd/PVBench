#include <fstream>
#include <cstring>
#include <cassert>
#include "Packet.h"

int getFileLength(const char* filename)
{
    std::ifstream infile(filename, std::ifstream::binary);
    if (!infile)
        return -1;
    infile.seekg(0, infile.end);
    int length = infile.tellg();
    // Expect a non-negative file length when file is opened successfully
    assert(length >= 0);
    infile.close();
    return length;
}

uint8_t* readFileIntoBuffer(const char* filename, int& bufferLength)
{
    int fileLength = getFileLength(filename);
    // Expect success reading file length
    assert(fileLength != -1);
    if (fileLength == -1)
        return nullptr;

    std::ifstream infile(filename);
    // Expect the file to open successfully
    assert(!!infile);
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
    infile.close();
    bufferLength -= 2;
    // After reading, buffer length should be positive
    assert(bufferLength > 0);
    return result;
}

#define READ_FILE_INTO_BUFFER(num, filename) \
    int bufferLength##num = 0; \
    uint8_t* buffer##num = readFileIntoBuffer(filename, bufferLength##num); \
    assert(buffer##num != nullptr); \
    assert(bufferLength##num > 0)

#define READ_FILE_AND_CREATE_PACKET(num, filename) \
    READ_FILE_INTO_BUFFER(num, filename); \
    pcpp::RawPacket rawPacket##num(static_cast<const uint8_t*>(buffer##num), bufferLength##num, time, true)

int main(int argc, char* argv[])
{
    timeval time;
    gettimeofday(&time, nullptr);

    READ_FILE_AND_CREATE_PACKET(1, "Tests/Packet++Test/PacketExamples/TcpPacketWithOptions3.dat");
    pcpp::Packet packet1(&rawPacket1, pcpp::OsiModelTransportLayer);

    // Verify that the packet has layers
    pcpp::Layer* firstLayer = packet1.getFirstLayer();
    assert(firstLayer != nullptr);
    assert(firstLayer->getData() != nullptr);
    size_t firstLen = firstLayer->getDataLen();
    assert(firstLen > 0);
    assert(firstLen <= static_cast<size_t>(bufferLength1));

    pcpp::Layer* lastLayer = packet1.getLastLayer();
    assert(lastLayer != nullptr);
    assert(lastLayer->getData() != nullptr);
    size_t lastLen = lastLayer->getDataLen();
    assert(lastLen > 0);

    // Ensure we can query OSI model layer successfully
    auto lastOsi = lastLayer->getOsiModelLayer();
    (void)lastOsi; // silence unused warning while still invoking the API

    // Recompute fields and ensure layer data remains valid
    packet1.computeCalculateFields();
    assert(lastLayer->getData() != nullptr);
    assert(lastLayer->getDataLen() > 0);

    return 0;
}