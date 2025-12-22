#include "GtpLayer.h"
#include <cassert>

int main()
{
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
        new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));

    assert(gtpLayer != nullptr);

    gtpLayer->getHeader()->messageType = 0xFF;

    auto ext = gtpLayer->addExtension(0x85, 0x1234);
    assert(!ext.isNull());  // Should successfully add extension

    return 0;
}
