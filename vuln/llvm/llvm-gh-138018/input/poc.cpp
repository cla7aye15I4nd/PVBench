struct foo { };

template <typename T>
struct vec { };

auto structure_to_typelist(const auto& s) noexcept {
  return []<template <typename...> typename T, typename... Args>(T<Args...>) {
    return 0;
  }(vec<int>{});
}

template <typename T>
using helper2 = decltype(structure_to_typelist(T{}));
auto tl_ok2 = helper2<foo>{};
