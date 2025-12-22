#!/bin/bash -eu

/samtools/samtools view \
    -T /testcases/htslib-gh-2063/poc_data/GRCh38_reference_genome_trunc.fa \
    -F 3840 -M \
    -L /testcases/htslib-gh-2063/poc_data/test.bed.trunc  \
    /testcases/htslib-gh-2063/poc_data/HG00113.trunc.cram