template <class>
struct A {};

template <class T = int, class U = T>
using AA = A<U>;

AA a{};
