#include "unicode/locid.h"
#include "unicode/listformatter.h"
#include "unicode/utypes.h"
#include <vector>
#include <assert.h>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    std::unique_ptr<ListFormatter> fmt(ListFormatter::createInstance("en", status));
    assert(U_SUCCESS(status));

    std::vector<UnicodeString> inputs;
    UnicodeString input(0xAAAFF00, 0x00000042, 0xAAAFF00);
    for (int32_t i = 0; i < 16; i++) {
        inputs.push_back(input);
    }

    FormattedList result = fmt->formatStringsToValue(inputs.data(), static_cast<int32_t>(inputs.size()), status);
    assert(status == U_INPUT_TOO_LONG_ERROR);  // Should produce error due to int32 overflow

    return 0;
}