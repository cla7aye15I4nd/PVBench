struct foo { char a; int b; };
constexpr foo t{'a', 1};
constexpr auto [...m] = t;