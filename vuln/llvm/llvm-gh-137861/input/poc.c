#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
int main(){
__attribute__ ((deprecated))
int my_val = 5;
const char* my_string = "Hello, World!\n";
__attribute__((aligned(64)))
#pragma clang attribute push(__attribute__((cleanup(cleanup1))))
{
char* p = malloc(100);
free(p);
 }
#pragma clang attribute pop
}