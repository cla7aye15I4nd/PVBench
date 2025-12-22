void f(void) {
    #pragma omp simd collapse(a)
      for (int i = 0; i < 10; i++)
        ;
    }