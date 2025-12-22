#!/bin/bash
./autogen.sh
./configure --prefix=$PWD/install
make -j$(nproc)
make install

cat<<EOF > poc.c
#include <tiffio.h>

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <stdint.h>

int main(int argc, char** argv) {
	if (argc < 2) {
		printf("Usage: %s <file>\n", argv[0]);
		return 1;
	}

	TIFF* tif = TIFFOpen(argv[1], "rh");
	if (tif == 0) return 1;
	TIFFReadGPSDirectory(tif, 4);
	TIFFClose(tif);
	return 0;
}
EOF

if [ -z "$CC" ]; then
    clang  -I./install/include -L./install/lib -Wl,-rpath=$PWD/install/lib -ltiff -lz -ljpeg -llzma -o poc-647 poc.c
else
    $CC $CFLAGS -I./install/include -L./install/lib -Wl,-rpath=$PWD/install/lib -ltiff -lz -ljpeg -llzma -o poc-647 poc.c
fi

test -f poc-647
