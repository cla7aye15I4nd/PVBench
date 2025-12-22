void f(void) {
    #pragma omp tile sizes(a)
      for (int i = 0; i < 10; i++)
        ;
    }