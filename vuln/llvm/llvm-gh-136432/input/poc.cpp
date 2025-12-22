namespace std
{
    template<typename _Functor, typename _ArgTypes>
    struct invoke_result
    { 
        using type = decltype(_Functor()(_ArgTypes()));
    };

    template<typename _Fn, typename _Args>
    using invoke_result_t = typename invoke_result<_Fn, _Args>::type;
}

template<typename T1, typename T2>
struct eee {
    int b() const { return 5; }
};

template<typename T, typename E>
auto append(const eee<T, E>& val)
{
    return [val]<template<typename,typename> class TExpectedOut>(const TExpectedOut<int, int>& tuple)
    {
        return 5;
    };
}
eee<int, int> CreateEOS(int arg) { return {}; }

void flash()
{
    auto apply = []<typename TError>(const eee<int, TError>& tuple) {
         append(CreateEOS(tuple.b()))(tuple);
    };
    std::invoke_result_t<decltype(apply), eee<int, int>>* f;
}
