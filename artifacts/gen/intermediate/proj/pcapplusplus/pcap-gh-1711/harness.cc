#include "GtpLayer.h"

int main()
{
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
        new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));
    gtpLayer->getHeader()->messageType = 0xFF;
    gtpLayer->addExtension(0x85, 0x1234);
    return 0;
}