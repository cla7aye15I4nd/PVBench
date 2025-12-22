typedef unsigned long uint64_t;
struct R {
  uint64_t args[3];
};
template <class... Ts>
void g(Ts... args) {
  R r{.args = {uint64_t(args)...}};
}
struct S {
  virtual void f() {
    g(0, nullptr);
  }
};
S s;