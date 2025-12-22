#include <tiffio.h>
#include <cassert>

int main(int argc, char** argv)
{
    TIFF* tif = TIFFOpen(argv[1], "rh");
    assert(tif != NULL);
    int ret_TIFFReadGPSDirectory = TIFFReadGPSDirectory(tif, 4);
    assert(ret_TIFFReadGPSDirectory == 1);
    TIFFClose(tif);
    return 0;
}