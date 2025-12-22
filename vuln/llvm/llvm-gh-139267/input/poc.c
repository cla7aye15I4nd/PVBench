void f(void) {
    #pragma omp unroll partial(a)
      for (int i = 0; i < 10; i++)
        ;
    }