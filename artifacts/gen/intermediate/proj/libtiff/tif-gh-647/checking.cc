#include <tiffio.h>
#include <assert.h>
#include <stdio.h>

#define FILENAME "test_solitary_custom_directory.tif"

int main(void)
{
    /* Create a dummy file and set a field. */
    TIFF *tif = TIFFOpen(FILENAME, "w");
    assert(tif != NULL);
    TIFFSetField(tif, TIFFTAG_DOCUMENTNAME, "DocName");
    TIFFClose(tif);

    /* Open file without reading a directory using option "h".
     * This tests that TIFFSetField works with "h" option after fix. */
    tif = TIFFOpen(FILENAME, "r+h");
    assert(tif != NULL);
    /* TIFFSetField here would fail or cause SegFault before fix of issue 643. */
    assert(TIFFSetField(tif, TIFFTAG_DOCUMENTNAME, "DocName") != 0);
    TIFFClose(tif);

    /* Open and test reading with "rh" option. */
    tif = TIFFOpen(FILENAME, "rh");
    assert(tif != NULL);
    /* Reading operations should work with "h" option after fix. */
    TIFFClose(tif);

    unlink(FILENAME);
    return 0;
}
