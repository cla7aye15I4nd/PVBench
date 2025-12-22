#include <tiffio.h>

int main(int argc, char** argv)
{
    TIFF* tif = TIFFOpen(argv[1], "rh");
    TIFFReadGPSDirectory(tif, 4);
    TIFFClose(tif);
    return 0;
}